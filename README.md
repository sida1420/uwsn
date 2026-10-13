# UWSN Simulator

Prototype Python mô phỏng mạng cảm biến không dây dưới nước (Underwater Wireless Sensor Network — UWSN) trong không gian 3D. Mỗi vòng mô phỏng chọn các cluster head (CH), lập cây truyền dữ liệu về sink, tính năng lượng tiêu thụ và lặp đến khi mạng chết, không còn route hợp lệ, hoặc đạt `T_max`.

## Tính năng và thuật toán

| Thành phần | Trạng thái | Ghi chú |
| --- | --- | --- |
| `SimpleACO` | Được benchmark mặc định | Ant Colony Optimization; chọn CH và duy trì pheromone qua các round. |
| `NodeACO` | Được benchmark mặc định | ACO tương tự SimpleACO nhưng pheromone gắn với từng node CH thay vì từng cạnh. |
| `PSO` | Được benchmark mặc định | Particle Swarm Optimization; chọn CH bằng quần thể particle. |
| `D-ACO` | Được benchmark mặc định | ACO với mật độ trên grid, fitness năng lượng/load-density và calibration tham chiếu. |
| `AC-ACO` | Được benchmark mặc định | Adaptive Chaotic ACO; chọn CH bằng pheromone, chaos và chi phí năng lượng. Xem [tài liệu riêng](src/algorithms/clustering/ac_aco/AC_ACO_README.md). |

Các thuật toán benchmark dùng `dropping_member_multi_hop_routing`: sensor thành viên nối tới CH gần nhất trong bán kính; CH và sensor không thuộc cụm (outlier) nối thẳng sink hoặc relay qua một node sống gần sink hơn. Relay có thể là CH, sensor thường hoặc outlier, được chọn theo khoảng cách và năng lượng còn lại. Routing có thể tách một member khỏi cụm để giải quyết trường hợp bị chặn. Mọi hop phải không vượt quá bán kính liên lạc.

## Kiến trúc và luồng chạy

```text
map.pkl -> NetworkInstance -> Simulator
                              |
        ACACO / SimpleACO / NodeACO / PSO
                              |
           sink (-1) <- relay <- CH / outlier <- sensor member
                              |
                    Evaluator -> residual energy -> CSV
```

`src/run.py` nạp map, tạo instance mới cho từng thuật toán và chạy bằng hai worker process với multiprocessing `spawn`. Mỗi thuật toán ghi CSV khi hoàn tất; bảng so sánh được in sau khi tất cả hoàn tất. `Simulator.run()` khởi tạo lại năng lượng và danh sách node sống, nhưng không đặt lại trạng thái tìm kiếm của instance thuật toán đã dùng. Để benchmark độc lập, dùng instance thuật toán mới trên cùng map.

## Yêu cầu và cài đặt

- Python 3
- các gói trong `requirements.txt` (`numpy`, `pandas`, `matplotlib`)

