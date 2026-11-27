"""BFS (Breadth-First Search) - chép nguyên văn từng cell của notebook 24110080_BTTL_Buoi4.ipynb.

Queue FIFO, kiểm tra goal khi SINH node con.
Chạy thử giống notebook:  python bfs.py
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
    return state == problem.goal_condition


# ============================== Cell 3 ==============================
# hàm khởi tạo queue
def Queue():
  return []


# ============================== Cell 4 ==============================
# hàm push vào queue
def enqueue(queue, item):
    queue.append(item)


# ============================== Cell 5 ==============================
# hàm kiểm tra queue có rỗng hay không
def is_empty(queue):
    return len(queue) == 0


# ============================== Cell 6 ==============================
# hàm pop phần tử đầu của queue ra (phải kiểm tra queue có rỗng không)
def dequeue(queue):
  if is_empty(queue):
    return None
  node = queue[0]
  del queue[0]
  return node


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
# hàm khởi tạo action
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

# hàm khởi tạo result
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


# ============================== Cell 10 ==============================
def BFS(problem):
    node = Node(problem.initial_state)
    if is_goal(problem, node.state):
        return solution(node)

    frontier = Queue()
    enqueue(frontier, node)
    explored = set()

    while not is_empty(frontier):
        node = dequeue(frontier)
        explored.add(node.state)
        for action in problem.actions(node.state):
            child = child_node(problem, node, action)
            if child.state not in explored and all(n.state != child.state for n in frontier):
                if is_goal(problem, child.state):
                    return solution(child)
                enqueue(frontier, child)

    return None


def print_state(state):
    for row in state:
        print("[" + " ".join(map(str, row)) + "]")
    print()


if __name__ == "__main__":
    initial = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
    goal = ((1, 2, 3), (4, 5, 6), (7, 8, 0))
    problem = Problem(initial, goal, actions_puzzle, result_puzzle)

    path = BFS(problem)
    if path is None:
        print("No solution")
    else:
        for i, state in enumerate(path):
            print(f"Step {i}:")
            print_state(state)
