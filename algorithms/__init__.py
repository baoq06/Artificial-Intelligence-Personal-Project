"""Thuật toán tìm kiếm chạy từng bước (có thể tiến / lùi).

  core.py      Problem, Node, Step và hàm tiện ích
  base.py      lớp cơ sở SearchAlgorithm
  bfs.py       BFS
  dfs.py       DFS
  ucs.py       UCS (Uniform Cost Search)
  registry.py  tên thuật toán -> lớp
  machine.py   SearchMachine: chạy / lùi từng vòng lặp, từng dòng code
"""
from .core import Node, Problem, Step, child_node, is_goal, solution, solution_actions, solution_costs
from .machine import SearchMachine
from .registry import ALGORITHMS

__all__ = ["ALGORITHMS", "Node", "Problem", "SearchMachine", "Step", "child_node", "is_goal",
           "solution", "solution_actions", "solution_costs"]
