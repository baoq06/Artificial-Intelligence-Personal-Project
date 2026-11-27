"""Cấu trúc dùng chung từ notebook: Problem, Node và các hàm tiện ích."""


class Problem:
    def __init__(self, initial_state, goal_condition, actions, result, step_cost=None):
        self.initial_state = initial_state
        self.goal_condition = goal_condition
        self.actions = actions
        self.result = result
        # step_cost(state, action) -> chi phí của 1 hành động (mặc định mỗi hành động tốn 1)
        self.step_cost = step_cost or (lambda state, action: 1)


class Node:
    __slots__ = ("state", "parent", "action", "depth", "cost")

    def __init__(self, state, parent=None, action=None, cost=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.depth = 0 if parent is None else parent.depth + 1
        self.cost = cost          # g(n): tổng chi phí từ root tới node này


def is_goal(problem, state):
    if callable(problem.goal_condition):
        return problem.goal_condition(state)
    return state == problem.goal_condition


def child_node(problem, parent, action):
    new_state = problem.result(parent.state, action)
    cost = parent.cost + problem.step_cost(parent.state, action)
    return Node(state=new_state, parent=parent, action=action, cost=cost)


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


def solution_costs(node):
    """Chi phí tích lũy g(n) tại từng trạng thái trên đường đi (root = 0)."""
    costs = []
    while node is not None:
        costs.append(node.cost)
        node = node.parent
    costs.reverse()
    return costs


class Step:
    """Một vòng lặp của thuật toán (chỉ lưu phần thay đổi để có thể hoàn tác nhanh)."""
    __slots__ = ("popped", "added", "kids", "goal", "events", "exhaust", "trace", "ops", "olds", "costs")

    def __init__(self, popped, added, kids, goal, events=(), olds=None, costs=None):
        self.popped = popped      # node vừa lấy ra khỏi frontier
        self.added = added        # có thêm vào explored ("Empty") không
        self.kids = kids          # các node con vừa được đẩy vào frontier
        self.goal = goal          # node goal nếu tìm thấy ở bước này
        self.events = events      # [(action, "skip"|"push"|"goal"|"replace")] - dùng để highlight từng dòng code
        self.olds = olds          # UCS: song song với kids, node cũ trong Frontier bị thay thế (None = chỉ push)
        self.costs = costs        # UCS: chi phí g của node con ứng với từng event
        self.exhaust = False      # sau bước này frontier rỗng (không có lời giải)
        self.trace = None         # [(tag, note)] - các dòng code chạy trong vòng lặp (tính khi cần)
        self.ops = None           # thao tác ứng với từng dòng trong trace
