"""Search Visualizer: BFS / DFS / UCS trên 8-puzzle và Vacuum robot (pygame).

Chạy:  python main.py
Phím tắt:  →  Next   ←  Prev   Space  Auto   R  Reset   ↑ ↓ / PgUp PgDn  cuộn trang
"""
import os
import sys
import time

import pygame

from algorithms import SearchMachine, solution_costs
from codeview import GAME_NAMES, CodeView, code_lines, explain, init_trace, step_trace
from inputs import PuzzleInput, VacuumInput
from problems import make_puzzle_problem, make_vacuum_problem
from ui import (COL, Button, Dropdown, Slider, approach, clamp, draw_icon, draw_panel, draw_text, mix, rrect,
                shadow, text_width)
from views import CardList, PuzzleBoard, VacuumBoard, paint_card

W = 1220                 # chiều rộng trang (không tính thanh cuộn)
SB_W = 14                # rãnh thanh cuộn nằm ngoài trang, bên phải
DEFAULT_VIEW_H = 720
# Hệ số thu nhỏ toàn bộ giao diện khi hiển thị (1.0 = kích thước gốc).
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
        self.page = pygame.Surface((W, PAGE_H))
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
        total = f", total cost = {m.found.cost}" if self.is_ucs else ""
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
        """Cuộn bảng dưới chuột trước; nếu bảng đã tới đầu/cuối thì cuộn cả trang."""
        m = self.machine
        handled = False
        if FRONT_RECT.collidepoint(pos):
            handled = self.front_list.scroll(dy, m.frontier_len + (1 if m.found and m.found is not m.current else 0))
        elif EMPTY_RECT.collidepoint(pos):
            handled = self.empty_list.scroll(dy, len(m.explored))
        elif PATH_RECT.collidepoint(pos):
            handled = self.path_list.scroll(dy, len(m.path_states()))
        elif CODE_RECT.collidepoint(pos):
            handled = self.code.scroll(dy)
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
            lw = int(self.logo.get_width() * lh / self.logo.get_height())
            s.blit(pygame.transform.smoothscale(self.logo, (lw, lh)), (badge.centerx - lw // 2, badge.centery - lh // 2))
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
            act = (f"{act} (+{node.cost - node.parent.cost}) · g={node.cost}" if node.parent
                   else f"— · g={node.cost}")
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
            pygame.draw.line(s, COL["border"], (ix, y + 22), (ix + iw, y + 22))
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
                text = f"Tìm thấy goal · chi phí {m.found.cost}"
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

        pygame.draw.line(s, COL["border"], (BOARD_RECT.x + 16, BOARD_RECT.bottom - 68),
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
            draw_text(s, f"Độ sâu: {node.depth}", (x, card.y + 47), 13, COL["muted"])
            if self.is_ucs:
                step_c = f" (+{node.cost - node.parent.cost})" if node.parent else ""
                draw_text(s, f"Chi phí g(n): {node.cost}{step_c}", (x, card.y + 66), 13, COL["orange"], True)
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
                       node.cost if self.is_ucs else None)

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
            cost = m.enodes[len(m.enodes) - 1 - idx].cost if self.is_ucs else None
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
                   badge=(f"{len(acts)} bước" + (f" · chi phí {m.found.cost}" if self.is_ucs else ""))
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
                pygame.draw.polygon(surf, COL["muted"], [(ax, ay - 4), (ax + 6, ay), (ax, ay + 4)])

        self.path_list.draw(s, len(states), lambda a, c: states[a:a + c], paint_path, "")


# ---------------------------------------------------------------------- main
class Viewport:
    """Vẽ giao diện ở kích thước logic (rộng W) rồi thu nhỏ theo UI_SCALE ra cửa sổ thật."""

    def __init__(self, win):
        self.win = win
        self.resize(win.get_size())

    def resize(self, size):
        ww, wh = max(400, size[0]), max(300, size[1])
        # trang vừa chiều cao -> không cần rãnh thanh cuộn; ngược lại thêm rãnh SB_W bên phải
        cw = W
        if wh / (ww / W) < PAGE_H:
            cw = W + SB_W
        self.k = ww / cw
        self.view_h = int(min(PAGE_H, wh / self.k))
        self.canvas = pygame.Surface((cw, self.view_h))

    def to_logic(self, pos):
        return pos[0] / self.k, pos[1] / self.k

    def present(self):
        if abs(self.k - 1.0) < 1e-3:
            self.win.blit(self.canvas, (0, 0))
        else:
            size = (self.win.get_width(), round(self.view_h * self.k))
            self.win.fill(COL["bg"])
            self.win.blit(pygame.transform.smoothscale(self.canvas, size), (0, 0))


def main():
    pygame.init()
    pygame.display.set_caption("Search Visualizer — BFS / DFS / UCS · Mai Quốc Bảo · 24110080")
    info = pygame.display.Info()
    desk_h = info.current_h if info.current_h and info.current_h > 0 else DEFAULT_VIEW_H + 100
    win_h = int(clamp(desk_h - 110, 480, PAGE_H * UI_SCALE))
    win_w = round((W if win_h >= PAGE_H * UI_SCALE else W + SB_W) * UI_SCALE)
    win = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    try:
        p = os.path.join(HERE, "ute_logo.png")
        if os.path.exists(p):
            pygame.display.set_icon(pygame.image.load(p))
    except pygame.error:
        pass
    vp = Viewport(win)
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
