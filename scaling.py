"""Scaling: giao diện sắc nét ở mọi kích thước cửa sổ và mọi tỉ lệ scale của màn hình (HiDPI).

Toàn bộ code giao diện vẫn dùng toạ độ "logic" (trang rộng 1220). Thay vì vẽ ở 1220px rồi phóng to ảnh
(làm mờ chữ, viền), ở đây:
  * enable_hidpi(): báo Windows là app tự xử lý DPI -> Windows không tự phóng to cửa sổ (nguyên nhân mờ).
  * Surface: Surface đo bằng đơn vị logic, mỗi đơn vị = k pixel thật (k chọn khớp đúng chiều rộng cửa sổ).
  * rect / circle / line / ... : thay cho pygame.draw.*, tự nhân toạ độ với k.
  * Chữ được render ở cỡ font * k (xem draw_text trong visualizer.py), ảnh co giãn từ ảnh gốc (blit_image).
=> Mọi thứ được vẽ thẳng ở độ phân giải của cửa sổ, không có bước phóng to ảnh nào.
"""
import ctypes
import sys

import pygame

S = 1.0           # tỉ lệ pixel thật / đơn vị logic cho các Surface tạo mới, đặt theo kích thước cửa sổ


def set_scale(s):
    global S
    S = float(s)


# ##############################################################################
# Báo Windows là app tự xử lý DPI
# ##############################################################################

def enable_hidpi():
    """Gọi trước pygame.init(). Trả về tỉ lệ scale của hệ thống (1.0 = 100%, 2.0 = 200%, ...)."""
    if sys.platform != "win32":
        return 1.0
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


def initial_window_size(page_w, page_h, sb_w, ui_scale=1.0, default_view_h=720, dpi=1.0):
    """Kích thước cửa sổ lúc mở app (pixel thật): cao vừa màn hình (chừa thanh taskbar), rộng theo trang."""
    info = pygame.display.Info()
    desk_h = info.current_h if info.current_h and info.current_h > 0 else (default_view_h + 100) * dpi
    sc = ui_scale * dpi
    win_h = int(max(480 * dpi, min(desk_h - 110 * dpi, page_h * sc)))
    win_w = round((page_w if win_h >= page_h * sc else page_w + sb_w) * sc)
    if info.current_w and info.current_w > 0:
        win_w = min(win_w, info.current_w)
    return win_w, win_h


# ##############################################################################
# Đổi toạ độ logic -> pixel thật
# ##############################################################################

def _k(surf):
    return getattr(surf, "k", 1.0)


def _pt(p, k):
    return (p[0] * k, p[1] * k)


def _rect(r, k):
    if isinstance(r, pygame.Rect):
        x, y, w, h = r.x, r.y, r.w, r.h
    elif len(r) == 2:
        (x, y), (w, h) = r
    else:
        x, y, w, h = r
    x0, y0 = round(x * k), round(y * k)
    return pygame.Rect(x0, y0, max(0, round((x + w) * k) - x0), max(0, round((y + h) * k) - y0))


def _width(w, k):
    return 0 if w <= 0 else max(1, round(w * k))


class Surface(pygame.Surface):
    """Surface đo bằng đơn vị logic; pixel thật = logic * k."""

    def __init__(self, size, flags=0, *args):
        self.k = S
        self._lsize = (size[0], size[1])
        super().__init__((max(1, round(size[0] * S)), max(1, round(size[1] * S))), flags, *args)

    def get_width(self):
        return self._lsize[0]

    def get_height(self):
        return self._lsize[1]

    def get_size(self):
        return self._lsize

    def get_rect(self, **kw):
        r = pygame.Rect(0, 0, round(self._lsize[0]), round(self._lsize[1]))
        for name, v in kw.items():
            setattr(r, name, v)
        return r

    def blit(self, source, dest, area=None, special_flags=0):
        k = self.k
        pos = (round(dest[0] * k), round(dest[1] * k))
        if isinstance(source, Surface):
            sk = source.k
            if abs(sk - k) > 1e-6:          # hiếm: surface tạo ở tỉ lệ cũ -> co giãn về tỉ lệ đích
                sz = source.get_size()
                source = pygame.transform.smoothscale(source, (max(1, round(sz[0] * k)), max(1, round(sz[1] * k))))
                sk = k
            if area is not None:
                area = _rect(area, sk)
            return pygame.Surface.blit(self, source, pos, area, special_flags)
        # ảnh pixel thường (chữ đã render ở độ phân giải thật): giữ nguyên kích thước
        return super().blit(source, pos, area, special_flags)

    def fill(self, color, rect=None, special_flags=0):
        return super().fill(color, None if rect is None else _rect(rect, self.k), special_flags)

    def set_clip(self, rect=None):
        super().set_clip(None if rect is None else _rect(rect, self.k))

    def get_clip(self):
        c, k = super().get_clip(), self.k
        x, y = round(c.x / k), round(c.y / k)
        return pygame.Rect(x, y, round(c.right / k) - x, round(c.bottom / k) - y)


