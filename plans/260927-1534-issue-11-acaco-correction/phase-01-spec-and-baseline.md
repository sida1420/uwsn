# Pha 1 — Chốt đặc tả và baseline

**Ưu tiên:** P1 · **Ước lượng:** 2h · **Trạng thái:** Completed · **Phụ thuộc:** không

## Mục đích

Biến [bảng đối chiếu nguồn](./source-audit.md) thành contract có thể kiểm thử trước khi đổi code. Đọc [issue #11](https://github.com/sida1420/uwsn/issues/11), [paper chính thức](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf) Eq. (10)–(21), Algorithm 1/Table 2, slide 27–43/47/55, và các module hiện tại. Không suy công thức từ text PPTX bị thiếu equation object.

## Tệp liên quan

- Đọc: `src/algorithms/ac_aco/{parameters,adaptive,pheromone,optimizer,objective,cluster_tree,ac_aco}.py`, `src/algorithms/{clustering,routing}.py`, `src/{evaluate,simulate,hparameter,node,network}.py`, `tests/*`.
- Cập nhật trong khi thực thi: `plans/260927-1534-issue-11-acaco-correction/source-audit.md` nếu phát hiện sai dữ kiện. Không sửa code ở pha này.

## Các bước cụ thể

1. Kiểm `git status --short`; giữ nguyên PPTX untracked và thay đổi có sẵn. Chạy baseline compile/test với interpreter được cấu hình; ghi lỗi từng test, không gán lỗi sẵn cho bản sửa.
2. Xác nhận 3 contract riêng: `Simulator.T_max` là round mạng; `optimizer_iterations` là lần lặp ACO trong **một** round; `M` là ants/iteration. Giữ `T_max=3500` theo issue và repo, `M=10`; `optimizer_iterations=5` là budget triển khai cần ghi rõ, không mượn tên `T_max`.
3. Xác nhận hình dạng candidate: một đường chọn CH có thứ tự, số CH `min(live_count, max(1, round(.1*live_count)))`. ID vẫn là index gốc. Một node không thể chọn hai lần; dead node không tham gia. Cây đánh giá là `Node(-1)` root có thể có relay đa hop.
4. Chốt policy cho `E_m(i,j)` của Eq. (20): sử dụng chi phí acoustic của `Evaluator` cho một packet/hop, luôn dương; nếu `distance=0`, dùng epsilon dương cho phép tính heuristic, vẫn kiểm radius vật lý bằng giá trị thật. Không trộn `E_tx` với `E_m` tùy tiện; test xác suất bằng network 3 node có số học dễ kiểm.
5. Chốt `L_k` của Eq. (10) là **tổng độ dài các cạnh trên đường CH do kiến xây**, >0 bằng epsilon khi degenerate; không dùng `solution.cost` (đơn vị J) như chiều dài m. Ghi đây là cách cụ thể hóa paper cho CH search của repo. Nếu muốn dùng độ dài cả route, đổi spec trước khi code.
6. Chốt Eq. (15): `E_total(t)` là energy của **best feasible route trong iteration ACO trước**, không phải residual energy. `E_lb/E_ub` là min/max energy của mọi candidate hợp lệ đã thấy trong optimizer call hiện tại; iteration đầu/chưa có cost hoặc biên bằng nhau dùng `a_min`; clamp về `[a_min,a_max]`. Đây là adapter tối thiểu vì paper không định nghĩa iteration window chính xác.
7. Chốt phạm vi: thay AC-ACO và sửa lỗi shared router/test mà integration thật sự chạm; không tái tạo 2D radio benchmark, không viết thêm GA/PSO, không sửa figure/slide.

## Điều kiện qua pha

- [x] Contract trên được ghi trong source audit, không còn ký hiệu α/β/γ/`T_max` hai nghĩa trong task tiếp theo.
- [x] Có baseline test (tên fail, nguyên nhân, ảnh hưởng tới pha 4).
- [x] Mỗi giá trị issue có trạng thái: dùng, shared, paper-only, hoặc chưa đủ ngữ nghĩa.

## Rủi ro/câu hỏi

Paper gọi α vừa là số mũ pheromone vừa là cường độ chaos; tên code phải tách rõ. `L_best=1000`, `alpha=0`, `p=0` không có quy tắc sử dụng nhất quán; bỏ khỏi đường tính toán cho đến khi được giải thích, và báo ở cuối.