Từ PowerShell tại thư mục gốc, tạo môi trường và cài dependencies (có thể thay `python` bằng `py` nếu dùng Windows Python Launcher):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/run.py
```

Lệnh trên chạy `PSO`, `D-ACO`, `SimpleACO`, `AC-ACO` và `NodeACO`, rồi ghi mỗi lịch sử vào `runs/<width>_<height>_<depth>_<sensor-count>_<distribution>_<YYYYMMDDHH>_<seed:02d>_<algorithm>.csv`. Đặt `SEED = 24` trong `src/run.py` để tái lập benchmark; nếu để `None`, chương trình tạo và in seed từ 1 đến 99. Các thuật toán trong cùng một lần chạy dùng chung timestamp. Timestamp chỉ chính xác tới giờ: chạy lại cùng môi trường, seed và thuật toán trong cùng giờ sẽ ghi đè CSV tương ứng.

Benchmark hiện không có CLI options. Chỉnh `ALGORITHMS` để đổi tập thuật toán; đổi map và seed bằng lời gọi `main(map_path="...", seed=24)` trong entry point. Khi gọi từ script khác, đặt lời gọi dưới `if __name__ == "__main__":` để dùng multiprocessing `spawn`.

All five algorithms, including `NodeACO`, accept `seed=24` when constructed.
An explicit seed gives each instance its own random stream, including D-ACO's
calibration and PSO's initialization, mutation and movement. Running another
instance does not affect that stream; pickle checkpoints retain its position.
Reproducibility requires the same map, parameters, source and runtime, and a
fresh instance at the start. For compatibility, unseeded SimpleACO, D-ACO,
NodeACO and PSO still use Python's global RNG; AC-ACO retains its private RNG.
The benchmark and v2 optimizer always pass explicit seeds.

## Map mặc định và tạo map mới

Generator hiện tạo 100 sensor trong khối `500 × 500 × 500 m`; sink ở `(250, 250, 0)`, năng lượng đầu là `0.6`, bán kính liên lạc `200 m`. Quy ước `z = 0` là mặt nước. Benchmark dùng nội dung `map.pkl` tại thời điểm chạy, không tự tạo lại map.

Để sinh deployment ngẫu nhiên mới và ảnh minh họa:

```powershell
.\.venv\Scripts\python.exe src/map_gen.py
```

> Cảnh báo: lệnh này ghi đè `map.pkl` và `map_3d.svg`. `map.pkl` là pickle, chỉ nạp file từ nguồn tin cậy.

Configure `new_map(...)` at the bottom of `src/map_gen.py` directly; there are
no CLI parameters. Choose `distribution="normal"`, `"clustered"`, or `"uniform"`.
The script entry point currently selects `uniform`; the `new_map()` function's
default is `normal`. Change dimensions, sensor count, energy and radius in the
`gen()` call inside `new_map()`.
Normal placement uses a Gaussian around the sink, truncated to the map bounds
with every sensor underwater (`z > 0`). Horizontal standard deviations are
`width / 6` and `height / 6`; depth uses `1.5 * depth / 6`. For the default
surface sink, this produces a concentration below the sink, extending deeper.
Clustered placement pulls uniform samples toward the nearest of
`num_cluster_points` random centers (default 5). Uniform placement samples the
whole water volume equally.

Map seeds range from `01` to `99`. Set `seed=7` in `new_map(...)` to reproduce
the map, or omit it to choose and print a random seed. The seed, distribution,
and cluster count are stored inside `map.pkl`. Algorithm seeds are separate.
Set `plot=False` to skip the SVG or `save_path=...` to change the pickle path.
Older maps without distribution metadata are recognized as clustered when
their saved cluster count is positive, otherwise uniform.

Khả năng dựng route và số round sống phụ thuộc deployment, thuật toán, tham số và seed. Xem [phân tích hiệu năng](plans/analysis/README.md) để đọc các phép đo lịch sử cùng điều kiện và giới hạn diễn giải.

## Kết quả

Khi có ít nhất một round hợp lệ, mỗi CSV có các cột:

| Cột | Ý nghĩa |
| --- | --- |
| `round` | Chỉ số round, bắt đầu từ 0. |
| `alive_nodes` | Số sensor còn năng lượng sau round. |
| `round_energy` | Tổng năng lượng mô hình tính cho round. |
| `time` | Elapsed wall-clock seconds for this round: search, evaluation and energy update. |

Runs with no feasible round still export the CSV column headers. Timing excludes
CSV writes and between-round printing; initial calibration is included in the
first round. Optimizer per-round CSVs use the same `time` field and include their
observation overhead. Historical CSVs retain their originally recorded columns.

## Kiểm thử

Từ PowerShell tại thư mục gốc:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
# Cài thêm dependencies và chạy kiểm thử optimizer khi cần:
.\.venv\Scripts\python.exe -m pip install -r optimizer/requirements.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s optimizer/tests -v
```

Maintained production checks cover AC-ACO, D-ACO, PSO, algorithm/map seeds, checkpoints and run naming. See [tests/README.md](tests/README.md); optimizer tests live in optimizer/tests/.

## Cấu trúc dự án

```text
src/
├── run.py                 # Entry point benchmark
├── network.py             # Map bất biến và ma trận khoảng cách 3D
├── simulate.py            # Vòng đời mô phỏng, trạng thái năng lượng
├── evaluate.py            # Mô hình năng lượng trên cây route
├── node.py                # Node của cây (sink có id -1)
├── hparameter.py          # Hằng số mô phỏng/âm học chung
├── map_gen.py             # Sinh map.pkl và map_3d.svg
└── algorithms/
    ├── base/base.py       # Algorithm, ClusteringAlgorithm, RoutingAlgorithm
    ├── aco.py             # Orchestrator SimpleACO (edge pheromone)
    ├── node_aco.py        # Orchestrator NodeACO (node pheromone)
    ├── pso.py             # Orchestrator PSO
    ├── d_aco.py           # Orchestrator D-ACO
    ├── ac_aco.py          # Orchestrator AC-ACO và route multi-hop
    ├── clustering/       # Clustering và tham số riêng từng thuật toán
    └── routing/routing.py # Routing đa chặng dùng chung
tests/                     # production algorithm and seeding regressions
optimizer/                 # Tuning D-ACO, Windows launchers và tests
plans/analysis/            # Phân tích và bằng chứng hiệu năng
runs/                      # CSV benchmark và dữ liệu lịch sử
```

