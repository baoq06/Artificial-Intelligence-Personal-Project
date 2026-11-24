"""Tiện ích giao diện: theme, font, widget (Button, Segmented, Slider), panel."""
import math

import pygame

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
    s = render_text(txt, size, tuple(color), bold)
    r = s.get_rect(**{anchor: pos})
    if alpha is not None and alpha < 255:
        s = s.copy()
        s.set_alpha(max(0, int(alpha)))
    surf.blit(s, r)
    return r


def text_width(txt, size, bold=False):
    return get_font(size, bold).size(txt)[0]


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
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, width=border, border_radius=radius)


_shadow_cache = {}


def shadow(surf, rect, radius=12, spread=10, strength=70, offset=(0, 4)):
    rect = pygame.Rect(rect)
    key = (rect.w, rect.h, radius, spread, strength)
    img = _shadow_cache.get(key)
    if img is None:
        img = pygame.Surface((rect.w + spread * 2, rect.h + spread * 2), pygame.SRCALPHA)
        steps = spread
        for i in range(steps):
            a = int(strength * (1 - i / steps) ** 2 / 4)
            r = pygame.Rect(i, i, rect.w + (spread - i) * 2, rect.h + (spread - i) * 2)
            pygame.draw.rect(img, (0, 0, 0, a), r, border_radius=radius + spread - i)
        if len(_shadow_cache) > 300:
            _shadow_cache.clear()
        _shadow_cache[key] = img
    surf.blit(img, (rect.x - spread + offset[0], rect.y - spread + offset[1]))


def draw_icon(surf, name, center, size, color):
    cx, cy = center
    h = size / 2
    if name == "next":
        pygame.draw.polygon(surf, color, [(cx - h * .7, cy - h), (cx - h * .7, cy + h), (cx + h * .5, cy)])
        pygame.draw.rect(surf, color, (cx + h * .6, cy - h, max(2, size * .18), size))
    elif name == "prev":
        pygame.draw.polygon(surf, color, [(cx + h * .7, cy - h), (cx + h * .7, cy + h), (cx - h * .5, cy)])
        pygame.draw.rect(surf, color, (cx - h * .6 - max(2, size * .18), cy - h, max(2, size * .18), size))
    elif name == "play":
        pygame.draw.polygon(surf, color, [(cx - h * .6, cy - h), (cx - h * .6, cy + h), (cx + h * .8, cy)])
    elif name == "pause":
        w = max(3, size * .3)
        pygame.draw.rect(surf, color, (cx - h * .7, cy - h, w, size), border_radius=1)
        pygame.draw.rect(surf, color, (cx + h * .7 - w, cy - h, w, size), border_radius=1)
    elif name == "skip":
        pygame.draw.polygon(surf, color, [(cx - h, cy - h * .9), (cx - h, cy + h * .9), (cx, cy)])
        pygame.draw.polygon(surf, color, [(cx - h * .1, cy - h * .9), (cx - h * .1, cy + h * .9), (cx + h * .9, cy)])
    elif name == "reset":
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        pygame.draw.arc(surf, color, rect, 0.6, 5.6, 2)
        ax, ay = cx + h * math.cos(0.6), cy - h * math.sin(0.6)
        pygame.draw.polygon(surf, color, [(ax - 1, ay - 5), (ax + 5, ay + 1), (ax - 5, ay + 2)])
    elif name == "dice":
        r = pygame.Rect(0, 0, size, size)
        r.center = (cx, cy)
        pygame.draw.rect(surf, color, r, 2, border_radius=4)
        for dx, dy in ((-.32, -.32), (.32, .32), (0, 0), (.32, -.32), (-.32, .32)):
            pygame.draw.circle(surf, color, (cx + dx * size, cy + dy * size), 1.5)
    elif name == "home":
        pygame.draw.polygon(surf, color, [(cx - h, cy), (cx, cy - h), (cx + h, cy)], 2)
        pygame.draw.rect(surf, color, (cx - h * .6, cy, h * 1.2, h), 2)
    elif name == "check":
        pygame.draw.lines(surf, color, False, [(cx - h * .7, cy), (cx - h * .15, cy + h * .6), (cx + h * .8, cy - h * .6)], 3)
    elif name == "warn":
        pygame.draw.polygon(surf, color, [(cx, cy - h), (cx + h, cy + h * .8), (cx - h, cy + h * .8)], 2)
        pygame.draw.line(surf, color, (cx, cy - h * .3), (cx, cy + h * .25), 2)
        pygame.draw.circle(surf, color, (cx, cy + h * .55), 1.3)


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
        pygame.draw.circle(surf, (0, 0, 0), (kx, cy + 2), 9 + self.knob)
        pygame.draw.circle(surf, COL["white"], (kx, cy), 8 + self.knob * 1.5)
        pygame.draw.circle(surf, COL["accent"], (kx, cy), 4)


def draw_panel(surf, rect, title=None, dot=None, badge=None, badge_color=None, subtitle=None):
    rect = pygame.Rect(rect)
    shadow(surf, rect, 16, 14, 70, (0, 6))
    rrect(surf, COL["panel"], rect, 16, 1, COL["border"])
    if title:
        x = rect.x + 18
        if dot:
            pygame.draw.circle(surf, dot, (x + 4, rect.y + 20), 5)
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
        pygame.draw.lines(surf, COL["muted"], False, [(cx - 5, cy - d / 2 - 1), (cx, cy + d / 2 + 1), (cx + 5, cy - d / 2 - 1)], 2)

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
