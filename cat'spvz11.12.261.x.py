import math
import random
import sys
import pygame
from array import array

# --- CONFIG & CONSTANTS ---
WIDTH, HEIGHT = 900, 600
FPS = 60
SHOVEL_X = 730
TITLE = "Cat's PvZ 0.1.a | Replanted-style"

GRID_X, GRID_Y = 220, 100
CELL_W, CELL_H = 72, 90
ROWS, COLS = 5, 9

pygame.init()
MUSIC_VOLUME = 0.4
_wave_surf_cache = None
_music_ready = False
_music_muted = False
_music_channel = None
_music_sound = None


def build_original_ost():
    """Create an original, looping garden-defense tune in memory; no audio files."""
    rate = 22050
    bpm = 120
    beat = 60.0 / bpm
    notes = [64, 67, 71, 67, 62, 66, 69, 66,
             60, 64, 67, 64, 62, 65, 69, 65]
    bass = [40, 40, 43, 43, 36, 36, 41, 41]
    duration = len(notes) * beat
    pcm = array('h')
    for i in range(int(rate * duration)):
        t = i / rate
        step = min(int(t / beat), len(notes) - 1)
        local = (t % beat) / beat
        midi = notes[step]
        freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        bass_note = bass[min(int(t / (2 * beat)), len(bass) - 1)]
        bass_freq = 440.0 * (2.0 ** ((bass_note - 69) / 12.0))
        env = min(1.0, local * 12.0) * (1.0 - 0.55 * local)
        lead = (math.sin(2 * math.pi * freq * t) +
                0.18 * math.sin(2 * math.pi * freq * 2 * t)) * env
        low = 0.35 * math.sin(2 * math.pi * bass_freq * t)
        pulse = 0.11 * math.sin(2 * math.pi * 110 * t) * math.exp(-25 * (t % beat))
        sample = max(-1.0, min(1.0, 0.23 * lead + 0.27 * low + pulse))
        pcm.append(int(sample * 32767))
    return pygame.mixer.Sound(buffer=pcm.tobytes())


def start_music():
    global _music_ready, _music_channel, _music_sound
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        _music_sound = build_original_ost()
        _music_channel = _music_sound.play(loops=-1)
        if _music_channel is None:
            raise pygame.error("No mixer channel available")
        _music_channel.set_volume(MUSIC_VOLUME)
        _music_ready = True
    except (pygame.error, OSError, ValueError) as exc:
        _music_ready = False
        print(f"Music unavailable (game continues silently): {exc}")


def sync_music_for_scene(scene):
    """Keep the main menu silent; honor the player's M-key preference in-game."""
    if _music_ready and _music_channel is not None:
        if scene == "MENU" or _music_muted:
            _music_channel.pause()
        else:
            _music_channel.unpause()


def toggle_music():
    global _music_muted
    _music_muted = not _music_muted
    # The scene-aware update below also keeps the main menu silent.

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

font_sm = pygame.font.SysFont("Segoe UI", 15, bold=True)
font_md = pygame.font.SysFont("Segoe UI", 22, bold=True)
font_lg = pygame.font.SysFont("Segoe UI", 54, bold=True)
font_tiny = pygame.font.SysFont("Segoe UI", 12, bold=True)
PACKET_X, PACKET_STEP, PACKET_W, PACKET_Y, PACKET_H = 123, 66, 62, 9, 73

# --- PLANT CATALOG (Pure PvZ — No Cat Theme) ---
CATALOG = [
    {"id": "sunflower", "name": "Sunflower", "cost": 50, "cd": 300, "hp": 300, "color": (255, 215, 0)},
    {"id": "peashooter", "name": "Peashooter", "cost": 100, "cd": 300, "hp": 300, "color": (60, 200, 60)},
    {"id": "snowpea", "name": "Snow Pea", "cost": 175, "cd": 360, "hp": 300, "color": (70, 200, 255)},
    {"id": "wallnut", "name": "Wall-nut", "cost": 50, "cd": 900, "hp": 3600, "color": (165, 115, 55)},
    {"id": "cherrybomb", "name": "Cherry Bomb", "cost": 150, "cd": 1200, "hp": 9999, "color": (220, 30, 45)},
    {"id": "repeater", "name": "Repeater", "cost": 200, "cd": 420, "hp": 300, "color": (30, 170, 40)},
    {"id": "tallnut", "name": "Tall-nut", "cost": 125, "cd": 1200, "hp": 7000, "color": (135, 90, 50)},
    {"id": "puffshroom", "name": "Puff-shroom", "cost": 0, "cd": 450, "hp": 300, "color": (175, 130, 220)},
    {"id": "potatomine", "name": "Potato Mine", "cost": 25, "cd": 900, "hp": 300, "color": (150, 105, 60)},
]


