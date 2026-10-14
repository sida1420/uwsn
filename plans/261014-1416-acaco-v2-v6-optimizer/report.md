# Kiểm tra optimizer tham số cho AC-ACO-V2-V6

## Cách chạy

Mở PowerShell tại repository root rồi chạy:

```powershell
cd C:\Users\LOQ\Desktop\uwsn
& 'C:\Users\LOQ\miniconda3\python.exe' -m optimizer smoke-v2-v6 --study optimizer/runs/acaco-v2-v6-my-check --trials 3 --rounds 3 --seeds 24 25
```

Thư mục `--study` phải chưa tồn tại và nằm trong `optimizer/`. Mỗi lần chạy lại hãy đổi tên thư mục. Không cần `init`, lịch sử legacy hay sửa `ALGORITHMS` trong `src/run.py`.

Đây là đường kiểm tra tìm tham số ngắn, riêng cho V2+V6. Đường optimizer khoa học `init/run` cũ vẫn chỉ hỗ trợ D-ACO. Giới hạn: 2–3 trials, 1–10 round vật lý, 1–3 seeds khác nhau, tối đa 200 sensors, một worker. Cần Python 3.14+ để có thể kết thúc worker khi timeout. Môi trường đã cài Optuna 4.6.0 và psutil 7.2.2.

## Phạm vi và cấu hình

`optimizer/adapters.py` bổ sung adapter `acaco_v2_v6`; `optimizer/v2_v6_smoke.py` điều phối; `optimizer/__main__.py` cung cấp CLI. Adapter tái sử dụng `ResearchACACO`, heuristic marginal, chaos chỉ qua evaporation, κ=0.5. Giữ objective chọn candidate theo năng lượng, không disturbance trực tiếp khi selection.

Trial đầu là preset đã báo cáo: 40 ants, load_weight=0, tau_min=0.01, tau0=1, tau_max=20. Sau đó Optuna đề xuất hai cấu hình. Chỉ năm tọa độ được thay đổi:

| Tham số | Khoảng thử |
|---|---|
| pheromone_exponent | 0.5–2.0 |
| beta_min | 0.5–2.0 |
| Q | 0.003–0.03, log scale |
| rho_max | 0.3–0.7 |
| elite_weight | 0–0.2 |

Các tham số khác bị khóa theo preset, gồm ngân sách ants, pheromone bounds và lịch thích nghi T_max=3500. Không thay công thức V2/V6. Khoảng thử là phạm vi thăm dò, không phải khoảng tối ưu đã xác nhận. Cơ chế baseline enqueue và ask/tell dùng [API Study chính thức của Optuna 4.6](https://optuna.readthedocs.io/en/v4.6.0/reference/generated/optuna.study.Study.html).

Meta-objective của lần thử là trung bình tổng năng lượng vật lý của các round đã chọn, trên cùng seeds và cùng horizon. Chỉ so sánh trial hoàn thành toàn bộ horizon và còn đủ nodes theo hợp đồng `run_seed`. Đây không phải objective service-lifetime và constraint +2% của campaign D-ACO. Baseline lỗi hoặc timeout sẽ dừng campaign; không xuất provisional winner khi campaign chưa hoàn tất.

## Kết quả thực chạy

Thư mục xác nhận: `optimizer/runs/acaco-v2-v6-check-261014-verified/`. Một map hiện có, seeds 24 và 25, ba round mỗi seed, ba trials. Cả ba hoàn tất; 240 evaluator calls mỗi trial, 720 tổng cộng. Thời gian 7.407 giây trên máy hiện tại.

| Trial | Cấu hình | Mean tổng năng lượng 3 round (J) | Giảm so với baseline |
|---|---|---:|---:|
| 0 | Preset đã báo cáo | 0.04620775637 | 0% |
| 1 | Đề xuất 1 | 0.04567106912 | 1.1615% |
| 2 | Đề xuất 2 | 0.04448217878 | 3.7344% |

Trial 2: pheromone_exponent=1.7948529991398563, beta_min=1.8466780007893162, Q=0.0030083763097873205, rho_max=0.36995865491610147, elite_weight=0.19848620098111747. Toàn bộ tham số hiệu dụng được lưu trong JSON/CSV, không tự ghi vào production defaults.

Lần chạy trước bằng cùng seeds cho cùng kết quả; đó là kiểm tra tái lập, không phải mẫu độc lập. Chưa có holdout hoặc nhiều topology cho thử tham số này, chưa kiểm tra lifetime, chưa có cơ sở gọi trial 2 là bộ tham số tối ưu. Kết quả chỉ xác nhận pipeline đề xuất và đánh giá tham số hoạt động; không thay khuyến nghị khoa học từ nghiên cứu candidate pool trước đó.

## Kiểm chứng và artifacts

89 tests passed trong 20.66 giây; compileall optimizer thành công. Kiểm tra preset/RNG tương đương lớp V2+V6 đã tích hợp, validation tham số khóa, chạy vật lý và checkpoint/resume, ngân sách, output scope, baseline lỗi và timeout. Báo cáo JUnit: `validation.xml`.

`summary.json`, `trial-results.csv`, `trial-results.json`: kết quả. `config.json`, `provenance.json`, `search-space.json`, `study.db`: tái lập nghiên cứu. Mỗi seed lưu trajectories, checkpoints và metrics trong `trials/`. Map được sao chép vào thư mục study, không ghi đè map gốc hoặc CSV lịch sử. `before.json` và `verification.json` ghi fingerprint trước/sau; tất cả source trong `src/` giữ nguyên ở tác vụ optimizer này.

Bước tiếp theo có giá trị khoa học là so sánh preset với một số cấu hình đề xuất trên nhiều topology độc lập và seeds holdout, cùng ngân sách; chỉ cân nhắc thử lifetime sau đó. Lệnh này cố ý không mở tìm kiếm hàng nghìn rounds.
