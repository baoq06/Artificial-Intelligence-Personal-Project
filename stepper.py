"""Thể hiện thuật toán trong app: chạy BFS / DFS / UCS TỪNG BƯỚC và highlight dòng code đang chạy.

  BFSStepper / DFSStepper / UCSStepper
        mỗi lần compute() = đúng 1 vòng `while` của BFS() (bfs.py) / DFS() (dfs.py) / UCS() (ucs.py),
        dùng chính Node, child_node và các hàm frontier (enqueue / dequeue, push / pop, heapq) của notebook
  SearchMachine
        Next / Prev theo từng dòng code hoặc từng vòng lặp, lưu lịch sử các vòng để lùi lại được
  code_lines / init_trace / step_trace / explain
        nội dung code hiển thị, các dòng code đã chạy trong mỗi vòng (để highlight) và lời giải thích
"""
import heapq
import time
from collections import Counter

import bfs
import dfs
import ucs


# ##############################################################################
# Dữ liệu 1 vòng lặp + tiện ích cho node
# ##############################################################################

class Step:
    """Một vòng lặp `while` của thuật toán (chỉ lưu phần thay đổi để có thể hoàn tác nhanh)."""
    __slots__ = ("popped", "added", "kids", "goal", "events", "costs", "stale", "exhaust", "trace", "ops")

    def __init__(self, popped, added, kids, goal, events=(), costs=None, stale=False):
        self.popped = popped      # node vừa lấy ra khỏi frontier
        self.added = added        # có thêm vào explored ("Empty") không
        self.kids = kids          # các node con vừa được đẩy vào frontier
        self.goal = goal          # node goal nếu tìm thấy ở bước này
        self.events = events      # [(action, "skip"|"push"|"goal")] - dùng để highlight từng dòng code
        self.costs = costs        # UCS: path_cost của node con ứng với từng event
        self.stale = stale        # UCS: node lấy ra là bản cũ của trạng thái đã thăm -> `continue`
        self.exhaust = False      # sau bước này frontier rỗng (không có lời giải)
        self.trace = None         # [(tag, note)] - các dòng code chạy trong vòng lặp (tính khi cần)
        self.ops = None           # thao tác ứng với từng dòng trong trace


def solution_actions(node):
    """Danh sách hành động từ start tới node."""
    acts = []
    while node is not None and node.parent is not None:
        acts.append(node.action)
        node = node.parent
    acts.reverse()
    return acts


def solution_costs(node):
    """path_cost g(n) tại từng trạng thái trên đường đi (chỉ node UCS có path_cost)."""
    costs = []
    while node is not None:
        costs.append(getattr(node, "path_cost", None))
        node = node.parent
    costs.reverse()
    return costs


def node_depth(node):
    """Độ sâu của node (số bước từ root) - Node trong notebook không lưu sẵn."""
    d = 0
    while node.parent is not None:
        node = node.parent
        d += 1
    return d


# ##############################################################################
# Lớp cơ sở: 1 thuật toán chạy từng bước
# ##############################################################################

class SearchAlgorithm:
    name = ""
    frontier_kind = ""            # mô tả cấu trúc frontier, vd "Queue (FIFO)"
    check_goal_at_init = True     # có `if is_goal(problem, node.state)` cho root trước vòng lặp không

    def __init__(self, machine):
        self.m = machine          # SearchMachine giữ frontier (m.q), explored (m.eset), ...

    def make_root(self):
        """node = Node(problem.initial_state)"""
        raise NotImplementedError

    def goal_test(self, state):
        raise NotImplementedError

    def push(self, node):
        """Đưa node vào frontier."""
        raise NotImplementedError

    def unpush(self, node):
        """Hoàn tác push()."""
        raise NotImplementedError

    def pop(self):
        """Lấy node kế tiếp ra khỏi frontier (đã biết trước là node nào, nên không cần trả về)."""
        raise NotImplementedError

    def unpop(self, node):
        """Hoàn tác pop(): đưa node trở lại đúng vị trí cũ trong frontier (dùng cho nút Prev)."""
        raise NotImplementedError

    def frontier_slice(self, start, count):
        """Các node trong frontier theo thứ tự SẼ ĐƯỢC LẤY RA."""
        raise NotImplementedError

    def compute(self):
        """Tính trước kết quả 1 vòng `while` (chưa thay đổi frontier / explored), trả về Step."""
        raise NotImplementedError


