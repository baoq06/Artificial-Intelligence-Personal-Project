"""Định nghĩa 2 bài toán: 8-puzzle và Vacuum robot (lấy từ notebook)."""
import random

from algorithms import Problem

PUZZLE_INIT = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
PUZZLE_GOAL = ((1, 2, 3), (4, 5, 6), (7, 8, 0))
VACUUM_INIT = ("A", ("Dirty", "Dirty"))
VACUUM_GOAL_ROOMS = ("Clean", "Clean")


# ------------------------------------------------------------------ 8-puzzle
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


def result_puzzle(state, action):
    if action == "Up":
        dr, dc = -1, 0
    elif action == "Down":
        dr, dc = 1, 0
    elif action == "Left":
        dr, dc = 0, -1
    else:
        dr, dc = 0, 1
    r, c = 0, 0
    for i in range(3):
        for j in range(3):
            if state[i][j] == 0:
                r, c = i, j
    board = [list(row) for row in state]
    board[r][c], board[r + dr][c + dc] = board[r + dr][c + dc], board[r][c]
    return tuple(tuple(row) for row in board)


def make_puzzle_problem(initial, goal):
    return Problem(initial, goal, actions_puzzle, result_puzzle)


def _inversions(state):
    flat = [v for row in state for v in row if v != 0]
    return sum(1 for i in range(len(flat)) for j in range(i + 1, len(flat)) if flat[i] > flat[j])


def puzzle_solvable(initial, goal):
    return _inversions(initial) % 2 == _inversions(goal) % 2


def random_puzzle(goal, moves=14):
    """Xáo trộn từ goal bằng các nước đi hợp lệ => chắc chắn giải được."""
    state, prev = goal, None
    opposite = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}
    for _ in range(moves):
        acts = [a for a in actions_puzzle(state) if a != opposite.get(prev)]
        prev = random.choice(acts)
        state = result_puzzle(state, prev)
    if state == goal:
        return random_puzzle(goal, moves)
    return state


# ------------------------------------------------------------------ Vacuum robot
def actions_vacuum(state):
    loc, _ = state
    moves = ["Suck"]
    if loc == "A":
        moves.append("Right")
    elif loc == "B":
        moves.append("Left")
    return moves


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


def make_vacuum_problem(initial, goal_rooms):
    goal = lambda s: s[1] == goal_rooms
    return Problem(initial, goal, actions_vacuum, result_vacuum)


def vacuum_reachable(initial, goal_rooms):
    """Vacuum chỉ có thể làm sạch phòng, không làm bẩn lại."""
    for cur, want in zip(initial[1], goal_rooms):
        if cur == "Clean" and want == "Dirty":
            return False
    return True
