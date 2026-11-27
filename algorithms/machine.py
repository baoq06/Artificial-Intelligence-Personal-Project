"""SearchMachine: chạy một thuật toán tìm kiếm "từng bước" (có thể tiến / lùi).

Mỗi lần gọi next() thực hiện đúng 1 vòng lặp `while` của thuật toán và ghi lại một Step
(chỉ lưu phần thay đổi) để prev() có thể hoàn tác rất nhanh, kể cả khi frontier có hàng chục nghìn phần tử.
Phần riêng của từng thuật toán (cách lấy node ra, sinh con, kiểm tra goal) nằm trong bfs.py / dfs.py / ucs.py.
"""
import time
from collections import Counter

from .core import Node, is_goal, solution, solution_actions
from .registry import ALGORITHMS

# tag dòng code -> thao tác lên frontier / explored khi chạy từng dòng
_TAG_OP = {"pop": "pop", "explored_add": "add", "push_child": "push", "replace_child": "replace",
           "return_child": "found", "return_pop": "found"}
_KID_OPS = ("push", "replace")      # các thao tác đưa 1 node con vào frontier


class SearchMachine:
    """Vị trí hiện tại = (cursor, sub): đã chạy xong `cursor` vòng lặp, và đã chạy `sub` dòng
    của vòng lặp kế tiếp (sub = 0 nghĩa là chưa bắt đầu vòng đó)."""

    def __init__(self, problem, algo, tracer=None):
        self.problem = problem
        self.algo = algo                      # tên thuật toán, khóa trong ALGORITHMS
        self.tracer = tracer                  # (algo, step, exhausted_after) -> [(tag, note)]
        self.sub = 0
        self.root = Node(problem.initial_state)
        self.q = [self.root]                  # frontier; BFS dùng q[head:], DFS như stack, UCS luôn sắp xếp theo g
        self.head = 0
        self.fcount = Counter({self.root.state: 1})
        self.explored = []                    # theo thứ tự thăm
        self.enodes = []                      # node tương ứng với từng state trong explored (để biết chi phí g)
        self.eset = set()
        self.strategy = ALGORITHMS[algo](self)
        self.history = []
        self.cursor = 0
        self.current = None
        self.found = None
        if self.strategy.check_goal_at_init and is_goal(problem, self.root.state):
            self.current = self.root
            self.found = self.root

    # ---- thông tin
    @property
    def frontier_len(self):
        return len(self.q) - self.head

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
        n = sum(1 for o in ops[:i + 1] if o in _KID_OPS)
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
        """Các node trong frontier theo thứ tự SẼ ĐƯỢC LẤY RA (đầu queue / đỉnh stack trước)."""
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
        return solution(self.found) if self.found else []

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
        net_kids = len(step.kids) - (sum(1 for o in step.olds if o is not None) if step.olds else 0)
        step.exhaust = step.goal is None and self.frontier_len - 1 + net_kids == 0
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
                    self.explored.append(st.popped.state)
                    self.enodes.append(st.popped)
                    self.eset.add(st.popped.state)
                else:
                    self.explored.pop()
                    self.enodes.pop()
                    self.eset.discard(st.popped.state)
        elif op in _KID_OPS:
            j = sum(1 for o in ops[:i] if o in _KID_OPS)
            self._add_kid(st, j) if not undo else self._del_kid(st, j)
        elif op == "found":
            self.found = None if undo else st.goal

    def _add_kid(self, st, j):
        """Đưa node con thứ j vào frontier; nếu nó thay thế node cũ (UCS) thì bỏ node cũ trước."""
        old = st.olds[j] if st.olds else None
        if old is not None:
            self.strategy.remove(old)
            self.fcount[old.state] -= 1
        k = st.kids[j]
        self.strategy.push(k)
        self.fcount[k.state] += 1

    def _del_kid(self, st, j):
        k = st.kids[j]
        self.strategy.unpush(k)
        self.fcount[k.state] -= 1
        old = st.olds[j] if st.olds else None
        if old is not None:
            self.strategy.restore(old)
            self.fcount[old.state] += 1

    def _apply(self, st):
        self.strategy.pop()
        self.fcount[st.popped.state] -= 1
        if st.added:
            self.explored.append(st.popped.state)
            self.enodes.append(st.popped)
            self.eset.add(st.popped.state)
        for j in range(len(st.kids)):
            self._add_kid(st, j)
        self.current = st.popped
        self.found = st.goal
        self.cursor += 1

    def _undo(self, st):
        self.cursor -= 1
        for j in reversed(range(len(st.kids))):
            self._del_kid(st, j)
        if st.added:
            self.explored.pop()
            self.enodes.pop()
            self.eset.discard(st.popped.state)
        self.strategy.unpop(st.popped)
        self.fcount[st.popped.state] += 1
        self.current = self.history[self.cursor - 1].popped if self.cursor > 0 else None
        self.found = None
