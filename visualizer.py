"""Search Visualizer: BFS / DFS / UCS trên 8-puzzle và Vacuum robot (pygame).

Chạy:  python visualizer.py
Phím tắt:  →  Next   ←  Prev   Space  Auto   R  Reset   ↑ ↓ / PgUp PgDn  cuộn trang
"""
import math
import os
import random
import re
import sys
import time

import pygame

import scaling
from problems import (PUZZLE_GOAL, PUZZLE_INIT, VACUUM_GOAL_ROOMS, VACUUM_INIT, make_puzzle_problem, make_vacuum_problem,
                      puzzle_solvable, random_puzzle, vacuum_reachable)
from stepper import SearchMachine, code_lines, explain, init_trace, node_depth, solution_costs, step_trace


# ##############################################################################
# Theme, font, widget (Button, Dropdown, Slider, Panel)
# ##############################################################################

COL = dict(
    bg=(12, 15, 25),
    panel=(21, 26, 41),
    panel2=(30, 36, 57),
    panel3=(38, 46, 72),
    border=(44, 53, 80),
    text=(233, 237, 248),
    muted=(137, 148, 178),
    accent=(96, 130, 255),
    accent2=(152, 102, 250),
    orange=(255, 167, 70),
    green=(52, 211, 153),
    red=(248, 113, 113),
    gray=(104, 118, 152),
    white=(255, 255, 255),
)


# ------------------------------------------------------------------ font / text
_fonts = {}
_text_cache = {}


def get_font(size, bold=False):
    """Font theo cỡ PIXEL THẬT (đã nhân tỉ lệ scaling)."""
    key = (size, bold)
    f = _fonts.get(key)
    if f is None:
        path = pygame.font.match_font("segoeui", bold=bold)
        if path:
            f = pygame.font.Font(path, size)
        else:
            f = pygame.font.SysFont("tahoma,arial,dejavusans", size, bold=bold)
        _fonts[key] = f
    return f


def render_text(txt, size, color, bold=False):
    key = (txt, size, color, bold)
    s = _text_cache.get(key)
    if s is None:
        if len(_text_cache) > 4000:
            _text_cache.clear()
        s = get_font(size, bold).render(txt, True, color)
        _text_cache[key] = s
    return s


def draw_text(surf, txt, pos, size=15, color=COL["text"], bold=False, anchor="topleft", alpha=None):
    """Vẽ chữ ở độ phân giải thật của surf (nét); pos và rect trả về tính bằng đơn vị logic."""
    k = getattr(surf, "k", 1.0)
    s = render_text(txt, scaling.px_size(size, k), tuple(color), bold)
    rp = s.get_rect(**{anchor: (round(pos[0] * k), round(pos[1] * k))})
    if alpha is not None and alpha < 255:
        s = s.copy()
        s.set_alpha(max(0, int(alpha)))
    scaling.blit_px(surf, s, rp)
    x, y = round(rp.x / k), round(rp.y / k)
    return pygame.Rect(x, y, round(rp.right / k) - x, round(rp.bottom / k) - y)


def text_width(txt, size, bold=False):
    """Chiều rộng chữ theo đơn vị logic."""
    return get_font(scaling.px_size(size), bold).size(txt)[0] / scaling.S


# ------------------------------------------------------------------ toán / màu
def approach(cur, target, dt, rate):
    """Tiến dần tới target theo hàm mũ (mượt, không phụ thuộc FPS)."""
    return target + (cur - target) * math.exp(-rate * dt)


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def clamp(v, a, b):
    return max(a, min(b, v))


def ease_out(t):
    t = clamp(t, 0, 1)
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ vẽ cơ bản
def rrect(surf, color, rect, radius=10, border=0, border_color=None):
    rect = pygame.Rect(rect)
    scaling.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        scaling.rect(surf, border_color, rect, width=border, border_radius=radius)


_shadow_cache = {}


def shadow(surf, rect, radius=12, spread=10, strength=70, offset=(0, 4)):
    rect = pygame.Rect(rect)
    key = (rect.w, rect.h, radius, spread, strength, scaling.S)
    img = _shadow_cache.get(key)
    if img is None:
        img = scaling.Surface((rect.w + spread * 2, rect.h + spread * 2), pygame.SRCALPHA)
        steps = spread
        for i in range(steps):
            a = int(strength * (1 - i / steps) ** 2 / 4)
            r = pygame.Rect(i, i, rect.w + (spread - i) * 2, rect.h + (spread - i) * 2)
            scaling.rect(img, (0, 0, 0, a), r, border_radius=radius + spread - i)
        if len(_shadow_cache) > 300:
            _shadow_cache.clear()
        _shadow_cache[key] = img
    surf.blit(img, (rect.x - spread + offset[0], rect.y - spread + offset[1]))


def draw_icon(surf, name, center, size, color):
    cx, cy = center
    h = size / 2
    if name == "next":
        scaling.polygon(surf, color, [(cx - h * .7, cy - h), (cx - h * .7, cy + h), (cx + h * .5, cy)])
        scaling.rect(surf, color, (cx + h * .6, cy - h, max(2, size * .18), size))
    elif name == "prev":
        scaling.polygon(surf, color, [(cx + h * .7, cy - h), (cx + h * .7, cy + h), (cx - h * .5, cy)])
        scaling.rect(surf, color, (cx - h * .6 - max(2, size * .18), cy - h, max(2, size * .18), size))
    elif name == "play":
        scaling.polygon(surf, color, [(cx - h * .6, cy - h), (cx - h * .6, cy + h), (cx + h * .8, cy)])
    elif name == "pause":
        w = max(3, size * .3)
        scaling.rect(surf, color, (cx - h * .7, cy - h, w, size), border_radius=1)
        scaling.rect(surf, color, (cx + h * .7 - w, cy - h, w, size), border_radius=1)
    elif name == "skip":
        scaling.polygon(surf, color, [(cx - h, cy - h * .9), (cx - h, cy + h * .9), (cx, cy)])
        scaling.polygon(surf, color, [(cx - h * .1, cy - h * .9), (cx - h * .1, cy + h * .9), (cx + h * .9, cy)])
    elif name == "reset":
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        scaling.arc(surf, color, rect, 0.6, 5.6, 2)
        ax, ay = cx + h * math.cos(0.6), cy - h * math.sin(0.6)
        scaling.polygon(surf, color, [(ax - 1, ay - 5), (ax + 5, ay + 1), (ax - 5, ay + 2)])
    elif name == "dice":
        r = pygame.Rect(0, 0, size, size)
        r.center = (cx, cy)
        scaling.rect(surf, color, r, 2, border_radius=4)
        for dx, dy in ((-.32, -.32), (.32, .32), (0, 0), (.32, -.32), (-.32, .32)):
            scaling.circle(surf, color, (cx + dx * size, cy + dy * size), 1.5)
    elif name == "home":
        scaling.polygon(surf, color, [(cx - h, cy), (cx, cy - h), (cx + h, cy)], 2)
        scaling.rect(surf, color, (cx - h * .6, cy, h * 1.2, h), 2)
    elif name == "down":
        scaling.line(surf, color, (cx, cy - h), (cx, cy + h * .4), 2)
        scaling.polygon(surf, color, [(cx - h * .7, cy + h * .1), (cx + h * .7, cy + h * .1), (cx, cy + h)])
    elif name == "up":
        scaling.line(surf, color, (cx, cy + h), (cx, cy - h * .4), 2)
        scaling.polygon(surf, color, [(cx - h * .7, cy - h * .1), (cx + h * .7, cy - h * .1), (cx, cy - h)])
    elif name == "check":
        scaling.lines(surf, color, False, [(cx - h * .7, cy), (cx - h * .15, cy + h * .6), (cx + h * .8, cy - h * .6)], 3)
    elif name == "warn":
        scaling.polygon(surf, color, [(cx, cy - h), (cx + h, cy + h * .8), (cx - h, cy + h * .8)], 2)
        scaling.line(surf, color, (cx, cy - h * .3), (cx, cy + h * .25), 2)
        scaling.circle(surf, color, (cx, cy + h * .55), 1.3)


# ------------------------------------------------------------------ widget
class Button:
    KINDS = {
        "primary": ((96, 130, 255), (122, 154, 255), COL["white"]),
        "secondary": ((36, 44, 69), (50, 60, 92), COL["text"]),
        "success": ((40, 168, 124), (52, 200, 150), COL["white"]),
        "danger": ((214, 84, 96), (240, 108, 120), COL["white"]),
    }

    def __init__(self, rect, label="", icon=None, kind="secondary"):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.icon = icon
        self.kind = kind
        self.enabled = True
        self.visible = True
        self.hover = 0.0
        self.press = 0.0

    def update(self, dt, mouse, down):
        over = self.enabled and self.visible and self.rect.collidepoint(mouse)
        self.hover = approach(self.hover, 1.0 if over else 0.0, dt, 16)
        self.press = approach(self.press, 1.0 if (over and down) else 0.0, dt, 30)

    def hit(self, pos):
        return self.enabled and self.visible and self.rect.collidepoint(pos)

    def draw(self, surf):
        if not self.visible:
            return
        base, hov, fg = self.KINDS[self.kind]
        col = mix(base, hov, self.hover)
        r = self.rect.inflate(-int(4 * self.press), -int(3 * self.press))
        if not self.enabled:
            col = mix(col, COL["panel"], 0.65)
            fg = mix(fg, COL["panel"], 0.6)
        elif self.kind == "secondary":
            shadow(surf, r, 10, 6, 40, (0, 2))
        rrect(surf, col, r, 10, 1 if self.kind == "secondary" else 0,
              mix(COL["border"], COL["accent"], self.hover) if self.kind == "secondary" else None)
        icon_w = 14 if self.icon else 0
        tw = text_width(self.label, 14, True) if self.label else 0
        gap = 7 if (self.icon and self.label) else 0
        total = icon_w + gap + tw
        x = r.centerx - total / 2
        if self.icon:
            draw_icon(surf, self.icon, (x + icon_w / 2, r.centery), 12, fg)
        if self.label:
            draw_text(surf, self.label, (x + icon_w + gap, r.centery), 14, fg, True, "midleft")