# ##############################################################################
# BFS chạy từng bước - notebook Buoi4 (bfs.py)
# ##############################################################################

class BFSStepper(SearchAlgorithm):
    name = "BFS"
    frontier_kind = "Queue (FIFO)"

    def make_root(self):
        return bfs.Node(self.m.problem.initial_state)

    def goal_test(self, state):
        # is_goal của Buoi4 chỉ so sánh `==` nên không chạy được goal dạng hàm (lambda) của Vacuum;
        # dùng bản Buoi5 (giống hệt khi goal là 1 trạng thái như 8-puzzle).
        return dfs.is_goal(self.m.problem, state)

    def push(self, node):
        bfs.enqueue(self.m.q, node)             # enqueue(frontier, child)

    def unpush(self, node):
        self.m.q.pop()                          # node vừa enqueue luôn nằm cuối queue

    def pop(self):
        bfs.dequeue(self.m.q)                   # node = dequeue(frontier)

    def unpop(self, node):
        self.m.q.insert(0, node)                # trả node về đầu queue

    def frontier_slice(self, start, count):
        return self.m.q[start:start + count]    # đầu queue (sẽ dequeue trước) đứng đầu

    def compute(self):
        m, problem = self.m, self.m.problem
        node = m.q[0]                           # node = dequeue(frontier)
        added = node.state not in m.eset        # explored.add(node.state)

        def in_explored(state):                 # (explored lúc này đã có node.state)
            return state == node.state or state in m.eset

        def in_frontier(state):                 # all(n.state != child.state for n in frontier) == False
            # m.fcount đếm số node của mỗi state trong frontier (khỏi duyệt cả queue, kết quả như nhau);
            # node vừa dequeue không còn trong frontier, các con vừa enqueue ở vòng này thì có.
            return m.fcount[state] - (1 if state == node.state else 0) > 0 or state in pushed

        kids, goal, pushed, events = [], None, set(), []
        for action in problem.actions(node.state):
            child = bfs.child_node(problem, node, action)
            if not in_explored(child.state) and not in_frontier(child.state):
                if self.goal_test(child.state):
                    events.append((action, "goal"))     # return solution(child)
                    goal = child
                    break
                events.append((action, "push"))         # enqueue(frontier, child)
                kids.append(child)
                pushed.add(child.state)
            else:
                events.append((action, "skip"))
        return Step(node, added, kids, goal, events)


# ##############################################################################
# DFS chạy từng bước - notebook Buoi5 (dfs.py)
# ##############################################################################

class DFSStepper(SearchAlgorithm):
    name = "DFS"
    frontier_kind = "Stack (LIFO)"

    def make_root(self):
        return dfs.Node(self.m.problem.initial_state)

    def goal_test(self, state):
        return dfs.is_goal(self.m.problem, state)

    def push(self, node):
        dfs.push(self.m.q, node)                # push(frontier, child)

    def unpush(self, node):
        self.m.q.pop()

    def pop(self):
        dfs.pop(self.m.q)                       # node = pop(frontier)

    def unpop(self, node):
        dfs.push(self.m.q, node)                # đặt node lại lên đỉnh stack

    def frontier_slice(self, start, count):
        q = self.m.q                            # đỉnh stack (sẽ pop trước) đứng đầu
        top = len(q) - 1 - start
        return [q[top - i] for i in range(count)]

    def compute(self):
        m, problem = self.m, self.m.problem
        node = m.q[-1]                          # node = pop(frontier)
        if self.goal_test(node.state):          # if is_goal(problem, node.state):
            return Step(node, False, [], node)  #     return solution(node)

        added = node.state not in m.eset        # explored.add(node.state)
        kids, events = [], []
        for action in problem.actions(node.state):
            child = dfs.child_node(problem, node, action)
            if child.state != node.state and child.state not in m.eset:     # child.state not in explored
                kids.append(child)                                          # push(frontier, child)
                events.append((action, "push"))
            else:
                events.append((action, "skip"))
        return Step(node, added, kids, None, events)


