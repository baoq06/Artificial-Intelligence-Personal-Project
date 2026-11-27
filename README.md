# Search Visualizer — BFS, DFS & UCS trên 8-Puzzle và Vacuum Robot

Ứng dụng **Python + Pygame** minh họa từng bước ba thuật toán tìm kiếm **BFS**, **DFS** và **UCS** (Uniform Cost Search) trên hai bài toán **8-Puzzle** và **Vacuum Robot**. Mỗi lần bấm *Next*, thuật toán chạy đúng **một dòng code**: bảng **Code** highlight dòng đó, các bảng Node, Frontier (Queue/Stack), Empty cập nhật ngay theo dòng vừa chạy (`dequeue`, `explored.add`, `enqueue`…). Nút *Node tiếp* chạy hết cả vòng lặp để xét xong một node. Khi tìm thấy goal, bảng **Đường đi** hiện toàn bộ đường đi từ đầu đến goal.

> **Sinh viên:** Mai Quốc Bảo · **MSSV:** 24110080 · HCM-UTE

![8-Puzzle với BFS tìm thấy goal](screenshots/02_puzzle_bfs_found.png)

## Tính năng

- **Chọn trò chơi và thuật toán** bằng dropdown: 8-Puzzle / Vacuum Robot, BFS / DFS / UCS.
- **Điều khiển từng bước**:
  - `Next` / `Prev`: chạy tới / lùi lại **1 dòng code**.
  - `Node tiếp`: chạy hết vòng lặp hiện tại (xét xong 1 node), highlight lướt qua các dòng còn lại.
  - `Auto`: tự bấm Next liên tục, thanh trượt chỉnh 1–240 dòng/giây.
  - `Kết quả`: chạy nhanh đến khi tìm thấy goal, bấm lần nữa để dừng.
  - `Reset`.
- **Bảng Code**: hiện code BFS/DFS/UCS giống notebook, kèm phần khởi tạo `Problem(...)` tương ứng với trò đang chọn (`actions_puzzle`/`result_puzzle` hoặc `actions_vacuum`/`result_vacuum`, trạng thái đầu và goal theo đầu vào hiện tại).
  - Mỗi lần *Next*, highlight chuyển sang dòng kế tiếp của vòng lặp (`while` → `pop`/`dequeue` → `for` → `if` → `push`/`enqueue` …), kèm giá trị như `action = 'Up'`, `True`/`False`. Bảng Node giải thích dòng vừa chạy.
  - Dòng đang chạy luôn được cuộn vào tầm nhìn; có thể tự cuộn bằng con lăn.
- **Bảng Đường đi**: sau khi tìm thấy goal, hiện chuỗi hành động (`Down → Right`) và từng trạng thái từ *Bước 0* đến *GOAL*, cuộn được khi đường đi dài. Đường đi cũng được in ra terminal giống output của notebook (`Step 0:`, `Step 1:` …).
- **Ba bảng trạng thái**:
  - **Node**: node vừa được lấy ra khỏi Frontier, kèm một câu giải thích dòng code vừa chạy.
  - **Frontier**: Queue (FIFO) với BFS, Stack (LIFO) với DFS, Priority Queue với UCS; có nhãn `HEAD` / `TOP` / `MIN` cho phần tử sắp được lấy ra.
  - **Empty**: các node đã thăm (explored), node mới nhất ở đầu.
- **Animation mượt**: ô số trượt, robot di chuyển giữa hai phòng, bụi mờ dần và có hiệu ứng hút. Thẻ mới sinh hiện dần kèm viền nổi bật.
- **Phát lại đường đi** từ đầu đến goal sau khi tìm thấy lời giải.
- **Tùy chỉnh đầu vào**:
  - 8-Puzzle: chỉnh trạng thái đầu và đích (click 2 ô để hoán đổi, hoặc click 1 ô rồi gõ `0–8`), có nút *Random* và *Về mặc định*. Đầu vào không giải được sẽ bị cảnh báo và khóa nút chạy.
  - Vacuum: đổi Dirty/Clean từng phòng, chọn vị trí xuất phát của robot, chỉnh trạng thái đích.

