"""Bảng "Code": hiển thị code BFS/DFS/UCS (theo notebook) cho từng trò, tô màu cú pháp
và highlight dòng đang chạy. Mỗi lần Next, highlight chạy lần lượt qua các dòng của vòng lặp."""
import re

import pygame

from ui import COL, approach, clamp, draw_panel, draw_text, mix, rrect, text_width

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
KEYWORDS = {"def", "if", "elif", "return", "while", "for", "in", "not", "and", "lambda", "is", "None", "True", "False"}
BUILTINS = {"set", "all", "len"}
TOKEN_RE = re.compile(r'(#.*$)|("[^"]*"|\'[^\']*\')|(\b\d+\b)|([A-Za-z_]\w*)|(\s+)|(.)')

_mono = {}


def mono_font(size):
    f = _mono.get(size)
    if f is None:
        path = pygame.font.match_font("consolas") or pygame.font.match_font("couriernew")
        f = pygame.font.Font(path, size) if path else pygame.font.SysFont("monospace", size)
        _mono[size] = f
    return f


def _q(v):
    """repr với nháy kép giống notebook."""
    return repr(v).replace("'", '"')


# ------------------------------------------------------------------ nội dung code
def code_lines(algo, game, initial, goal):
    """Trả về list[(text, tag)]. tag dùng để map bước thuật toán -> dòng code."""
    if algo == "BFS":
        body = [
            ("def BFS(problem):", "def"),
            ("    node = Node(problem.initial_state)", "init_node"),
            ("    if is_goal(problem, node.state):", "init_goal"),
            ("        return solution(node)", "init_return"),
            ("", None),
            ("    frontier = Queue()", "frontier_init"),
            ("    enqueue(frontier, node)", "push_root"),
            ("    explored = set()", "explored_init"),
            ("", None),
            ("    while not is_empty(frontier):", "while"),
            ("        node = dequeue(frontier)", "pop"),
            ("        explored.add(node.state)", "explored_add"),
            ("        for action in problem.actions(node.state):", "for"),
            ("            child = child_node(problem, node, action)", "child"),
            ("            if child.state not in explored and \\", "if_new"),
            ("               all(n.state != child.state for n in frontier):", "if_new"),
            ("                if is_goal(problem, child.state):", "goal_child"),
            ("                    return solution(child)", "return_child"),
            ("                enqueue(frontier, child)", "push_child"),
            ("", None),
            ("    return None", "return_none"),
        ]
    elif algo == "UCS":
        body = [
            ("def UCS(problem):", "def"),
            ("    node = Node(problem.initial_state)", "init_node"),
            ("    frontier = PriorityQueue()   # g(n) nhỏ nhất ra trước", "frontier_init"),
            ("    push(frontier, node)", "push_root"),
            ("    explored = set()", "explored_init"),
            ("", None),
            ("    while not is_empty(frontier):", "while"),
            ("        node = pop_min(frontier)", "pop"),
            ("        if is_goal(problem, node.state):", "goal_pop"),
            ("            return solution(node)", "return_pop"),
            ("", None),
            ("        explored.add(node.state)", "explored_add"),
            ("        for action in problem.actions(node.state):", "for"),
            ("            child = child_node(problem, node, action)", "child"),
            ("            if child.state not in explored and \\", "if_new"),
            ("               child.state not in frontier:", "if_new"),
            ("                push(frontier, child)", "push_child"),
            ("            elif child.state in frontier and \\", "if_better"),
            ("                 child.cost < frontier[child.state].cost:", "if_better"),
            ("                replace(frontier, child)", "replace_child"),
            ("", None),
            ("    return None", "return_none"),
        ]
    else:
        body = [
            ("def DFS(problem):", "def"),
            ("    node = Node(problem.initial_state)", "init_node"),
            ("    if is_goal(problem, node.state):", "init_goal"),
            ("        return solution(node)", "init_return"),
            ("", None),
            ("    frontier = Stack()", "frontier_init"),
            ("    push(frontier, node)", "push_root"),
            ("    explored = set()", "explored_init"),
            ("", None),
            ("    while not is_empty(frontier):", "while"),
            ("        node = pop(frontier)", "pop"),
            ("        if is_goal(problem, node.state):", "goal_pop"),
            ("            return solution(node)", "return_pop"),
            ("", None),
            ("        explored.add(node.state)", "explored_add"),
            ("        for action in problem.actions(node.state):", "for"),
            ("            child = child_node(problem, node, action)", "child"),
            ("            if child.state not in explored:", "if_new"),
            ("                push(frontier, child)", "push_child"),
            ("", None),
            ("    return None", "return_none"),
        ]
    ucs = algo == "UCS"
    if game == "puzzle":
        setup = [("# ---------------- 8-puzzle ----------------", None),
                 (f"initial = {_q(initial)}", "setup_init"),
                 (f"goal = {_q(goal)}", "setup_goal")]
        if ucs:
            setup += [("def step_cost_puzzle(state, action):", "setup_cost"),
                      ('    return 1 if action in ("Up", "Down") else 2', "setup_cost")]
        setup.append(("problem = Problem(initial, goal, actions_puzzle, result_puzzle"
                      + (", step_cost_puzzle)" if ucs else ")"), "setup_problem"))
    else:
        setup = [("# -------------- vacuum robot ---------------", None),
                 (f"initial = {_q(initial)}", "setup_init"),
                 (f"goal = lambda s: s[1] == {_q(goal)}", "setup_goal")]
        if ucs:
            setup += [("def step_cost_vacuum(state, action):", "setup_cost"),
                      ("    return 1          # Suck / Left / Right đều tốn 1", "setup_cost")]
        setup.append(("problem = Problem(initial, goal, actions_vacuum, result_vacuum"
                      + (", step_cost_vacuum)" if ucs else ")"), "setup_problem"))
    setup.append((f"path = {algo}(problem)", "call"))
    return body + [("", None)] + setup