# ##############################################################################
# UCS chạy từng bước - notebook Buoi6 (ucs.py)
# ##############################################################################

class UCSStepper(SearchAlgorithm):
    """frontier = heap các bộ (path_cost, thứ tự, node) của ucs.push / ucs.pop.

    Giống notebook: node con rẻ hơn được push THÊM (không xóa bản cũ); bản cũ khi lấy ra
    sẽ gặp `if node.state in explored: continue`.
    """
    name = "UCS"
    frontier_kind = "Priority Queue (path_cost nhỏ nhất)"
    check_goal_at_init = False                  # UCS chỉ kiểm tra goal khi lấy node ra

    def __init__(self, machine):
        super().__init__(machine)
        self.best_cost = {}                     # best_cost: chi phí nhỏ nhất đã biết của mỗi trạng thái
        self.prev_best = {}                     # id(node) -> best_cost cũ trước khi push node (để hoàn tác)
        self.entries = {}                       # id(node) -> bộ (path_cost, thứ tự, node) đã lấy khỏi heap
        self._order = None                      # cache: các node theo thứ tự sẽ pop (để vẽ bảng Frontier)

    def make_root(self):
        return ucs.Node(self.m.problem.initial_state)

    def goal_test(self, state):
        return ucs.is_goal(self.m.problem, state)

    def push(self, node):
        # best_cost[child.state] = child.path_cost ; push(frontier, child)
        # (root: best_cost = {node.state: 0} ; push(frontier, node))
        self.prev_best[id(node)] = self.best_cost.get(node.state)
        self.best_cost[node.state] = node.path_cost
        ucs.push(self.m.q, node)
        self._order = None

    def unpush(self, node):
        q = self.m.q
        i = next(i for i, e in enumerate(q) if e[2] is node)
        q[i] = q[-1]
        q.pop()
        heapq.heapify(q)
        prev = self.prev_best.pop(id(node))
        if prev is None:
            del self.best_cost[node.state]
        else:
            self.best_cost[node.state] = prev
        self._order = None

    def pop(self):
        entry = self.m.q[0]                     # bộ có path_cost nhỏ nhất = cái ucs.pop sẽ lấy
        self.entries[id(entry[2])] = entry
        ucs.pop(self.m.q)                       # node = pop(frontier)
        self._order = None

    def unpop(self, node):
        heapq.heappush(self.m.q, self.entries[id(node)])   # trả lại đúng bộ cũ (giữ thứ tự)
        self._order = None

    def frontier_slice(self, start, count):
        need = start + count
        if self._order is None or len(self._order) < min(need, len(self.m.q)):
            self._order = [e[2] for e in heapq.nsmallest(max(need, 64), self.m.q)]
        return self._order[start:need]

    def compute(self):
        m, problem = self.m, self.m.problem
        node = m.q[0][2]                        # node = pop(frontier)
        if node.state in m.eset:                # if node.state in explored:
            return Step(node, False, [], None, stale=True)     # continue
        if self.goal_test(node.state):          # if is_goal(problem, node.state):
            return Step(node, False, [], node)  #     return solution(node), node.path_cost

        # explored.add(node.state)
        kids, events, costs, best = [], [], [], {}
        for action in problem.actions(node.state):
            child = ucs.child_node(problem, node, action)
            costs.append(child.path_cost)
            known = best.get(child.state, self.best_cost.get(child.state, float("inf")))
            explored = child.state == node.state or child.state in m.eset
            # if child.state not in explored and child.path_cost < best_cost.get(child.state, float("inf")):
            if not explored and child.path_cost < known:
                best[child.state] = child.path_cost         # best_cost[child.state] = child.path_cost
                kids.append(child)                          # push(frontier, child)
                events.append((action, "push"))
            else:
                events.append((action, "skip"))
        return Step(node, True, kids, None, events, costs)


# ##############################################################################
# Danh sách thuật toán: tên -> lớp (thêm thuật toán mới: thêm 1 dòng ở đây)
# ##############################################################################

ALGORITHMS = {cls.name: cls for cls in (BFSStepper, DFSStepper, UCSStepper)}


# ##############################################################################
# SearchMachine: Next / Prev theo dòng code hoặc theo vòng lặp
# ##############################################################################