- **Trang cuộn được**: nếu màn hình không đủ cao, nội dung kéo dài xuống dưới và có thanh cuộn bên phải (kéo thanh cuộn, lăn chuột, hoặc dùng phím ↑ ↓ / PgUp PgDn). Nút *Đường đi* trên bàn chơi cuộn thẳng tới bảng Đường đi.

- **Cửa sổ co giãn được**: kéo giãn cửa sổ thì giao diện tự co/giãn theo chiều rộng. Muốn cửa sổ mặc định nhỏ hơn thì giảm hằng số `UI_SCALE` trong `visualizer.py` (ví dụ `0.85`).

### Bố cục

| Hàng | Bên trái | Bên phải |
|---|---|---|
| 1 | Bàn chơi + nút điều khiển + tốc độ Auto | Code (highlight dòng đang chạy) |
| 2 | Node · Frontier · Empty | |
| 3 | Đầu vào | Đường đi |

## Ảnh chụp ứng dụng

| 8-Puzzle · BFS đang chạy từng dòng (giữa vòng lặp 2) | 8-Puzzle · DFS (đường đi dài, cuộn được) |
|---|---|
| ![BFS đang chạy](screenshots/01_puzzle_bfs_running.png) | ![DFS](screenshots/03_puzzle_dfs.png) |

| Vacuum Robot · DFS | Dropdown chọn trò chơi |
|---|---|
| ![Vacuum Robot](screenshots/04_vacuum_dfs.png) | ![Dropdown](screenshots/05_dropdown.png) |

| 8-Puzzle · UCS (chi phí g trên từng thẻ) | Vacuum Robot · UCS |
|---|---|
| ![UCS 8-Puzzle](screenshots/06_puzzle_ucs.png) | ![UCS Vacuum](screenshots/07_vacuum_ucs.png) |

## Cài đặt và chạy

Yêu cầu: Python 3.9+ (đã thử với 3.11) và `pygame`.

```bash
pip install -r requirements.txt
python visualizer.py
```

### Phím tắt

| Phím | Chức năng |
|---|---|
| `→` / `←` | Next / Prev (1 dòng code) |
| `Shift` + `→` | Node tiếp (chạy hết vòng lặp) |
| `Shift` + `←` | Lùi về đầu vòng lặp (hoặc lùi cả vòng lặp trước) |
| `Space` | Auto / Pause |
| `R` | Reset |
| `Esc` | Đóng dropdown / bỏ chọn ô |
| `↑` `↓` / `PgUp` `PgDn` / `Home` `End` | Cuộn trang |

## Cách hoạt động của ba thuật toán

Logic bám theo hai notebook bài tập (`Problem`, `Node`, `child_node`, `solution`), chỉ khác là thuật toán được tách thành từng dòng để có thể bấm *Next* / *Prev* (mỗi dòng có thể hoàn tác).

| | BFS | DFS | UCS |
|---|---|---|---|
| Frontier | Queue (FIFO) | Stack (LIFO) | Priority Queue theo g(n) |
| Kiểm tra goal | Khi **sinh node con** | Khi **lấy node ra** | Khi **lấy node ra** |
| Bỏ qua node con | Đã ở Empty hoặc đã nằm trong Frontier | Chỉ cần đã ở Empty | Đã ở Empty, hoặc không rẻ hơn `best_cost` đã biết (đường rẻ hơn được `push` thêm; bản cũ khi lấy ra gặp `if node.state in explored: continue`) |
| Đường đi | Ít bước nhất | Có thể rất dài, không tối ưu | **Chi phí thấp nhất** |

### Chi phí hành động (dùng cho UCS)

