"""Danh sách thuật toán: tên -> lớp. Thêm thuật toán mới chỉ cần thêm 1 dòng ở đây."""
from .bfs import BFS
from .dfs import DFS
from .ucs import UCS

ALGORITHMS = {cls.name: cls for cls in (BFS, DFS, UCS)}
