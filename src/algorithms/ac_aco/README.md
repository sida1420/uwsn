# AC-ACO Phase 1 — phân cụm

Package này triển khai Phase 1 của **Adaptive Chaotic Ant Colony Optimization**
theo `IT4906_WSN_final.pptx`: chọn Cluster Head (CH) và gán sensor vào CH.

Thư mục dùng `ac_aco` thay vì `ac-aco` vì dấu `-` không hợp lệ trong Python
package import. Tên thuật toán hiển thị vẫn là `AC-ACO`.

## Phạm vi khoa học

Đã triển khai:

- Ma trận pheromone cạnh `tau[i][j]` cho đường xây dựng tập CH có thứ tự.
- `M=10` kiến, mỗi kiến tạo một tập CH ứng viên.
- 5 iteration nội bộ mặc định, tổng cộng 50 candidate/round như kịch bản tại
  slide 55.
- Logistic chaos, adaptive `rho`, adaptive `beta`, chaos theo năng lượng mạng.
- Objective `min f = w1*E + w2*D + w3*L` từ slide 42.
- Coverage repair giữ mọi cạnh sensor→CH trong `radius` của repo.
- Seed riêng để kết quả tái lập và không ảnh hưởng global random state.
- Interface `ClusteringAlgorithm` và adapter cây `Node` của repo.

Chưa triển khai:

- Phase 2 multi-hop CH/relay→sink.
- Mô hình radio 2D free-space/multipath ở slide 22–24. Package tái sử dụng mô
  hình acoustic 3D trong `src/evaluate.py`.

## Cấu trúc

```text
ac_aco/
├── __init__.py
├── ac_aco.py          adapter ClusteringAlgorithm
├── adaptive.py        logistic map và adaptive schedules
├── cluster_tree.py    cây tương thích sink -> CH -> member
├── objective.py       objective phase 1 đã chuẩn hóa
├── optimizer.py       edge-pheromone AC-ACO
├── parameters.py      config có validation
├── pheromone.py       evaporation, chaos và all-ant deposit
├── phase1_demo.py     chạy chọn CH độc lập với routing phase 2
└── README.md
```

## Thuật toán

Mỗi lần chọn cụm:

1. Tính số CH mục tiêu:

   ```text
   k = max(1, round(ch_proportion * số node sống))
   ```

2. Trong mỗi iteration, 10 kiến xây đường gồm `k` CH khác nhau.
3. Xác suất chuyển từ CH `i` sang ứng viên `j`:

   ```text
   P(i,j) ∝ tau(i,j)^pheromone_weight
            * eta(i,j)^beta
            * (1 / (1 + E_tx(i,j)))^energy_cost_weight

   eta(i,j) = residual_energy(j) / distance(i,j)
   ```

4. Coverage repair bổ sung CH nếu topology 3D thưa khiến `k` CH không phủ đủ
   node trong bán kính liên lạc.
5. Gán mỗi node vào CH gần nhất và tính objective.
6. Bay hơi toàn bộ pheromone cạnh, thêm nhiễu logistic và deposit pheromone từ
   đường CH do từng kiến chọn. CH do coverage repair thêm không được reinforce
   như quyết định của kiến.
7. Trả tập CH tốt nhất toàn cục sau các iteration nội bộ.

Adaptive equations:

```text
x[n+1] = r*x[n]*(1-x[n])
rho(t)  = rho_max - (t/T)*(rho_max-rho_min)
beta(t) = beta_min + (beta_max-beta_min)/(1+exp(-slope*(t/T-0.5)))
tau     = (1-rho)*tau + deposit + chaos_weight*Chaos(x)
```

Slide 38 mâu thuẫn: công thức làm chaos tăng cùng năng lượng, nhưng mô tả nói
năng lượng giảm thì cần tăng exploration. Code chọn semantics của phần mô tả:

```text
chaos_weight = chaos_min + (chaos_max-chaos_min)*(1-energy_ratio)
energy_ratio = tổng residual energy / tổng initial energy của toàn mạng
```

Objective dùng lựa chọn rõ ràng từ slide 42 vì fitness slide 43 không nói rõ
maximize/minimize và có dấu mâu thuẫn:

```text
cost = energy_weight*E + distance_weight*D
       + load_balance_weight*L + extra_head_weight*CH_extra
```

- `E`: kết hợp chi phí truyền một round và chất lượng năng lượng trung
  bình/tối thiểu của CH.
- `D`: kết hợp khoảng cách member→CH và CH→sink đã chuẩn hóa.
- `L`: hệ số biến thiên tải cụm.
- `CH_extra`: phạt số CH coverage repair bổ sung quá `k`.

## Chạy Phase 1 trên map hiện tại

Không cần `pandas`:

```powershell
$env:PYTHONPATH='src'
python -B -m algorithms.ac_aco.phase1_demo
```

Thay search budget/seed:

```powershell
python -B -m algorithms.ac_aco.phase1_demo --ants 10 --iterations 5 --seed 2026
```

Demo in target CH, số CH sau repair, objective, max member→CH distance và IDs.
Output tách riêng `ACO-selected CHs` và `repair-added CHs` để không gán phần
greedy repair cho metaheuristic.

## Dùng từ Python

