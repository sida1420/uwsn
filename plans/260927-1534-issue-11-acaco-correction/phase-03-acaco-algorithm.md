# Pha 3 — Sửa lõi AC-ACO

**Ưu tiên:** P1 · **Ước lượng:** 3.5h · **Trạng thái:** Completed · **Phụ thuộc:** pha 2

## Mục đích

Triển khai các thành phần paper có đủ đặc tả: logistic Eq. (11), pheromone Eq. (10),(12)/(21), ρ Eq. (13), β Eq. (14), chaos strength Eq. (15), heuristic Eq. (18), xác suất Eq. (20). Các lựa chọn còn thiếu được gắn nhãn UWSN adaptation, không tự nhận faithful reproduction.

## Tệp dự kiến

Sửa `src/algorithms/ac_aco/{adaptive,pheromone,optimizer,ac_aco,phase1_demo}.py`. Không tạo optimizer/objective/route thứ hai. Nếu file >200 dòng, chỉ tách hàm toán học thuần vào `adaptive.py`/`pheromone.py` đã có; giữ API nội bộ gọn.

## Công thức và flow bắt buộc

1. Cho mỗi `plan_round`, chỉ đọc `live_nodes`, `residual_e`; RNG cục bộ seed. `k=max(1, round(ch_proportion*live_count))` rồi chặn bởi live count. Mỗi ant chọn `k` CH không lặp. Nút đầu chọn đều trên tập live (paper chưa nêu quy tắc khởi đầu); các lựa chọn sau áp dụng Eq. (20) trên CH chưa chọn. `tau[i][j]` chỉ cho cạnh CH→CH; không dùng start pheromone vector như một ma trận giấy không định nghĩa.
2. Với `i→j`: `eta=E_j/max(dist(i,j),eps)` theo Eq. (18); `E_m(i,j)>0` lấy từ `Evaluator` acoustic theo contract pha 1. Trọng số chưa chuẩn hóa `tau[i][j]^pheromone_exponent * eta^beta(t) * (1/E_m(i,j))^gamma`. Chuẩn hóa trên đúng tập allowed. Có thể tính trong log-space để tránh overflow **nếu** tương đương về xác suất; không giữ `_transition_log_weight` hoặc biến thể `1/(1+E_tx)`. Khi tất cả trọng số mất hiệu lực, chọn đều chỉ như fallback được test.
3. ρ(t) theo Eq. (13), β(t) theo Eq. (14) với `t=1..num_iterations`, `T=num_iterations`; test giá trị tính độc lập và tính đơn điệu/biên. Không thay `(t-T/2)` bằng `(t/T-.5)` mà vẫn gắn nhãn Eq. (14). Dùng logistic sigmoid ổn định với số mũ lớn.
4. Logistic `x_next=r*x*(1-x)`, seed `(0,1)`, r issue `3.61`. Chaos additive Eq. (20) `P' = P + chaos_strength*Chaos(x_i)` dùng cùng giá trị nguồn `i` cho các candidate tại bước đó, rồi **chuẩn hóa lại** để tổng P'=1 và không âm. Cộng cùng hằng rồi chuẩn hóa làm phân phối phẳng hơn, nên vẫn tăng exploration. Paper không định nghĩa seed/ánh xạ `x_i` cho mỗi node; dùng chuỗi deterministic theo node, ghi rõ trong README và test cùng seed.
5. `alpha_chaos` Eq. (15) cần năng lượng tiêu thụ đo ở iteration trước. Iteration 1 dùng `a_min`; từ iteration 2, `E_total(t)` = cost của best feasible candidate ở iteration trước, `E_lb/E_ub` = min/max của **mọi** candidate hợp lệ đã thấy trong optimizer call hiện tại. Clamp về `[a_min,a_max]`; nếu chưa có cost hoặc max=min thì dùng `a_min`. Không trừ residual energy trong loop kiến. Không gọi fallback này là điều paper định nghĩa đầy đủ.
6. Mỗi ant → `build_clusters` → `multi_hop_routing` → kiểm cây → `Evaluator.energy_consumption`. Candidate bất khả thi bị loại; **best feasible** theo tổng năng lượng trong round, tie-break ổn định theo CH tuple; giữ best toàn bộ optimizer iterations. `last_solution` chứa raw CH path, route và cost đúng evaluator. Không sử dụng `phase1_cost` 4 trọng số hoặc extra-CH penalty.
7. Cập nhật pheromone **một lần mỗi optimizer iteration**, không thêm chaos hai lần do Eq. (12) và Eq. (21) là cùng dạng. Evaporate mọi cạnh live, cộng chaos có biên, cộng `Q/L_k` trên các cạnh của best feasible ant trong iteration (Algorithm 1); `L_k` theo contract pha 1. Không deposit cạnh của outlier, relay hay CH do helper tạo vì kiến không chọn chúng. Nếu không có candidate khả thi, vẫn tiến chaos/evap theo policy nhất quán đã test, và trả `None` sau hết budget. Không dùng `Q/(1+cost)` hoặc `L_best=1000` cố định.
8. Không dùng vòng lặp ACO để cập nhật `residual_e`; chỉ `Simulator.run()` trừ chi phí cây được chọn **một lần**. `optimizer.optimize()` không được làm thay đổi input lists/network. Pheromone chỉ là state của algorithm instance.

### Pseudocode định hướng

```text
best_global = None
for t in 1..num_iterations:
    rho, beta = schedules(t, T)
    alpha_chaos = strength(previous_iteration_best_cost, all_costs_seen)
    candidates = []
    repeat num_ants times:
        ordered_CHs = sample_without_replacement(live, k, tau, eta, Em, beta, alpha_chaos)
        root = shared_build_and_route(ordered_CHs)
        if valid_complete_tree(root):
            cost = Evaluator.energy_consumption(root).total
            candidates.append((ordered_CHs, root, cost))
    best_iteration = min(candidates, by=(cost, ordered_CHs)) if candidates else None
    best_global = min_non_null(best_global, best_iteration)
    update_tau_once(rho, logistic, Q / path_length(best_iteration), best_iteration)
    all_costs_seen.extend(candidate.cost for candidate in candidates)
    previous_iteration_best_cost = best_iteration.cost if best_iteration else None
return best_global
```

## Test buộc có ở pha 4

- [x] Tính tay xác suất 2 candidate, rồi kiểm chaos/normalization; không có candidate chết hoặc đã chọn.
- [x] `num_ants * num_iterations` là budget tối đa, số CH đúng target, deterministic seed.
- [x] ρ/β/chaos bounds, Eq. (11),(13)–(15), zero-denominator và extreme `exp`.
- [x] Chỉ best feasible path được deposit `Q/L_k`; no double update; k=1 không chia 0.
- [x] Candidate evaluation không mutate residual/network; simulator trừ năng lượng đúng một lần.

## Rủi ro

Paper Eq. (20) cộng chaos vào `P(i,j)` nhưng không định nghĩa cách chuẩn hóa/chaos theo cạnh; lựa chọn deterministic là một adapter. Paper prose đề cập thay đổi `r` theo thời gian mà không đưa công thức; giữ r cố định 3.61 theo issue, không chế schedule. Khi không có route cho map mặc định, báo topology thay vì bỏ radius.
