"""UCS (Uniform Cost Search): Priority Queue theo g(n) = chi phí đường đi từ root, kiểm tra goal lúc LẤY node ra.

Node con đã có trong Frontier mà đường đi mới RẺ HƠN thì thay thế node cũ (replace).
Frontier giữ sắp xếp theo (g, thứ tự thêm vào) nên đầu danh sách luôn là node sẽ được lấy ra.
"""
from bisect import bisect_left

from .base import SearchAlgorithm
from .core import Step, child_node, is_goal


class UCS(SearchAlgorithm):
    name = "UCS"
    frontier_kind = "Priority Queue (g nhỏ nhất)"
    check_goal_at_init = False

    def __init__(self, machine):
        super().__init__(machine)
        self.seq = 0
        self.key = {}                 # id(node) -> (g, số thứ tự) ; giữ nguyên khi hoàn tác / làm lại
        self.ks = []                  # khóa sắp xếp, song song với m.q
        self.by_state = {}            # state -> node đang nằm trong frontier
        root = machine.q[0]           # root đã nằm sẵn trong m.q, chỉ cần đăng ký khóa
        self.key[id(root)] = (root.cost, 0)
        self.ks.append(self.key[id(root)])
        self.by_state[root.state] = root

    # ---- frontier = m.q sắp xếp tăng dần theo khóa (g, seq)
    def _insert(self, node):
        k = self.key.get(id(node))
        if k is None:
            self.seq += 1
            k = self.key[id(node)] = (node.cost, self.seq)
        i = bisect_left(self.ks, k)
        self.ks.insert(i, k)
        self.m.q.insert(i, node)
        self.by_state[node.state] = node

    def _delete(self, node):
        i = bisect_left(self.ks, self.key[id(node)])
        del self.ks[i]
        del self.m.q[i]
        if self.by_state.get(node.state) is node:
            del self.by_state[node.state]

    def pop(self):
        self._delete(self.m.q[0])

    def unpop(self, node):
        self._insert(node)

    def push(self, node):
        self._insert(node)

    def unpush(self, node):
        self._delete(node)

    def remove(self, node):
        self._delete(node)

    def restore(self, node):
        self._insert(node)

    def frontier_slice(self, start, count):
        return self.m.q[start:start + count]

    # ---- 1 vòng lặp
    def compute(self):
        m, p = self.m, self.m.problem
        node = m.q[0]                                  # node có g nhỏ nhất
        if is_goal(p, node.state):
            return Step(node, False, [], node)
        added = node.state not in m.eset
        ns = node.state
        kids, olds, events, costs, local = [], [], [], [], {}
        for action in p.actions(ns):
            child = child_node(p, node, action)
            cs = child.state
            costs.append(child.cost)
            if cs == ns or cs in m.eset:
                events.append((action, "skip"))
                continue
            old = local.get(cs) or self.by_state.get(cs)
            if old is None:
                events.append((action, "push"))
                olds.append(None)
            elif child.cost < old.cost:
                events.append((action, "replace"))
                olds.append(old)
            else:
                events.append((action, "skip"))
                continue
            kids.append(child)
            local[cs] = child
        return Step(node, added, kids, None, events, olds, costs)
