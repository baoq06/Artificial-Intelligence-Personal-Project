"""DFS (Buoi5): Stack LIFO, kiểm tra goal lúc LẤY node ra, chỉ bỏ qua con đã ở explored."""
from .base import SearchAlgorithm
from .core import Step, child_node, is_goal


class DFS(SearchAlgorithm):
    name = "DFS"
    frontier_kind = "Stack (LIFO)"

    # Stack = list q, đỉnh stack là phần tử cuối
    def pop(self):
        self.m.q.pop()

    def unpop(self, node):
        self.m.q.append(node)

    def frontier_slice(self, start, count):
        q = self.m.q
        top = len(q) - 1 - start
        return [q[top - i] for i in range(count)]

    def compute(self):
        m, p = self.m, self.m.problem
        node = m.q[-1]
        if is_goal(p, node.state):
            return Step(node, False, [], node)
        added = node.state not in m.eset
        ns = node.state
        kids, events = [], []
        for action in p.actions(node.state):
            child = child_node(p, node, action)
            if child.state != ns and child.state not in m.eset:
                kids.append(child)
                events.append((action, "push"))
            else:
                events.append((action, "skip"))
        return Step(node, added, kids, None, events)