# ##############################################################################
# Hàm vẽ (thay cho pygame.draw.*), toạ độ logic
# ##############################################################################

def rect(surf, color, r, width=0, border_radius=0):
    k = _k(surf)
    return pygame.draw.rect(surf, color, _rect(r, k), _width(width, k), round(border_radius * k))


def circle(surf, color, center, radius, width=0):
    k = _k(surf)
    return pygame.draw.circle(surf, color, _pt(center, k), radius * k, _width(width, k))


def ellipse(surf, color, r, width=0):
    k = _k(surf)
    return pygame.draw.ellipse(surf, color, _rect(r, k), _width(width, k))


def arc(surf, color, r, start, stop, width=1):
    k = _k(surf)
    return pygame.draw.arc(surf, color, _rect(r, k), start, stop, _width(width, k))


def line(surf, color, a, b, width=1):
    k = _k(surf)
    return pygame.draw.line(surf, color, _pt(a, k), _pt(b, k), _width(width, k))


def lines(surf, color, closed, points, width=1):
    k = _k(surf)
    return pygame.draw.lines(surf, color, closed, [_pt(p, k) for p in points], _width(width, k))


def polygon(surf, color, points, width=0):
    k = _k(surf)
    return pygame.draw.polygon(surf, color, [_pt(p, k) for p in points], _width(width, k))


# ##############################################################################
# Ảnh pixel và chữ
# ##############################################################################

def blit_px(surf, img, pos_px):
    """Blit ảnh đã có sẵn ở độ phân giải thật, toạ độ tính bằng pixel thật."""
    return pygame.Surface.blit(surf, img, pos_px)


_img_cache = {}


def blit_image(surf, img, r):
    """Vẽ ảnh (logo, ...) vừa khung r (đơn vị logic), co giãn từ ảnh gốc theo độ phân giải thật."""
    pr = _rect(r, _k(surf))
    key = (id(img), pr.size)
    scaled = _img_cache.get(key)
    if scaled is None:
        if len(_img_cache) > 50:
            _img_cache.clear()
        scaled = pygame.transform.smoothscale(img, pr.size)
        _img_cache[key] = scaled
    pygame.Surface.blit(surf, scaled, pr.topleft)


def px_size(size, k=None):
    """Cỡ chữ logic -> cỡ chữ pixel thật."""
    return max(1, round(size * (S if k is None else k)))


# ##############################################################################
# Viewport: trang logic -> cửa sổ thật
# ##############################################################################

class Viewport:
    """Trang dùng toạ độ logic (rộng page_w); tỉ lệ k = pixel thật / đơn vị logic được chọn khớp đúng
    chiều rộng cửa sổ, và mọi thứ được vẽ thẳng ở độ phân giải đó (không co giãn ảnh -> không mờ)."""

    def __init__(self, win, page_w, page_h, sb_w, bg):
        self.win = win
        self.page_w, self.page_h, self.sb_w, self.bg = page_w, page_h, sb_w, bg
        self.resize(win.get_size())

    def resize(self, size):
        ww, wh = max(400, size[0]), max(300, size[1])
        # trang vừa chiều cao -> không cần rãnh thanh cuộn; ngược lại thêm rãnh sb_w bên phải
        cw = self.page_w
        if wh / (ww / self.page_w) < self.page_h:
            cw = self.page_w + self.sb_w
        self.k = ww / cw
        set_scale(self.k)
        self.view_h = int(min(self.page_h, wh / self.k))
        self.canvas = Surface((cw, self.view_h))

    def to_logic(self, pos):
        """Toạ độ trên cửa sổ thật -> toạ độ logic."""
        return pos[0] / self.k, pos[1] / self.k

    def present(self):
        # canvas đã ở đúng độ phân giải cửa sổ: chỉ copy pixel
        self.win.fill(self.bg)
        pygame.Surface.blit(self.win, self.canvas, (0, 0))