# ------------------------------------------------------------------ trace (dòng nào chạy)
def _node_label(node):
    return "root" if node.action is None else node.action


def init_trace(algo, root_is_goal):
    t = [("setup_init", ""), ("setup_goal", "")]
    if algo == "UCS":
        t.append(("setup_cost", ""))
    t += [("setup_problem", ""), ("call", ""), ("def", ""), ("init_node", "node = root")]
    if algo == "UCS":       # UCS không kiểm tra goal ở root, mà kiểm tra khi lấy node ra
        return t + [("frontier_init", ""), ("push_root", "push root"), ("explored_init", "")]
    if root_is_goal:
        t += [("init_goal", "True"), ("init_return", "")]
    else:
        t += [("init_goal", "False"), ("frontier_init", ""), ("push_root", "push root"), ("explored_init", "")]
    return t


def step_trace(algo, step, exhausted_after):
    t = [("while", "True"), ("pop", f"node = {_node_label(step.popped)}")]
    if algo == "UCS":
        t[1] = ("pop", f"node = {_node_label(step.popped)} · g={step.popped.cost}")
        if step.goal is not None:
            return t + [("goal_pop", "True"), ("return_pop", "")]
        t += [("goal_pop", "False"), ("explored_add", "")]
        j = 0                                    # chỉ số node con trong step.kids / step.olds
        for (action, outcome), cost in zip(step.events, step.costs):
            t += [("for", f"action = '{action}'"), ("child", f"g={cost}")]
            if outcome == "push":
                t += [("if_new", "True"), ("push_child", "")]
                j += 1
                continue
            t.append(("if_new", "False"))
            if outcome == "replace":
                t += [("if_better", f"True · {cost} < {step.olds[j].cost}"), ("replace_child", "")]
                j += 1
            else:
                t.append(("if_better", "False"))
    elif algo == "BFS":
        t.append(("explored_add", ""))
        for action, outcome in step.events:
            t.append(("for", f"action = '{action}'"))
            t.append(("child", ""))
            if outcome == "skip":
                t.append(("if_new", "False"))
                continue
            t.append(("if_new", "True"))
            if outcome == "goal":
                t += [("goal_child", "True"), ("return_child", "")]
                break
            t += [("goal_child", "False"), ("push_child", "")]
    else:
        if step.goal is not None:
            return t + [("goal_pop", "True"), ("return_pop", "")]
        t += [("goal_pop", "False"), ("explored_add", "")]
        for action, outcome in step.events:
            t += [("for", f"action = '{action}'"), ("child", "")]
            if outcome == "push":
                t += [("if_new", "True"), ("push_child", "")]
            else:
                t.append(("if_new", "False"))
    if exhausted_after:
        t += [("while", "False"), ("return_none", "")]
    return t


