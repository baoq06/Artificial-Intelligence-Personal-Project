"""Vẽ trạng thái: thẻ nhỏ, bàn 8-puzzle, phòng Vacuum (có animation) và danh sách thẻ cuộn được."""
import math
import random

import pygame

from ui import (COL, approach, clamp, draw_text, mix, rrect, shadow, text_width)

TILE_BASE = (62, 84, 160)
TILE_GOOD = (38, 142, 108)
DIRT = (150, 108, 66)
FLOOR_DIRTY = (58, 50, 52)
FLOOR_CLEAN = (30, 66, 64)


# ------------------------------------------------------------------ thẻ nhỏ (dùng trong các bảng)
def draw_puzzle_state(surf, rect, state, goal=None):
    n = 3
    pad = max(2, rect.w // 22)
    cell = (rect.w - pad * (n + 1)) / n
    fsize = max(9, int(cell * 0.62))
    for r in range(n):
        for c in range(n):
            v = state[r][c]
            x = rect.x + pad + c * (cell + pad)
            y = rect.y + pad + r * (cell + pad)
            cr = pygame.Rect(round(x), round(y), round(cell), round(cell))
            if v == 0:
                rrect(surf, (15, 19, 31), cr, 3)
            else:
                good = goal is not None and goal[r][c] == v
                rrect(surf, TILE_GOOD if good else TILE_BASE, cr, 3)
                draw_text(surf, str(v), cr.center, fsize, COL["white"], True, "center")


def draw_vacuum_state(surf, rect, state):
    loc, rooms = state
    gap = 3
    w = (rect.w - gap) / 2
    for i, name in enumerate("AB"):
        rr = pygame.Rect(round(rect.x + i * (w + gap)), rect.y, round(w), rect.h)
        dirty = rooms[i] == "Dirty"
        rrect(surf, FLOOR_DIRTY if dirty else FLOOR_CLEAN, rr, 4)
        if dirty:
            for dx, dy, rad in ((.3, .62, 3), (.65, .72, 2), (.5, .4, 2.5), (.72, .5, 2)):
                pygame.draw.circle(surf, DIRT, (rr.x + rr.w * dx, rr.y + rr.h * dy), rad)
        draw_text(surf, name, (rr.centerx, rr.y + 5), 11, COL["muted"], True, "midtop")
        if loc == name:
            c = (rr.centerx, rr.y + rr.h * .66)
            pygame.draw.circle(surf, COL["accent"], c, min(rr.w, rr.h) * .24)
            pygame.draw.circle(surf, COL["white"], c, min(rr.w, rr.h) * .24, 1)
            pygame.draw.circle(surf, COL["green"], (c[0], c[1] - 1), 2)


def paint_card(surf, rect, game, state, goal=None, border=None, border_w=1, alpha=255, tag=None, tag_color=None):
    if alpha < 255:
        tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
        paint_card(tmp, pygame.Rect(0, 0, rect.w, rect.h), game, state, goal, border, border_w, 255, tag, tag_color)
        tmp.set_alpha(int(alpha))
        surf.blit(tmp, rect.topleft)
        return
    rrect(surf, COL["panel2"], rect, 9, border_w, border or COL["border"])
    inner = rect.inflate(-8, -8)
    if game == "puzzle":
        draw_puzzle_state(surf, inner, state, goal)
    else:
        draw_vacuum_state(surf, inner, state)
    if tag:
        tc = tag_color or COL["accent"]
        tw = text_width(tag, 10, True)
        t = pygame.Rect(0, 0, tw + 10, 15)
        t.midtop = (rect.centerx, rect.y - 7)
        rrect(surf, tc, t, 7)
        draw_text(surf, tag, t.center, 10, COL["white"], True, "center")


# ------------------------------------------------------------------ danh sách thẻ cuộn
class CardList:
    def __init__(self, rect, accent, cw=64, ch=64, gap=10, top=50):
        self.rect = pygame.Rect(rect)
        self.accent = accent
        self.CW, self.CH, self.GAP = cw, ch, gap
        self.row = 0.0
        self.target = 0
        self.area = pygame.Rect(self.rect.x + 16, self.rect.y + top, self.rect.w - 32, self.rect.h - top - 12)

    @property
    def cols(self):
        return max(1, (self.area.w + self.GAP) // (self.CW + self.GAP))

    @property
    def rows_visible(self):
        return max(1, (self.area.h + self.GAP) // (self.CH + self.GAP))

    def scroll(self, dy, total):
        total_rows = -(-total // self.cols)
        new = int(clamp(self.target + dy, 0, max(0, total_rows - self.rows_visible)))
        changed = new != self.target
        self.target = new
        return changed

    def reset_scroll(self):
        self.target = 0

    def update(self, dt):
        self.row = approach(self.row, self.target, dt, 14)

    def draw(self, surf, total, getter, painter, empty_text):
        if total == 0:
            draw_text(surf, empty_text, self.area.center, 15, COL["muted"], False, "center")
            return
        cols = self.cols
        first_row = int(math.floor(self.row))
        frac = self.row - first_row
        rows = self.rows_visible + 2
        items = getter(first_row * cols, rows * cols)
        old_clip = surf.get_clip()
        surf.set_clip(self.area.inflate(8, 0).clip(old_clip))
        step = self.CH + self.GAP
        for i, item in enumerate(items):
            r, c = divmod(i, cols)
            x = self.area.x + c * (self.CW + self.GAP)
            y = self.area.y + (r - frac) * step + 8
            rect = pygame.Rect(round(x), round(y), self.CW, self.CH)
            if rect.bottom < self.area.y or rect.y > self.area.bottom:
                continue
            painter(surf, rect, item, first_row * cols + i)
        surf.set_clip(old_clip)
        total_rows = -(-total // cols)
        if total_rows > self.rows_visible:
            track = pygame.Rect(self.rect.right - 9, self.area.y, 4, self.area.h)
            rrect(surf, COL["panel2"], track, 2)
            th = max(24, track.h * self.rows_visible / total_rows)
            ty = track.y + (track.h - th) * (self.row / max(1, total_rows - self.rows_visible))
            rrect(surf, mix(COL["panel3"], self.accent, 0.7), pygame.Rect(track.x, ty, 4, th), 2)


# ------------------------------------------------------------------ bàn 8-puzzle có animation
class PuzzleBoard:
    def __init__(self, tile=80, gap=8):
        self.tile = tile
        self.gap = gap
        self.size = 3 * tile + 4 * gap
        self.pos = {n: [0.0, 0.0] for n in range(1, 9)}
        self.good = {n: 0.0 for n in range(1, 9)}
        self.target = {}
        self.good_t = {}
        self.goal = None

    def set_state(self, state, goal, snap=False):
        self.goal = goal
        for r in range(3):
            for c in range(3):
                v = state[r][c]
                if v:
                    self.target[v] = (c, r)
                    self.good_t[v] = 1.0 if goal[r][c] == v else 0.0
                    if snap:
                        self.pos[v] = [float(c), float(r)]
                        self.good[v] = self.good_t[v]

    def update(self, dt):
        for v in range(1, 9):
            tx, ty = self.target.get(v, (0, 0))
            p = self.pos[v]
            p[0] = approach(p[0], tx, dt, 13)
            p[1] = approach(p[1], ty, dt, 13)
            self.good[v] = approach(self.good[v], self.good_t.get(v, 0), dt, 10)

    def draw(self, surf, origin):
        ox, oy = origin
        frame = pygame.Rect(ox, oy, self.size, self.size)
        rrect(surf, (14, 18, 30), frame, 16, 1, COL["border"])
        step = self.tile + self.gap
        for r in range(3):
            for c in range(3):
                rrect(surf, (20, 25, 41), (ox + self.gap + c * step, oy + self.gap + r * step, self.tile, self.tile), 12)
        # tile đang di chuyển xa vẽ sau (nổi lên trên)
        order = sorted(range(1, 9), key=lambda v: abs(self.pos[v][0] - self.target.get(v, (0, 0))[0])
                       + abs(self.pos[v][1] - self.target.get(v, (0, 0))[1]))
        for v in order:
            px, py = self.pos[v]
            r = pygame.Rect(round(ox + self.gap + px * step), round(oy + self.gap + py * step), self.tile, self.tile)
            col = mix(TILE_BASE, TILE_GOOD, self.good[v])
            shadow(surf, r, 12, 8, 90, (0, 4))
            rrect(surf, col, r, 12)
            hl = pygame.Rect(r.x + 3, r.y + 3, r.w - 6, r.h // 2 - 3)
            hl_s = pygame.Surface(hl.size, pygame.SRCALPHA)
            pygame.draw.rect(hl_s, (255, 255, 255, 22), hl_s.get_rect(), border_radius=9)
            surf.blit(hl_s, hl.topleft)
            pygame.draw.rect(surf, mix(col, COL["white"], 0.25), r, 1, border_radius=12)
            draw_text(surf, str(v), r.center, 38, COL["white"], True, "center")


# ------------------------------------------------------------------ phòng Vacuum có animation
class VacuumBoard:
    ROOM_W = 172
    ROOM_H = 232
    GAP = 16

    def __init__(self):
        self.rx = 0.0           # vị trí robot (0 = phòng A, 1 = phòng B)
        self.dirt = [1.0, 1.0]
        self.target_loc = 0
        self.target_dirt = [1, 1]
        self.dirty_flags = [True, True]
        self.suck_t = 0.0
        self.time = 0.0
        self.last_node = None
        rng = random.Random(7)
        self.specks = [[(rng.uniform(.12, .88), rng.uniform(.24, .74), rng.uniform(3.5, 8))
                        for _ in range(15)] for _ in range(2)]

    @property
    def width(self):
        return self.ROOM_W * 2 + self.GAP

    def set_state(self, state, node=None, snap=False):
        loc, rooms = state
        self.target_loc = 0 if loc == "A" else 1
        self.target_dirt = [1 if r == "Dirty" else 0 for r in rooms]
        self.dirty_flags = [r == "Dirty" for r in rooms]
        if snap:
            self.rx = float(self.target_loc)
            self.dirt = [float(d) for d in self.target_dirt]
            self.last_node = node
        elif node is not self.last_node:
            self.last_node = node
            if node is not None and node.action == "Suck":
                self.suck_t = 1.0

    def update(self, dt):
        self.time += dt
        self.rx = approach(self.rx, self.target_loc, dt, 7)
        for i in range(2):
            self.dirt[i] = approach(self.dirt[i], self.target_dirt[i], dt, 5)
        self.suck_t = max(0.0, self.suck_t - dt)

    def draw(self, surf, origin):
        ox, oy = origin
        for i, name in enumerate("AB"):
            room = pygame.Rect(ox + i * (self.ROOM_W + self.GAP), oy, self.ROOM_W, self.ROOM_H)
            shadow(surf, room, 16, 12, 70, (0, 5))
            d = clamp(self.dirt[i], 0, 1)
            floor = mix(FLOOR_CLEAN, FLOOR_DIRTY, d)
            rrect(surf, floor, room, 16, 1, mix(COL["border"], COL["white"], 0.1))
            # lát sàn
            for k in range(1, 4):
                pygame.draw.line(surf, mix(floor, COL["white"], 0.06), (room.x + 12, room.y + 36 + k * 36),
                                 (room.right - 12, room.y + 36 + k * 36))
            for k in range(1, 4):
                pygame.draw.line(surf, mix(floor, COL["white"], 0.06), (room.x + k * 43, room.y + 36),
                                 (room.x + k * 43, room.bottom - 40))
            draw_text(surf, f"PHÒNG {name}", (room.x + 14, room.y + 12), 14, COL["white"], True)
            # bụi
            for sx, sy, rad in self.specks[i]:
                rr = rad * math.sqrt(d)
                if rr > 0.6:
                    pygame.draw.circle(surf, DIRT, (room.x + room.w * sx, room.y + room.h * sy), rr)
                    pygame.draw.circle(surf, mix(DIRT, COL["white"], 0.25), (room.x + room.w * sx - rr * .3,
                                                                           room.y + room.h * sy - rr * .3), rr * .35)
            # nhãn trạng thái
            dirty = self.dirty_flags[i]
            label = "Dirty" if dirty else "Clean"
            color = COL["orange"] if dirty else COL["green"]
            tw = text_width(label, 14, True)
            pill = pygame.Rect(0, 0, tw + 28, 26)
            pill.midbottom = (room.centerx, room.bottom - 10)
            rrect(surf, mix((18, 22, 36), color, 0.18), pill, 13, 1, mix((18, 22, 36), color, 0.7))
            pygame.draw.circle(surf, color, (pill.x + 12, pill.centery), 4)
            draw_text(surf, label, (pill.x + 21, pill.centery), 14, color, True, "midleft")
        self._draw_robot(surf, ox, oy)

    def _draw_robot(self, surf, ox, oy):
        step = self.ROOM_W + self.GAP
        cx = ox + self.ROOM_W / 2 + self.rx * step
        cy = oy + 150 + math.sin(self.time * 3) * 2
        # bóng
        sh = pygame.Surface((90, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
        surf.blit(sh, (cx - 45, cy + 30))
        # sóng hút
        if self.suck_t > 0:
            ring = pygame.Surface((200, 200), pygame.SRCALPHA)
            for k in range(3):
                ph = ((1 - self.suck_t) * 1.6 + k * 0.33) % 1.0
                rad = 78 - ph * 52
                a = int(190 * (1 - abs(ph - .5) * 2) * min(1, self.suck_t * 3))
                pygame.draw.circle(ring, (*COL["green"], max(0, a)), (100, 100), rad, 3)
            surf.blit(ring, (cx - 100, cy - 100 + 6))
        body = (98, 132, 255)
        pygame.draw.circle(surf, mix(body, (0, 0, 0), 0.45), (cx, cy + 3), 38)
        pygame.draw.circle(surf, body, (cx, cy), 38)
        pygame.draw.circle(surf, mix(body, COL["white"], 0.22), (cx, cy - 6), 30)
        pygame.draw.circle(surf, mix(body, (0, 0, 0), 0.25), (cx, cy), 38, 3)
        # mặt
        visor = pygame.Rect(0, 0, 50, 24)
        visor.center = (cx, cy - 2)
        rrect(surf, (16, 20, 38), visor, 12)
        happy = self.suck_t > 0
        for dx in (-9, 9):
            if happy:
                pygame.draw.arc(surf, COL["green"], (cx + dx - 5, cy - 11, 10, 10), 0.2, 2.9, 2)
            else:
                pygame.draw.circle(surf, COL["green"], (cx + dx, cy - 3), 4)
        pygame.draw.circle(surf, COL["orange"], (cx + 24, cy - 26), 3)
        # chổi quay khi hút
        spin = self.time * (14 if self.suck_t > 0 else 2)
        for k in range(3):
            a = spin + k * 2.094
            pygame.draw.line(surf, COL["white"], (cx, cy + 22),
                             (cx + math.cos(a) * 12, cy + 22 + math.sin(a) * 4), 2)