class Segmented:
    def __init__(self, rect, options, selected=0):
        self.rect = pygame.Rect(rect)
        self.options = options
        self.selected = selected
        self.pos = float(selected)
        self.hover = [0.0] * len(options)

    def seg_w(self):
        return (self.rect.w - 6) / len(self.options)

    def hit(self, pos):
        if not self.rect.collidepoint(pos):
            return None
        i = int((pos[0] - self.rect.x - 3) // self.seg_w())
        return clamp(i, 0, len(self.options) - 1)

    def update(self, dt, mouse):
        self.pos = approach(self.pos, self.selected, dt, 18)
        h = self.hit(mouse)
        for i in range(len(self.options)):
            self.hover[i] = approach(self.hover[i], 1.0 if h == i else 0.0, dt, 14)

    def draw(self, surf):
        rrect(surf, (16, 20, 33), self.rect, 12, 1, COL["border"])
        sw = self.seg_w()
        pill = pygame.Rect(self.rect.x + 3 + self.pos * sw, self.rect.y + 3, sw, self.rect.h - 6)
        shadow(surf, pill, 10, 8, 80, (0, 3))
        rrect(surf, COL["accent"], pill, 10)
        for i, opt in enumerate(self.options):
            cx = self.rect.x + 3 + sw * (i + .5)
            sel = 1 - min(1.0, abs(self.pos - i))
            col = mix(mix(COL["muted"], COL["text"], self.hover[i]), COL["white"], sel)
            draw_text(surf, opt, (cx, self.rect.centery), 15, col, True, "center")


class Slider:
    def __init__(self, rect, value=0.5):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.drag = False
        self.knob = 0.0

    def hit(self, pos):
        return self.rect.inflate(10, 16).collidepoint(pos)

    def set_from_x(self, x):
        self.value = clamp((x - self.rect.x) / self.rect.w, 0, 1)

    def update(self, dt, mouse):
        over = self.drag or self.hit(mouse)
        self.knob = approach(self.knob, 1.0 if over else 0.0, dt, 14)

    def draw(self, surf):
        cy = self.rect.centery
        track = pygame.Rect(self.rect.x, cy - 3, self.rect.w, 6)
        rrect(surf, (16, 20, 33), track, 3, 1, COL["border"])
        fill = pygame.Rect(track.x, track.y, max(6, self.rect.w * self.value), 6)
        rrect(surf, COL["accent"], fill, 3)
        kx = self.rect.x + self.rect.w * self.value
        scaling.circle(surf, (0, 0, 0), (kx, cy + 2), 9 + self.knob)
        scaling.circle(surf, COL["white"], (kx, cy), 8 + self.knob * 1.5)
        scaling.circle(surf, COL["accent"], (kx, cy), 4)


def draw_panel(surf, rect, title=None, dot=None, badge=None, badge_color=None, subtitle=None):
    rect = pygame.Rect(rect)
    shadow(surf, rect, 16, 14, 70, (0, 6))
    rrect(surf, COL["panel"], rect, 16, 1, COL["border"])
    if title:
        x = rect.x + 18
        if dot:
            scaling.circle(surf, dot, (x + 4, rect.y + 20), 5)
            x += 16
        r = draw_text(surf, title, (x, rect.y + 20), 16, COL["text"], True, "midleft")
        if subtitle:
            draw_text(surf, subtitle, (r.right + 10, rect.y + 21), 13, COL["muted"], False, "midleft")
    if badge is not None:
        bc = badge_color or COL["accent"]
        tw = text_width(str(badge), 13, True)
        b = pygame.Rect(0, 0, tw + 22, 24)
        b.midright = (rect.right - 16, rect.y + 20)
        rrect(surf, mix(COL["panel"], bc, 0.22), b, 12, 1, mix(COL["panel"], bc, 0.6))
        draw_text(surf, str(badge), b.center, 13, bc, True, "center")


class Dropdown:
    """Menu thả xuống. Danh sách vẽ riêng (draw_list) để nằm TRÊN cùng mọi thành phần khác."""

    def __init__(self, rect, options, selected=0):
        self.rect = pygame.Rect(rect)
        self.options = options          # list[str] - thêm lựa chọn mới chỉ cần thêm vào đây
        self.selected = selected
        self.open = False
        self.anim = 0.0
        self.hover_head = 0.0
        self.hover = [0.0] * len(options)
        self.row_h = 38

    def set_options(self, options, selected=None):
        self.options = options
        self.hover = [0.0] * len(options)
        if selected is not None:
            self.selected = selected

    def _list_rect(self):
        return pygame.Rect(self.rect.x, self.rect.bottom + 6, self.rect.w, len(self.options) * self.row_h + 10)

    def _opt_rect(self, i):
        lr = self._list_rect()
        return pygame.Rect(lr.x + 5, lr.y + 5 + i * self.row_h, lr.w - 10, self.row_h)

    def click(self, pos):
        """Trả về (consumed, selected_index_or_None)."""
        if self.rect.collidepoint(pos):
            self.open = not self.open
            return True, None
        if self.open:
            for i in range(len(self.options)):
                if self._opt_rect(i).collidepoint(pos):
                    self.open = False
                    return True, i
            self.open = False
            return self._list_rect().collidepoint(pos), None
        return False, None

    def update(self, dt, mouse):
        self.anim = approach(self.anim, 1.0 if self.open else 0.0, dt, 20)
        over = self.rect.collidepoint(mouse)
        self.hover_head = approach(self.hover_head, 1.0 if (over or self.open) else 0.0, dt, 16)
        for i in range(len(self.options)):
            on = self.open and self._opt_rect(i).collidepoint(mouse)
            self.hover[i] = approach(self.hover[i], 1.0 if on else 0.0, dt, 18)

    def draw(self, surf):
        r = self.rect
        rrect(surf, mix((16, 20, 33), (28, 34, 54), self.hover_head), r, 12, 1,
              mix(COL["border"], COL["accent"], self.hover_head))
        draw_text(surf, self.options[self.selected], (r.x + 16, r.centery), 15, COL["text"], True, "midleft")
        # mũi tên xoay
        cx, cy = r.right - 20, r.centery
        d = 4 * (1 - 2 * self.anim)
        scaling.lines(surf, COL["muted"], False, [(cx - 5, cy - d / 2 - 1), (cx, cy + d / 2 + 1), (cx + 5, cy - d / 2 - 1)], 2)

    def draw_list(self, surf):
        if self.anim < 0.02:
            return
        lr = self._list_rect()
        visible_h = int(lr.h * self.anim)
        old = surf.get_clip()
        surf.set_clip(pygame.Rect(lr.x - 20, lr.y - 4, lr.w + 40, visible_h + 24).clip(old))
        shadow(surf, lr, 12, 14, 110, (0, 6))
        rrect(surf, (24, 29, 46), lr, 12, 1, COL["border"])
        for i, opt in enumerate(self.options):
            o = self._opt_rect(i)
            if self.hover[i] > 0.01 or i == self.selected:
                col = mix((24, 29, 46), COL["accent"], 0.9 if i == self.selected and self.hover[i] < .5 else 0.35 + 0.4 * self.hover[i])
                rrect(surf, col, o, 8)
            fg = COL["white"] if i == self.selected else mix(COL["muted"], COL["text"], self.hover[i])
            draw_text(surf, opt, (o.x + 12, o.centery), 15, fg, True, "midleft")
            if i == self.selected:
                draw_icon(surf, "check", (o.right - 16, o.centery), 10, COL["white"])
        surf.set_clip(old)


# ##############################################################################
# Vẽ trạng thái: thẻ nhỏ, bàn 8-puzzle, phòng Vacuum, danh sách thẻ cuộn
# ##############################################################################

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
                scaling.circle(surf, DIRT, (rr.x + rr.w * dx, rr.y + rr.h * dy), rad)
        draw_text(surf, name, (rr.centerx, rr.y + 5), 11, COL["muted"], True, "midtop")
        if loc == name:
            c = (rr.centerx, rr.y + rr.h * .66)
            scaling.circle(surf, COL["accent"], c, min(rr.w, rr.h) * .24)
            scaling.circle(surf, COL["white"], c, min(rr.w, rr.h) * .24, 1)
            scaling.circle(surf, COL["green"], (c[0], c[1] - 1), 2)


def _cost_pill(surf, rect, cost):
    label = f"g={cost}"
    c = pygame.Rect(0, 0, text_width(label, 10, True) + 10, 15)
    c.midbottom = (rect.centerx, rect.bottom + 6)
    rrect(surf, (44, 52, 84), c, 7, 1, COL["border"])
    draw_text(surf, label, c.center, 10, COL["text"], True, "center")


def paint_card(surf, rect, game, state, goal=None, border=None, border_w=1, alpha=255, tag=None, tag_color=None,
               cost=None):
    """cost: chi phí g(n) (UCS) - vẽ thành nhãn nhỏ ở cạnh dưới thẻ."""
    if alpha < 255:
        tmp = scaling.Surface(rect.size, pygame.SRCALPHA)
        paint_card(tmp, pygame.Rect(0, 0, rect.w, rect.h), game, state, goal, border, border_w, 255, tag, tag_color)
        tmp.set_alpha(int(alpha))
        surf.blit(tmp, rect.topleft)
        if cost is not None:          # nhãn chi phí nằm ngoài thẻ nên vẽ riêng (không bị cắt khi mờ)
            _cost_pill(surf, rect, cost)
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
    if cost is not None:
        _cost_pill(surf, rect, cost)


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
            hl_s = scaling.Surface(hl.size, pygame.SRCALPHA)
            scaling.rect(hl_s, (255, 255, 255, 22), hl_s.get_rect(), border_radius=9)
            surf.blit(hl_s, hl.topleft)
            scaling.rect(surf, mix(col, COL["white"], 0.25), r, 1, border_radius=12)
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
                scaling.line(surf, mix(floor, COL["white"], 0.06), (room.x + 12, room.y + 36 + k * 36),
                                 (room.right - 12, room.y + 36 + k * 36))
            for k in range(1, 4):
                scaling.line(surf, mix(floor, COL["white"], 0.06), (room.x + k * 43, room.y + 36),
                                 (room.x + k * 43, room.bottom - 40))
            draw_text(surf, f"PHÒNG {name}", (room.x + 14, room.y + 12), 14, COL["white"], True)
            # bụi
            for sx, sy, rad in self.specks[i]:
                rr = rad * math.sqrt(d)
                if rr > 0.6:
                    scaling.circle(surf, DIRT, (room.x + room.w * sx, room.y + room.h * sy), rr)
                    scaling.circle(surf, mix(DIRT, COL["white"], 0.25), (room.x + room.w * sx - rr * .3,
                                                                           room.y + room.h * sy - rr * .3), rr * .35)
            # nhãn trạng thái
            dirty = self.dirty_flags[i]
            label = "Dirty" if dirty else "Clean"
            color = COL["orange"] if dirty else COL["green"]
            tw = text_width(label, 14, True)
            pill = pygame.Rect(0, 0, tw + 28, 26)
            pill.midbottom = (room.centerx, room.bottom - 10)
            rrect(surf, mix((18, 22, 36), color, 0.18), pill, 13, 1, mix((18, 22, 36), color, 0.7))
            scaling.circle(surf, color, (pill.x + 12, pill.centery), 4)
            draw_text(surf, label, (pill.x + 21, pill.centery), 14, color, True, "midleft")
        self._draw_robot(surf, ox, oy)

    def _draw_robot(self, surf, ox, oy):
        step = self.ROOM_W + self.GAP
        cx = ox + self.ROOM_W / 2 + self.rx * step
        cy = oy + 150 + math.sin(self.time * 3) * 2
        # bóng
        sh = scaling.Surface((90, 26), pygame.SRCALPHA)
        scaling.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
        surf.blit(sh, (cx - 45, cy + 30))
        # sóng hút
        if self.suck_t > 0:
            ring = scaling.Surface((200, 200), pygame.SRCALPHA)
            for k in range(3):
                ph = ((1 - self.suck_t) * 1.6 + k * 0.33) % 1.0
                rad = 78 - ph * 52
                a = int(190 * (1 - abs(ph - .5) * 2) * min(1, self.suck_t * 3))
                scaling.circle(ring, (*COL["green"], max(0, a)), (100, 100), rad, 3)
            surf.blit(ring, (cx - 100, cy - 100 + 6))
        body = (98, 132, 255)
        scaling.circle(surf, mix(body, (0, 0, 0), 0.45), (cx, cy + 3), 38)
        scaling.circle(surf, body, (cx, cy), 38)
        scaling.circle(surf, mix(body, COL["white"], 0.22), (cx, cy - 6), 30)
        scaling.circle(surf, mix(body, (0, 0, 0), 0.25), (cx, cy), 38, 3)
        # mặt
        visor = pygame.Rect(0, 0, 50, 24)
        visor.center = (cx, cy - 2)
        rrect(surf, (16, 20, 38), visor, 12)
        happy = self.suck_t > 0
        for dx in (-9, 9):
            if happy:
                scaling.arc(surf, COL["green"], (cx + dx - 5, cy - 11, 10, 10), 0.2, 2.9, 2)
            else:
                scaling.circle(surf, COL["green"], (cx + dx, cy - 3), 4)
        scaling.circle(surf, COL["orange"], (cx + 24, cy - 26), 3)
        # chổi quay khi hút
        spin = self.time * (14 if self.suck_t > 0 else 2)
        for k in range(3):
            a = spin + k * 2.094
            scaling.line(surf, COL["white"], (cx, cy + 22),
                             (cx + math.cos(a) * 12, cy + 22 + math.sin(a) * 4), 2)


# ##############################################################################
# Bảng nhập đầu vào
# ##############################################################################

CELL = 44
CGAP = 5
GRID = 3 * CELL + 2 * CGAP


def _wrap(text, size, width):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_width(t, size) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class _BaseInput:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.changed = False
        bx = self.rect.x + 392
        self.btn_random = Button((bx, self.rect.y + 46, 232 - 16, 34), "Random đầu vào", "dice", "secondary")
        self.btn_default = Button((bx, self.rect.y + 88, 232 - 16, 34), "Về mặc định", "home", "secondary")
        self.buttons = [self.btn_random, self.btn_default]
        self.init_pos = (self.rect.x + 24, self.rect.y + 58)
        self.goal_pos = (self.rect.x + 24 + GRID + 52, self.rect.y + 58)

    def update(self, dt, mouse, down):
        for b in self.buttons:
            b.update(dt, mouse, down)

    def _hint_and_warning(self, surf, hint):
        x = self.rect.x + 392
        y = self.rect.y + 132
        for ln in _wrap(hint, 12, 214):
            draw_text(surf, ln, (x, y), 12, COL["muted"])
            y += 16
        w = self.warning()
        if w:
            y = self.rect.bottom - 14 - 16 * len(_wrap(w, 12, 190))
            draw_icon(surf, "warn", (x + 8, y + 8), 13, COL["red"])
            for ln in _wrap(w, 12, 190):
                draw_text(surf, ln, (x + 24, y), 12, COL["red"], True)
                y += 16

    def _draw_grid_labels(self, surf):
        draw_text(surf, "ĐẦU VÀO (INITIAL)", (self.init_pos[0], self.rect.y + 38), 12, COL["muted"], True)
        draw_text(surf, "ĐÍCH (GOAL)", (self.goal_pos[0], self.rect.y + 38), 12, COL["muted"], True)
        ax = self.init_pos[0] + GRID + 26
        scaling.line(surf, COL["muted"], (ax - 9, self.init_pos[1] + GRID // 2), (ax + 9, self.init_pos[1] + GRID // 2), 2)
        scaling.polygon(surf, COL["muted"], [(ax + 10, self.init_pos[1] + GRID // 2),
                                                 (ax + 3, self.init_pos[1] + GRID // 2 - 5),
                                                 (ax + 3, self.init_pos[1] + GRID // 2 + 5)])


# ------------------------------------------------------------------ 8-puzzle
class PuzzleInput(_BaseInput):
    def __init__(self, rect):
        super().__init__(rect)
        self.init = [v for row in PUZZLE_INIT for v in row]
        self.goal = [v for row in PUZZLE_GOAL for v in row]
        self.sel = None          # ("init"|"goal", index)
        self.hov = {}

    @staticmethod
    def _tuple(flat):
        return tuple(tuple(flat[r * 3:r * 3 + 3]) for r in range(3))

    def initial_state(self):
        return self._tuple(self.init)

    def goal_state(self):
        return self._tuple(self.goal)

    def warning(self):
        if not puzzle_solvable(self.initial_state(), self.goal_state()):
            return "Không giải được: đầu vào và đích khác tính chẵn lẻ (inversions)."
        return None

    def _cell_rect(self, which, i):
        ox, oy = self.init_pos if which == "init" else self.goal_pos
        r, c = divmod(i, 3)
        return pygame.Rect(ox + c * (CELL + CGAP), oy + r * (CELL + CGAP), CELL, CELL)

    def _grid(self, which):
        return self.init if which == "init" else self.goal

    def click(self, pos):
        if self.btn_random.hit(pos):
            self.init = [v for row in random_puzzle(self.goal_state()) for v in row]
            self.sel = None
            self.changed = True
            return True
        if self.btn_default.hit(pos):
            self.init = [v for row in PUZZLE_INIT for v in row]
            self.goal = [v for row in PUZZLE_GOAL for v in row]
            self.sel = None
            self.changed = True
            return True
        for which in ("init", "goal"):
            for i in range(9):
                if self._cell_rect(which, i).collidepoint(pos):
                    if self.sel is None or self.sel[0] != which:
                        self.sel = (which, i)
                    elif self.sel[1] == i:
                        self.sel = None
                    else:  # click ô thứ 2 -> hoán đổi
                        g = self._grid(which)
                        g[self.sel[1]], g[i] = g[i], g[self.sel[1]]
                        self.sel = None
                        self.changed = True
                    return True
        if self.rect.collidepoint(pos):
            self.sel = None
            return True
        return False

    def key(self, ev):
        if self.sel is None:
            return False
        ch = ev.unicode
        if ch and ch in "012345678":
            v = int(ch)
            which, i = self.sel
            g = self._grid(which)
            j = g.index(v)
            g[i], g[j] = g[j], g[i]
            self.changed = True
            return True
        if ev.key == pygame.K_ESCAPE:
            self.sel = None
            return True
        return False

    def draw(self, surf, dt, mouse):
        draw_panel(surf, self.rect, "Đầu vào", COL["orange"], subtitle="tùy chỉnh trạng thái đầu / đích")
        self._draw_grid_labels(surf)
        for which in ("init", "goal"):
            g = self._grid(which)
            for i in range(9):
                r = self._cell_rect(which, i)
                key = (which, i)
                hv = self.hov.get(key, 0.0)
                hv = approach(hv, 1.0 if r.collidepoint(mouse) else 0.0, dt, 16)
                self.hov[key] = hv
                selected = self.sel == key
                v = g[i]
                if v == 0:
                    col = (14, 18, 30)
                else:
                    col = mix((58, 78, 150), (82, 106, 190), hv)
                rrect(surf, col, r, 9, 2 if selected else 1,
                      COL["orange"] if selected else mix(COL["border"], COL["accent"], hv))
                if v:
                    draw_text(surf, str(v), r.center, 22, COL["white"], True, "center")
                else:
                    draw_text(surf, "0", r.center, 16, COL["muted"], True, "center")
        for b in self.buttons:
            b.draw(surf)
        self._hint_and_warning(surf, "Click 2 ô để hoán đổi, hoặc click 1 ô rồi gõ phím 0–8 (0 = ô trống).")


# ------------------------------------------------------------------ Vacuum
class VacuumInput(_BaseInput):
    def __init__(self, rect):
        super().__init__(rect)
        self.loc = VACUUM_INIT[0]
        self.rooms = list(VACUUM_INIT[1])
        self.goal = list(VACUUM_GOAL_ROOMS)
        self.hov = {}

    def initial_state(self):
        return (self.loc, tuple(self.rooms))

    def goal_state(self):
        return tuple(self.goal)

    def warning(self):
        if not vacuum_reachable(self.initial_state(), self.goal_state()):
            return "Không đạt được: robot chỉ hút bụi, không làm bẩn lại phòng đã Clean."
        return None

    BOX = 62

    def _room_rect(self, which, i):
        ox, oy = self.init_pos if which == "init" else self.goal_pos
        return pygame.Rect(ox + i * (self.BOX + 10), oy, self.BOX, self.BOX)

    def _robot_rect(self, i):
        r = self._room_rect("init", i)
        return pygame.Rect(r.x, r.bottom + 8, r.w, 24)

    def click(self, pos):
        if self.btn_random.hit(pos):
            import random
            self.loc = random.choice("AB")
            self.rooms = [random.choice(["Dirty", "Clean"]) for _ in range(2)]
            if self.rooms == ["Clean", "Clean"]:
                self.rooms[random.randint(0, 1)] = "Dirty"
            self.goal = ["Clean", "Clean"]
            self.changed = True
            return True
        if self.btn_default.hit(pos):
            self.loc = VACUUM_INIT[0]
            self.rooms = list(VACUUM_INIT[1])
            self.goal = list(VACUUM_GOAL_ROOMS)
            self.changed = True
            return True
        for i in range(2):
            if self._room_rect("init", i).collidepoint(pos):
                self.rooms[i] = "Clean" if self.rooms[i] == "Dirty" else "Dirty"
                self.changed = True
                return True
            if self._robot_rect(i).collidepoint(pos):
                self.loc = "AB"[i]
                self.changed = True
                return True
            if self._room_rect("goal", i).collidepoint(pos):
                self.goal[i] = "Clean" if self.goal[i] == "Dirty" else "Dirty"
                self.changed = True
                return True
        return False

    def key(self, ev):
        return False

    def _draw_room(self, surf, r, name, dirty, hv, robot=False):
        floor = (74, 60, 54) if dirty else (32, 84, 76)
        rrect(surf, mix(floor, COL["white"], hv * 0.12), r, 10, 1, mix(COL["border"], COL["accent"], hv))
        draw_text(surf, name, (r.x + 7, r.y + 4), 11, COL["muted"], True)
        if dirty:
            for dx, dy, rad in ((.3, .6, 4), (.62, .72, 3), (.5, .42, 3.5), (.75, .5, 2.5)):
                scaling.circle(surf, (170, 124, 78), (r.x + r.w * dx, r.y + r.h * dy), rad)
        label = "Dirty" if dirty else "Clean"
        draw_text(surf, label, (r.centerx, r.bottom - 6), 11, COL["orange"] if dirty else COL["green"], True, "midbottom")
        if robot:
            scaling.circle(surf, COL["accent"], (r.centerx, r.y + r.h * .42), 11)
            scaling.circle(surf, COL["white"], (r.centerx, r.y + r.h * .42), 11, 1)
            scaling.circle(surf, COL["green"], (r.centerx, r.y + r.h * .42), 3)

    def draw(self, surf, dt, mouse):
        draw_panel(surf, self.rect, "Đầu vào", COL["orange"], subtitle="tùy chỉnh trạng thái đầu / đích")
        self._draw_grid_labels(surf)
        for i in range(2):
            r = self._room_rect("init", i)
            hv = self.hov[("i", i)] = approach(self.hov.get(("i", i), 0.0), 1.0 if r.collidepoint(mouse) else 0.0, dt, 16)
            self._draw_room(surf, r, "AB"[i], self.rooms[i] == "Dirty", hv, robot=self.loc == "AB"[i])
            rb = self._robot_rect(i)
            on = self.loc == "AB"[i]
            hb = self.hov[("r", i)] = approach(self.hov.get(("r", i), 0.0), 1.0 if rb.collidepoint(mouse) else 0.0, dt, 16)
            rrect(surf, COL["accent"] if on else mix((30, 36, 57), (46, 56, 88), hb), rb, 8, 1,
                  COL["accent"] if on else COL["border"])
            draw_text(surf, "Robot", rb.center, 12, COL["white"] if on else COL["muted"], True, "center")
            g = self._room_rect("goal", i)
            hg = self.hov[("g", i)] = approach(self.hov.get(("g", i), 0.0), 1.0 if g.collidepoint(mouse) else 0.0, dt, 16)
            self._draw_room(surf, g, "AB"[i], self.goal[i] == "Dirty", hg)
        draw_text(surf, "(vị trí robot ở đích: bất kỳ)", (self.goal_pos[0], self.goal_pos[1] + self.BOX + 12), 11, COL["muted"])
        for b in self.buttons:
            b.draw(surf)
        self._hint_and_warning(surf, "Click phòng để đổi Dirty/Clean; bấm nút Robot để đặt vị trí xuất phát.")


# ##############################################################################
# Bảng Code: tô màu cú pháp, highlight dòng đang chạy
# ##############################################################################

GAME_NAMES = {"puzzle": "8-Puzzle", "vacuum": "Vacuum Robot"}

# màu cú pháp
SYN = dict(
    kw=(198, 120, 221),
    fn=(97, 175, 239),
    builtin=(86, 182, 194),
    str=(152, 195, 121),
    num=(209, 154, 102),
    com=(106, 116, 142),
    text=(214, 219, 232),
    op=(171, 178, 196),
)
KEYWORDS = {"def", "if", "elif", "return", "while", "for", "in", "not", "and", "lambda", "is", "None", "True", "False", "continue"}
BUILTINS = {"set", "all", "len", "float"}
TOKEN_RE = re.compile(r'(#.*$)|("[^"]*"|\'[^\']*\')|(\b\d+\b)|([A-Za-z_]\w*)|(\s+)|(.)')

_mono = {}


def mono_font(size):
    f = _mono.get(size)
    if f is None:
        path = pygame.font.match_font("consolas") or pygame.font.match_font("couriernew")
        f = pygame.font.Font(path, size) if path else pygame.font.SysFont("monospace", size)
        _mono[size] = f
    return f


# ------------------------------------------------------------------ view
class CodeView:
    LINE_H = 19
    FONT = 13

    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.area = pygame.Rect(self.rect.x + 12, self.rect.y + 44, self.rect.w - 24, self.rect.h - 56)
        self.lines = []
        self.tag_idx = {}
        self.trace = []
        self.pos = 0.0
        self.start = 0.0
        self.end = 0.0
        self.t = 0.0
        self.per_line = 0.07
        self.top = 0.0
        self.top_t = 0.0
        self.last_active = None
        self.title = ""
        self._tok_cache = {}

    @property
    def visible(self):
        return max(1, (self.area.h - 8) // self.LINE_H)

    def set_code(self, lines, title):
        self.lines = lines
        self.title = title
        self.tag_idx = {}
        for i, (_, tag) in enumerate(lines):
            if tag:
                self.tag_idx.setdefault(tag, []).append(i)
        self._tok_cache = {}
        self.last_active = None

    def set_trace(self, trace, animate=True, per_line=0.07, start=0, end=None):
        """Highlight dòng trace[end]. animate=True: chạy highlight lần lượt từ trace[start] tới trace[end]."""
        self.trace = trace
        self.per_line = max(0.001, per_line)
        self.t = 0.0
        self.end = float(max(0, len(trace) - 1) if end is None else max(0, end))
        self.start = float(clamp(start, 0, self.end))
        self.pos = self.start if animate else self.end

    @property
    def animating(self):
        return self.pos < self.end

    def finish(self):
        self.pos = self.end

    def scroll(self, dy):
        mx = max(0, len(self.lines) - self.visible)
        new = clamp(self.top_t + dy * 3, 0, mx)
        changed = new != self.top_t
        self.top_t = new
        return changed

    def current(self):
        if not self.trace:
            return None, ""
        return self.trace[int(self.pos)]

    def update(self, dt):
        if self.animating:
            self.t += dt
            self.pos = min(self.end, self.start + self.t / self.per_line)
        tag, _ = self.current()
        idxs = self.tag_idx.get(tag)
        if idxs and idxs[0] != self.last_active:
            self.last_active = idxs[0]
            a, b = idxs[0], idxs[-1]
            vis = self.visible
            if a < self.top_t + 2:
                self.top_t = max(0, a - 2)
            elif b > self.top_t + vis - 3:
                self.top_t = min(max(0, len(self.lines) - vis), b - vis + 3)
        self.top = approach(self.top, self.top_t, dt, 12)

    def active_line_no(self):
        tag, _ = self.current()
        idxs = self.tag_idx.get(tag)
        return idxs[0] + 1 if idxs else None

    def _tokens(self, text):
        toks = self._tok_cache.get(text)
        if toks is not None:
            return toks
        toks = []
        for m in TOKEN_RE.finditer(text):
            com, st, num, ident, ws, other = m.groups()
            if com:
                toks.append((com, SYN["com"]))
            elif st:
                toks.append((st, SYN["str"]))
            elif num:
                toks.append((num, SYN["num"]))
            elif ident:
                if ident in KEYWORDS:
                    c = SYN["kw"]
                elif ident in BUILTINS:
                    c = SYN["builtin"]
                elif text[m.end():m.end() + 1] == "(":
                    c = SYN["fn"]
                else:
                    c = SYN["text"]
                toks.append((ident, c))
            elif ws:
                toks.append((ws, None))
            else:
                toks.append((other, SYN["op"]))
        self._tok_cache[text] = toks
        return toks

    def draw(self, surf):
        tag, note = self.current()
        ln = self.active_line_no()
        draw_panel(surf, self.rect, "Code", COL["accent2"], subtitle=self.title,
                   badge=f"dòng {ln}" if ln else None, badge_color=COL["accent2"])
        rrect(surf, (13, 16, 27), self.area, 10, 1, COL["border"])
        sk = getattr(surf, "k", 1.0)          # tỉ lệ pixel thật / đơn vị logic
        font = mono_font(scaling.px_size(self.FONT, sk))
        cw = font.size("M")[0] / sk             # bề rộng 1 ký tự, đơn vị logic
        gutter = 36
        old = surf.get_clip()
        surf.set_clip(self.area.inflate(-2, -2).clip(old))

        active = set(self.tag_idx.get(tag, [])) if tag else set()
        done_tags = {tg for tg, _ in self.trace[:int(self.pos)]}
        done = set()
        for tg in done_tags:
            done.update(self.tag_idx.get(tg, []))
        if tag in ("return_child", "return_pop", "init_return"):
            hcol = COL["green"]
        elif tag == "return_none":
            hcol = COL["orange"]
        else:
            hcol = COL["accent"]

        first = int(self.top)
        frac = self.top - first
        y0 = self.area.y + 6 - frac * self.LINE_H
        for k in range(self.visible + 2):
            i = first + k
            if i >= len(self.lines):
                break
            y = y0 + k * self.LINE_H
            row = pygame.Rect(self.area.x + 2, round(y), self.area.w - 4, self.LINE_H)
            if i in active:
                scaling.rect(surf, mix((13, 16, 27), hcol, 0.28), row)
                scaling.rect(surf, hcol, (row.x, row.y, 3, row.h))
            elif i in done:
                scaling.rect(surf, mix((13, 16, 27), hcol, 0.09), row)
            num_col = COL["white"] if i in active else (88, 98, 128)
            draw_text(surf, str(i + 1), (self.area.x + gutter - 8, row.centery), 12, num_col, False, "midright")
            x = self.area.x + gutter
            text = self.lines[i][0]
            for tok, col in self._tokens(text):
                if col is not None:
                    s = font.render(tok, True, col)
                    scaling.blit_px(surf, s, (round(x * sk), round((row.y + self.LINE_H / 2) * sk - s.get_height() / 2)))
                x += cw * len(tok)
            if i in active and note and i == min(active):
                nw = text_width(note, 12, True) + 16
                nx = max(x + 14, self.area.right - nw - 10)
                pill = pygame.Rect(nx, row.y + 1, nw, self.LINE_H - 2)
                rrect(surf, mix((13, 16, 27), hcol, 0.45), pill, 8)
                draw_text(surf, note, pill.center, 12, COL["white"], True, "center")
        surf.set_clip(old)

        # thanh cuộn
        mx = len(self.lines) - self.visible
        if mx > 0:
            track = pygame.Rect(self.area.right - 6, self.area.y + 6, 3, self.area.h - 12)
            th = max(24, track.h * self.visible / len(self.lines))
            ty = track.y + (track.h - th) * (self.top / mx)
            rrect(surf, mix(COL["panel3"], COL["accent2"], 0.6), pygame.Rect(track.x, ty, 3, th), 2)


# ##############################################################################
# App: bố cục, xử lý sự kiện, vòng lặp chính
# ##############################################################################

W = 1220                 # chiều rộng trang (không tính thanh cuộn)
SB_W = 14                # rãnh thanh cuộn nằm ngoài trang, bên phải
DEFAULT_VIEW_H = 720
# Hệ số phóng to giao diện, nhân thêm vào tỉ lệ scale của Windows (1.0 = đúng tỉ lệ hệ thống).
# Cửa sổ có thể kéo giãn: giao diện tự co/giãn theo chiều rộng cửa sổ.
UI_SCALE = 1.0
HERE = os.path.dirname(os.path.abspath(__file__))

# ---- bố cục trang (cuộn dọc nếu cửa sổ không đủ cao)
#  hàng 1: Bàn chơi | Code
#  hàng 2: Node | Frontier | Empty
#  hàng 3: Đầu vào | Đường đi
# Lề ngoài và khoảng cách giữa các bảng đều bằng GAP.
GAP = 16
HEADER_H = 76                                   # header nằm trong [GAP, HEADER_H]
_ROW1_Y = HEADER_H + GAP
_ROW2_Y = _ROW1_Y + 392 + GAP
_ROW3_Y = _ROW2_Y + 216 + GAP
_LEFT_W = 640
_RIGHT_X = GAP + _LEFT_W + GAP
_RIGHT_W = W - GAP - _RIGHT_X
_LIST_W = (W - 2 * GAP - 2 * GAP - 300) // 2
BOARD_RECT = pygame.Rect(GAP, _ROW1_Y, _LEFT_W, 392)
CODE_RECT = pygame.Rect(_RIGHT_X, _ROW1_Y, _RIGHT_W, 392)
NODE_RECT = pygame.Rect(GAP, _ROW2_Y, 300, 216)
FRONT_RECT = pygame.Rect(NODE_RECT.right + GAP, _ROW2_Y, _LIST_W, 216)
EMPTY_RECT = pygame.Rect(FRONT_RECT.right + GAP, _ROW2_Y, W - GAP - FRONT_RECT.right - GAP, 216)
INPUT_RECT = pygame.Rect(GAP, _ROW3_Y, _LEFT_W, 290)
PATH_RECT = pygame.Rect(_RIGHT_X, _ROW3_Y, _RIGHT_W, 290)
PAGE_H = INPUT_RECT.bottom + GAP

GAMES = [("puzzle", "8-Puzzle"), ("vacuum", "Vacuum Robot")]
ALGOS = [("BFS", "BFS"), ("DFS", "DFS"), ("UCS", "UCS")]

STUDENT_NAME = "Mai Quốc Bảo"
STUDENT_ID = "24110080"

# tốc độ Auto (số bước trên giây)
MIN_SPS, MAX_SPS, DEFAULT_SPS = 1, 240, 4      # Auto: số dòng code / giây
CODE_LINE_TIME = 0.07      # thời gian highlight mỗi dòng code khi bấm "Node tiếp"


def load_logo():
    p = os.path.join(HERE, "ute_logo.png")
    if os.path.exists(p):
        return pygame.image.load(p).convert_alpha()
    return None


def wrap_text(text, size, width, bold=False):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_width(t, size, bold) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class App:
    def __init__(self, screen):
        self.screen = screen
        self.view_h = screen.get_height()
        self.mouse_fn = pygame.mouse.get_pos        # trả về toạ độ chuột (đơn vị logic)
        self.page = scaling.Surface((W, PAGE_H))
        self.scroll = 0.0
        self.scroll_t = 0.0
        self.sb_drag = None
        self.logo = load_logo()
        self.time = 0.0
        self.dt = 1 / 60
        self.game = "puzzle"
        self.algo = "BFS"

        # ---- header
        # Thêm trò chơi / thuật toán mới: chỉ cần thêm vào 2 danh sách này (id, tên hiển thị)
        self.game_list = GAMES
        self.algo_list = ALGOS
        self.dd_game = Dropdown((330, HEADER_H - 40, 330, 40), [n for _, n in GAMES], 0)
        self.dd_algo = Dropdown((690, HEADER_H - 40, 200, 40), [n for _, n in ALGOS], 0)

        # ---- điều khiển
        by = BOARD_RECT.bottom - 58
        x = BOARD_RECT.x + 16
        row = []
        for w, label, icon, kind in ((84, "Reset", "reset", "secondary"),
                                     (84, "Prev", "up", "secondary"),       # lùi 1 dòng code
                                     (88, "Next", "down", "primary"),       # chạy 1 dòng code
                                     (114, "Node tiếp", "next", "secondary"),  # chạy hết 1 vòng lặp
                                     (86, "Auto", "play", "success"),
                                     (104, "Kết quả", "skip", "secondary")):
            row.append(Button((x, by, w, 42), label, icon, kind))
            x += w + 8
        self.btn_reset, self.btn_prev, self.btn_next, self.btn_node, self.btn_auto, self.btn_skip = row
        # thanh tốc độ Auto nằm ở cột thông tin (chỗ của nút Phát lại khi chưa tìm thấy goal)
        self.slider = Slider((0, 0, 100, 10), (DEFAULT_SPS - MIN_SPS) / (MAX_SPS - MIN_SPS))
        self.btn_replay = Button((0, 0, 100, 30), "Phát lại", "play", "secondary")
        self.btn_path = Button((0, 0, 100, 30), "Đường đi", "down", "secondary")
        self.controls = row + [self.btn_replay, self.btn_path]

        # ---- đầu vào / bàn / danh sách / code
        self.inputs = {"puzzle": PuzzleInput(INPUT_RECT), "vacuum": VacuumInput(INPUT_RECT)}
        self.pboard = PuzzleBoard()
        self.vboard = VacuumBoard()
        self.front_list = CardList(FRONT_RECT, COL["orange"])
        self.empty_list = CardList(EMPTY_RECT, COL["gray"])
        self.path_list = CardList(PATH_RECT, COL["green"], cw=64, ch=86, gap=12, top=80)
        self.code = CodeView(CODE_RECT)

        self.auto = False
        self.fast = False          # chế độ "Kết quả": chạy nhanh qua nhiều frame, UI không bị đơ
        self.auto_acc = 0.0
        self.step_age = 10.0
        self.node_age = 10.0
        self._shown_node = None
        self.play_states = None
        self.play_idx = 0
        self.play_t = 0.0
        self.printed_goal = None
        self.rebuild(snap=True)

    # ------------------------------------------------------------ trạng thái
    @property
    def inp(self):
        return self.inputs[self.game]

    @property
    def blocked(self):
        return self.inp.warning() is not None

    @property
    def steps_per_sec(self):
        return round(MIN_SPS + self.slider.value * (MAX_SPS - MIN_SPS))

    def set_view(self, screen):
        """Đổi kích thước vùng nhìn (khi cửa sổ bị kéo giãn)."""
        self.screen = screen
        self.view_h = screen.get_height()
        if self.page.k != screen.k:
            self.page = scaling.Surface((W, PAGE_H))
        self.scroll_t = clamp(self.scroll_t, 0, self.max_scroll)
        self.scroll = clamp(self.scroll, 0, self.max_scroll)

    @property
    def max_scroll(self):
        return max(0, PAGE_H - self.view_h)

    def rebuild(self, snap=False):
        inp = self.inp
        init, goal = inp.initial_state(), inp.goal_state()
        if self.game == "puzzle":
            self.problem = make_puzzle_problem(init, goal)
        else:
            self.problem = make_vacuum_problem(init, goal)
        self.machine = SearchMachine(self.problem, self.algo, tracer=step_trace)
        self.auto = False
        self.fast = False
        self.play_states = None
        self.step_age = 10.0
        self.front_list.reset_scroll()
        self.empty_list.reset_scroll()
        self.path_list.reset_scroll()
        self.code.set_code(code_lines(self.algo, self.game, init, goal), f"{self.algo} · {GAME_NAMES[self.game]}")
        self.code.set_trace(init_trace(self.algo, self.machine.found is not None), animate=True, per_line=CODE_LINE_TIME)
        self._sync_board(snap)

    def display_node(self):
        return self.machine.found or self.machine.current

    def display_state(self):
        if self.play_states is not None:
            return self.play_states[self.play_idx]
        n = self.display_node()
        return n.state if n else self.problem.initial_state

    def _sync_board(self, snap=False):
        st = self.display_state()
        node = self.display_node() if self.play_states is None else None
        if self.game == "puzzle":
            self.pboard.set_state(st, self.inp.goal_state(), snap)
        else:
            self.vboard.set_state(st, node, snap)

    def stepped(self, animate=False, from_line=0):
        """Cập nhật giao diện sau khi máy tìm kiếm đổi vị trí.
        animate=True (Node tiếp): highlight chạy lần lượt từ dòng from_line tới dòng cuối của vòng lặp."""
        m = self.machine
        self.step_age = 0.0
        if m.current is not self._shown_node:
            self._shown_node = m.current
            self.node_age = 0.0
        self.front_list.reset_scroll()
        self.empty_list.reset_scroll()
        self.path_list.reset_scroll()
        self.play_states = None
        self._sync_board()
        st, i = m.active_pos()
        if st is None:
            self.code.set_trace(init_trace(self.algo, m.found is not None), animate=False)
        else:
            self.code.set_trace(m.trace_of(st), animate=animate, per_line=CODE_LINE_TIME,
                                start=from_line, end=i)
        if m.found is not None and m.found is not m.current:      # BFS: cuộn tới thẻ goal ở cuối Frontier
            fl = self.front_list
            fl.scroll(m.frontier_len // fl.cols - fl.rows_visible + 1, m.frontier_len + 1)
        if m.found is not None and self.printed_goal is not m.found:
            self.printed_goal = m.found
            self.print_path()

    @property
    def is_ucs(self):
        return self.algo == "UCS"

    def print_path(self):
        """In đường đi ra terminal giống output của notebook."""
        m = self.machine
        total = f", total cost = {m.found.path_cost}" if self.is_ucs else ""
        out = [f"\n===== {self.algo} - {GAME_NAMES[self.game]}: path = {len(m.path_actions())} steps{total} ====="]
        acts = [None] + m.path_actions()
        costs = solution_costs(m.found)
        for i, st in enumerate(m.path_states()):
            out.append(f"Step {i}:" + (f"  ({acts[i]})" if acts[i] else "")
                       + (f"  g = {costs[i]}" if self.is_ucs else ""))
            if self.game == "puzzle":
                out += ["[" + " ".join(map(str, row)) + "]" for row in st]
            else:
                loc, (ra, rb) = st
                out.append(f"Current position: Room {loc} | Room A: {ra} | Room B: {rb}")
            out.append("")
        try:
            print("\n".join(out), flush=True)
        except (OSError, ValueError, UnicodeError):
            pass      # không có terminal (vd. chạy bằng pythonw) thì bỏ qua

    # ------------------------------------------------------------ hành động
    def do_next(self):
        """Next: chạy đúng 1 dòng code."""
        if self.blocked:
            return False
        ok = self.machine.line_next()
        if ok:
            self.stepped()
        else:
            self.auto = False
        return ok

    def do_node(self):
        """Node tiếp: chạy hết vòng lặp hiện tại (xét xong 1 node)."""
        m = self.machine
        if self.blocked or not m.can_next():
            return False
        self.auto = False
        self.fast = False
        start = m.sub          # đang chạy dở thì highlight tiếp từ dòng kế tiếp
        m.next()
        self.stepped(animate=True, from_line=start)
        return True

    def do_prev(self):
        """Prev: lùi lại 1 dòng code."""
        self.auto = False
        self.fast = False
        if self.machine.line_prev():
            self.stepped()

    def do_node_prev(self):
        """Lùi về đầu vòng lặp (hoặc hoàn tác cả vòng lặp trước)."""
        self.auto = False
        self.fast = False
        if self.machine.prev():
            self.stepped()

    def do_skip(self):
        """Bật/tắt chạy nhanh tới kết quả (chạy dần qua từng frame)."""
        if self.fast:
            self.fast = False
            return
        if self.blocked or not self.machine.can_next():
            return
        self.auto = False
        self.fast = True

    def finish_now(self):
        """Chạy thẳng tới kết quả trong 1 lần (dùng cho test)."""
        self.fast = False
        self.machine.run_to_end(budget=60)
        self.stepped(animate=False)

    def toggle_auto(self):
        self.fast = False
        if self.auto:
            self.auto = False
        elif self.machine.can_next() and not self.blocked:
            self.auto = True
            self.auto_acc = 0.0

    def start_replay(self):
        if self.machine.found is None:
            return
        self.play_states = self.machine.path_states()
        self.play_idx = 0
        self.play_t = 0.0
        self.auto = False
        self._sync_board()

    def scroll_to(self, y):
        self.scroll_t = clamp(y, 0, self.max_scroll)

    def set_game(self, g):
        if g != self.game:
            self.game = g
            self.dd_game.selected = [k for k, _ in self.game_list].index(g)
            self.rebuild(snap=True)

    def set_algo(self, a):
        if a != self.algo:
            self.algo = a
            self.dd_algo.selected = [k for k, _ in self.algo_list].index(a)
            self.rebuild()

    # ------------------------------------------------------------ sự kiện
    def to_page(self, pos):
        return pos[0], pos[1] + int(round(self.scroll))

    def _sb_geom(self):
        track = pygame.Rect(W + (SB_W - 8) // 2, 6, 8, self.view_h - 12)
        th = max(40, track.h * self.view_h / PAGE_H)
        ty = track.y + (track.h - th) * (self.scroll / self.max_scroll if self.max_scroll else 0)
        return track, pygame.Rect(track.x, ty, track.w, th)

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.max_scroll and ev.pos[0] >= W:
                track, thumb = self._sb_geom()
                if not thumb.collidepoint(ev.pos):
                    frac = (ev.pos[1] - track.y - thumb.h / 2) / max(1, track.h - thumb.h)
                    self.scroll_to(frac * self.max_scroll)
                    self.scroll = self.scroll_t
                    track, thumb = self._sb_geom()
                self.sb_drag = ev.pos[1] - thumb.y
                return
            self.click(self.to_page(ev.pos))
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.slider.drag = False
            self.sb_drag = None
        elif ev.type == pygame.MOUSEMOTION:
            if self.sb_drag is not None:
                track, thumb = self._sb_geom()
                frac = (ev.pos[1] - self.sb_drag - track.y) / max(1, track.h - thumb.h)
                self.scroll_to(frac * self.max_scroll)
                self.scroll = self.scroll_t
            elif self.slider.drag:
                self.slider.set_from_x(ev.pos[0])
        elif ev.type == pygame.MOUSEWHEEL:
            self.wheel(self.to_page(self.mouse_fn()), -ev.y)
        elif ev.type == pygame.KEYDOWN:
            self.key(ev)

    def wheel(self, pos, dy):
        """Cuộn bảng dưới chuột trước; nếu bảng đã tới đầu/cuối thì cuộn cả trang (riêng bảng Code thì không)."""
        m = self.machine
        handled = False
        if FRONT_RECT.collidepoint(pos):
            handled = self.front_list.scroll(dy, m.frontier_len + (1 if m.found and m.found is not m.current else 0))
        elif EMPTY_RECT.collidepoint(pos):
            handled = self.empty_list.scroll(dy, len(m.explored))
        elif PATH_RECT.collidepoint(pos):
            handled = self.path_list.scroll(dy, len(m.path_states()))
        elif CODE_RECT.collidepoint(pos):
            # chuột trong bảng Code: chỉ cuộn bảng Code, kể cả khi đã tới đầu/cuối (không cuộn cả trang)
            self.code.scroll(dy)
            handled = True
        if not handled:
            self.scroll_to(self.scroll_t + dy * 70)

    def key(self, ev):
        if self.inp.key(ev):
            self.after_input()
            return
        shift = ev.mod & pygame.KMOD_SHIFT
        if ev.key == pygame.K_RIGHT:
            self.auto = False
            self.do_node() if shift else self.do_next()
        elif ev.key == pygame.K_LEFT:
            self.do_node_prev() if shift else self.do_prev()
        elif ev.key == pygame.K_SPACE:
            self.toggle_auto()
        elif ev.key == pygame.K_ESCAPE:
            self.dd_game.open = self.dd_algo.open = False
        elif ev.key == pygame.K_r:
            self.rebuild()
        elif ev.key == pygame.K_DOWN:
            self.scroll_to(self.scroll_t + 70)
        elif ev.key == pygame.K_UP:
            self.scroll_to(self.scroll_t - 70)
        elif ev.key == pygame.K_PAGEDOWN:
            self.scroll_to(self.scroll_t + self.view_h * 0.8)
        elif ev.key == pygame.K_PAGEUP:
            self.scroll_to(self.scroll_t - self.view_h * 0.8)
        elif ev.key == pygame.K_HOME:
            self.scroll_to(0)
        elif ev.key == pygame.K_END:
            self.scroll_to(self.max_scroll)

    def after_input(self):
        if self.inp.changed:
            self.inp.changed = False
            self.rebuild()

    def click(self, pos):
        # dropdown: khi đang mở thì chiếm sự kiện click trước
        for dd, other, setter, lst in ((self.dd_game, self.dd_algo, self.set_game, self.game_list),
                                       (self.dd_algo, self.dd_game, self.set_algo, self.algo_list)):
            consumed, idx = dd.click(pos)
            if dd.open:
                other.open = False
            if idx is not None:
                setter(lst[idx][0])
            if consumed:
                return
        if self.machine.found is None and self.slider.hit(pos):
            self.slider.drag = True
            self.slider.set_from_x(pos[0])
            return
        if self.btn_reset.hit(pos):
            self.rebuild()
        elif self.btn_prev.hit(pos):
            self.do_prev()
        elif self.btn_next.hit(pos):
            self.auto = False
            self.fast = False
            self.do_next()
        elif self.btn_node.hit(pos):
            self.do_node()
        elif self.btn_auto.hit(pos):
            self.toggle_auto()
        elif self.btn_skip.hit(pos):
            self.do_skip()
        elif self.btn_replay.hit(pos):
            self.start_replay()
        elif self.btn_path.hit(pos):
            self.scroll_to(PATH_RECT.y - 92)
        else:
            self.inp.click(pos)
            self.after_input()

    # ------------------------------------------------------------ cập nhật
    def update(self, dt, mouse, down):
        mouse = self.to_page(mouse)
        self.time += dt
        self.dt = dt
        self.step_age += dt
        self.node_age += dt
        m = self.machine
        self.inp.update(dt, mouse, down)

        if self.auto:
            interval = 1.0 / self.steps_per_sec
            self.auto_acc += dt
            n = 0
            while self.auto_acc >= interval and n < 8:
                self.auto_acc -= interval
                n += 1
                if not self.do_next():
                    break
            if not m.can_next():
                self.auto = False

        if self.fast:
            t0 = time.perf_counter()
            while m.can_next() and time.perf_counter() - t0 < 0.03:
                for _ in range(64):
                    if not m.next():
                        break
            self.stepped(animate=False)
            if not m.can_next():
                self.fast = False

        if self.play_states is not None:
            self.play_t += dt
            if self.play_t >= 0.75 and self.play_idx < len(self.play_states) - 1:
                self.play_t = 0.0
                self.play_idx += 1
                self._sync_board()

        # trạng thái nút
        self.btn_prev.enabled = m.can_prev()
        self.btn_next.enabled = m.can_next() and not self.blocked
        self.btn_node.enabled = m.can_next() and not self.blocked
        self.btn_skip.enabled = self.fast or (m.can_next() and not self.blocked)
        self.btn_skip.label = "Dừng" if self.fast else "Kết quả"
        self.btn_skip.icon = "pause" if self.fast else "skip"
        self.btn_skip.kind = "danger" if self.fast else "secondary"
        self.btn_auto.enabled = self.auto or (m.can_next() and not self.blocked)
        self.btn_auto.label = "Pause" if self.auto else "Auto"
        self.btn_auto.icon = "pause" if self.auto else "play"
        self.btn_auto.kind = "danger" if self.auto else "success"
        found = m.found is not None
        self.btn_replay.visible = found and self.play_states is None
        self.btn_path.visible = found
        ix, iw = self.info_x(), self.info_w()
        half = (iw - 8) // 2
        self.btn_replay.rect = pygame.Rect(ix, BOARD_RECT.y + 286, half, 30)
        self.btn_path.rect = pygame.Rect(ix + half + 8, BOARD_RECT.y + 286, iw - half - 8, 30)
        self.slider.rect = pygame.Rect(ix + 4, BOARD_RECT.y + 310, iw - 8, 10)
        for b in self.controls:
            b.update(dt, mouse, down)
        self.slider.update(dt, mouse)
        self.dd_game.update(dt, mouse)
        self.dd_algo.update(dt, mouse)

        (self.pboard if self.game == "puzzle" else self.vboard).update(dt)
        self.front_list.update(dt)
        self.empty_list.update(dt)
        self.path_list.update(dt)
        self.code.update(dt)
        self.scroll = approach(self.scroll, self.scroll_t, dt, 14)
        if abs(self.scroll - self.scroll_t) < 0.5:
            self.scroll = self.scroll_t

    def info_x(self):
        if self.game == "puzzle":
            return BOARD_RECT.x + 36 + self.pboard.size + 36
        return BOARD_RECT.x + 28 + self.vboard.width + 26

    def info_w(self):
        return BOARD_RECT.right - 18 - self.info_x()

    # ------------------------------------------------------------ vẽ
    def draw(self, mouse):
        s = self.page
        mouse = self.to_page(mouse)
        s.fill(COL["bg"])
        self.draw_header(s)
        self.draw_board_panel(s)
        self.code.draw(s)
        self.draw_node_panel(s)
        self.draw_lists(s)
        self.inp.draw(s, self.dt, mouse)
        self.draw_path_panel(s)
        # danh sách thả xuống vẽ sau cùng để nằm trên mọi thành phần
        self.dd_game.draw_list(s)
        self.dd_algo.draw_list(s)

        sy = int(round(self.scroll))
        self.screen.blit(s, (0, 0), pygame.Rect(0, sy, W, self.view_h))
        if self.screen.get_width() > W:
            self.screen.fill(COL["bg"], pygame.Rect(W, 0, self.screen.get_width() - W, self.view_h))
        if self.max_scroll:
            track, thumb = self._sb_geom()
            rrect(self.screen, (24, 29, 46), track, 3)
            hot = self.sb_drag is not None or pygame.Rect(W, 0, SB_W, self.view_h).collidepoint(
                self.mouse_fn())
            rrect(self.screen, mix(COL["panel3"], COL["accent"], 0.9 if hot else 0.5), thumb, 3)

    def draw_header(self, s):
        # logo + tên + MSSV (góc trái trên)
        badge = pygame.Rect(GAP, GAP, 60, HEADER_H - GAP)
        shadow(s, badge, 14, 10, 80)
        rrect(s, COL["white"], badge, 14)
        if self.logo:
            lh = 50
            lw = self.logo.get_width() * lh / self.logo.get_height()
            scaling.blit_image(s, self.logo, (badge.centerx - lw / 2, badge.centery - lh / 2, lw, lh))
        draw_text(s, STUDENT_NAME, (90, 19), 22, COL["text"], True)
        draw_text(s, f"MSSV: {STUDENT_ID}", (90, 49), 16, COL["accent"], True)

        draw_text(s, "TRÒ CHƠI", (self.dd_game.rect.x + 4, GAP), 11, COL["muted"], True)
        draw_text(s, "THUẬT TOÁN", (self.dd_algo.rect.x + 4, GAP), 11, COL["muted"], True)
        self.dd_game.draw(s)
        self.dd_algo.draw(s)

        # chip mô tả cấu trúc dữ liệu
        txt, sub = {"BFS": ("Queue · FIFO", "Duyệt theo chiều rộng"),
                    "DFS": ("Stack · LIFO", "Duyệt theo chiều sâu"),
                    "UCS": ("Priority Queue", "Tìm kiếm chi phí đồng nhất")}[self.algo]
        chip = pygame.Rect(W - GAP - 300, HEADER_H - 52, 300, 52)
        rrect(s, COL["panel"], chip, 14, 1, COL["border"])
        draw_text(s, f"{self.algo} — {sub}", (chip.x + 16, chip.y + 9), 14, COL["text"], True)
        draw_text(s, f"Frontier: {txt}  ·  check goal: " + ("khi sinh con" if self.algo == "BFS" else "khi lấy ra"),
                  (chip.x + 16, chip.y + 30), 12, COL["muted"])

    def draw_board_panel(self, s):
        m = self.machine
        draw_panel(s, BOARD_RECT, "Bàn chơi", COL["accent"],
                   badge="8-Puzzle" if self.game == "puzzle" else "Vacuum Robot")
        if self.game == "puzzle":
            self.pboard.draw(s, (BOARD_RECT.x + 36, BOARD_RECT.y + 50))
        else:
            self.vboard.draw(s, (BOARD_RECT.x + 28, BOARD_RECT.y + 52))

        ix, iy = self.info_x(), BOARD_RECT.y + 50
        iw = self.info_w()
        draw_text(s, "ĐÍCH (GOAL)", (ix, iy), 11, COL["muted"], True)
        gr = pygame.Rect(ix, iy + 18, 64, 64)
        goal = self.inp.goal_state()
        if self.game == "puzzle":
            paint_card(s, gr, "puzzle", goal, goal, COL["green"], 2)
        else:
            paint_card(s, gr, "vacuum", ("A", goal), None, COL["green"], 2)
            draw_text(s, "(robot ở đâu cũng được)", (gr.right + 10, gr.centery), 11, COL["muted"], False, "midleft")

        node = self.display_node()
        act = node.action if node and node.action else "—"
        if self.is_ucs and node:
            act = (f"{act} (+{node.path_cost - node.parent.path_cost}) · g={node.path_cost}" if node.parent
                   else f"— · g={node.path_cost}")
        rows = [
            ("Vòng lặp", str(m.iteration) + (" (đang chạy)" if m.sub else "")),
            ("Frontier", str(m.frontier_len)),
            ("Empty", str(len(m.explored))),
            ("Hành động", act),
        ]
        y = iy + 98
        for k, v in rows:
            draw_text(s, k, (ix, y), 14, COL["muted"])
            draw_text(s, v, (ix + iw, y), 14, COL["text"], True, "topright")
            scaling.line(s, COL["border"], (ix, y + 22), (ix + iw, y + 22))
            y += 26

        # pill trạng thái
        warn = self.inp.warning()
        if warn:
            text, color, icon = "Đầu vào không hợp lệ", COL["red"], "warn"
        elif self.fast:
            text, color, icon = f"Đang chạy nhanh… {m.cursor} bước", COL["accent"], "skip"
        elif self.play_states is not None:
            text, color, icon = f"Phát lại {self.play_idx}/{len(self.play_states) - 1}", COL["accent"], "play"
        elif m.found is not None:
            text, color, icon = f"Tìm thấy goal · {len(m.path_actions())} bước", COL["green"], "check"
            if self.is_ucs:
                text = f"Tìm thấy goal · chi phí {m.found.path_cost}"
        elif m.exhausted:
            text, color, icon = "Không có lời giải", COL["orange"], "warn"
        elif m.cursor == 0 and m.sub == 0:
            text, color, icon = "Sẵn sàng · bấm Next", COL["muted"], "next"
        else:
            text, color, icon = "Đang tìm kiếm…", COL["accent"], "play"
        pill = pygame.Rect(ix, BOARD_RECT.y + 250, iw, 28)
        rrect(s, mix(COL["panel"], color, 0.18), pill, 14, 1, mix(COL["panel"], color, 0.6))
        draw_icon(s, icon, (pill.x + 16, pill.centery), 11, color)
        draw_text(s, text, (pill.x + 30, pill.centery), 13, color, True, "midleft")

        scaling.line(s, COL["border"], (BOARD_RECT.x + 16, BOARD_RECT.bottom - 68),
                         (BOARD_RECT.right - 16, BOARD_RECT.bottom - 68))
        for b in self.controls:
            b.draw(s)
        if m.found is None:
            sr = self.slider.rect
            draw_text(s, "Tốc độ Auto", (ix, sr.y - 22), 12, COL["muted"], True)
            draw_text(s, f"{self.steps_per_sec} dòng/giây", (ix + iw, sr.y - 22), 12, COL["text"], True, "topright")
            self.slider.draw(s)

    def draw_node_panel(self, s):
        """Node = node vừa được LẤY RA khỏi Frontier (cũng là node mới nhất trong Empty)."""
        m = self.machine
        R = NODE_RECT
        draw_panel(s, R, "Node", COL["accent"], subtitle="vừa lấy ra khỏi Frontier")
        node = m.current
        goal = self.inp.goal_state()
        gl = goal if self.game == "puzzle" else None
        card = pygame.Rect(R.x + 18, R.y + 46, 84, 84)
        x = card.right + 16
        tw = R.right - 16 - x
        if node is None:
            paint_card(s, card, self.game, self.problem.initial_state, gl, COL["accent"], 2, alpha=140)
            draw_text(s, "Chưa bắt đầu", (x, card.y), 16, COL["text"], True)
            draw_text(s, "Root đang nằm", (x, card.y + 26), 13, COL["muted"])
            draw_text(s, "trong Frontier.", (x, card.y + 44), 13, COL["muted"])
            lines = wrap_text("Bấm Next để lấy node đầu tiên ra khỏi Frontier.", 13, R.w - 36)
        else:
            child_goal = m.found is not None and m.found is not node      # BFS: goal là node con
            is_goal = m.found is node                                     # DFS / root là goal
            fade = int(120 + 135 * min(1, self.node_age / 0.3))
            paint_card(s, card, self.game, node.state, gl, COL["green"] if is_goal else COL["accent"], 2, alpha=fade)
            tr = draw_text(s, f"Vòng lặp {m.iteration}", (x, card.y), 17,
                           COL["green"] if is_goal else COL["text"], True)
            if is_goal:
                pg = pygame.Rect(tr.right + 8, tr.y + 3, 48, 20)
                rrect(s, COL["green"], pg, 10)
                draw_text(s, "GOAL", pg.center, 11, COL["white"], True, "center")
            draw_text(s, f"Hành động: {node.action or '— (root)'}", (x, card.y + 28), 13, COL["muted"])
            draw_text(s, f"Độ sâu: {node_depth(node)}", (x, card.y + 47), 13, COL["muted"])
            if self.is_ucs:
                step_c = f" (+{node.path_cost - node.parent.path_cost})" if node.parent else ""
                draw_text(s, f"Chi phí g(n): {node.path_cost}{step_c}", (x, card.y + 66), 13, COL["orange"], True)
            st, i = m.active_pos()
            if child_goal:
                msg = f"Con '{m.found.action}' là goal → hiện ở cuối Frontier (thẻ GOAL) → dừng."
            elif st is not None:
                msg = explain(self.algo, m.trace_of(st), i)
            else:
                msg = ""
            lines = wrap_text(msg, 13, R.w - 36)
        y = card.bottom + 12
        for ln in lines[:4]:
            draw_text(s, ln, (R.x + 18, y), 13, COL["text"])
            y += 18

    def draw_lists(self, s):
        m = self.machine
        goal = self.inp.goal_state()
        gl = goal if self.game == "puzzle" else None
        pushed = m.pushed_kids()
        new_ids = {id(k) for k in pushed}
        # thẻ vừa được đẩy vào ở dòng code vừa chạy -> hiện dần; các thẻ mới khác trong vòng lặp giữ viền xanh
        st, i = m.active_pos()
        just_ids = set()
        if st is not None and pushed and m.ops_of(st)[i] == "push" and not self.code.animating:
            just_ids = {id(pushed[-1])}
        elif self.code.animating:
            just_ids = new_ids
        added_now = m.added_in_active()
        age = self.step_age

        # --- Frontier
        kind = {"BFS": "Queue · FIFO", "DFS": "Stack · LIFO", "UCS": "Priority Queue · g nhỏ nhất trước"}[self.algo]
        head_tag = {"BFS": "HEAD", "DFS": "TOP", "UCS": "MIN"}[self.algo]
        goal_node = m.found if (m.found is not None and m.found is not m.current) else None
        draw_panel(s, FRONT_RECT, "Frontier", COL["orange"],
                   subtitle=kind,
                   badge=f"{m.frontier_len} node" + (" + goal" if goal_node else ""),
                   badge_color=COL["orange"])

        def paint_front(surf, rect, node, idx):
            if node is goal_node:
                a = int(70 + 185 * min(1, age / 0.35))
                paint_card(surf, rect, self.game, node.state, gl, COL["green"], 2, a, "GOAL", COL["green"])
                return
            a, border, bw = 255, COL["border"], 1
            if id(node) in just_ids:
                a = int(70 + 185 * min(1, age / 0.35))
                border = mix(COL["green"], COL["border"], min(0.5, age / 1.6))
                bw = 2
            elif id(node) in new_ids:
                border = mix(COL["green"], COL["border"], 0.5)
                bw = 2
            tag = head_tag if idx == 0 else None
            paint_card(surf, rect, self.game, node.state, gl, border, bw, a, tag, COL["orange"],
                       node.path_cost if self.is_ucs else None)

        n_front = m.frontier_len

        def front_items(start, count):
            items = m.frontier_slice(start, count)
            if goal_node is not None and start + count > n_front >= start:
                items = items + [goal_node]
            return items

        total_front = n_front + (1 if goal_node is not None else 0)
        self.front_list.draw(s, total_front, front_items, paint_front, "Frontier đang rỗng")

        # --- Empty (đã thăm)
        def paint_empty(surf, rect, state, idx):
            fresh = idx == 0 and added_now
            a, border, bw = 255, COL["border"], 1
            if fresh:
                just = self.code.animating or (st is not None and m.ops_of(st)[i] == "add")
                if just:
                    a = int(70 + 185 * min(1, age / 0.35))
                border = mix(COL["accent"], COL["border"], min(0.5, age / 1.6) if just else 0.5)
                bw = 2
            cost = m.enodes[len(m.enodes) - 1 - idx].path_cost if self.is_ucs else None
            paint_card(surf, rect, self.game, state, gl, border, bw, a, "MỚI" if fresh else None, COL["accent"], cost)

        draw_panel(s, EMPTY_RECT, "Empty", COL["gray"], subtitle="đã thăm (explored)",
                   badge=f"{len(m.explored)} node", badge_color=COL["gray"])
        self.empty_list.draw(s, len(m.explored), m.explored_slice, paint_empty, "Chưa thăm node nào")

    def draw_path_panel(self, s):
        m = self.machine
        R = PATH_RECT
        states = m.path_states()
        acts = m.path_actions()
        draw_panel(s, R, "Đường đi", COL["green"], subtitle="từ trạng thái đầu đến goal",
                   badge=(f"{len(acts)} bước" + (f" · chi phí {m.found.path_cost}" if self.is_ucs else ""))
                   if m.found else None, badge_color=COL["green"])
        if m.found is None:
            msg = "Không có lời giải." if m.exhausted else "Chưa tìm thấy goal — đường đi sẽ hiện ở đây."
            draw_text(s, msg, (R.centerx, R.centery + 10), 14, COL["muted"], False, "center")
            return
        # dòng hành động
        x0, y0 = R.x + 18, R.y + 44
        lab = draw_text(s, "Hành động:", (x0, y0), 13, COL["muted"], True)
        maxw = R.right - 18 - (lab.right + 8)
        if not acts:
            text = "(trạng thái đầu đã là goal)"
        else:
            text = ""
            for i, a in enumerate(acts):
                t = a if i == 0 else text + " → " + a
                rest = len(acts) - i - 1
                suffix = f" … (+{rest})" if rest else ""
                if text_width(t + suffix, 13, True) > maxw:
                    text += f" … (+{len(acts) - i})"
                    break
                text = t
        draw_text(s, text, (lab.right + 8, y0), 13, COL["text"], True)

        gl = self.inp.goal_state() if self.game == "puzzle" else None
        costs = solution_costs(m.found)
        last_i = len(states) - 1
        cols = self.path_list.cols

        def paint_path(surf, rect, state, idx):
            card = pygame.Rect(rect.x, rect.y, 64, 64)
            is_last = idx == last_i
            border = COL["green"] if is_last else (COL["accent"] if idx == 0 else COL["border"])
            tag = "START" if idx == 0 else acts[idx - 1]
            if self.is_ucs and idx:
                tag += f" +{costs[idx] - costs[idx - 1]}"
            paint_card(surf, card, self.game, state, gl, border, 2 if (is_last or idx == 0) else 1, 255, tag,
                       COL["green"] if is_last else COL["accent"])
            label = f"Bước {idx}" + (" · GOAL" if is_last else "")
            if self.is_ucs:
                label = f"g={costs[idx]}" + (" · GOAL" if is_last else "")
            draw_text(surf, label, (card.centerx, card.bottom + 5), 11,
                      COL["green"] if is_last else COL["muted"], True, "midtop")
            if not is_last and (idx % cols) != cols - 1:
                ax, ay = card.right + 3, card.centery
                scaling.polygon(surf, COL["muted"], [(ax, ay - 4), (ax + 6, ay), (ax, ay + 4)])

        self.path_list.draw(s, len(states), lambda a, c: states[a:a + c], paint_path, "")


# ---------------------------------------------------------------------- main
def main():
    dpi = scaling.enable_hidpi()          # Windows không tự phóng to cửa sổ (nguyên nhân mờ)
    pygame.init()
    pygame.display.set_caption("Search Visualizer — BFS / DFS / UCS · Mai Quốc Bảo · 24110080")
    win_w, win_h = scaling.initial_window_size(W, PAGE_H, SB_W, UI_SCALE, DEFAULT_VIEW_H, dpi)
    win = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    try:
        p = os.path.join(HERE, "ute_logo.png")
        if os.path.exists(p):
            pygame.display.set_icon(pygame.image.load(p))
    except pygame.error:
        pass
    vp = scaling.Viewport(win, W, PAGE_H, SB_W, COL["bg"])
    app = App(vp.canvas)
    app.mouse_fn = lambda: vp.to_logic(pygame.mouse.get_pos())
    clock = pygame.time.Clock()
    mouse_events = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)
    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.VIDEORESIZE:
                win = pygame.display.get_surface()
                vp.win = win
                vp.resize(win.get_size())
                app.set_view(vp.canvas)
                continue
            if ev.type in mouse_events:
                d = dict(ev.dict)
                d["pos"] = tuple(int(v) for v in vp.to_logic(ev.pos))
                ev = pygame.event.Event(ev.type, d)
            app.handle_event(ev)
        mouse = app.mouse_fn()
        down = pygame.mouse.get_pressed()[0]
        app.update(dt, mouse, down)
        app.draw(mouse)
        vp.present()
        pygame.display.flip()


if __name__ == "__main__":
    main()
