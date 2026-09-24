# UWSN Simulator

Prototype Python mô phỏng mạng cảm biến không dây dưới nước (Underwater Wireless Sensor Network — UWSN) trong không gian 3D. Mỗi vòng mô phỏng chọn các cluster head (CH), lập cây truyền dữ liệu về sink, tính năng lượng tiêu thụ và lặp đến khi mạng chết, không còn route hợp lệ, hoặc đạt `T_max`.

## Tính năng và thuật toán

| Thành phần | Trạng thái | Ghi chú |
| --- | --- | --- |
| `SimpleACO` | Được benchmark mặc định | Ant Colony Optimization; chọn CH và duy trì pheromone qua các round. |
| `PSO` | Được benchmark mặc định | Particle Swarm Optimization; chọn CH bằng quần thể particle. |
| AC-ACO | Thử nghiệm Phase 1 | Chọn CH/gán cụm có seed mặc định `42`; chưa có adapter multi-hop nên không thuộc benchmark chính. Xem [tài liệu riêng](src/algorithms/ac_aco/README.md). |

Hai thuật toán mặc định đều dùng route đa chặng: sensor thành viên nối tới CH gần nhất trong bán kính, sau đó CH nối thẳng sink hoặc relay qua một CH gần sink hơn. Mọi hop phải không vượt quá bán kính liên lạc.

## Kiến trúc và luồng chạy

```text
map.pkl -> NetworkInstance -> Simulator
                              |
                 ACOClustering / PSOClustering
                              |
           sink (-1) <- CH relay <- CH <- sensor member
                              |
                    Evaluator -> residual energy -> CSV
```

`src/run.py` nạp map, tạo instance mới cho từng thuật toán, chạy `Simulator`, ghi kết quả và in bảng so sánh. `Simulator.run()` luôn khởi tạo lại năng lượng và danh sách node sống, nên các thuật toán được chạy độc lập trên cùng một map.

## Yêu cầu và cài đặt

- Python 3
- `pandas` và `matplotlib`

Repository hiện chưa có dependency manifest. Từ PowerShell tại thư mục gốc, cài dependencies (có thể làm trong môi trường Python riêng nếu cần):

```powershell
python -m pip install pandas matplotlib
python src/run.py
```

Lệnh trên chạy `SimpleACO` và `PSO`, luôn tạo `results_SimpleACO.csv` và `results_PSO.csv`, rồi in tổng kết. Nếu không có round hợp lệ, file CSV tương ứng không có header hoặc dòng dữ liệu.

## Map mặc định và tạo map mới

`map.pkl` mặc định gồm 100 sensor trong khối `500 × 500 × 500 m`; sink ở `(250, 250, 0)`, năng lượng đầu là `0.6`, bán kính liên lạc `100 m`. Quy ước `z = 0` là mặt nước.

Để sinh deployment ngẫu nhiên mới và ảnh minh họa:

```powershell
python src/map_gen.py
```

> Cảnh báo: lệnh này ghi đè `map.pkl` và `map_3d.svg`. `map.pkl` là pickle, chỉ nạp file từ nguồn tin cậy.

Map hiện thưa: chỉ một node nằm trong phạm vi 100 m của sink. Với khoảng 5 CH, cả hai thuật toán có thể không dựng được chuỗi relay hợp lệ và dừng ở round 0. Đây là kết quả topology/ràng buộc range, không phải bảo đảm simulator luôn có output.

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

Bộ kiểm thử hiện có 16 test và đã chạy thành công. Các test kiểm tra clustering, PSO và AC-ACO nhưng chưa bao phủ lần chạy end-to-end của `src/run.py`; cần cài dependencies trước khi chạy simulator.

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
    ├── aco/               # SimpleACO
    ├── pso/               # PSO
    └── ac_aco/            # AC-ACO Phase 1 thử nghiệm
tests/                     # unittest cho clustering, PSO, AC-ACO
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

- SimpleACO và PSO chưa đặt seed, nên benchmark không tái lập hoàn toàn.
- Map mặc định có thể dừng ngay round 0 do không tìm được route multi-hop hợp lệ.
- Chưa có dependency manifest, CLI hay file cấu hình ngoài mã nguồn.
- Gói dữ liệu CH không tăng theo số member; `E_da` chỉ tính một lần cho CH.
- Ở round cuối, `round_energy` có thể lớn hơn năng lượng còn lại trước round vì chi phí được tính toàn bộ rồi năng lượng được chặn về 0.
- `rounds_survived = len(history)` không cho biết lý do dừng (hết node, hết route hay đạt `T_max`).