class Sun:
    def __init__(self, x, y, target_y, from_sky=True):
        self.x = float(x)
        self.y = float(y)
        self.target_y = float(target_y)
        self.from_sky = from_sky
        self.vy = 1.6 if from_sky else -3.5
        self.vx = 0.0 if from_sky else random.uniform(-1.2, 1.2)
        self.timer = 600  # 10s @ 60 FPS
        self.collected = False
        self.t = random.uniform(0, 6.28)

    def update(self):
        self.t += 0.1
        if self.collected:
            dx, dy = 52 - self.x, 42 - self.y
            dist = math.hypot(dx, dy)
            if dist < 14:
                return False
            self.x += (dx / dist) * 18.0
            self.y += (dy / dist) * 18.0
            return True

        if self.from_sky:
            if self.y < self.target_y:
                self.y += self.vy
        else:
            if self.y < self.target_y or self.vy < 0:
                self.x += self.vx
                self.y += self.vy
                self.vy += 0.22
        self.timer -= 1
        return self.timer > 0

    def draw(self, surf):
        r = 18 + math.sin(self.t) * 2
        for i in range(10):
            ang = self.t * 0.4 + i * (math.pi / 5)
            px = self.x + math.cos(ang) * (r + 6)
            py = self.y + math.sin(ang) * (r + 6)
            pygame.draw.circle(surf, (255, 240, 90), (int(px), int(py)), 5)
        pygame.draw.circle(surf, (255, 200, 0), (int(self.x), int(self.y)), int(r))
        pygame.draw.circle(surf, (255, 250, 180), (int(self.x), int(self.y)), int(r - 5))


class Pea:
    def __init__(self, x, y, row, slow=False):
        self.x = float(x)
        self.y = float(y)
        self.row = row
        self.slow = slow
        self.speed = 6.5
        self.dmg = 20

    def update(self):
        self.x += self.speed
        return self.x < WIDTH + 30

    def draw(self, surf):
        c = (90, 220, 255) if self.slow else (100, 235, 65)
        pygame.draw.circle(surf, (20, 60, 20), (int(self.x), int(self.y)), 9)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), 7)
        pygame.draw.circle(surf, (220, 255, 220), (int(self.x - 2), int(self.y - 2)), 2)


