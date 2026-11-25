"""Search Visualizer: BFS / DFS trên 8-puzzle và Vacuum robot (pygame).

Chạy:  python main.py
Phím tắt:  →  Next   ←  Prev   Space  Auto   R  Reset
"""
import os
import sys

import pygame

from algorithms import SearchMachine
from inputs import PuzzleInput, VacuumInput
from problems import make_puzzle_problem, make_vacuum_problem
from ui import (COL, Button, Dropdown, Slider, approach, clamp, draw_icon, draw_panel, draw_text, mix, rrect,
                shadow, text_width)
from views import CardList, PuzzleBoard, VacuumBoard, paint_card

W, H = 1220, 720
HERE = os.path.dirname(os.path.abspath(__file__))

BOARD_RECT = pygame.Rect(16, 92, 640, 392)
INPUT_RECT = pygame.Rect(16, 496, 640, 208)
NODE_RECT = pygame.Rect(672, 92, 532, 104)
FRONT_RECT = pygame.Rect(672, 208, 532, 248)
EMPTY_RECT = pygame.Rect(672, 468, 532, 236)

GAMES = [("puzzle", "8-Puzzle"), ("vacuum", "Vacuum Robot")]
ALGOS = [("BFS", "BFS"), ("DFS", "DFS")]

STUDENT_NAME = "Mai Quốc Bảo"
STUDENT_ID = "24110080"

# tốc độ Auto (số bước trên giây)
MIN_SPS, MAX_SPS, DEFAULT_SPS = 1, 128, 5


def load_logo():
    for p in (os.path.join(HERE, "ute_logo.png"), os.path.join(HERE, "..", "ute_logo.png")):
        if os.path.exists(p):
            return pygame.image.load(p).convert_alpha()
    return None


