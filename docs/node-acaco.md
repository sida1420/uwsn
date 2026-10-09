# NodeACACO

## Multi-objective fitness (PR #28)

`NodeACACOParameters` accepts `w_energy`, `w_load`, `energy_reference` and
`fitness_eps`. Weights are finite, nonnegative and sum to one. Defaults remain
energy-only (`1.0, 0.0`): the controlled experiments found that load weighting
extends service while requiring more energy for the same delivered workload.
Gamma stays 0.05; rho stays 0.9 to 0.1. Weight/rho trials and results are in
`plans/261008-1051-node-acaco-fitness`.

For each complete, affordable candidate, the unchanged shared `Evaluator`
computes `delta[i]` in joules, including TX, RX, aggregation and relay forwarding.

```
total_energy = sum(delta.values())
r[i] = delta[i] / residual_energy[i]
load = (N * sum(r[i]**2) / sum(r[i])**2 - 1) / (N - 1)
fitness = w_energy * total_energy / energy_reference + w_load * load
```

`energy_reference` is a configured positive reference in joules, fixed across
all ants and all rounds. Its default is **1 J**, preserving the original
energy-only score and deposit scale with Q=0.03 and pheromone bounds [1, 8].
It is a unit reference, not candidate-dependent min/max normalization or a
guarantee that the two objective terms have equal ranges. Changing it changes
the effective trade-off and the deposit magnitude, so weights should be tuned
again after changing the reference. A fixed denominator preserves energy-only
rankings. Very small references weaken deposits; very large ones may saturate
pheromone. Inspect the measured bound occupancy before tuning either.

All alive sensors enter the load calculation: each produces its own reading,
and CHs and relays also spend energy for other sensors. Relative depletion
accounts for unequal residual energy. Restricting load to CHs would hide
member/relay hotspots; omitting sensors would reward reduced delivery.
Missing, duplicate, disconnected, out-of-range or unaffordable candidates are
rejected before ranking/deposit. An ordinary interior node without the relay
flag is rejected because it would not forward descendant packets. A CH may
also have the relay flag: shared-model aggregation takes precedence.

Singleton and zero total depletion have load zero. Invalid/nonfinite energies
or nonpositive residual energy are rejected. Log-scaled ratios avoid squared
ratio overflow/underflow; final load is clamped to [0, 1] for floating-point
roundoff. A zero-total-energy tree is rejected because Simulator requires
positive physical round energy. Exact affordable depletion is permitted.

Both ant selection and winner selection minimize fitness with the original
ordered-CH tie-break. Deposits use that same score:

```
ant_deposit = Q / (num_ants * max(fitness, fitness_eps))
winner_deposit = theta * Q / max(fitness, fitness_eps)
```

The original update order remains ant deposits, evaporation plus chaos and
bounds, then winner deposit and bounds. Chaos's cost window remains **joules**;
adaptive beta/rho and the node-based chaotic mechanisms are unchanged.
Returned consumption and Simulator CSV `round_energy` remain joules; candidate
evaluation never debits the network. With pure load weighting, zero load can
produce epsilon-limited deposits and saturation, so bound monitoring matters.

```python
params = NodeACACOParameters(w_energy=0.4, w_load=0.6)
algorithm = NodeACACO(network, hparameters, params, seed=42)
```

Strict affordability can stop service while sensors still have positive
energy. FND is then censored, and routing/service lifetime is the completed
round count, not full network lifetime. Baseline comparisons must disclose
that the previous implementation allowed final-round energy overdraw.

## Measured trade-off and tuning recommendation

The [complete study](../plans/261008-1051-node-acaco-fitness/results-report.md)
contains five pilot seeds for every requested weight/rho setting and 30 held-out
paired seeds for five main arms. At the common 1484-round horizon, every case
delivered 148400 readings with no overdraw. Against the affordable energy-only
control, weights **0.4/0.6** increased energy by **1.069 J** (paired 95% CI
[1.058, 1.080]), about **4.53%**, while extending affordable service by
**731.9 rounds** (CI [725.1, 738.6]), about **48.3%**. Mean relative-depletion
load fell about **53%**. This is an energy/service trade-off, not joint energy
saving and lifetime improvement. Use this setting when longer affordable
service justifies the extra joules. Equal weights were not assumed optimal;
the other requested weights have separate pilot results.

Reducing `rho_max` from 0.9 to 0.4 did not establish an improvement on held-out
seeds: energy difference -0.00519 J (CI [-0.01211, 0.00173]), service difference
-0.53 rounds (CI [-5.92, 4.85]). Combining rho=0.4 with load fitness also did
not establish an energy/service benefit over fitness alone. Retain rho=0.9
as the default and rho_min=0.1. No upper-bound/deposit saturation occurred in
the measured diagnostics, although the lower bound was frequently occupied.

Keep gamma=0.05 for this ablation. Native NodeACO has alpha=1, **fixed** beta=0.6
and gamma=0.05; its measured median weighted log ranges were 1.933 for
pheromone, 0.480 for residual energy and 0.199 for hop energy. NodeACACO's
adaptive beta from 1 to 5 makes residual contrast dominate late in service;
its large chaos mixture further flattens probabilities. A separate controlled
gamma trial should test **0.025, 0.05, 0.1, 0.2** with other parameters fixed.
These are measured follow-up candidates, not validated optima.

All improved main runs stopped service with 100 sensors alive; FND was censored
and full network lifetime was unobserved. Legacy baseline service includes
unaffordable rounds, so the additional affordable control is required for
physical lifetime attribution. The shared energy model and other algorithms
remain unchanged. All 36 repository tests and seven study-harness tests pass.

The implementation has its own ant orchestration so ACACO stays unchanged.
The historical energy-only implementation notes below describe the baseline;
fitness now replaces cost only for ranking and deposits.

