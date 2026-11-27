"""Khởi tạo các bài toán cho app: 8-puzzle và Vacuum robot.

Problem, actions, result và step_cost lấy từ ucs.py (notebook Buoi6) - bản đầy đủ nhất của 3 notebook
(Problem có thêm step_cost; actions / result giống hệt Buoi4, Buoi5). File này chỉ thêm phần riêng của app:
trạng thái mặc định, hàm tạo Problem, xáo trộn ngẫu nhiên và kiểm tra đầu vào có giải được không.
"""
import random

from ucs import (Problem, actions_puzzle, actions_vacuum, result_puzzle, result_vacuum, step_cost_puzzle,
                 step_cost_vacuum)

PUZZLE_INIT = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
PUZZLE_GOAL = ((1, 2, 3), (4, 5, 6), (7, 8, 0))
VACUUM_INIT = ("A", ("Dirty", "Dirty"))
VACUUM_GOAL_ROOMS = ("Clean", "Clean")


# ------------------------------------------------------------------ 8-puzzle
def make_puzzle_problem(initial, goal):
    """Giống notebook: Problem(initial, goal, actions_puzzle, result_puzzle, step_cost_puzzle)."""
    return Problem(initial, goal, actions_puzzle, result_puzzle, step_cost_puzzle)


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
def make_vacuum_problem(initial, goal_rooms):
    """Giống notebook: goal = lambda s: s[1] == ("Clean", "Clean")."""
    goal = lambda s: s[1] == goal_rooms
    return Problem(initial, goal, actions_vacuum, result_vacuum, step_cost_vacuum)


def vacuum_reachable(initial, goal_rooms):
    """Vacuum chỉ có thể làm sạch phòng, không làm bẩn lại."""
    for cur, want in zip(initial[1], goal_rooms):
        if cur == "Clean" and want == "Dirty":
            return False
    return True