class Plant:
    def __init__(self, row, col, spec):
        self.row = row
        self.col = col
        self.id = spec["id"]
        self.hp = spec["hp"]
        self.max_hp = spec["hp"]
        self.x = GRID_X + col * CELL_W + CELL_W // 2
        self.y = GRID_Y + row * CELL_H + CELL_H // 2
        self.timer = 0 if spec["id"] == "cherrybomb" else random.randint(20, 60)
        self.t = random.uniform(0, 6.28)

    def update(self, game):
        self.t += 0.08
        self.timer += 1
        if self.id == "sunflower":
            if self.timer >= 720:  # 12s sun cycle
                self.timer = 0
                game.suns.append(Sun(self.x, self.y - 10, self.y + 18, from_sky=False))
        elif self.id in ("peashooter", "snowpea", "repeater", "puffshroom"):
            if self.timer >= 85:
                if any(z.row == self.row and z.x > self.x - 10 and (self.id != "puffshroom" or 0 < z.x - self.x < 260) for z in game.zombies):
                    self.timer = 0
                    game.peas.append(Pea(self.x + 18, self.y - 12, self.row, slow=(self.id == "snowpea")))
                    if self.id == "repeater":
                        game.peas.append(Pea(self.x + 2, self.y - 12, self.row))
        elif self.id == "potatomine":
            if self.timer >= 300 and any(z.row == self.row and abs(z.x-self.x)<32 for z in game.zombies):
                for z in game.zombies:
                    if abs(z.row-self.row)<=1 and abs(z.x-self.x)<95: z.hp -= 1800
                game.explosions.append([self.x,self.y,28])
                self.hp=0
        elif self.id == "cherrybomb":
            if self.timer >= 50:
                for z in game.zombies:
                    if abs(z.row - self.row) <= 1 and abs(z.x - self.x) <= CELL_W * 1.8:
                        z.hp -= 1800
                game.explosions.append([self.x, self.y, 28])
                self.hp = 0

    def draw(self, surf):
        bob = math.sin(self.t) * 2.5
        cx, cy = int(self.x), int(self.y + bob)
        pygame.draw.ellipse(surf, (25, 75, 25), (self.x - 22, self.y + 24, 44, 14))

        if self.id == "sunflower":
            pygame.draw.line(surf, (40, 150, 40), (self.x, self.y + 28), (cx, cy), 6)
            for i in range(12):
                ang = i * (math.pi / 6) + self.t * 0.15
                px = cx + math.cos(ang) * 20
                py = cy - 8 + math.sin(ang) * 20
                pygame.draw.circle(surf, (255, 215, 0), (int(px), int(py)), 7)
            pygame.draw.circle(surf, (110, 65, 20), (cx, cy - 8), 14)
            pygame.draw.circle(surf, (25, 15, 5), (cx - 5, cy - 11), 2)
            pygame.draw.circle(surf, (25, 15, 5), (cx + 5, cy - 11), 2)

        elif self.id in ("peashooter", "snowpea", "repeater", "puffshroom"):
            c = (75, 195, 255) if self.id == "snowpea" else ((170, 130, 215) if self.id == "puffshroom" else (65, 200, 60))
            pygame.draw.line(surf, (35, 140, 35), (self.x, self.y + 28), (cx, cy), 6)
            pygame.draw.circle(surf, c, (cx - 3, cy - 10), 16)
            pygame.draw.rect(surf, c, (cx + 2, cy - 19, 20, 14), border_radius=4)
            pygame.draw.circle(surf, (20, 50, 20), (cx + 20, cy - 12), 5)
            pygame.draw.circle(surf, (20, 20, 20), (cx + 1, cy - 15), 3)

        elif self.id in ("wallnut", "tallnut"):
            if self.id == "tallnut": cy -= 9
            pygame.draw.ellipse(surf, (165, 115, 55), (cx - 21, cy - 26, 42, 54))
            pygame.draw.ellipse(surf, (110, 75, 30), (cx - 21, cy - 26, 42, 54), 3)
            pygame.draw.circle(surf, (255, 255, 255), (cx - 7, cy - 6), 5)
            pygame.draw.circle(surf, (255, 255, 255), (cx + 7, cy - 6), 5)
            pygame.draw.circle(surf, (20, 20, 20), (cx - 6, cy - 6), 2)
            pygame.draw.circle(surf, (20, 20, 20), (cx + 8, cy - 6), 2)
            if self.hp < self.max_hp * 0.65:
                pygame.draw.line(surf, (70, 45, 15), (cx - 12, cy - 18), (cx - 3, cy - 8), 2)
            if self.hp < self.max_hp * 0.33:
                pygame.draw.line(surf, (70, 45, 15), (cx + 12, cy + 2), (cx + 2, cy + 14), 2)

        elif self.id == "potatomine":
            pygame.draw.ellipse(surf,(140,95,45),(cx-19,cy+2,38,25))
            pygame.draw.circle(surf,(255,255,255),(cx-6,cy+8),4)
            pygame.draw.circle(surf,(255,255,255),(cx+7,cy+8),4)
        elif self.id == "cherrybomb":
            scale = 1.0 + (self.timer / 50.0) * 0.35
            r = int(15 * scale)
            pygame.draw.line(surf, (50, 160, 40), (cx - 12, cy + 4), (cx, cy - 22), 3)
            pygame.draw.line(surf, (50, 160, 40), (cx + 12, cy + 4), (cx, cy - 22), 3)
            pygame.draw.circle(surf, (220, 25, 40), (cx - 12, cy + 6), r)
            pygame.draw.circle(surf, (220, 25, 40), (cx + 12, cy + 6), r)


