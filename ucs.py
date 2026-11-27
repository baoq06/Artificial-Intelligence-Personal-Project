"""UCS (Uniform Cost Search) - chép nguyên văn từng cell của notebook 24110080_BTTL_Buoi6.ipynb.

Priority Queue theo path_cost g(n), kiểm tra goal khi LẤY node ra.
Chạy thử giống notebook:  python ucs.py
Bản chạy từng bước + highlight dòng code cho app nằm trong stepper.py.
"""


# ============================== Cell 0 ==============================
# class khởi tạo Problem
class Problem:
  def __init__(self, initial_state, goal_condition, actions, result, step_cost = None):
      self.initial_state = initial_state
      self.goal_condition = goal_condition
      self.actions = actions
      self.result = result
      # chi phí một bước đi, mặc định mỗi hành động tốn 1
      self.step_cost = step_cost or (lambda state, action: 1)


# ============================== Cell 1 ==============================
#class khởi tạo Node
class Node:
  def __init__(self, state, parent = None, action = None, path_cost = 0):
      self.state = state
      self.parent = parent
      self.action = action
      self.path_cost = path_cost  # g(n): chi phí từ start tới node


# ============================== Cell 2 ==============================
#hàm check trạng thái hiện tại có phải là goal hay không
def is_goal(problem, state):
    if callable(problem.goal_condition):
        return problem.goal_condition(state)
    return state == problem.goal_condition


# ============================== Cell 3 ==============================
# hàm khởi tạo priority queue
import heapq
from itertools import count

def PriorityQueue():
  return []


# ============================== Cell 4 ==============================
# hàm push vào priority queue, ưu tiên node có path_cost nhỏ nhất
order = count()  # khi bằng chi phí thì node vào trước ra trước

def push(queue, node):
    heapq.heappush(queue, (node.path_cost, next(order), node))


# ============================== Cell 5 ==============================
# hàm kiểm tra priority queue có rỗng hay không
def is_empty(queue):
    return len(queue) == 0


# ============================== Cell 6 ==============================
# hàm lấy node có path_cost nhỏ nhất ra (phải kiểm tra queue có rỗng không)
def pop(queue):
  if is_empty(queue):
      return None
  return heapq.heappop(queue)[2]


# ============================== Cell 7 ==============================
# hàm tạo node con của một node
def child_node(problem, parent, action):
  new_state = problem.result(parent.state, action)
  new_cost = parent.path_cost + problem.step_cost(parent.state, action)
  return Node(state=new_state, parent=parent, action=action, path_cost=new_cost)


# ============================== Cell 8 ==============================
# hàm trả về các bước từ start tới goal
def solution(node):
    trace = []
    while node is not None:
        trace.append(node.state)
        node = node.parent
    trace.reverse()
    return trace


# ============================== Cell 9 ==============================
def UCS(problem):
    node = Node(problem.initial_state)
    frontier = PriorityQueue()
    push(frontier, node)
    best_cost = {node.state: 0}  # chi phí nhỏ nhất đã biết của mỗi trạng thái
    explored = set()

    while not is_empty(frontier):
        node = pop(frontier)
        # bỏ qua bản cũ (chi phí cao hơn) của trạng thái đã xét
        if node.state in explored:
            continue
        # chỉ kiểm tra goal khi lấy node ra để đảm bảo tối ưu
        if is_goal(problem, node.state):
            return solution(node), node.path_cost

        explored.add(node.state)
        for action in problem.actions(node.state):
            child = child_node(problem, node, action)
            if child.state not in explored and child.path_cost < best_cost.get(child.state, float("inf")):
                best_cost[child.state] = child.path_cost
                push(frontier, child)

    return None, None


# ============================== Cell 10 ==============================
# hàm khởi tạo action game 8-puzzle
def actions_puzzle(state):
    r, c = 0, 0
    for i in range(3):
      for j in range(3):
        if state[i][j] == 0:
          r, c = i, j

    moves = []
    if r > 0: moves.append("Up")
    if r < 2: moves.append("Down")
    if c > 0: moves.append("Left")
    if c < 2: moves.append("Right")
    return moves

# hàm khởi tạo result 8-puzzle
def result_puzzle(state, action):
    if action == "Up":
        dr = -1
        dc = 0
    elif action == "Down":
        dr = 1
        dc = 0
    elif action == "Left":
        dr = 0
        dc = -1
    else:
        dr = 0
        dc = 1

    r, c = 0, 0
    for i in range(3):
        for j in range(3):
            if state[i][j] == 0:
                r, c = i, j

    board = []
    for row in state:
        new_row = []
        for cell in row:
            new_row.append(cell)
        board.append(new_row)

    board[r][c], board[r + dr][c + dc] = board[r + dr][c + dc], board[r][c]
    return tuple(tuple(row) for row in board)

# hàm chi phí 8-puzzle: Up/Down tốn 1, Left/Right tốn 2
def step_cost_puzzle(state, action):
    if action in ("Up", "Down"):
        return 1
    return 2


# ============================== Cell 11 ==============================
# 8-puzzle

def print_state(state):
    for row in state:
        print("[" + " ".join(map(str, row)) + "]")
    print()


if __name__ == "__main__":
    initial = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
    goal = ((1, 2, 3), (4, 5, 6), (7, 8, 0))
    problem = Problem(initial, goal, actions_puzzle, result_puzzle, step_cost_puzzle)

    path, cost = UCS(problem)
    if path is None:
        print("No solution")
    else:
        for i, state in enumerate(path):
            print(f"Step {i}:")
            print_state(state)
        print(f"Total cost: {cost}")


# ============================== Cell 12 ==============================
# hàm khởi tạo action cho vacuum robot
def actions_vacuum(state):
    loc, _ = state
    moves = ["Suck"]
    if loc == "A":
        moves.append("Right")
    elif loc == "B":
        moves.append("Left")
    return moves

# hàm khởi tạo result cho vacuum robot
def result_vacuum(state, action):
    loc, (r0, r1) = state

    if action == "Left":
        return ("A", (r0, r1))
    elif action == "Right":
        return ("B", (r0, r1))
    elif action == "Suck":
        if loc == "A":
            return ("A", ("Clean", r1))
        else:
            return ("B", (r0, "Clean"))

    return state

# hàm chi phí vacuum robot: Suck tốn 1, Left/Right tốn 2
def step_cost_vacuum(state, action):
    if action == "Suck":
        return 1
    return 2


# ============================== Cell 13 ==============================
def print_state(state):
    loc, (rA, rB) = state
    print(f"Current position: Room {loc} | Room A: {rA} | Room B: {rB}")
    print()

if __name__ == "__main__":
    initial = ("A", ("Dirty", "Dirty"))
    goal = lambda s: s[1] == ("Clean", "Clean")

    problem = Problem(initial, goal, actions_vacuum, result_vacuum, step_cost_vacuum)

    path, cost = UCS(problem)
    if path is None:
        print("No solution")
    else:
        for i, state in enumerate(path):
            print(f"Step {i}:")
            print_state(state)
        print(f"Total cost: {cost}")