# tag dòng code -> thao tác lên frontier / explored khi chạy từng dòng
_TAG_OP = {"pop": "pop", "explored_add": "add", "push_child": "push",
           "return_child": "found", "return_pop": "found"}


class SearchMachine:
    """Vị trí hiện tại = (cursor, sub): đã chạy xong `cursor` vòng lặp, và đã chạy `sub` dòng
    của vòng lặp kế tiếp (sub = 0 nghĩa là chưa bắt đầu vòng đó)."""

    def __init__(self, problem, algo, tracer=None):
        self.problem = problem
        self.algo = algo                      # tên thuật toán, khóa trong ALGORITHMS
        self.tracer = tracer                  # (algo, step, exhausted_after) -> [(tag, note)]
        self.sub = 0
        self.q = []                           # frontier: Queue / Stack (list) hoặc heap của UCS
        self.strategy = ALGORITHMS[algo](self)
        self.root = self.strategy.make_root()
        self.strategy.push(self.root)
        self.fcount = Counter({self.root.state: 1})
        self.explored = []                    # theo thứ tự thăm
        self.enodes = []                      # node tương ứng với từng state trong explored (để biết chi phí)
        self.eset = set()
        self.history = []
        self.cursor = 0
        self.current = None
        self.found = None
        if self.strategy.check_goal_at_init and self.strategy.goal_test(self.root.state):
            self.current = self.root
            self.found = self.root

    # ---- thông tin
    @property
    def frontier_len(self):
        return len(self.q)

    @property
    def exhausted(self):
        return (self.found is None and self.frontier_len == 0 and self.sub == 0
                and self.cursor == len(self.history))

    @property
    def iteration(self):
        """Số thứ tự vòng lặp đang chạy / vừa chạy xong."""
        return self.cursor + (1 if self.sub else 0)

    def can_next(self):
        return self.found is None and (self.sub > 0 or self.cursor < len(self.history) or self.frontier_len > 0)

    def can_prev(self):
        return self.cursor > 0 or self.sub > 0

    def last_step(self):
        return self.history[self.cursor - 1] if self.cursor > 0 else None

    def active_step(self):
        """Vòng lặp đang chạy dở, hoặc vòng vừa chạy xong."""
        if self.sub:
            return self.history[self.cursor]
        return self.last_step()

    def active_pos(self):
        """(step, chỉ số dòng vừa chạy trong trace của step) - None nếu chưa chạy vòng nào."""
        if self.sub:
            st = self.history[self.cursor]
            return st, self.sub - 1
        st = self.last_step()
        if st is None:
            return None, -1
        return st, len(self.trace_of(st)) - 1

    def pushed_kids(self):
        """Các node con đã được đẩy vào frontier trong vòng lặp đang xét (theo số dòng đã chạy)."""
        st, i = self.active_pos()
        if st is None:
            return []
        ops = self.ops_of(st)
        n = sum(1 for o in ops[:i + 1] if o == "push")
        return st.kids[:n]

    def added_in_active(self):
        st, i = self.active_pos()
        if st is None or not st.added:
            return False
        return "add" in self.ops_of(st)[:i + 1]

    def trace_of(self, st):
        if st.trace is None:
            st.trace = self.tracer(self.algo, st, st.exhaust) if self.tracer else []
        return st.trace

    def ops_of(self, st):
        if st.ops is None:
            st.ops = [_TAG_OP.get(tag) for tag, _ in self.trace_of(st)]
        return st.ops

    def frontier_slice(self, start, count):
        """Các node trong frontier theo thứ tự SẼ ĐƯỢC LẤY RA (đầu queue / đỉnh stack / g nhỏ nhất trước)."""
        n = self.frontier_len
        if start >= n:
            return []
        return self.strategy.frontier_slice(start, min(count, n - start))

    def explored_slice(self, start, count):
        """Các state đã thăm, mới nhất trước."""
        m = len(self.explored)
        if start >= m:
            return []
        count = min(count, m - start)
        top = m - 1 - start
        return [self.explored[top - i] for i in range(count)]

    def path_states(self):
        return ucs.solution(self.found) if self.found else []

    def path_actions(self):
        return solution_actions(self.found) if self.found else []

    # ---- điều khiển
    def next(self):
        """Chạy hết vòng lặp hiện tại (nếu đang chạy dở thì chạy nốt các dòng còn lại)."""
        if not self.can_next():
            return False
        if self.sub:
            while self.sub:
                self.line_next()
            return True
        if self.cursor < len(self.history):
            step = self.history[self.cursor]
        else:
            step = self._new_step()
        self._apply(step)
        return True

    def prev(self):
        """Lùi về đầu vòng lặp đang chạy dở, hoặc hoàn tác cả vòng lặp trước đó."""
        if not self.can_prev():
            return False
        if self.sub:
            while self.sub:
                self.line_prev()
            return True
        self._undo(self.history[self.cursor - 1])
        return True

    def line_next(self):
        """Chạy đúng 1 dòng code tiếp theo."""
        if not self.can_next():
            return False
        if self.sub == 0 and self.cursor == len(self.history):
            self._new_step()
        st = self.history[self.cursor]
        ops = self.ops_of(st)
        self._op(st, ops[self.sub], ops, self.sub, undo=False)
        self.sub += 1
        if self.sub >= len(ops):
            self.sub = 0
            self.cursor += 1
        return True

    def line_prev(self):
        """Lùi lại đúng 1 dòng code."""
        if not self.can_prev():
            return False
        if self.sub == 0:
            self.cursor -= 1
            self.sub = len(self.ops_of(self.history[self.cursor]))
        st = self.history[self.cursor]
        ops = self.ops_of(st)
        self.sub -= 1
        self._op(st, ops[self.sub], ops, self.sub, undo=True)
        return True

    def run_to_end(self, max_steps=400000, budget=6.0):
        """Chạy liên tục đến khi tìm thấy goal / hết frontier. Trả về số bước đã chạy."""
        t0 = time.time()
        n = 0
        while self.can_next() and n < max_steps:
            self.next()
            n += 1
            if (n & 1023) == 0 and time.time() - t0 > budget:
                break
        return n

    # ---- nội bộ
    def _new_step(self):
        step = self.strategy.compute()
        step.exhaust = step.goal is None and self.frontier_len - 1 + len(step.kids) == 0
        self.history.append(step)
        return step

    def _op(self, st, op, ops, i, undo):
        """Thực hiện (hoặc hoàn tác) thao tác của dòng thứ i trong vòng lặp st."""
        if op is None:
            return
        if op == "pop":
            if not undo:
                self.strategy.pop()
                self.fcount[st.popped.state] -= 1
                self.current = st.popped
            else:
                self.strategy.unpop(st.popped)
                self.fcount[st.popped.state] += 1
                self.current = self.history[self.cursor - 1].popped if self.cursor > 0 else None
        elif op == "add":
            if st.added:
                if not undo:
                    self._explore(st.popped)
                else:
                    self._unexplore(st.popped)
        elif op == "push":
            j = sum(1 for o in ops[:i] if o == "push")
            self._add_kid(st.kids[j]) if not undo else self._del_kid(st.kids[j])
        elif op == "found":
            self.found = None if undo else st.goal

    def _explore(self, node):
        self.explored.append(node.state)
        self.enodes.append(node)
        self.eset.add(node.state)

    def _unexplore(self, node):
        self.explored.pop()
        self.enodes.pop()
        self.eset.discard(node.state)

    def _add_kid(self, k):
        self.strategy.push(k)
        self.fcount[k.state] += 1

    def _del_kid(self, k):
        self.strategy.unpush(k)
        self.fcount[k.state] -= 1

    def _apply(self, st):
        self.strategy.pop()
        self.fcount[st.popped.state] -= 1
        if st.added:
            self._explore(st.popped)
        for k in st.kids:
            self._add_kid(k)
        self.current = st.popped
        self.found = st.goal
        self.cursor += 1

    def _undo(self, st):
        self.cursor -= 1
        for k in reversed(st.kids):
            self._del_kid(k)
        if st.added:
            self._unexplore(st.popped)
        self.strategy.unpop(st.popped)
        self.fcount[st.popped.state] += 1
        self.current = self.history[self.cursor - 1].popped if self.cursor > 0 else None
        self.found = None


