# Đối chiếu nguồn cho issue #11

## Nguồn đã đọc

- [GitHub issue #11](https://github.com/sida1420/uwsn/issues/11), body tại 2026-09-27; không có comment.
- Zhou, Chen, Cao, *An Efficient Clustering Algorithm for Enhancing the Lifetime and Energy Efficiency of Wireless Sensor Networks*, CMC 84(3), 2025; [PDF chính thức](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf), §§3–5, Eq. (1)–(21), Algorithm 1, Table 2.
- `IT4906_WSN_final.pptx`: slide 16–24 (mô hình), 27–43 (thuật toán), 47 (tham số), 55 (thử nghiệm nội bộ). Text đọc trực tiếp từ OOXML; công thức trên một số slide là ảnh hoặc equation object nên **dùng PDF bài báo để chốt công thức**.
- Repo tại `main` 2026-09-27: `src/algorithms/ac_aco/*`, `src/algorithms/{clustering,routing}.py`, `src/evaluate.py`, `src/hparameter.py`, `tests/*`.

## Những chênh lệch quyết định thiết kế

| Chủ đề | Paper/issue | Code hiện tại | Quyết định cho issue #11 |
|---|---|---|---|
| Bài báo | Paper Eq. (11)–(21), Algorithm 1 | README nói “PPT-derived phase 1” | Paper làm chuẩn công thức; slide chỉ hỗ trợ đọc. |
| Mô hình vật lý | Paper WSN 2D radio, Eq. (2)–(7) | Repo UWSN 3D acoustic `Evaluator` | Giữ acoustic cho simulation chung; thêm profile radio riêng chỉ nếu yêu cầu nghiên cứu. |
| `T_max` | Issue 3500; paper Table 2 2500; slide 47 2500, slide 55 3500 | `HyperParameters.T_max=3500`, optimizer 5 iteration/round | Tách **số round simulator** và **iteration optimizer/round**. Giữ 3500 round theo issue/repo. 5 iteration là budget thực dụng từ bản thử, ghi rõ không phải Table 2. Không chạy 3500×3500 mù quáng. |
| Scenario paper | Paper Table 2 ghi **200** sensor, radius **20 m**; chính đoạn ngay sau ghi radius **50 m**. Slide 47 ghi **100** sensor, radius 20 m. | `map.pkl` là 100 sensor trong 500×500×500 m, radius 100 m | Không dùng Table 2/slide làm expected cho UWSN. Tái lập WSN là một scenario riêng, cần xác nhận các mâu thuẫn trước khi so số. |
| `M` | Issue `M=10` kèm comment “50”; paper không liệt kê M ở Table 2 | 10 kiến × 5 iteration = 50 candidate | `M=10` mỗi iteration; budget 50/round là lựa chọn thử nghiệm, không phải hằng số paper. |
| Xác suất | Paper Eq. (18),(20): `eta=E_j/dist(i,j)`; `tau^alpha * eta^beta * (1/E_m)^gamma` | `_transition_log_weight` thêm chuẩn hóa và `1/(1+E_tx)` | Bỏ hàm và công thức ad hoc; dùng đúng ba yếu tố. Tính log chỉ là thủ thuật ổn định số nếu cho cùng xác suất, nhưng issue yêu cầu bỏ hàm hiện tại. |
| Ký hiệu `alpha` | Eq. (12),(15) dùng α chaos; Eq. (20) lại dùng α pheromone | Một số mũ `pheromone_weight`, `chaos_min/max` | Tên code tách `pheromone_exponent` và `chaos_strength`; issue `pheromone_w=1`, `a_min=.05`, `a_max=.3`, `alpha=0` là mơ hồ, không đánh đồng. |
| β schedule | Paper Eq. (14) dùng `t-T/2`; slide 37 diễn giải sigmoid | Code dùng `t/T-.5` | Chọn công thức paper với `t,T` optimizer và xử lý overflow; test t=0, mid, T. Ghi rõ nếu dùng chuẩn hóa thì là biến thể. |
| Chaos strength | Paper Eq. (15) tăng theo **E_total tiêu thụ** trong `[E_lb,E_ub]` | Code tăng theo **residual energy giảm** | Dùng energy best candidate iteration trước và min/max của candidate cost đã thấy trong optimizer call; clamp. Đây là adaptation vì paper không xác định độ dài cửa sổ. |
| Pheromone | Paper Eq. (10): `Q/L_k` cho cạnh ant đi qua; Algorithm 1 nói best path | Code `0.5/(1+cost)` deposit mọi ant | `Q=100`; định nghĩa `L_k` là chiều dài đường chọn CH hoặc route thực, nhất quán và ghi rõ. Ưu tiên best feasible candidate trong iteration theo Algorithm 1; không dùng fixed `L_best=1000` như cost thật. |
| Clustering/routing | Issue: `cluster_tree.py`, `_assign_members`, `_repair_coverage`, `objective.py` trùng/sai; repo có `build_clusters`, `multi_hop_routing` | AC-ACO vẫn nối mọi CH trực tiếp sink, coverage repair thêm CH | Dùng helper chung và route đa hop; outlier do helper xử lý; không thêm CH sau ACO để sửa coverage. |
| Objective | Paper mô tả đa mục tiêu, không đưa trọng số cụ thể Eq. (42/43) như slide; paper Eq. (6) là E_DA | `phase1_cost` 4 trọng số 0.4/0.35/0.15/0.1 | Bỏ objective riêng; chọn **tổng `Evaluator.energy_consumption`** của candidate route hợp lệ, là tiêu chí đo được, công bố là UWSN adaptation. |
| Energy trong Algorithm 1 | Dòng 13 viết cập nhật residual energy của mỗi ant/path ứng viên | Repo `Simulator` trừ sau khi chọn root | Không tiêu năng lượng vật lý cho mọi lời giải thử; chỉ trừ cây thắng một lần/round. Đây là cách diễn giải để mô phỏng có nghĩa. |

## Bảng tham số issue: không đưa nhầm vào config AC-ACO

| Nhóm | Giá trị issue | Sử dụng/ghi chú |
|---|---|---|
| Tìm kiếm | `M=10`, `CHs_proportion=.1`, `t0=1`, `r=3.61`, `k=5`, `Q=100` | AC-ACO config; test từng default. `r` khác paper Table 2 `3.58`; issue ưu tiên. |
| Lịch thích ứng | `p_min=.1`, `p_max=.9`, `b_min=1`, `b_max=5`, `a_min=.05`, `a_max=.3` | AC-ACO config; `p`=evaporation, `b`=heuristic, `a`=chaos. |
| Xác suất | `pheromone_w=1`, `gamma=.1`, `beta=3`, `alpha=0`, `p=0` | Chỉ `pheromone_w`, `gamma` có vai trò rõ. `beta=3` là mức tham chiếu/Table 2, còn β(t) chạy 1–5. `alpha=0`, `p=0` trùng/đụng lịch; **không đưa vào công thức** nếu chưa xác nhận ngữ nghĩa. |
| Route | `hopping_factor=.4`, `hopping_factor_min=.67`, `hopping_factor_max=.9` | Shared router hiện dùng `.4`; min/max mâu thuẫn, không clamp tự tiện. |
| WSN radio/experiment | `bit_count=2000`, `ctrl_bit=100`, `E_elec=50e-9`, `E_agg=5e-9`, `free_space_coeff=10e-12`, `multipath_coeff=.0013e-12`, `distance_threshold=sqrt(eps_fs/eps_mp)` | Chỉ thuộc paper radio profile; `HyperParameters` chung hiện acoustic, `packet_size=200`. Không đổi trong AC-ACO fix. |
| Shared simulation | `T_max=3500` | Đã nằm ở `src/hparameter.py`; kiểm chứng, không duplicate. |
| Chưa định nghĩa | `L_best=1000` | Paper Eq. (10) dùng `L_k`, không có quy tắc dùng constant này; không sử dụng để deposit. |

## Baseline kiểm chứng 2026-09-27

`C:\Users\LOQ\miniconda3\python.exe -B -m unittest discover -s tests -v`: 15 test, 4 lỗi (1 fail, 3 error): `test_clustering` import `multi_hop_routing` từ `clustering` sai; hai test PSO gặp TypeError do chữ ký router đã đổi; một test AC-ACO energy kỳ vọng CH rỗng trả `E_tx+E_da` nhưng code hiện tính thêm một packet. Ghi baseline; khi sửa shared router/test phải xử lý tương ứng. PPTX là file untracked của người dùng; không stage/sửa.

Kiểm tra BFS trên đồ thị 3D với cạnh `distance<=radius=100` và cạnh base tương tự: **100/100 sensor có đường đa hop tới base**. Đây chỉ là điều kiện cần cho clustered routing, nhưng loại trừ kết luận “map tách rời” nếu AC-ACO dừng tại round 0. Nếu router greedy trả `None`, phải phân tích ràng buộc/hướng tiến hoặc thuật toán dựng cây.