## Cấu hình và mở rộng

Các hằng số chung, gồm `T_max` (mặc định 3000 round) và tham số acoustic, nằm trong `src/hparameter.py`. Map giữ `width`, `height`, `depth`, `base_pos`, `sensors`, `init_energy`, `radius` cùng metadata seed/distribution. Tham số thuật toán nằm trong `src/algorithms/clustering/<algorithm>/parameters.py`.

Để thêm thuật toán:

1. Tạo subclass của `Algorithm` trong `src/algorithms/base/base.py`, nhận `(network, hparameters, seed=None)` và đặt `name` riêng. Cài đặt `init_params()` để tạo tham số và thành phần clustering/routing; base constructor tự gọi hàm này.
2. Cài đặt `plan_round(live_nodes, residual_e)`; trả về `(root, consumption)` với root `Node(-1)` và consumption `{sensor_id: energy}`, hoặc `(None, {})` khi không có route khả thi. Consumption rỗng cho route thành công sẽ dùng evaluator fallback.
3. Bảo đảm cây chỉ chứa node sống, ID là index gốc của sensor, và liên kết `prev`/`nxts` nhất quán.
4. Thêm class vào `ALGORITHMS` trong `src/run.py`.

## Mô hình năng lượng

Khoảng cách trong map dùng mét, nhưng attenuation đổi sang kilomet: `d_km = d_m / 1000`. Với `A(d) = d_km^spreading_factor * attenuation_coeff^d_km`, chi phí phát là `E_tx = P_0 * A(d) * packet_size / transmission_rate`.

- Sensor lá thường: phát một packet tới parent.
- Mỗi sensor không phải sink: trả `E_rx` theo số packet nhận từ các node con.
- CH: thêm `E_da` theo số packet nhận và phát hai packet theo evaluator hiện tại.
- Relay không phải CH: phát các packet nhận cùng một packet của mình.
- Sink không tiêu thụ năng lượng.

## Giới hạn đã biết

- `run.py` sinh seed ngẫu nhiên cho mỗi benchmark; cần cố định seed khi so sánh các lần chạy khác nhau.
- Route hợp lệ và số round sống thay đổi theo thuật toán, tập CH và seed; cần đo với seed cố định khi so sánh.
- Benchmark và map generator cấu hình qua mã Python, không có CLI options; optimizer dùng YAML và CLI riêng.
- Ở round cuối, `round_energy` có thể lớn hơn năng lượng còn lại trước round vì chi phí được tính toàn bộ rồi năng lượng được chặn về 0.
- `rounds_survived = len(history)` không cho biết lý do dừng (hết node, hết route hay đạt `T_max`).
- Không tìm được route trong tìm kiếm không chứng minh mạng đã mất kết nối vật lý; số round hoàn tất cũng khác thời điểm node đầu tiên chết. Kết quả đạt `T_max` bị giới hạn bởi horizon.

## Optimizer

[optimizer/README.md](optimizer/README.md) mô tả controller tối ưu tham số D-ACO, map cố định cho từng campaign, checkpoints, Windows launchers và báo cáo. Campaign mặc định dùng horizon 3500, khác benchmark 3000. PSO và AC-ACO có adapter smoke check nhưng chưa hỗ trợ tuning.

```powershell
.\.venv\Scripts\python.exe -m pip install -r optimizer/requirements.txt
.\.venv\Scripts\python.exe -B -m optimizer --help
```

Xem [config mẫu](optimizer/config.example.yaml) và hướng dẫn riêng để khởi tạo campaign, chạy/resume, dừng và xuất report.

## Performance evidence

See [plans/analysis](plans/analysis/README.md) for the consolidated measurements,
parameter sets and interpretation across historical experiments and both optimizer maps.