# ##############################################################################
# Highlight dòng code: nội dung code hiển thị + dòng nào chạy ở mỗi vòng
# ##############################################################################

def _q(v):
    """repr với nháy kép giống notebook."""
    return repr(v).replace("'", '"')


def code_lines(algo, game, initial, goal):
    """Trả về list[(text, tag)]: code của notebook; tag dùng để map bước thuật toán -> dòng code."""
    if algo == "BFS":           # notebook Buoi4 - cell 10
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
    elif algo == "UCS":         # notebook Buoi6 - cell 9
        body = [
            ("def UCS(problem):", "def"),
            ("    node = Node(problem.initial_state)", "init_node"),
            ("    frontier = PriorityQueue()", "frontier_init"),
            ("    push(frontier, node)", "push_root"),
            ("    best_cost = {node.state: 0}  # chi phí nhỏ nhất đã biết của mỗi trạng thái", "best_init"),
            ("    explored = set()", "explored_init"),
            ("", None),
            ("    while not is_empty(frontier):", "while"),
            ("        node = pop(frontier)", "pop"),
            ("        # bỏ qua bản cũ (chi phí cao hơn) của trạng thái đã xét", None),
            ("        if node.state in explored:", "if_stale"),
            ("            continue", "continue"),
            ("        # chỉ kiểm tra goal khi lấy node ra để đảm bảo tối ưu", None),
            ("        if is_goal(problem, node.state):", "goal_pop"),
            ("            return solution(node), node.path_cost", "return_pop"),
            ("", None),
            ("        explored.add(node.state)", "explored_add"),
            ("        for action in problem.actions(node.state):", "for"),
            ("            child = child_node(problem, node, action)", "child"),
            ("            if child.state not in explored and \\", "if_new"),
            ("               child.path_cost < best_cost.get(child.state,", "if_new"),
            ('                                               float("inf")):', "if_new"),
            ("                best_cost[child.state] = child.path_cost", "best_update"),
            ("                push(frontier, child)", "push_child"),
            ("", None),
            ("    return None, None", "return_none"),
        ]
    else:                       # notebook Buoi5 - cell 9
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
    ucs_ = algo == "UCS"
    if game == "puzzle":        # cell chạy thử 8-puzzle
        setup = [("# ---------------- 8-puzzle ----------------", None),
                 (f"initial = {_q(initial)}", "setup_init"),
                 (f"goal = {_q(goal)}", "setup_goal")]
        if ucs_:                # Buoi6 - cell 10
            setup += [("def step_cost_puzzle(state, action):", "setup_cost"),
                      ('    if action in ("Up", "Down"):', "setup_cost"),
                      ("        return 1", "setup_cost"),
                      ("    return 2", "setup_cost")]
        setup.append(("problem = Problem(initial, goal, actions_puzzle, result_puzzle"
                      + (", step_cost_puzzle)" if ucs_ else ")"), "setup_problem"))
    else:                       # cell chạy thử vacuum robot
        setup = [("# -------------- vacuum robot ---------------", None),
                 (f"initial = {_q(initial)}", "setup_init"),
                 (f"goal = lambda s: s[1] == {_q(goal)}", "setup_goal")]
        if ucs_:                # Buoi6 - cell 12
            setup += [("def step_cost_vacuum(state, action):", "setup_cost"),
                      ('    if action == "Suck":', "setup_cost"),
                      ("        return 1", "setup_cost"),
                      ("    return 2", "setup_cost")]
        setup.append(("problem = Problem(initial, goal, actions_vacuum, result_vacuum"
                      + (", step_cost_vacuum)" if ucs_ else ")"), "setup_problem"))
    setup.append(((f"path, cost = {algo}(problem)" if ucs_ else f"path = {algo}(problem)"), "call"))
    return body + [("", None)] + setup


