# UWSN Simulator

Prototype Python mô phỏng mạng cảm biến không dây dưới nước (Underwater Wireless Sensor Network — UWSN) trong không gian 3D. Mỗi vòng mô phỏng chọn các cluster head (CH), lập cây truyền dữ liệu về sink, tính năng lượng tiêu thụ và lặp đến khi mạng chết, không còn route hợp lệ, hoặc đạt `T_max`.

## Tính năng và thuật toán

| Thành phần | Trạng thái | Ghi chú |
| --- | --- | --- |
| `SimpleACO` | Được benchmark mặc định | Ant Colony Optimization; chọn CH và duy trì pheromone qua các round. |
| `NodeACO` | Được benchmark mặc định | ACO tương tự SimpleACO nhưng pheromone gắn với từng node CH thay vì từng cạnh. |
| `PSO` | Được benchmark mặc định | Particle Swarm Optimization; chọn CH bằng quần thể particle. |
| `AC-ACO` | Được benchmark mặc định | Adaptive Chaotic ACO; chọn CH bằng pheromone, chaos và chi phí năng lượng. Xem [tài liệu riêng](src/algorithms/clustering/ac_aco/AC_ACO_README.md). |

Các thuật toán benchmark dùng route đa chặng: sensor thành viên nối tới CH gần nhất trong bán kính, sau đó CH nối thẳng sink hoặc relay qua một CH gần sink hơn. Mọi hop phải không vượt quá bán kính liên lạc.

## Kiến trúc và luồng chạy

```text
map.pkl -> NetworkInstance -> Simulator
                              |
        ACACO / SimpleACO / NodeACO / PSO
                              |
           sink (-1) <- CH relay <- CH <- sensor member
                              |
                    Evaluator -> residual energy -> CSV
```

`src/run.py` nạp map, tạo instance mới cho từng thuật toán, chạy `Simulator`, ghi kết quả và in bảng so sánh. `Simulator.run()` luôn khởi tạo lại năng lượng và danh sách node sống, nên các thuật toán được chạy độc lập trên cùng một map.

## Yêu cầu và cài đặt

- Python 3
- các gói trong `requirements.txt` (`numpy`, `pandas`, `matplotlib`)

Từ PowerShell tại thư mục gốc, cài dependencies vào môi trường Python đang dùng:

```powershell
python -m pip install -r requirements.txt
python src/run.py
python src/run.py --seed 24
```

Lệnh trên chạy `PSO`, `D-ACO`, `SimpleACO` và `AC-ACO`, rồi ghi mỗi lịch sử vào `runs/<timestamp>_<seed>_<algorithm>.csv`. Dùng `--seed 24` để tái lập benchmark; nếu bỏ qua, chương trình tạo và in seed của lần chạy.

All five algorithms, including `NodeACO`, accept `seed=24` when constructed.
An explicit seed gives each instance its own random stream, including D-ACO's
calibration and PSO's initialization, mutation and movement. Running another
instance does not affect that stream; pickle checkpoints retain its position.
Reproducibility requires the same map, parameters, source and runtime, and a
fresh instance at the start. For compatibility, unseeded SimpleACO, D-ACO,
NodeACO and PSO still use Python's global RNG; AC-ACO retains its private RNG.
The benchmark and v2 optimizer always pass explicit seeds.

## Map mặc định và tạo map mới

`map.pkl` mặc định gồm 100 sensor trong khối `500 × 500 × 500 m`; sink ở `(250, 250, 0)`, năng lượng đầu là `0.6`, bán kính liên lạc `200 m`. Quy ước `z = 0` là mặt nước.

Để sinh deployment ngẫu nhiên mới và ảnh minh họa:

```powershell
python src/map_gen.py
python src/map_gen.py --seed 07
```

> Cảnh báo: lệnh này ghi đè `map.pkl` và `map_3d.svg`. `map.pkl` là pickle, chỉ nạp file từ nguồn tin cậy.