class Zombie:
    def __init__(self, row, ztype="normal"):
        self.row = row
        self.ztype = ztype
        self.x = float(WIDTH + random.randint(15, 70))
        self.y = float(GRID_Y + row * CELL_H + CELL_H // 2)
        if ztype == "normal":
            self.hp = 200
            self.base_speed = 0.36
        elif ztype == "cone":
            self.hp = 560
            self.base_speed = 0.36
        else:  # bucket
            self.hp = 1100
            self.base_speed = 0.34
        self.max_hp = self.hp
        self.slow_timer = 0
        self.t = random.uniform(0, 6.28)
        self.eating = False

    def update(self, game):
        self.t += 0.08
        if self.slow_timer > 0:
            self.slow_timer -= 1
        mult = 0.5 if self.slow_timer > 0 else 1.0
        self.eating = False

        for p in game.plants:
            if p.row == self.row and abs(self.x - p.x) < 26:
                self.eating = True
                p.hp -= 2.0 * mult
                break

        if not self.eating:
            self.x -= self.base_speed * mult

    def draw(self, surf):
        bob = math.sin(self.t * (2.2 if self.eating else 1.0)) * 2.5
        zx, zy = int(self.x), int(self.y + bob)
        skin = (100, 165, 225) if self.slow_timer > 0 else (130, 165, 115)
        coat = (60, 80, 115) if self.slow_timer > 0 else (90, 70, 55)

        pygame.draw.ellipse(surf, (25, 65, 25), (self.x - 18, self.y + 26, 36, 12))
        pygame.draw.line(surf, (45, 55, 80), (zx - 5, zy + 10), (zx - 7, zy + 28), 5)
        pygame.draw.line(surf, (45, 55, 80), (zx + 5, zy + 10), (zx + 7, zy + 28), 5)
        pygame.draw.rect(surf, coat, (zx - 11, zy - 14, 22, 26), border_radius=4)
        pygame.draw.line(surf, (200, 35, 35), (zx, zy - 12), (zx - 2, zy + 4), 3)

        arm_y = zy - 6 + (math.sin(self.t * 4) * 4 if self.eating else 0)
        pygame.draw.line(surf, coat, (zx - 4, zy - 8), (zx - 22, int(arm_y)), 5)
        pygame.draw.circle(surf, skin, (zx, zy - 26), 14)
        pygame.draw.circle(surf, (255, 255, 210), (zx - 5, zy - 28), 4)
        pygame.draw.circle(surf, (20, 20, 20), (zx - 6, zy - 28), 2)

        if self.ztype == "cone" and self.hp > 200:
            pygame.draw.polygon(surf, (240, 125, 20), [(zx - 13, zy - 36), (zx + 13, zy - 36), (zx, zy - 62)])
        elif self.ztype == "bucket" and self.hp > 200:
            pygame.draw.rect(surf, (165, 175, 185), (zx - 13, zy - 54, 26, 20), border_radius=2)
            pygame.draw.rect(surf, (110, 120, 130), (zx - 13, zy - 54, 26, 20), 2, border_radius=2)


class LawnMower:
    def __init__(self, row):
        self.row = row
        self.x = float(GRID_X - 38)
        self.y = float(GRID_Y + row * CELL_H + CELL_H // 2 + 8)
        self.triggered = False
        self.active = True

    def update(self, game):
        if not self.active:
            return
        if not self.triggered:
            for z in game.zombies:
                if z.row == self.row and z.x < self.x + 26:
                    self.triggered = True
                    break
        else:
            self.x += 9.0
            for z in game.zombies:
                if z.row == self.row and abs(z.x - self.x) < 32:
                    z.hp = -999
            if self.x > WIDTH + 50:
                self.active = False

    def draw(self, surf):
        if not self.active:
            return
        mx, my = int(self.x), int(self.y)
        pygame.draw.rect(surf, (215, 35, 35), (mx - 18, my - 14, 36, 20), border_radius=5)
        pygame.draw.line(surf, (180, 180, 180), (mx - 14, my - 14), (mx - 24, my - 28), 3)
        pygame.draw.circle(surf, (35, 35, 35), (mx - 10, my + 8), 7)
        pygame.draw.circle(surf, (35, 35, 35), (mx + 10, my + 8), 7)


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sun = 150
        self.plants = []
        self.zombies = []
        self.peas = []
        self.suns = []
        self.explosions = []
        self.mowers = [LawnMower(r) for r in range(ROWS)]
        self.cooldowns = {c["id"]: 0 for c in CATALOG}
        self.selected = 0
        self.shovel = False
        self.sky_timer = 180
        self.spawn_timer = 260
        self.ticks = 0
        self.max_ticks = 60 * 120  # 2-minute stage wave
        self.huge_wave_banner = 0
        self.state = "PLAY"  # PLAY, WIN, LOSE

    def update(self):
        if self.state != "PLAY":
            return

        self.ticks += 1
        for k in self.cooldowns:
            if self.cooldowns[k] > 0:
                self.cooldowns[k] -= 1

        if self.huge_wave_banner > 0:
            self.huge_wave_banner -= 1

        self.sky_timer -= 1
        if self.sky_timer <= 0:
            self.sky_timer = 450
            sx = random.randint(GRID_X + 30, GRID_X + COLS * CELL_W - 30)
            sy = random.randint(GRID_Y + 40, GRID_Y + ROWS * CELL_H - 30)
            self.suns.append(Sun(sx, 85, sy, from_sky=True))

        # Zombie wave logic ("The zombies are coming" @ [00:01:05])
        if self.ticks < self.max_ticks:
            self.spawn_timer -= 1
            if self.ticks in (2400, 5400):
                self.huge_wave_banner = 150
                for _ in range(7):
                    zt = random.choice(["normal", "cone", "bucket"])
                    self.zombies.append(Zombie(random.randint(0, ROWS - 1), zt))
            elif self.spawn_timer <= 0:
                progress = self.ticks / self.max_ticks
                self.spawn_timer = int(max(110, 420 - progress * 280))
                r = random.randint(0, ROWS - 1)
                pool = ["normal"] * 5
                if progress > 0.25:
                    pool += ["cone"] * 3
                if progress > 0.55:
                    pool += ["bucket"] * 2
                self.zombies.append(Zombie(r, random.choice(pool)))
        elif len(self.zombies) == 0:
            self.state = "WIN"

        for p in self.plants:
            p.update(self)
        self.plants = [p for p in self.plants if p.hp > 0]

        for m in self.mowers:
            m.update(self)

        for pea in self.peas[:]:
            if not pea.update():
                self.peas.remove(pea)
                continue
            for z in self.zombies:
                if z.row == pea.row and abs(z.x - pea.x) < 22:
                    z.hp -= pea.dmg
                    if pea.slow:
                        z.slow_timer = 240
                    self.peas.remove(pea)
                    break

        for z in self.zombies:
            z.update(self)
            if z.x < GRID_X - 55 and not any(m.row == z.row and m.active for m in self.mowers):
                self.state = "LOSE"
        self.zombies = [z for z in self.zombies if z.hp > 0]

        self.suns = [s for s in self.suns if s.update()]
        for ex in self.explosions:
            ex[2] -= 1
        self.explosions = [ex for ex in self.explosions if ex[2] > 0]

    def click(self, mx, my, btn):
        if self.state != "PLAY":
            if btn == 1:
                self.reset()
            return

        if btn == 3:
            self.shovel = False
            return

        # Collect sun first
        for s in self.suns:
            if not s.collected and math.hypot(mx - s.x, my - s.y) <= 28:
                s.collected = True
                self.sun += 25
                return

        # HUD hitboxes match the rendered packet and shovel rectangles.
        if PACKET_Y <= my < PACKET_Y + PACKET_H:
            if SHOVEL_X <= mx < SHOVEL_X + 70:
                self.shovel = not self.shovel
                return
            for i, spec in enumerate(CATALOG):
                bx = PACKET_X + i * PACKET_STEP
                if bx <= mx < bx + PACKET_W:
                    self.selected = i
                    self.shovel = False
                    return

        # Lawn Grid
        if GRID_X <= mx < GRID_X + COLS * CELL_W and GRID_Y <= my < GRID_Y + ROWS * CELL_H:
            col = (mx - GRID_X) // CELL_W
            row = (my - GRID_Y) // CELL_H
            occupant = next((p for p in self.plants if p.row == row and p.col == col), None)

            if self.shovel:
                if occupant:
                    self.plants.remove(occupant)
                self.shovel = False
            elif occupant is None:
                spec = CATALOG[self.selected]
                if self.sun >= spec["cost"] and self.cooldowns[spec["id"]] == 0:
                    self.sun -= spec["cost"]
                    self.cooldowns[spec["id"]] = spec["cd"]
                    self.plants.append(Plant(row, col, spec))

    def draw(self, surf):
        # Background & DS/PC Yard
        surf.fill((48, 92, 40))
        pygame.draw.rect(surf, (135, 110, 82), (0, GRID_Y, GRID_X - 15, ROWS * CELL_H))

        # Checkerboard Lawn
        for r in range(ROWS):
            for c in range(COLS):
                shade = (82, 168, 56) if (r + c) % 2 == 0 else (68, 148, 46)
                rect = (GRID_X + c * CELL_W, GRID_Y + r * CELL_H, CELL_W, CELL_H)
                pygame.draw.rect(surf, shade, rect)

        # Hover preview on grid
        mx, my = pygame.mouse.get_pos()
        if GRID_X <= mx < GRID_X + COLS * CELL_W and GRID_Y <= my < GRID_Y + ROWS * CELL_H:
            hc = (mx - GRID_X) // CELL_W
            hr = (my - GRID_Y) // CELL_H
            pygame.draw.rect(surf, (255, 255, 255), (GRID_X + hc * CELL_W, GRID_Y + hr * CELL_H, CELL_W, CELL_H), 2)

        # Replanted-style seed bank: warm wood, parchment cards, and clear cooldowns.
        pygame.draw.rect(surf, (66, 42, 24), (0, 0, WIDTH, 92))
        pygame.draw.rect(surf, (125, 83, 43), (3, 3, WIDTH - 6, 84), border_radius=9)
        pygame.draw.rect(surf, (184, 131, 69), (6, 5, WIDTH - 12, 79), 3, border_radius=9)
        for y in (7, 84):
            pygame.draw.line(surf, (81, 49, 26), (8, y), (WIDTH - 8, y), 2)
        # Sun bank (visual center and pickup target both use 52, 42).
        pygame.draw.rect(surf, (92, 65, 34), (10, 9, 104, 73), border_radius=8)
        pygame.draw.rect(surf, (233, 194, 112), (14, 12, 96, 67), 3, border_radius=8)
        pygame.draw.circle(surf, (255, 204, 34), (52, 34), 17)
        for a in range(8):
            angle = a * math.pi / 4
            pygame.draw.line(surf, (255, 232, 99),
                             (int(52 + math.cos(angle) * 19), int(34 + math.sin(angle) * 19)),
                             (int(52 + math.cos(angle) * 23), int(34 + math.sin(angle) * 23)), 3)
        pygame.draw.circle(surf, (255, 239, 139), (52, 34), 11)
        sun_label = font_md.render(str(self.sun), True, (255, 245, 195))
        surf.blit(sun_label, (62 - sun_label.get_width() // 2, 52))
        for i, spec in enumerate(CATALOG):
            bx = PACKET_X + i * PACKET_STEP
            cd = self.cooldowns[spec["id"]]
            affordable = self.sun >= spec["cost"]
            ready = cd == 0
            rect = pygame.Rect(bx, PACKET_Y, PACKET_W, PACKET_H)
            pygame.draw.rect(surf, (67, 46, 29), rect.move(2, 3), border_radius=5)
            pygame.draw.rect(surf, (219, 199, 145) if affordable else (153, 147, 121), rect, border_radius=5)
            pygame.draw.rect(surf, (102, 80, 48), rect, 2, border_radius=5)
            pygame.draw.rect(surf, (105, 151, 80), (bx + 5, 14, 52, 41), border_radius=4)
            # Procedural packet portrait (no external assets).
            cx, cy = bx + 31, 34
            pygame.draw.ellipse(surf, (42, 90, 42), (cx - 15, cy + 10, 30, 9))
            pygame.draw.line(surf, (36, 108, 43), (cx, cy + 10), (cx, cy - 5), 4)
            pygame.draw.circle(surf, spec["color"], (cx, cy - 5), 13)
            pygame.draw.circle(surf, (255, 255, 230), (cx - 4, cy - 8), 2)
            pygame.draw.circle(surf, (255, 255, 230), (cx + 4, cy - 8), 2)
            pygame.draw.rect(surf, (245, 230, 185), (bx + 4, 56, 54, 22), border_radius=3)
            cost = font_sm.render(str(spec["cost"]), True, (54, 52, 31))
            surf.blit(cost, (bx + 31 - cost.get_width() // 2, 58))
            if cd > 0:
                shade = pygame.Surface((PACKET_W, PACKET_H), pygame.SRCALPHA)
                shade.fill((25, 25, 25, 90))
                surf.blit(shade, rect.topleft)
                height = max(1, int(PACKET_H * cd / spec["cd"]))
                cooldown = pygame.Surface((PACKET_W, height), pygame.SRCALPHA)
                cooldown.fill((15, 17, 21, 165))
                surf.blit(cooldown, (bx, PACKET_Y + PACKET_H - height))
            if self.selected == i and not self.shovel:
                pygame.draw.rect(surf, (255, 239, 95), rect, 3, border_radius=5)
            if not affordable:
                pygame.draw.line(surf, (122, 44, 32), (bx + 5, 76), (bx + 56, 76), 2)
        # Shovel slot.
        shovel_rect = pygame.Rect(SHOVEL_X, 9, 70, 73)
        pygame.draw.rect(surf, (97, 67, 40), shovel_rect, border_radius=6)
        pygame.draw.rect(surf, (255, 224, 108) if self.shovel else (195, 158, 96), shovel_rect, 3, border_radius=6)
        pygame.draw.line(surf, (113, 75, 40), (SHOVEL_X + 35, 21), (SHOVEL_X + 35, 58), 6)
        pygame.draw.ellipse(surf, (187, 194, 193), (SHOVEL_X + 22, 13, 26, 24))
        pygame.draw.ellipse(surf, (86, 94, 92), (SHOVEL_X + 22, 13, 26, 24), 2)
        shovel_label = font_tiny.render("SHOVEL [S]", True, (255, 240, 201))
        surf.blit(shovel_label, (SHOVEL_X + 35 - shovel_label.get_width() // 2, 65))
        # Compact wave tracker with finish flag.
        prog = min(1.0, self.ticks / max(1, self.max_ticks))
        pygame.draw.rect(surf, (68, 49, 30), (808, 18, 83, 23), border_radius=5)
        pygame.draw.rect(surf, (66, 116, 46), (812, 23, int(72 * prog), 12), border_radius=3)
        pygame.draw.rect(surf, (213, 192, 127), (808, 18, 83, 23), 2, border_radius=5)
        for fy in range(2):
            for fx in range(2):
                pygame.draw.rect(surf, (245, 245, 245) if (fx + fy) % 2 == 0 else (34, 34, 34),
                                 (878 + fx * 5, 9 + fy * 5, 5, 5))
        fps_label = font_tiny.render(f"{int(clock.get_fps())} FPS", True, (255, 234, 188))
        surf.blit(fps_label, (827, 56))

        # Entities
        for m in self.mowers:
            m.draw(surf)
        for p in self.plants:
            p.draw(surf)
        for z in sorted(self.zombies, key=lambda item: item.row):
            z.draw(surf)
        for pea in self.peas:
            pea.draw(surf)
        for ex in self.explosions:
            r = int((28 - ex[2]) * 4.2)
            pygame.draw.circle(surf, (255, 140, 30), (int(ex[0]), int(ex[1])), r, 4)
            ts = font_md.render("POWIE!", True, (255, 230, 60))
            surf.blit(ts, (ex[0] - ts.get_width() // 2, ex[1] - 25))
        for s in self.suns:
            s.draw(surf)

        if self.huge_wave_banner > 0:
            global _wave_surf_cache
            if _wave_surf_cache is None:
                wtxt = font_lg.render("A HUGE WAVE OF ZOMBIES IS APPROACHING!", True, (235, 40, 40))
                _wave_surf_cache = pygame.transform.scale(wtxt, (int(wtxt.get_width() * 0.55), int(wtxt.get_height() * 0.55)))
            surf.blit(_wave_surf_cache, (WIDTH // 2 - _wave_surf_cache.get_width() // 2, HEIGHT // 2 - 20))

        if self.state != "PLAY":
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 175))
            surf.blit(ov, (0, 0))
            msg = "THE ZOMBIES ATE YOUR BRAINS!" if self.state == "LOSE" else "LAWN DEFENDED! (CLICK TO RESTART)"
            col = (240, 55, 55) if self.state == "LOSE" else (110, 245, 95)
            mtxt = font_lg.render(msg, True, col)
            mtxt = pygame.transform.scale(mtxt, (int(mtxt.get_width() * 0.65), int(mtxt.get_height() * 0.65)))
            surf.blit(mtxt, (WIDTH // 2 - mtxt.get_width() // 2, HEIGHT // 2 - 25))



MODES = ["Adventure", "Tutorial", "Minigames", "Puzzle", "Survival", "Cloudy Day", "RIP Mode", "Zen Garden"]

class ExpandedGame(Game):
    def __init__(self):
        super().__init__()
        self.scene = "MENU"
        self.mode = "Adventure"
        self.level = 1
        self.paused = False
        self.menu_buttons = []
        self.help_page = False
        self.puzzle_goal = 0
        self.garden_growth = 0

    def start(self, mode):
        self.mode = mode
        self.level = 1
        self.reset()
        self.scene = "PLAY"
        self.paused = False
        self.configure_mode()

    def configure_mode(self):
        self.puzzle_goal = 0
        self.garden_growth = 0
        if self.mode == "Tutorial":
            self.sun = 250
            self.max_ticks = 60 * 65
            self.spawn_timer = 600
        elif self.mode == "Survival":
            self.max_ticks = 60 * 240
            self.sun = 200
        elif self.mode == "Minigames":
            self.max_ticks = 60 * 90
            self.spawn_timer = 90
            self.sun = 350
            self.sky_timer = 240
        elif self.mode == "Puzzle":
            self.max_ticks = 60 * 100
            self.sun = 100
            self.spawn_timer = 180
            self.puzzle_goal = 8
            # Puzzle challenge: pre-position a defensive line and survive.
            for row in range(ROWS):
                self.plants.append(Plant(row, 1, CATALOG[3]))
            self.cooldowns["wallnut"] = 0
        elif self.mode == "Cloudy Day":
            self.sky_timer = 999999
            self.sun = 200
        elif self.mode == "RIP Mode":
            self.spawn_timer = 90
            self.sun = 400
            self.max_ticks = 60 * 150
        elif self.mode == "Zen Garden":
            self.max_ticks = 99999999
            self.spawn_timer = 99999999
            self.sun = 999
            self.sky_timer = 99999999
        else:
            self.max_ticks = 60 * (80 + min(self.level, 10) * 10)

    def update(self):
        if self.scene != "PLAY" or self.paused: return
        if self.mode == "Zen Garden":
            self.ticks += 1
            self.garden_growth += 1
            for p in self.plants:
                p.t += 0.08
            return
        super().update()
        if self.mode == "Minigames" and self.ticks % 300 == 0:
            self.sun += 25  # Sun bonus for rapid-fire challenge.
        if self.mode == "RIP Mode" and self.ticks % 240 == 0:
            self.zombies.append(Zombie(random.randrange(ROWS), "bucket"))
        if self.mode == "Puzzle" and self.state == "WIN":
            self.puzzle_goal = sum(p.hp > 0 for p in self.plants)
        if self.mode == "Zen Garden":
            self.zombies.clear()
            self.spawn_timer = 99999999
        if self.mode == "Cloudy Day":
            self.suns = [s for s in self.suns if not s.from_sky]
        if self.state == "WIN" and self.mode == "Survival":
            self.level += 1
            self.state = "PLAY"
            self.ticks = 0
            self.spawn_timer = 260
            self.max_ticks += 60 * 30
            self.sun += 100

    def draw(self, surf):
        if self.scene == "MENU":
            self.draw_menu(surf)
            return
        super().draw(surf)
        label = font_sm.render(f"{self.mode}  |  Stage {self.level}  |  ESC: Menu  P: Pause", True, (255,255,255))
        pygame.draw.rect(surf,(25,28,32),(8,565,440,27),border_radius=5)
        surf.blit(label,(16,570))
        if self.mode == "Zen Garden":
            tip = "ZEN GARDEN: Plant freely. No zombies. R to clear garden."
            pygame.draw.rect(surf, (54, 77, 43), (130, 522, 650, 35), border_radius=6)
            surf.blit(font_sm.render(tip, True, (255, 245, 189)), (147, 533))
        if self.mode == "Tutorial" and self.state == "PLAY":
            tip = ("Crazy Dave: Collect sunlight!" if self.ticks < 900 else
                   "Crazy Dave: Select a seed and plant on the lawn!" if self.ticks < 1800 else
                   "Crazy Dave: Defend your brains from the zombies!")
            pygame.draw.rect(surf,(45,34,24),(155,522,600,34),border_radius=6)
            surf.blit(font_md.render(tip,True,(255,235,160)),(165,527))
        if self.paused:
            overlay = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            overlay.fill((0,0,0,165)); surf.blit(overlay,(0,0))
            self.center(surf,"PAUSED - Press P to resume",HEIGHT//2,(255,255,255),font_md)

    def center(self,surf,msg,y,color,font):
        img=font.render(msg,True,color)
        surf.blit(img,((WIDTH-img.get_width())//2,y))

    def draw_menu(self,surf):
        surf.fill((22,39,28))
        for row in range(6):
            for col in range(12):
                pygame.draw.rect(surf,(36,75,41) if (row+col)%2 else (42,88,47),(col*75,row*100,75,100))
        pygame.draw.rect(surf,(23,29,35),(100,25,700,550),border_radius=18)
        self.center(surf,"CAT'S PVZ 0.1.a",42,(255,215,80),font_lg)
        self.center(surf,"Replanted-inspired | 60 FPS | Original engine preserved",108,(180,230,180),font_sm)
        self.menu_buttons=[]
        for i,mode in enumerate(MODES):
            x=135+(i%2)*325; y=155+(i//2)*82
            rect=pygame.Rect(x,y,300,65)
            pygame.draw.rect(surf,(48,90,56),rect,border_radius=9)
            pygame.draw.rect(surf,(115,170,90),rect,2,border_radius=9)
            self.center_in_rect(surf,mode,rect)
            self.menu_buttons.append((rect,mode))
        self.center(surf,"H: Help  |  M: Music toggle  |  ESC: Menu  |  P: Pause",506,(190,205,210),font_sm)
        self.center(surf,"Menu music: OFF  |  In-game music: " + ("MUTED" if _music_muted else "ON"),535,(190,205,210),font_sm)
        if self.help_page:
            pygame.draw.rect(surf,(15,22,27),(120,180,660,280),border_radius=12)
            tips=["HOW TO PLAY", "Click a mode to begin. Collect suns with the mouse.",
                  "Click a seed packet, then an empty lawn tile.",
                  "1-9: seeds  |  S: shovel  |  P: pause  |  R: restart",
                  "Each mode has its own rules. Zen Garden is peaceful.",
                  "Press H to close this help screen."]
            for i,line in enumerate(tips): self.center(surf,line,205+i*38,(255,235,180),font_md if i==0 else font_sm)

    def center_in_rect(self,surf,msg,rect):
        img=font_md.render(msg,True,(245,245,230))
        surf.blit(img,(rect.centerx-img.get_width()//2,rect.centery-img.get_height()//2))

    def click(self,mx,my,btn):
        if self.scene == "MENU":
            if self.help_page: return
            if btn == 1:
                for rect,mode in self.menu_buttons:
                    if rect.collidepoint(mx,my): self.start(mode); return
            return
        if self.paused: return
        if self.mode == "Zen Garden" and btn == 1 and GRID_X <= mx < GRID_X + COLS * CELL_W and GRID_Y <= my < GRID_Y + ROWS * CELL_H:
            col = (mx - GRID_X) // CELL_W
            row = (my - GRID_Y) // CELL_H
            occupant = next((p for p in self.plants if p.row == row and p.col == col), None)
            if self.shovel:
                if occupant: self.plants.remove(occupant)
                self.shovel = False
            elif occupant is None:
                self.plants.append(Plant(row, col, CATALOG[self.selected]))
            return
        if self.state == "WIN" and btn == 1 and self.mode == "Adventure":
            self.level += 1
            self.reset()
            self.configure_mode()
            return
        if self.state in ("WIN", "LOSE") and btn == 1:
            self.reset()
            self.configure_mode()
            return
        super().click(mx,my,btn)


def main():
    start_music()
    game = ExpandedGame()
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                game.click(*ev.pos, ev.button)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_m:
                    toggle_music()
                elif ev.key == pygame.K_ESCAPE:
                    game.scene = "MENU"
                    game.help_page = False
                elif ev.key == pygame.K_h and game.scene == "MENU":
                    game.help_page = not game.help_page
                elif ev.key == pygame.K_p and game.scene == "PLAY":
                    game.paused = not game.paused
                elif game.scene == "PLAY":
                    if pygame.K_1 <= ev.key <= pygame.K_9:
                        game.selected = ev.key - pygame.K_1
                        game.shovel = False
                    elif ev.key == pygame.K_s:
                        game.shovel = not game.shovel
                    elif ev.key == pygame.K_r:
                        game.reset()
                        game.configure_mode()
        sync_music_for_scene(game.scene)
        game.update()
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()