def _node_label(node):
    return "root" if node.action is None else node.action


def init_trace(algo, root_is_goal):
    """Các dòng chạy trước vòng lặp: tạo problem, gọi hàm, khởi tạo frontier."""
    t = [("setup_init", ""), ("setup_goal", "")]
    if algo == "UCS":
        t.append(("setup_cost", ""))
    t += [("setup_problem", ""), ("call", ""), ("def", ""), ("init_node", "node = root")]
    if algo == "UCS":       # UCS không kiểm tra goal ở root, mà kiểm tra khi lấy node ra
        return t + [("frontier_init", ""), ("push_root", "push root"), ("best_init", "root: 0"),
                    ("explored_init", "")]
    if root_is_goal:
        t += [("init_goal", "True"), ("init_return", "")]
    else:
        t += [("init_goal", "False"), ("frontier_init", ""), ("push_root", "push root"), ("explored_init", "")]
    return t


def step_trace(algo, step, exhausted_after):
    """Các dòng code đã chạy trong 1 vòng `while` (step), kèm giá trị hiện bên cạnh dòng."""
    t = [("while", "True"), ("pop", f"node = {_node_label(step.popped)}")]
    if algo == "UCS":
        t[1] = ("pop", f"node = {_node_label(step.popped)} · g={step.popped.path_cost}")
        if step.stale:
            t += [("if_stale", "True"), ("continue", "")]
        else:
            t.append(("if_stale", "False"))
            if step.goal is not None:
                return t + [("goal_pop", "True"), ("return_pop", f"cost = {step.goal.path_cost}")]
            t += [("goal_pop", "False"), ("explored_add", "")]
            for (action, outcome), cost in zip(step.events, step.costs):
                t += [("for", f"action = '{action}'"), ("child", f"g={cost}")]
                if outcome == "push":
                    t += [("if_new", "True"), ("best_update", f"= {cost}"), ("push_child", "")]
                else:
                    t.append(("if_new", "False"))
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
            return f"Lấy node có path_cost nhỏ nhất ({note.rsplit('g=', 1)[-1]}) ra khỏi Frontier."
        where = "đầu Queue" if algo == "BFS" else "đỉnh Stack"
        return f"Lấy node ở {where} ra khỏi Frontier."
    if tag == "if_stale":
        return ("Trạng thái này đã thăm rồi (đây là bản cũ, chi phí cao hơn)." if note == "True"
                else "Trạng thái này chưa thăm → xét tiếp.")
    if tag == "continue":
        return "Bỏ qua node cũ này, quay lại đầu vòng lặp."
    if tag == "goal_pop":
        return "Node này là goal!" if note == "True" else "Node này chưa phải goal."
    if tag == "return_pop":
        if algo == "UCS":
            return "Trả về đường đi và chi phí → dừng (UCS kiểm tra goal khi lấy ra nên đường đi rẻ nhất)."
        return "Trả về đường đi tới node goal → dừng (DFS kiểm tra goal khi lấy ra)."
    if tag == "explored_add":
        return "Đánh dấu node đã thăm: thêm vào Empty (explored)."
    if tag == "for":
        return f"Xét hành động {action}."
    if tag == "child":
        if algo == "UCS":
            return f"Sinh node con bằng hành động {action}, path_cost = {note.replace('g=', '')}."
        return f"Sinh node con bằng hành động {action}."
    if tag == "if_new":
        if algo == "UCS":
            return ("Node con chưa thăm và rẻ hơn chi phí tốt nhất đã biết." if note == "True"
                    else "Node con đã thăm, hoặc không rẻ hơn chi phí tốt nhất đã biết → bỏ qua.")
        if note == "True":
            return "Node con chưa thăm" + (" và chưa có trong Frontier." if algo == "BFS" else ".")
        return "Node con đã thăm" + (" hoặc đã có trong Frontier" if algo == "BFS" else "") + " → bỏ qua."
    if tag == "best_update":
        return f"Ghi nhận chi phí nhỏ nhất đã biết của trạng thái con {note}."
    if tag == "goal_child":
        return "Node con là goal!" if note == "True" else "Node con chưa phải goal."
    if tag == "return_child":
        return "Trả về đường đi tới node con goal → dừng (BFS kiểm tra goal khi sinh con)."
    if tag == "push_child":
        if algo == "UCS":
            return f"Đưa node con ({action}) vào Priority Queue (xếp theo path_cost)."
        return f"Đưa node con ({action}) vào Frontier."
    if tag == "return_none":
        return "Không còn node nào để xét → không có lời giải."
    return ""