Map seeds range from `01` to `99`. Omitting `--seed` chooses one randomly and
prints it; the integer is stored as `seed` inside `map.pkl`. The same seed and
generation settings reproduce the sensors, including clustering. Algorithm
seeds are separate. Use `--no-plot` to save the map without generating its SVG.

Khả năng dựng route và số round sống phụ thuộc thuật toán, tập CH và seed. Trên map hiện tại, AC-ACO với seed `39` đã hoàn tất 2.182 round trong phép đo lịch sử; con số này không đại diện cho SimpleACO, PSO hoặc seed khác.

## Kết quả

Khi có ít nhất một round hợp lệ, mỗi CSV có các cột:

| Cột | Ý nghĩa |
| --- | --- |
| `round` | Chỉ số round, bắt đầu từ 0. |
| `alive_nodes` | Số sensor còn năng lượng sau round. |
| `round_energy` | Tổng năng lượng mô hình tính cho round. |

Một run không tìm được route ngay từ đầu hiện có thể tạo CSV rỗng, không có header. Bảng tổng kết dùng `len(history)` làm số round đã ghi.

## Kiểm thử

Từ PowerShell tại thư mục gốc:

```powershell
$env:PYTHONPATH='src'
python -B -m unittest discover -s tests -v
```

Hiện chỉ có regression test cho AC-ACO: kiểm tra kết quả seeded trong 10 round, xác nhận `E_m` không bị tính lại trong một round và kiểm tra hai node trùng vị trí. Chưa có test cho clustering, PSO hoặc lần chạy end-to-end của `src/run.py`; cần cài dependencies trước khi chạy simulator.

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
    ├── base.py            # Interface ClusteringAlgorithm
    ├── clustering.py      # Xây cụm, direct và multi-hop routing
    ├── aco/               # SimpleACO (edge pheromone)
    ├── node_aco/          # NodeACO (node pheromone)
    ├── pso/               # PSO
    ├── ac_aco.py          # Orchestrator AC-ACO và route multi-hop
    └── clustering/ac_aco/ # Tham số, ant walk, pheromone và chaos của AC-ACO
tests/                     # regression test hiện có cho AC-ACO
```

## Cấu hình và mở rộng

Các hằng số chung, gồm `T_max` và tham số acoustic, nằm trong `src/hparameter.py`. Map giữ `width`, `height`, `depth`, `base_pos`, `sensors`, `init_energy`, `radius`.

Để thêm thuật toán:

1. Tạo subclass của `ClusteringAlgorithm`.
2. Cài đặt `plan_round(live_nodes, residual_e)`; trả về root `Node(-1)` hoặc `None` khi không có route khả thi.
3. Bảo đảm cây chỉ chứa node sống, ID là index gốc của sensor, và liên kết `prev`/`nxts` nhất quán.
4. Thêm class vào `ALGORITHMS` trong `src/run.py`.

## Mô hình năng lượng

Khoảng cách trong map dùng mét, nhưng attenuation đổi sang kilomet: `d_km = d_m / 1000`. Với `A(d) = d_km^spreading_factor * attenuation_coeff^d_km`, chi phí phát là `E_tx = P_0 * A(d) * packet_size / transmission_rate`.

- Sensor thường: chỉ trả `E_tx` tới CH.
- CH: trả `E_rx` cho mỗi node con, một lần `E_da`, rồi `E_tx` tới parent (CH relay hoặc sink).
- Sink không tiêu thụ năng lượng.

## Giới hạn đã biết

- `run.py` sinh seed ngẫu nhiên cho mỗi benchmark; cần cố định seed khi so sánh các lần chạy khác nhau.
- Route hợp lệ và số round sống thay đổi theo thuật toán, tập CH và seed; cần đo với seed cố định khi so sánh.
- Chưa có CLI hay file cấu hình ngoài mã nguồn.
- Ở round cuối, `round_energy` có thể lớn hơn năng lượng còn lại trước round vì chi phí được tính toàn bộ rồi năng lượng được chặn về 0.
- `rounds_survived = len(history)` không cho biết lý do dừng (hết node, hết route hay đạt `T_max`).
