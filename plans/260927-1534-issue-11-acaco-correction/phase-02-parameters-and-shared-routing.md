# Pha 2 — Tham số và shared routing

**Ưu tiên:** P1 · **Ước lượng:** 2.5h · **Trạng thái:** Completed · **Phụ thuộc:** pha 1

## Mục đích

Loại phần trùng/sai của AC-ACO; dùng interface clustering/routing hiện có mà không tạo cây hoặc assignment thứ hai. Giữ mọi thay đổi shared nhỏ và có test cụ thể.

## Tệp dự kiến

| Thao tác | Tệp | Nội dung |
|---|---|---|
| Sửa | `src/algorithms/ac_aco/parameters.py` | Config AC-ACO có tên rõ, default theo issue, validate kiểu/range/finite. |
| Sửa | `src/algorithms/ac_aco/ac_aco.py` | `plan_round` dùng candidate root do optimizer trả, bỏ lọc CH chỉ gần base. |
| Xóa sau khi thay import | `src/algorithms/ac_aco/cluster_tree.py`, `src/algorithms/ac_aco/objective.py` | Không còn logic song song với helper chung và `Evaluator`. |
| Chỉ sửa khi test chứng minh cần | `src/algorithms/clustering.py`, `src/algorithms/routing.py` | Bảo đảm shared helper trả cây hợp lệ và tránh chu trình/mất node trên topology đặc biệt. |
| Giữ nguyên mặc định | `src/hparameter.py`, `src/evaluate.py`, `map.pkl` | Không đổi vật lý acoustic chỉ vì paper radio. |

## Các bước cụ thể

1. Giữ public constructor `ACACOClustering(network, hparameters, ac_aco_params=None)` và `select_cluster_heads()` nếu demo/test dùng. Lập danh sách tất cả caller trước khi đổi tên field; cập nhật đồng bộ `phase1_demo.py` và test ở pha 4.
2. Config hiệu lực: `num_ants=10`, `num_iterations=5`, `ch_proportion=.1`, `pheromone_exponent=1`, `energy_cost_exponent=.1`, `beta_min=1`, `beta_max=5`, `beta_slope=5`, `rho_min=.1`, `rho_max=.9`, `chaos_min=.05`, `chaos_max=.3`, `chaos_r=3.61`, `Q=100`, `tau0=1`, `hopping_factor=.4`, `random_seed=42`. Giữ `chaos_seed=.37`, `tau_min=.1`, `tau_max=10` như guard/reproducibility hiện có và ghi chúng là lựa chọn triển khai, không phải paper. Bỏ trọng số objective 4 thành phần, `ensure_member_coverage`, `enforce_sink_radius`, `deposit_strength` vì không còn ngữ nghĩa.
3. Validate: integer >0 cho ants/iterations; proportion `(0,1]`; `0<rho_min<=rho_max<1`; `0<=chaos_min<=chaos_max`; `3.57<r<4`; `tau0,Q>0`; beta/exponent finite không âm; seed là `int|None` (không chấp nhận bool). Không áp dụng `hopping_factor_min/max` để ép `.4` vào biên mâu thuẫn.
4. Định nghĩa một đường dựng route dùng chung cho **mọi** candidate: `build_clusters(CHs, live_nodes, dist_matrix, radius)` → `(CH_nodes, nodes, outliers)` → `multi_hop_routing(CH_nodes, nodes, live_nodes, outliers, dist_matrix, base_dists, residual_e, radius, hopping_factor)`. Nếu router trả `None`, loại candidate. `outliers` đi relay như shared helper cho phép; không nâng chúng thành CH.
5. Kiểm kết quả router trước khi score: base id `-1`; tất cả và chỉ live ID xuất hiện đúng một lần; mỗi node có đúng một `prev` nhất quán với `nxts`; không cycle; mọi sensor→sensor và sensor→base edge nằm trong radius; mọi node đến base. Sửa router chung nếu chính nó phá invariant (test tái hiện); không “repair” riêng trong AC-ACO.
6. `plan_round()` trả root của candidate tốt nhất đã được đánh giá; `last_solution` lưu CH, route, energy, path length/metadata đủ debug. Khi không có candidate hợp lệ, trả `None` và `last_solution=None`. Không trả root trực tiếp do `cluster_tree.py` tạo.

## Điều kiện qua pha

- [x] Không import `cluster_tree`/`objective` từ package AC-ACO; không có `_assign_members`/`_repair_coverage` trong optimizer.
- [x] Candidate CH ở ngoài radius base vẫn có thể đạt base qua relay nếu graph cho phép.
- [x] Cây route và `last_solution` thống nhất; không có node ảo, node chết, cạnh quá bán kính.
- [x] Interface shared được dùng theo đúng chữ ký hiện tại; các consumer khác không bị hỏng do sửa shared.

## Rủi ro

`multi_hop_routing()` hiện chọn relay dựa vào `prev`/khoảng cách base; test trường hợp CH→member→CH, khoảng cách base bằng nhau, route không liên thông. Nếu phát hiện lỗi shared, sửa tối thiểu và bổ sung regression test, không thêm routing policy mới trong AC-ACO.