NodeACACO chuyển các cải tiến NodeACO sang adaptive chaotic ACO, dùng chung
vòng lặp ant, đánh giá năng lượng và routing đa chặng của `ACACO`.
`src/run.py` chạy `[NodeACO, PSO, ACACO, NodeACACO]`, với cùng seed mỗi lần so sánh.

## Ánh xạ

| Thành phần | NodeACACO |
| --- | --- |
| Pheromone | Một giá trị `tau[j]` mỗi sensor; lưu O(N) thay vì N×N |
| Heuristic | `tau[j]^alpha * residual[j]^beta(t) / E_m(i,j)^gamma` |
| Alpha / gamma | 1 / 0,05 như NodeACO |
| Nạp theo ant | `Q / (num_ants * cost)` cho mọi CH, gồm cả CH duy nhất |
| Nạp winner | `theta * Q / cost`, theta=0,1 |
| Q / tau0 / bounds | 0,03 / 1 / [1, 8] như NodeACO |
| Cập nhật trong round | Ant sau thấy node deposit của ant trước như NodeACO |
| Rho | Giữ ACACO: 0,90→0,10 trên T_max |
| Beta | So sánh lịch 1→5 và 0,6→3; slope=5 |
| Chaos | Giữ ACACO: logistic r=3,61, seed=0,37, strength 0,05–0,30 |
| CH / ants / retries | 20% node sống / 40 / 10 |
| Chọn route | Tổng năng lượng thấp nhất trong round |

Khoảng cách chỉ tham gia qua `E_m`, không nhân thêm inverse-distance trong
heuristic. Chi phí static được cache một lần. Ma trận khoảng cách/chi phí vẫn
chiếm O(N²); chỉ bộ nhớ pheromone và bước evaporation chuyển sang O(N).
NodeACACO kế thừa ACACO, nên CH đầu tiên vẫn được lấy có hoàn lại giữa các ant,
khác NodeACO chọn các start khác nhau.

Mỗi round: nạp từ mọi ant khả thi → evaporation + chaos → clamp → nạp winner
với theta → clamp. Node pheromone luôn trong bounds. Chaos disturbance trong
probability vẫn dùng `strength*chaos[source]` và chuẩn hóa như ACACO; disturbance
trong cập nhật pheromone node dùng `strength*chaos[node]`, advance mỗi node sống
một lần. Cost window, lịch thích nghi và xử lý round thất bại giữ như ACACO.

ACACO gốc và NodeACO gốc được giữ nguyên. NodeACACO thay nhiều yếu tố cùng lúc;
không xem đây là ablation chỉ riêng vị trí lưu pheromone hay tái hiện paper.

## Sử dụng

```python
from algorithms.node_ac_aco import NodeACACO
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters

algorithm = NodeACACO(network, hparameters, NodeACACOParameters(), seed=42)
root, consumption = algorithm.plan_round(live_sensors, residual_e)
```

Tạo instance mới mỗi run. Params là frozen dataclass, có thể truyền
`NodeACACOParameters(beta_min=0.6, beta_max=3.0)` hoặc
`NodeACACOParameters(beta_min=1.0, beta_max=5.0)` để chọn dải cụ thể.

## Kiểm chứng và lưu tiến trình

22 test hiện có kiểm tra ACACO, PSO và NodeACACO. Test NodeACACO xác nhận
heuristic, deposit, hard bounds, chaos/lịch, route bao phủ đúng live IDs,
parent links/radius, seed repeatability, static cost cache, round không có route
và constructor từ chối tham số không hợp lệ.

Phép so sánh beta: [kế hoạch](../plans/261007-2010-node-acaco/plan.md),
script `plans/261007-2010-node-acaco/compare-beta.py`, dữ liệu
`plans/reports/node-acaco-beta-261007-2010`. Chạy 5 seed ghép cặp trên cùng map,
T_max=3000. Đo năng lượng tại 1000/2000 rounds, số round phục vụ và FND.
Chọn dải có mean energy tại 2000 thấp nhất khi mọi run đều đạt horizon;
nếu cả hai không đạt điều kiện, chọn mean service rounds rồi energy tại 1000.
95% CI dùng đơn vị seed. Năm seed trên một map chỉ là thử nghiệm thăm dò.
Kết quả 10 run: chọn mặc định `1→5` theo tiêu chí công bố trước, vì mean energy
tại round 2000 là 31,9188962107 J, thấp hơn 31,9374438134 J của `0,6→3`
(tiết kiệm 0,05807%). Chênh lệch ghép cặp (`0,6→3` trừ `1→5`) là
+0,0185476027 J, 95% CI [-0,0194414612, +0,0565366667], nên chưa cho thấy ưu thế
năng lượng bền vững. Service means là 2141,4 và 2143,8 rounds (CI chênh lệch
[-7,63369, 12,43369]); FND của `0,6→3` muộn hơn 9 rounds (95% CI
[4,7893, 13,2107]). Tất cả 10 run dừng do `no_route`, không phải `all_dead`.
Xem [báo cáo so sánh](../plans/reports/comparison-261007-2010-node-acaco-beta.md).

Checkpoint trước sửa: `plans/reports/checkpoint-261007-2010-before-node-acaco`,
gồm src, tests, runs, map, tài liệu và các kế hoạch/báo cáo cũ; `manifest.json`
ghi HEAD, Git status và SHA-256; `working-tree.diff` lưu thay đổi chưa commit.
Đối chứng rho cũ vẫn dang dở; chưa tuyên bố hoàn tất pilot hay main. Nếu tiếp tục
harness cũ có guard source hashes, dùng cây snapshot đầy đủ để giữ nguyên
source của đối chứng, vì `src/run.py` hiện đã thêm NodeACACO.
