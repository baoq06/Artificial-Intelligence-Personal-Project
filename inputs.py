"""Bảng "Đầu vào": cho phép người dùng tự chỉnh trạng thái đầu và trạng thái đích."""
import pygame

from problems import (PUZZLE_GOAL, PUZZLE_INIT, VACUUM_GOAL_ROOMS, VACUUM_INIT, puzzle_solvable, random_puzzle,
                      vacuum_reachable)
from ui import COL, Button, approach, draw_icon, draw_panel, draw_text, mix, rrect, text_width, clamp

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
        pygame.draw.line(surf, COL["muted"], (ax - 9, self.init_pos[1] + GRID // 2), (ax + 9, self.init_pos[1] + GRID // 2), 2)
        pygame.draw.polygon(surf, COL["muted"], [(ax + 10, self.init_pos[1] + GRID // 2),
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
                pygame.draw.circle(surf, (170, 124, 78), (r.x + r.w * dx, r.y + r.h * dy), rad)
        label = "Dirty" if dirty else "Clean"
        draw_text(surf, label, (r.centerx, r.bottom - 6), 11, COL["orange"] if dirty else COL["green"], True, "midbottom")
        if robot:
            pygame.draw.circle(surf, COL["accent"], (r.centerx, r.y + r.h * .42), 11)
            pygame.draw.circle(surf, COL["white"], (r.centerx, r.y + r.h * .42), 11, 1)
            pygame.draw.circle(surf, COL["green"], (r.centerx, r.y + r.h * .42), 3)

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
