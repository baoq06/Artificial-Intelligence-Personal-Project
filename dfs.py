"""DFS (Depth-First Search) - chép nguyên văn từng cell của notebook 24110080_BTTL_Buoi5.ipynb.

Stack LIFO, kiểm tra goal khi LẤY node ra.
Chạy thử giống notebook:  python dfs.py
Bản chạy từng bước + highlight dòng code cho app nằm trong stepper.py.
"""


# ============================== Cell 0 ==============================
# class khởi tạo Problem
class Problem:
  def __init__(self, initial_state, goal_condition, actions, result):
      self.initial_state = initial_state
      self.goal_condition = goal_condition
      self.actions = actions
      self.result = result


# ============================== Cell 1 ==============================
#class khởi tạo Node
class Node:
  def __init__(self, state, parent = None, action = None):
      self.state = state
      self.parent = parent
      self.action = action


# ============================== Cell 2 ==============================
#hàm check trạng thái hiện tại có phải là goal hay không
def is_goal(problem, state):
    if callable(problem.goal_condition):
        return problem.goal_condition(state)
    return state == problem.goal_condition


# ============================== Cell 3 ==============================
# hàm khởi tạo stack
def Stack():
  return []


# ============================== Cell 4 ==============================
# hàm push vào stack
def push(stack, item):
    stack.append(item)


# ============================== Cell 5 ==============================
# hàm kiểm tra stack có rỗng hay không
def is_empty(stack):
    return len(stack) == 0


# ============================== Cell 6 ==============================
# hàm pop phần tử đầu của queue ra (phải kiểm tra queue có rỗng không)
def pop(stack):
  if is_empty(stack):
      return None
  return stack.pop()


# ============================== Cell 7 ==============================
# hàm tạo node con của một node
def child_node(problem, parent, action):
  new_state = problem.result(parent.state, action)
  return Node(state=new_state, parent=parent, action=action)


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
def DFS(problem):
    node = Node(problem.initial_state)
    if is_goal(problem, node.state):
        return solution(node)

    frontier = Stack()
    push(frontier, node)
    explored = set()

    while not is_empty(frontier):
        node = pop(frontier)
        if is_goal(problem, node.state):
            return solution(node)

        explored.add(node.state)
        for action in problem.actions(node.state):
            child = child_node(problem, node, action)
            if child.state not in explored:
                push(frontier, child)

    return None


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


# ============================== Cell 11 ==============================
# 8-puzzle

def print_state(state):
    for row in state:
        print("[" + " ".join(map(str, row)) + "]")
    print()


if __name__ == "__main__":
    initial = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
    goal = ((1, 2, 3), (4, 5, 6), (7, 8, 0))
    problem = Problem(initial, goal, actions_puzzle, result_puzzle)

    path = DFS(problem)
    if path is None:
        print("No solution")
    else:
        for i, state in enumerate(path):
            print(f"Step {i}:")
            print_state(state)


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


# ============================== Cell 13 ==============================
def print_state(state):
    loc, (rA, rB) = state
    print(f"Current position: Room {loc} | Room A: {rA} | Room B: {rB}")
    print()

if __name__ == "__main__":
    initial = ("A", ("Dirty", "Dirty"))
    goal = lambda s: s[1] == ("Clean", "Clean")

    problem = Problem(initial, goal, actions_vacuum, result_vacuum)

    path = DFS(problem)
    if path is None:
        print("No solution")
    else:
        for i, state in enumerate(path):
            print(f"Step {i}:")
            print_state(state)