```python
from algorithms.ac_aco import ACACOClustering, ACACOParameters
from hparameter import HyperParameters
from network import NetworkInstance

network = NetworkInstance.from_pickle("map.pkl")
shared = HyperParameters()
config = ACACOParameters(
    num_ants=10,
    num_iterations=5,
    ch_proportion=0.10,
    random_seed=2026,
)
algorithm = ACACOClustering(network, shared, config)

live_nodes = list(range(network.N))
residual_e = [network.init_energy] * network.N
cluster_heads = algorithm.select_cluster_heads(live_nodes, residual_e)

print(cluster_heads)
print(algorithm.last_solution.assignments)  # sensor_id -> CH_id
print(algorithm.last_solution.cost)
```

## Kết nối Simulator hiện tại

`ACACOClustering` đã implement đúng constructor và `plan_round()` của
`ClusteringAlgorithm`. Tuy nhiên `Simulator` hiện chỉ hiểu cây hai tầng
`sink -> CH -> member`, trong khi PPT yêu cầu multi-hop.

Default `enforce_sink_radius=True`. Do map hiện tại chỉ có một sensor trong
100 m của sink, `plan_round()` trả `None` thay vì báo cáo một route vật lý sai.
Phase 1 vẫn chạy đầy đủ qua `select_cluster_heads()` hoặc demo ở trên.
Khi direct route khả thi, adapter lọc candidate CH theo sink trước khi tối ưu,
tránh bỏ một nghiệm hợp lệ chỉ vì global-best không nối được sink.

Chỉ khi bạn chủ động chấp nhận adapter direct-to-sink để đánh giá tạm thời:

```python
from simulate import Simulator

config = ACACOParameters(enforce_sink_radius=False)
algorithm = ACACOClustering(network, shared, config)
history = Simulator(network, shared).run(algorithm)
```

Sau đó có thể thêm class vào `ALGORITHMS` trong `src/run.py`. Không đăng ký mặc
định vì kết quả đó chưa phải routing multi-hop hợp lệ. Phase 2 nên thay
`cluster_tree.py` bằng cây relay và kiểm tra `distance <= radius` cho mọi hop.

## Config

### Search và xác suất

| Tham số | Default | Ý nghĩa |
|---|---:|---|
| `num_ants` | `10` | Số lời giải ứng viên mỗi iteration |
| `num_iterations` | `5` | Số iteration tối ưu nội bộ |
| `ch_proportion` | `0.10` | Tỷ lệ CH mục tiêu trước repair |
| `pheromone_weight` | `1.0` | Số mũ pheromone |
| `beta_min`, `beta_max` | `1.0`, `5.0` | Biên heuristic sigmoid |
| `beta_slope` | `5.0` | Độ dốc sigmoid |
| `energy_cost_weight` | `0.10` | Số mũ nghịch đảo chi phí truyền |
| `random_seed` | `42` | Seed; `None` để ngẫu nhiên |

### Pheromone và chaos

| Tham số | Default |
|---|---:|
| `rho_min`, `rho_max` | `0.10`, `0.90` |
| `chaos_min`, `chaos_max` | `0.02`, `0.25` |
| `chaos_r`, `chaos_seed` | `3.58`, `0.37` |
| `deposit_strength` | `0.50` |
| `tau0`, `tau_min`, `tau_max` | `1.0`, `0.10`, `10.0` |

### Objective và feasibility

| Tham số | Default |
|---|---:|
| `energy_weight` | `0.40` |
| `distance_weight` | `0.35` |
| `load_balance_weight` | `0.15` |
| `extra_head_weight` | `0.10` |
| `ensure_member_coverage` | `True` |
| `enforce_sink_radius` | `True` |

Mọi numeric config được kiểm tra finite/range khi khởi tạo.

Nếu “10 lần tìm” nghĩa là **tổng cộng đúng 10 candidate**, đặt
`num_ants=10, num_iterations=1`. Mặc định hiện dùng cấu trúc đầy đủ `M×T`:
10 kiến × 5 iteration = 50 candidate.

## Map 500×500×500

Package không tăng `radius=100`. Với deployment thưa hiện tại, target `k=10`
không đủ phủ sensor. Coverage repair có thể tăng số CH thực tế lên khoảng 40;
đây là hậu quả topology, không phải thay đổi bán kính. Nếu nghiên cứu yêu cầu
đúng 10% CH, cần sinh deployment liên thông hơn hoặc triển khai Phase 2
multi-hop thay vì bỏ range constraint.

Slide 41 còn đưa công thức `k_opt` dùng `epsilon_fs/epsilon_mp` của mô hình
radio 2D. Repo UWSN acoustic không có hai hệ số này, nên implementation dùng
`round(ch_proportion*N)` theo slide 47 thay vì giả lập `k_opt` bằng tham số sai.

Ma trận pheromone và coverage dùng `O(N^2)` bộ nhớ; phù hợp N=100 hiện tại.
Với mạng lớn cần sparse neighbor graph hoặc candidate pruning.

## Test

```powershell
$env:PYTHONPATH='src'
C:\Users\LOQ\miniconda3\python.exe -B -m unittest discover -s tests -v
```

Test kiểm tra config, NaN, adaptive bounds, seed, edge pheromone, live-node
filter, tree, coverage và default từ chối sink link vượt range.