class App:
    def __init__(self, screen):
        self.screen = screen
        self.logo = load_logo()
        self.time = 0.0
        self.dt = 1 / 60
        self.game = "puzzle"
        self.algo = "BFS"

        # ---- header
        # Thêm trò chơi / thuật toán mới: chỉ cần thêm vào 2 danh sách này (id, tên hiển thị)
        self.game_list = GAMES
        self.algo_list = ALGOS
        self.dd_game = Dropdown((330, 34, 330, 40), [n for _, n in GAMES], 0)
        self.dd_algo = Dropdown((690, 34, 200, 40), [n for _, n in ALGOS], 0)

        # ---- điều khiển
        by = BOARD_RECT.bottom - 58
        x = BOARD_RECT.x + 16
        self.btn_reset = Button((x, by, 86, 42), "Reset", "reset")
        self.btn_prev = Button((x + 94, by, 86, 42), "Prev", "prev")
        self.btn_next = Button((x + 188, by, 100, 42), "Next", "next", "primary")
        self.btn_auto = Button((x + 296, by, 88, 42), "Auto", "play", "success")
        self.btn_skip = Button((x + 392, by, 96, 42), "Kết quả", "skip")
        self.slider = Slider((BOARD_RECT.right - 130, by + 26, 114, 10),
                             (DEFAULT_SPS - MIN_SPS) / (MAX_SPS - MIN_SPS))
        self.btn_replay = Button((0, 0, 200, 30), "Phát lại đường đi", "play", "secondary")
        self.controls = [self.btn_reset, self.btn_prev, self.btn_next, self.btn_auto, self.btn_skip, self.btn_replay]

        # ---- đầu vào / bàn / danh sách
        self.inputs = {"puzzle": PuzzleInput(INPUT_RECT), "vacuum": VacuumInput(INPUT_RECT)}
        self.pboard = PuzzleBoard()
        self.vboard = VacuumBoard()
        self.front_list = CardList(FRONT_RECT, COL["orange"])
        self.empty_list = CardList(EMPTY_RECT, COL["gray"])

        self.auto = False
        self.auto_acc = 0.0
        self.step_age = 10.0
        self.play_states = None
        self.play_idx = 0
        self.play_t = 0.0
        self.note = ""
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

    def goal_for_view(self):
        return self.inp.goal_state()

    def rebuild(self, snap=False):
        inp = self.inp
        if self.game == "puzzle":
            self.problem = make_puzzle_problem(inp.initial_state(), inp.goal_state())
        else:
            self.problem = make_vacuum_problem(inp.initial_state(), inp.goal_state())
        self.machine = SearchMachine(self.problem, self.algo)
        self.auto = False
        self.play_states = None
        self.step_age = 10.0
        self.note = ""
        self.front_list.reset_scroll()
        self.empty_list.reset_scroll()
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

    def stepped(self):
        self.step_age = 0.0
        self.front_list.reset_scroll()
        self.empty_list.reset_scroll()
        self.play_states = None
        self._sync_board()
        m = self.machine
        if m.found is not None and m.found is not m.current:      # BFS: cuộn tới thẻ goal ở cuối Frontier
            fl = self.front_list
            fl.scroll(m.frontier_len // fl.cols - fl.rows_visible + 1, m.frontier_len + 1)

    # ------------------------------------------------------------ hành động
    def do_next(self):
        if self.blocked:
            return False
        ok = self.machine.next()
        if ok:
            self.stepped()
        else:
            self.auto = False
        return ok

    def do_prev(self):
        self.auto = False
        if self.machine.prev():
            self.stepped()

    def do_skip(self):
        if self.blocked:
            return
        self.auto = False
        n = self.machine.run_to_end()
        self.note = f"Đã chạy nhanh {n} bước"
        self.stepped()

    def toggle_auto(self):
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
    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.click(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.slider.drag = False
        elif ev.type == pygame.MOUSEMOTION and self.slider.drag:
            self.slider.set_from_x(ev.pos[0])
        elif ev.type == pygame.MOUSEWHEEL:
            mp = pygame.mouse.get_pos()
            self.wheel(mp, -ev.y)
        elif ev.type == pygame.KEYDOWN:
            self.key(ev)

    def wheel(self, pos, dy):
        if FRONT_RECT.collidepoint(pos):
            self.front_list.scroll(dy, self.machine.frontier_len)
        elif EMPTY_RECT.collidepoint(pos):
            self.empty_list.scroll(dy, len(self.machine.explored))

    def key(self, ev):
        if self.inp.key(ev):
            self.after_input()
            return
        if ev.key == pygame.K_RIGHT:
            self.do_next()
        elif ev.key == pygame.K_LEFT:
            self.do_prev()
        elif ev.key == pygame.K_SPACE:
            self.toggle_auto()
        elif ev.key == pygame.K_ESCAPE:
            self.dd_game.open = self.dd_algo.open = False
        elif ev.key == pygame.K_r:
            self.rebuild()

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
        if self.slider.hit(pos):
            self.slider.drag = True
            self.slider.set_from_x(pos[0])
            return
        if self.btn_reset.hit(pos):
            self.rebuild()
        elif self.btn_prev.hit(pos):
            self.do_prev()
        elif self.btn_next.hit(pos):
            self.auto = False
            self.do_next()
        elif self.btn_auto.hit(pos):
            self.toggle_auto()
        elif self.btn_skip.hit(pos):
            self.do_skip()
        elif self.btn_replay.hit(pos):
            self.start_replay()
        else:
            self.inp.click(pos)
            self.after_input()

    # ------------------------------------------------------------ cập nhật
    def update(self, dt, mouse, down):
        self.time += dt
        self.dt = dt
        self.step_age += dt
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

        if self.play_states is not None:
            self.play_t += dt
            if self.play_t >= 0.75 and self.play_idx < len(self.play_states) - 1:
                self.play_t = 0.0
                self.play_idx += 1
                self._sync_board()

        # trạng thái nút
        self.btn_prev.enabled = m.can_prev()
        self.btn_next.enabled = m.can_next() and not self.blocked
        self.btn_skip.enabled = m.can_next() and not self.blocked
        self.btn_auto.enabled = self.auto or (m.can_next() and not self.blocked)
        self.btn_auto.label = "Pause" if self.auto else "Auto"
        self.btn_auto.icon = "pause" if self.auto else "play"
        self.btn_auto.kind = "danger" if self.auto else "success"
        self.btn_replay.visible = m.found is not None and self.play_states is None
        self.btn_replay.rect.topleft = self.replay_pos()
        for b in self.controls:
            b.update(dt, mouse, down)
        self.slider.update(dt, mouse)
        self.dd_game.update(dt, mouse)
        self.dd_algo.update(dt, mouse)

        (self.pboard if self.game == "puzzle" else self.vboard).update(dt)
        self.front_list.update(dt)
        self.empty_list.update(dt)

    def replay_pos(self):
        ix = self.info_x()
        return (ix, BOARD_RECT.y + 286)

    def info_x(self):
        if self.game == "puzzle":
            return BOARD_RECT.x + 36 + self.pboard.size + 36
        return BOARD_RECT.x + 28 + self.vboard.width + 26

    # ------------------------------------------------------------ vẽ
    def draw(self, mouse):
        s = self.screen
        s.fill(COL["bg"])
        self.draw_header(s)
        self.draw_board_panel(s)
        self.inp.draw(s, self.dt, mouse)
        self.draw_node_panel(s)
        self.draw_lists(s)
        # danh sách thả xuống vẽ sau cùng để nằm trên mọi thành phần
        self.dd_game.draw_list(s)
        self.dd_algo.draw_list(s)

    def draw_header(self, s):
        # logo + tên + MSSV (góc trái trên)
        badge = pygame.Rect(16, 10, 60, 66)
        shadow(s, badge, 14, 10, 80)
        rrect(s, COL["white"], badge, 14)
        if self.logo:
            lh = 54
            lw = int(self.logo.get_width() * lh / self.logo.get_height())
            s.blit(pygame.transform.smoothscale(self.logo, (lw, lh)), (badge.centerx - lw // 2, badge.centery - lh // 2))
        draw_text(s, STUDENT_NAME, (90, 16), 22, COL["text"], True)
        draw_text(s, f"MSSV: {STUDENT_ID}", (90, 46), 16, COL["accent"], True)

        draw_text(s, "TRÒ CHƠI", (self.dd_game.rect.x + 4, 14), 11, COL["muted"], True)
        draw_text(s, "THUẬT TOÁN", (self.dd_algo.rect.x + 4, 14), 11, COL["muted"], True)
        self.dd_game.draw(s)
        self.dd_algo.draw(s)

        # chip mô tả cấu trúc dữ liệu
        txt = "Queue · FIFO" if self.algo == "BFS" else "Stack · LIFO"
        sub = "Duyệt theo chiều rộng" if self.algo == "BFS" else "Duyệt theo chiều sâu"
        chip = pygame.Rect(916, 24, 288, 52)
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
        iw = BOARD_RECT.right - 18 - ix
        draw_text(s, "ĐÍCH (GOAL)", (ix, iy), 11, COL["muted"], True)
        gr = pygame.Rect(ix, iy + 18, 64, 64)
        goal = self.inp.goal_state()
        if self.game == "puzzle":
            paint_card(s, gr, "puzzle", goal, goal, COL["green"], 2)
        else:
            paint_card(s, gr, "vacuum", ("A", goal), None, COL["green"], 2)
            draw_text(s, "(robot ở đâu cũng được)", (gr.right + 10, gr.centery), 11, COL["muted"], False, "midleft")

        node = self.display_node()
        last = m.last_step()
        rows = [
            ("Bước", str(m.cursor)),
            ("Frontier", str(m.frontier_len)),
            ("Empty", str(len(m.explored))),
            ("Hành động", (node.action if node and node.action else "—")),
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
        elif self.play_states is not None:
            text, color, icon = f"Phát lại {self.play_idx}/{len(self.play_states) - 1}", COL["accent"], "play"
        elif m.found is not None:
            text, color, icon = f"Tìm thấy goal · {len(m.path_actions())} bước", COL["green"], "check"
        elif m.exhausted:
            text, color, icon = "Không có lời giải", COL["orange"], "warn"
        elif m.cursor == 0:
            text, color, icon = "Sẵn sàng · bấm Next", COL["muted"], "next"
        else:
            text, color, icon = "Đang tìm kiếm…", COL["accent"], "play"
        pill = pygame.Rect(ix, BOARD_RECT.y + 250, iw, 28)
        rrect(s, mix(COL["panel"], color, 0.18), pill, 14, 1, mix(COL["panel"], color, 0.6))
        draw_icon(s, icon, (pill.x + 16, pill.centery), 11, color)
        draw_text(s, text, (pill.x + 30, pill.centery), 13, color, True, "midleft")

        self.btn_replay.rect.width = iw
        pygame.draw.line(s, COL["border"], (BOARD_RECT.x + 16, BOARD_RECT.bottom - 68),
                         (BOARD_RECT.right - 16, BOARD_RECT.bottom - 68))
        for b in self.controls:
            b.draw(s)
        draw_text(s, f"{self.steps_per_sec} bước/giây", (self.slider.rect.x, self.slider.rect.y - 22), 11,
                  COL["muted"], True)
        self.slider.draw(s)

    def draw_node_panel(self, s):
        """Node = node vừa được LẤY RA khỏi Frontier (cũng là node mới nhất trong Empty).
        Riêng BFS: goal là node CON được phát hiện lúc sinh con, nên hiển thị tách riêng ở bên phải."""
        m = self.machine
        draw_panel(s, NODE_RECT, "Node", COL["accent"], subtitle="node vừa lấy ra khỏi Frontier")
        node = m.current
        goal = self.inp.goal_state()
        gl = goal if self.game == "puzzle" else None
        card = pygame.Rect(NODE_RECT.x + 18, NODE_RECT.y + 34, 64, 64)
        x = card.right + 18
        if node is None:
            paint_card(s, card, self.game, self.problem.initial_state, gl, COL["accent"], 2, alpha=140)
            draw_text(s, "Chưa bắt đầu", (x, NODE_RECT.y + 36), 17, COL["text"], True)
            draw_text(s, "Đây là trạng thái ban đầu (root) đang nằm trong Frontier.", (x, NODE_RECT.y + 62), 13, COL["muted"])
            draw_text(s, "Bấm Next để lấy node đầu tiên ra khỏi Frontier.", (x, NODE_RECT.y + 80), 13, COL["muted"])
            return
        child_goal = m.found is not None and m.found is not node      # BFS: goal là node con
        is_goal = m.found is node                                     # DFS / root là goal
        fade = int(120 + 135 * min(1, self.step_age / 0.3))
        paint_card(s, card, self.game, node.state, gl, COL["green"] if is_goal else COL["accent"], 2, alpha=fade)
        title = f"Bước {m.cursor}: đang xét node này" if m.cursor else "Root là goal!"
        tr = draw_text(s, title, (x, NODE_RECT.y + 34), 17, COL["green"] if is_goal else COL["text"], True)
        if is_goal:
            pg = pygame.Rect(tr.right + 10, tr.y + 2, 52, 20)
            rrect(s, COL["green"], pg, 10)
            draw_text(s, "GOAL", pg.center, 11, COL["white"], True, "center")
        act = node.action or "— (root)"
        draw_text(s, f"Hành động đến node: {act}   ·   Độ sâu: {node.depth}", (x, NODE_RECT.y + 60), 13, COL["muted"])
        last = m.last_step()
        if is_goal:
            msg = "Node này là goal → dừng (DFS kiểm tra goal khi lấy ra)."
        elif child_goal:
            msg = f"Con '{m.found.action}' là goal → đưa vào Frontier (thẻ GOAL) → dừng."
        elif last:
            msg = f"Lấy khỏi Frontier → thêm vào Empty → sinh {len(last.kids)} node con mới."
        else:
            msg = ""
        draw_text(s, msg, (x, NODE_RECT.y + 78), 13, COL["text"])

    def draw_lists(self, s):
        m = self.machine
        goal = self.inp.goal_state()
        gl = goal if self.game == "puzzle" else None
        last = m.last_step()
        new_ids = {id(k) for k in last.kids} if last else set()
        age = self.step_age

        # --- Frontier
        is_bfs = self.algo == "BFS"
        draw_panel(s, FRONT_RECT, "Frontier", COL["orange"],
                   subtitle="Queue (FIFO) — lấy ở đầu hàng" if is_bfs else "Stack (LIFO) — lấy ở đỉnh",
                   badge=f"{m.frontier_len} node" + (" + goal" if (m.found is not None and m.found is not m.current) else ""),
                   badge_color=COL["orange"])

        def paint_front(surf, rect, node, idx):
            new = id(node) in new_ids
            a = 255
            border = COL["border"]
            bw = 1
            if new:
                a = int(70 + 185 * min(1, age / 0.35))
                border = mix(COL["green"], COL["border"], min(1, age / 1.6))
                bw = 2
            tag = None
            if idx == 0:
                tag = "HEAD" if is_bfs else "TOP"
            paint_card(surf, rect, self.game, node.state, gl, border, bw, a, tag, COL["orange"])

        goal_node = m.found if (m.found is not None and m.found is not m.current) else None
        n_front = m.frontier_len

        def front_items(start, count):
            items = m.frontier_slice(start, count)
            if goal_node is not None and start + count > n_front >= start:
                items = items + [goal_node]
            return items

        def paint_front_or_goal(surf, rect, node, idx):
            if node is goal_node:
                a = int(70 + 185 * min(1, age / 0.35))
                paint_card(surf, rect, self.game, node.state, gl, COL["green"], 2, a, "GOAL", COL["green"])
            else:
                paint_front(surf, rect, node, idx)

        total_front = n_front + (1 if goal_node is not None else 0)
        self.front_list.draw(s, total_front, front_items, paint_front_or_goal, "Frontier đang rỗng")

        # --- Empty (đã thăm)
        newest = len(m.explored) - 1

        def paint_empty(surf, rect, state, idx):
            fresh = idx == 0 and last is not None and last.added
            a = 255
            border = COL["border"]
            bw = 1
            if fresh:
                a = int(70 + 185 * min(1, age / 0.35))
                border = mix(COL["accent"], COL["border"], min(1, age / 1.6))
                bw = 2
            paint_card(surf, rect, self.game, state, gl, border, bw, a, "MỚI" if fresh else None, COL["accent"])

        draw_panel(s, EMPTY_RECT, "Empty", COL["gray"], subtitle="node đã thăm (explored)",
                   badge=f"{len(m.explored)} node", badge_color=COL["gray"])
        self.empty_list.draw(s, len(m.explored), m.explored_slice, paint_empty, "Chưa thăm node nào")


# ---------------------------------------------------------------------- main
def main():
    pygame.init()
    pygame.display.set_caption("Search Visualizer — BFS / DFS · Mai Quốc Bảo · 24110080")
    try:
        screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    except pygame.error:
        screen = pygame.display.set_mode((W, H))
    try:
        for name in ("ute_logo.png",):
            p = os.path.join(HERE, name)
            if os.path.exists(p):
                pygame.display.set_icon(pygame.image.load(p))
    except pygame.error:
        pass
    app = App(screen)
    clock = pygame.time.Clock()
    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            app.handle_event(ev)
        mouse = pygame.mouse.get_pos()
        down = pygame.mouse.get_pressed()[0]
        app.update(dt, mouse, down)
        app.draw(mouse)
        pygame.display.flip()


if __name__ == "__main__":
    main()
