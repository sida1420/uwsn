# Pha 4 — Kiểm thử, tích hợp, tài liệu

**Ưu tiên:** P1 · **Ước lượng:** 2h · **Trạng thái:** Completed · **Phụ thuộc:** pha 3

## Mục đích

Chứng minh sửa đúng issue trên trường hợp nhỏ có thể tính tay, giữ được UWSN constraints, và phân biệt sự thật của repo với tuyên bố trong paper/PPTX.

## Tệp dự kiến

- Sửa `tests/test_ac_aco.py`: thay test bám implementation cũ bằng contract mới.
- Sửa `tests/test_clustering.py` khi thay shared router: import đúng từ `algorithms.routing` và test shape/chữ ký hiện tại.
- Sửa `tests/test_pso.py` hoặc `src/algorithms/pso/pso.py` nếu shared router API đang làm baseline fail; chọn sửa consumer cho API hiện hữu, không đổi API chỉ để chiều test cũ. Ghi đây là lỗi baseline cần xử lý do đang xác nhận regression shared router.
- Sửa `src/algorithms/ac_aco/README.md` (tài liệu package có sẵn), `src/algorithms/ac_aco/phase1_demo.py` nếu cần; không tạo README ngoài `docs/`/`plans/` trong tác vụ này.
- Chỉ sửa `src/run.py` nếu AC-ACO đã pass smoke route và người dùng muốn benchmark từ entry point; nếu thêm, seed và config được ghi rõ, không tạo CSV bằng thao tác test.

## Ma trận test có giá trị

| Test | Fixture/kỳ vọng |
|---|---|
| Params | Default issue khớp từng field hiệu lực; invalid NaN/inf/range/bool bị từ chối; số radio-only không lọt vào acoustic config. |
| Phương trình | So sánh giá trị Eq. (11),(13),(14),(18),(20) với phép tính độc lập trên mạng 2–3 node; Eq. (15) tăng theo **consumed** cost, không theo residual ratio. |
| Pheromone | Sau một iteration trên path xác định: cạnh best được `Q/L_k`, cạnh khác chỉ evap+chaos; Q=100; không deposit 2 lần. |
| Candidate | M=10, T=5 tạo tối đa 50 lời giải/round; CH count = 10% làm tròn; seed lặp đúng CH/cost; dead node không xuất hiện. |
| Multi-hop | Fixture tuyến tính `base—A—B—C` với mỗi cạnh <=radius, B/C ở ngoài base radius: `plan_round()` cho complete tree. Fixture disconnected trả `None`; cạnh >radius bị từ chối. |
| Cây & energy | DFS không cycle, mỗi live ID đúng một lần, parent-child nhất quán, root tới mọi node; `Evaluator` tính route candidate và simulator trừ mỗi node một lần. |
| Baseline ngoài AC-ACO | `test_clustering` import sai, PSO truyền sai chữ ký router, test CH rỗng kỳ vọng energy cũ: sửa/báo rõ; không điều chỉnh assertion chỉ để xanh. |

## Chạy kiểm chứng

1. `C:\Users\LOQ\miniconda3\python.exe -B -m unittest tests.test_ac_aco -v` nếu package layout cho phép; nếu không dùng `unittest discover -s tests -p test_ac_aco.py -v`.
2. `C:\Users\LOQ\miniconda3\python.exe -B -m unittest discover -s tests -v` và `C:\Users\LOQ\miniconda3\python.exe -B -m compileall -q src`.
3. Smoke trên fixture connected với tối đa 2–3 round để kiểm integration; trên `map.pkl` mặc định chạy `plan_round` đúng một lần. Đồ thị raw có 100/100 node reachable từ base bằng đa hop; nếu trả `None`, kiểm tra router greedy, cluster assignment và search budget, rồi sửa lỗi trong phạm vi. Chỉ chấp nhận `None` sau khi có bằng chứng ràng buộc clustered routing làm instance bất khả thi. Không dùng `python src/run.py` mặc định làm chứng chỉ AC-ACO vì `ALGORITHMS` chưa đăng ký nó.
4. `git diff --check`, `git status --short`, review file changed; bảo đảm PPTX untracked không bị sửa/stage. Đối chiếu report với issue từng bullet, không nhận đã xử lý `L_best` hoặc radio profile khi chưa làm.

## Nội dung README phải cập nhật

Nguồn paper DOI, slide chỉ là diễn giải; bảng tham số gồm đơn vị/vai trò; `T_max` round vs optimizer iterations, 10 ants × 5 iterations; Eq. (20) và Eq. (15) với quyết định adapter; routing đa hop chung, objective bằng round energy acoustic, trạng thái map hiện tại; giới hạn không tái hiện Fig. 3–6 paper. Xóa mô tả coverage repair, direct-only, objective 4 trọng số, `r=3.58`, chaos residual ratio, `Q=.5` cũ. Đảm bảo UTF-8.

## Điều kiện kết thúc

- [x] Test AC-ACO và shared integration pass, hoặc lỗi baseline còn lại được liệt kê chính xác với nguyên nhân và phạm vi.
- [x] Có test chứng minh route hợp lệ **khi CH không chạm base trực tiếp**; không cho phép bypass radius.
- [x] Năng lượng chấm candidate bằng cùng Evaluator mà simulator dùng; không tiêu hao năng lượng trong search.
- [x] README không tuyên bố tái lập kết quả WSN paper trên UWSN 3D.
- [x] Review cuối xác nhận không có logic trùng `cluster_tree`/`objective`/`_assign_members`/`_repair_coverage`.

## Kết quả thực thi

`C:\Users\LOQ\miniconda3\python.exe -B -m compileall -q src` và
`C:\Users\LOQ\miniconda3\python.exe -B -m unittest discover -s tests -v`
đã pass (13 test). Smoke trực tiếp `plan_round()` trên `map.pkl` tạo cây đủ
100 node, mỗi cạnh trong `radius`. Smoke qua `Simulator` chưa chạy được vì
interpreter này thiếu dependency `pandas`; đây là thiếu dependency môi trường,
không phải lỗi AC-ACO.

## Câu hỏi còn mở

Nếu mục tiêu cuối là so khớp số liệu Table 3–5 của paper, cần một nghiên cứu riêng để tái tạo 2D radio deployment, seed, MAC, traffic, aggregation và baseline algorithms. Chỉ làm khi scope được xác nhận.