def explain(algo, trace, i):
    """Giải thích ngắn dòng trace[i] vừa chạy (hiện ở bảng Node)."""
    if not trace or i < 0:
        return ""
    tag, note = trace[i]
    action = ""
    for tg, nt in reversed(trace[:i + 1]):
        if tg == "for":
            action = nt.split("=", 1)[-1].strip()
            break
    fr = {"BFS": "Queue", "DFS": "Stack"}.get(algo, "Priority Queue")
    if tag == "while":
        return (f"{fr} chưa rỗng → vào vòng lặp." if note == "True"
                else f"{fr} rỗng → thoát vòng lặp.")
    if tag == "pop":
        if algo == "UCS":
            return f"Lấy node có g(n) nhỏ nhất ({note.rsplit('g=', 1)[-1]}) ra khỏi Frontier."
        where = "đầu Queue" if algo == "BFS" else "đỉnh Stack"
        return f"Lấy node ở {where} ra khỏi Frontier."
    if tag == "goal_pop":
        return "Node này là goal!" if note == "True" else "Node này chưa phải goal."
    if tag == "return_pop":
        if algo == "UCS":
            return "Trả về đường đi tới node goal → dừng (UCS kiểm tra goal khi lấy ra nên đường đi rẻ nhất)."
        return "Trả về đường đi tới node goal → dừng (DFS kiểm tra goal khi lấy ra)."
    if tag == "explored_add":
        return "Đánh dấu node đã thăm: thêm vào Empty (explored)."
    if tag == "for":
        return f"Xét hành động {action}."
    if tag == "child":
        if algo == "UCS":
            return f"Sinh node con bằng hành động {action}, g(con) = {note.replace('g=', '')}."
        return f"Sinh node con bằng hành động {action}."
    if tag == "if_new":
        if algo == "UCS":
            return ("Node con chưa thăm và chưa có trong Frontier." if note == "True"
                    else "Node con đã thăm hoặc đã có trong Frontier → xét tiếp elif.")
        if note == "True":
            return "Node con chưa thăm" + (" và chưa có trong Frontier." if algo == "BFS" else ".")
        return "Node con đã thăm" + (" hoặc đã có trong Frontier" if algo == "BFS" else "") + " → bỏ qua."
    if tag == "goal_child":
        return "Node con là goal!" if note == "True" else "Node con chưa phải goal."
    if tag == "return_child":
        return "Trả về đường đi tới node con goal → dừng (BFS kiểm tra goal khi sinh con)."
    if tag == "if_better":
        if note == "False":
            return "Node con đã thăm, hoặc đã có trong Frontier với chi phí không lớn hơn → bỏ qua."
        new, old = note.split("·")[1].split("<")
        return f"Node con đã có trong Frontier nhưng đường mới rẻ hơn ({new.strip()} < {old.strip()}) → thay thế."
    if tag == "replace_child":
        return f"Thay node cũ trong Frontier bằng node con ({action}) có chi phí thấp hơn."
    if tag == "push_child":
        if algo == "UCS":
            return f"Đưa node con ({action}) vào Frontier, tự xếp theo g(n)."
        return f"Đưa node con ({action}) vào Frontier."
    if tag == "return_none":
        return "Không còn node nào để xét → không có lời giải."
    return ""


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
        font = mono_font(self.FONT)
        cw = font.size("M")[0]
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
                pygame.draw.rect(surf, mix((13, 16, 27), hcol, 0.28), row)
                pygame.draw.rect(surf, hcol, (row.x, row.y, 3, row.h))
            elif i in done:
                pygame.draw.rect(surf, mix((13, 16, 27), hcol, 0.09), row)
            num_col = COL["white"] if i in active else (88, 98, 128)
            draw_text(surf, str(i + 1), (self.area.x + gutter - 8, row.centery), 12, num_col, False, "midright")
            x = self.area.x + gutter
            text = self.lines[i][0]
            for tok, col in self._tokens(text):
                if col is not None:
                    s = font.render(tok, True, col)
                    surf.blit(s, (x, row.y + (self.LINE_H - s.get_height()) // 2))
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
