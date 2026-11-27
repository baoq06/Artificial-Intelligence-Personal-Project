"""Lớp cơ sở cho một thuật toán tìm kiếm chạy từng bước.

Muốn thêm thuật toán mới: tạo file mới trong thư mục này, viết lớp con của SearchAlgorithm
(cách lấy / trả node khỏi frontier + compute() cho 1 vòng lặp), rồi đăng ký trong registry.py.
"""


class SearchAlgorithm:
    name = ""
    frontier_kind = ""            # mô tả cấu trúc frontier, vd "Queue (FIFO)"

    check_goal_at_init = True     # có kiểm tra goal cho root trước vòng lặp không (UCS thì không)

    def __init__(self, machine):
        self.m = machine          # SearchMachine giữ frontier (m.q, m.head), explored (m.eset), ...

    # ---- frontier
    def push(self, node):
        """Thêm node vào frontier (mặc định: cuối danh sách)."""
        self.m.q.append(node)

    def unpush(self, node):
        """Hoàn tác push(): bỏ node vừa thêm."""
        self.m.q.pop()

    def remove(self, node):
        """Bỏ một node bất kỳ khỏi frontier (UCS: node bị thay thế bởi node rẻ hơn)."""
        raise NotImplementedError

    def restore(self, node):
        """Hoàn tác remove()."""
        raise NotImplementedError

    def pop(self):
        """Lấy node kế tiếp ra khỏi frontier (đã biết trước là node nào, nên không cần trả về)."""
        raise NotImplementedError

    def unpop(self, node):
        """Hoàn tác pop(): đưa node trở lại đúng vị trí cũ trong frontier."""
        raise NotImplementedError

    def frontier_slice(self, start, count):
        """Các node trong frontier theo thứ tự SẼ ĐƯỢC LẤY RA."""
        raise NotImplementedError

    # ---- 1 vòng lặp
    def compute(self):
        """Tính vòng lặp kế tiếp (không thay đổi trạng thái machine), trả về Step."""
        raise NotImplementedError
