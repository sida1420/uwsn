# NodeACACO

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
