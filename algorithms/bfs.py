"""BFS (Buoi4): Queue FIFO, kiểm tra goal lúc SINH node con,
bỏ qua con đã ở explored hoặc đã nằm trong frontier."""
from .base import SearchAlgorithm
from .core import Step, child_node, is_goal


class BFS(SearchAlgorithm):
    name = "BFS"
    frontier_kind = "Queue (FIFO)"

    # Queue dùng list + con trỏ head: frontier = q[head:], dequeue = head += 1 (O(1), dễ hoàn tác)
    def pop(self):
        self.m.head += 1

    def unpop(self, node):
        self.m.head -= 1

    def frontier_slice(self, start, count):
        a = self.m.head + start
        return self.m.q[a:a + count]

    def compute(self):
        m, p = self.m, self.m.problem
        node = m.q[m.head]
        added = node.state not in m.eset
        ns = node.state
        kids, goal, local, events = [], None, set(), []
        for action in p.actions(node.state):
            child = child_node(p, node, action)
            cs = child.state
            if cs == ns or cs in m.eset or cs in local:
                events.append((action, "skip"))
                continue
            # trong frontier? (node vừa dequeue không còn trong frontier)
            in_frontier = m.fcount[cs] - (1 if cs == node.state else 0) > 0
            if in_frontier:
                events.append((action, "skip"))
                continue
            if is_goal(p, cs):
                events.append((action, "goal"))
                goal = child
                break
            events.append((action, "push"))
            kids.append(child)
            local.add(cs)
        return Step(node, added, kids, goal, events)
