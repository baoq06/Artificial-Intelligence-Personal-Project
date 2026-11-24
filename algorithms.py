"""BFS / DFS dạng "từng bước" (có thể tiến / lùi).

Logic bám sát 2 notebook:
  * BFS (Buoi4): Queue, kiểm tra goal lúc SINH node con, bỏ qua con đã ở explored hoặc đã nằm trong frontier.
  * DFS (Buoi5): Stack, kiểm tra goal lúc LẤY node ra, chỉ bỏ qua con đã ở explored.

Mỗi lần gọi next() thực hiện đúng 1 vòng lặp `while` của thuật toán và ghi lại một Step
(chỉ lưu phần thay đổi) để prev() có thể hoàn tác rất nhanh, kể cả khi frontier có hàng chục nghìn phần tử.
"""
import time
from collections import Counter


# ---------------------------------------------------------------- cấu trúc từ notebook
class Problem:
    def __init__(self, initial_state, goal_condition, actions, result):
        self.initial_state = initial_state
        self.goal_condition = goal_condition
        self.actions = actions
        self.result = result


class Node:
    __slots__ = ("state", "parent", "action", "depth")

    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.depth = 0 if parent is None else parent.depth + 1


def is_goal(problem, state):
    if callable(problem.goal_condition):
        return problem.goal_condition(state)
    return state == problem.goal_condition


def child_node(problem, parent, action):
    new_state = problem.result(parent.state, action)
    return Node(state=new_state, parent=parent, action=action)


def solution(node):
    trace = []
    while node is not None:
        trace.append(node.state)
        node = node.parent
    trace.reverse()
    return trace


def solution_actions(node):
    acts = []
    while node is not None and node.parent is not None:
        acts.append(node.action)
        node = node.parent
    acts.reverse()
    return acts


# ---------------------------------------------------------------- máy tìm kiếm từng bước
class Step:
    """Một vòng lặp của thuật toán."""
    __slots__ = ("popped", "added", "kids", "goal")

    def __init__(self, popped, added, kids, goal):
        self.popped = popped      # node vừa lấy ra khỏi frontier
        self.added = added        # có thêm vào explored ("Empty") không
        self.kids = kids          # các node con vừa được đẩy vào frontier
        self.goal = goal          # node goal nếu tìm thấy ở bước này


class SearchMachine:
    def __init__(self, problem, algo):
        self.problem = problem
        self.algo = algo                      # "BFS" | "DFS"
        self.root = Node(problem.initial_state)
        self.q = [self.root]                  # BFS: dùng q[head:]; DFS: dùng như stack
        self.head = 0
        self.fcount = Counter({self.root.state: 1})
        self.explored = []                    # theo thứ tự thăm
        self.eset = set()
        self.history = []
        self.cursor = 0
        self.current = None
        self.found = None
        if is_goal(problem, self.root.state):
            self.current = self.root
            self.found = self.root

    # ---- thông tin
    @property
    def frontier_len(self):
        return len(self.q) - self.head

    @property
    def exhausted(self):
        return self.found is None and self.frontier_len == 0 and self.cursor == len(self.history)

    def can_next(self):
        return self.found is None and (self.cursor < len(self.history) or self.frontier_len > 0)

    def can_prev(self):
        return self.cursor > 0

    def last_step(self):
        return self.history[self.cursor - 1] if self.cursor > 0 else None

    def frontier_slice(self, start, count):
        """Các node trong frontier theo thứ tự SẼ ĐƯỢC LẤY RA (đầu queue / đỉnh stack trước)."""
        n = self.frontier_len
        if start >= n:
            return []
        count = min(count, n - start)
        if self.algo == "BFS":
            a = self.head + start
            return self.q[a:a + count]
        top = len(self.q) - 1 - start
        return [self.q[top - i] for i in range(count)]

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
        if not self.can_next():
            return False
        if self.cursor < len(self.history):
            step = self.history[self.cursor]
        else:
            step = self._compute()
            self.history.append(step)
        self._apply(step)
        return True

    def prev(self):
        if not self.can_prev():
            return False
        self._undo(self.history[self.cursor - 1])
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
    def _compute(self):
        p = self.problem
        if self.algo == "BFS":
            node = self.q[self.head]
            added = node.state not in self.eset
            ns = node.state
            kids, goal, local = [], None, set()
            for action in p.actions(node.state):
                child = child_node(p, node, action)
                cs = child.state
                if cs == ns or cs in self.eset or cs in local:
                    continue
                # trong frontier? (node vừa dequeue không còn trong frontier)
                in_frontier = self.fcount[cs] - (1 if cs == node.state else 0) > 0
                if in_frontier:
                    continue
                if is_goal(p, cs):
                    goal = child
                    break
                kids.append(child)
                local.add(cs)
            return Step(node, added, kids, goal)
        # DFS
        node = self.q[-1]
        if is_goal(p, node.state):
            return Step(node, False, [], node)
        added = node.state not in self.eset
        ns = node.state
        kids = []
        for action in p.actions(node.state):
            child = child_node(p, node, action)
            if child.state != ns and child.state not in self.eset:
                kids.append(child)
        return Step(node, added, kids, None)

    def _apply(self, st):
        if self.algo == "BFS":
            self.head += 1
        else:
            self.q.pop()
        self.fcount[st.popped.state] -= 1
        if st.added:
            self.explored.append(st.popped.state)
            self.eset.add(st.popped.state)
        for k in st.kids:
            self.q.append(k)
            self.fcount[k.state] += 1
        self.current = st.popped
        self.found = st.goal
        self.cursor += 1

    def _undo(self, st):
        self.cursor -= 1
        if st.kids:
            for k in st.kids:
                self.fcount[k.state] -= 1
            del self.q[-len(st.kids):]
        if st.added:
            self.explored.pop()
            self.eset.discard(st.popped.state)
        if self.algo == "BFS":
            self.head -= 1
        else:
            self.q.append(st.popped)
        self.fcount[st.popped.state] += 1
        self.current = self.history[self.cursor - 1].popped if self.cursor > 0 else None
        self.found = None