- **8-Puzzle**: `Up` / `Down` tốn **1**, `Left` / `Right` tốn **2** (`step_cost_puzzle`, notebook Buoi6, trong `ucs.py`).
- **Vacuum Robot**: `Suck` tốn **1**, `Left` / `Right` tốn **2** (`step_cost_vacuum`, notebook Buoi6, trong `ucs.py`).
- Thẻ trong Frontier / Empty / Đường đi hiển thị `g=…` (tổng chi phí từ trạng thái đầu); bảng Node và Đường đi hiện chi phí từng bước và tổng chi phí.

Ví dụ với 8-Puzzle `((1,2,3),(4,0,6),(7,5,8))` → `((1,2,3),(4,5,6),(7,8,0))`: BFS tìm ra đường đi 2 nước (`Down`, `Right`) sau 3 vòng lặp, còn DFS đi qua hàng trăm nước vì đào sâu theo một nhánh.

> Ở BFS, khi con của node đang xét là goal, thuật toán dừng ngay. App hiển thị thẻ goal đó ở cuối Frontier (nhãn `GOAL`) để dễ theo dõi, dù trong code gốc nó không được `enqueue`.

## Cấu trúc dự án

```
├── visualizer.py   # giao diện app (chạy file này): theme, widget, bàn chơi, bảng nhập, bảng Code, bố cục, vòng lặp chính
├── bfs.py          # notebook Buoi4 chép đủ mọi cell: Problem, Node, Queue, enqueue, dequeue, BFS(), ...  (chạy thử: python bfs.py)
├── dfs.py          # notebook Buoi5 chép đủ mọi cell: Problem, Node, Stack, push, pop, DFS(), ...        (chạy thử: python dfs.py)
├── ucs.py          # notebook Buoi6 chép đủ mọi cell: PriorityQueue (heapq), push, pop, UCS(), step_cost  (chạy thử: python ucs.py)
├── stepper.py      # BFS / DFS / UCS chạy từng bước (BFSStepper, DFSStepper, UCSStepper, SearchMachine) + highlight dòng code
├── scaling.py      # vẽ sắc nét ở độ phân giải thật của cửa sổ (HiDPI): Surface + hàm vẽ theo toạ độ logic, Viewport
├── problems.py     # khởi tạo bài toán cho app: trạng thái mặc định, tạo Problem, xáo trộn, kiểm tra giải được
├── ute_logo.png    # logo trường
└── screenshots/    # ảnh dùng trong README
```

## Thêm trò chơi hoặc thuật toán mới

Trong phần App của `visualizer.py` có hai danh sách `GAMES` và `ALGOS`; thêm một dòng vào đây là dropdown có thêm mục. Để mục mới chạy được còn cần:

- **Thuật toán mới**: chép notebook vào một file mới (như `bfs.py` / `dfs.py` / `ucs.py`), rồi trong `stepper.py` thêm một lớp con của `SearchAlgorithm` (xem `BFSStepper` / `DFSStepper` / `UCSStepper`), đăng ký trong `ALGORITHMS`, thêm code hiển thị (`code_lines`) và cách map từng bước sang dòng code (`step_trace`). Dòng code nào làm thay đổi Frontier/Empty thì khai báo trong `_TAG_OP` để Next/Prev theo dòng cập nhật đúng các bảng.
- **Trò chơi mới**: thêm `actions` / `result` / `step_cost` và hàm tạo `Problem` (`problems.py`), cách vẽ trạng thái và bảng nhập đầu vào (`visualizer.py`).

## Lưu ý

- DFS trên 8-Puzzle thường cho đường đi rất dài (có thể hàng nghìn nước). *Auto* chạy theo từng dòng code nên khá lâu với bài dài; dùng *Node tiếp* hoặc nút *Kết quả* để xem nhanh.
- BFS với đề rất khó (ví dụ lời giải 31 nước) cần khoảng 10 giây để chạy hết bằng *Kết quả*; app vẫn phản hồi và hiện số bước đang chạy trong lúc đó.
