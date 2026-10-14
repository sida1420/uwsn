# Tích hợp AC-ACO-V2-V6 vào runner

Ngày14/10/2026. Hoàn tất integration và smoke; không chạy full lifetime.

## Thay đổi chính xác

1. `src/algorithms/ac_aco_v2_v6.py`: class top-level `ACACO_V2_V6(ResearchACACO)`, name `AC-ACO-V2-V6`. Constructor nhận network/hparameters/seed, dùng lại implementation nghiên cứu.
2. `src/run.py`: import class mới; thêm class vào `ALGORITHMS`; factory có nhánh preset, giữ seed explicit hoặc fallbackSEED cho mọi class. Đã kiểm tra cấu hình `[ACACO,DACO,ACACO_V2_V6]`; working tree sau đó đổi lựa chọn thành `[PSO,ACACO_V2_V6]`, được giữ nguyên. Tests không khóa danh sách mặc định mà xác minh từng class chọn độc lập.
3. `src/algorithms/research_acaco/operators.py`: sửa numerical validation của rho tại endpoint. Schedule có thể cho `.09999999999999998` thay vì `.1`; validator chỉ chấp nhận sai số trong8 ULP rồi clamp về interval trước công thức cũ. Ngoài dung sai vẫn raise. Không đổi schedule, công thức evaporation, heuristic, objective hoặc tham số.
4. `tests/test_ac_aco_v2_v6_runner.py`: registry, factory/default isolation, exact research-preset equality, paired trajectories/RNG/pheromone, class/instance pickle, worker spawn thực, CSV độc lập và endpoint regression.

Working tree trước integration đã có sửa đổi chưa commit. `before.json` lưu snapshot; chỉ hai file có sẵn ở trên (`run.py`, experimental `operators.py`) được sửa. ACACO class/parameters/defaults, D-ACO, PSO, shared router/evaluator/simulator, maps và CSV lịch sử giữ nguyên fingerprint.

## Preset

Đối chiếu trực tiếp `make_algorithm('V2+V6',network,seed,40)` trong `plans/261014-1051-acaco-candidates/run-experiments.py`:

- `ResearchOptions(heuristic='marginal',chaos_policy='evaporation',evaporation_kappa=.5)`.
- Không direct probability chaos; không additive chaotic pheromone disturbance; ordinary energy reinforcement được giữ.
- `load_weight=0`: chọn minimum final total energy, không CV/load/density fitness.
- Ants40, attempts/ant10, CH proportion.20.
- `tau_min=.01,tau0=1,tau_max=20`, không dùng floor1 của current production defaults.
- Các tham số còn lại giữ nguyên preset nghiên cứu: alpha1, gamma.1, distance_weight1 (không tham gia marginal operator), beta1–5/raw/slope5, rho.1–.6, chaos.05–.30/r3.61/seed.37, Q.01/elite.1/hopping.4.

Test so sánh toàn bộ dataclass params/options, không chỉ vài fields. Hai physical-round decisions với T_max3500/seed24 khớp experimental factory về per-node consumption, RNG và pheromone. Không retune.

## Chạy

Từ repository root, với Python environment có dependencies hiện tại:

```powershell
python src/run.py
```

Trong môi trường này cũng có thể dùng:

```powershell
C:\Users\LOQ\miniconda3\python.exe src/run.py
```

Runner hiện chọn `[PSO,ACACO_V2_V6]` theo working tree lúc bàn giao. Để chỉ chạy variant, sửa danh sách thành `[ACACO_V2_V6]`; để so sánh ba algorithms đặt `ALGORITHMS=[ACACO,DACO,ACACO_V2_V6]`. Cả ba class đã được import và factory hỗ trợ. Nếu cần seed cố định, đặt `SEED=24` trong runner hoặc gọi `main(seed=24)` từ một script có main guard.

Class định nghĩa trong module importable, không phải lambda/local class/factory closure; hỗ trợ Windows spawn. `ProcessPoolExecutor` hiện hữu và main guard không đổi. Các file variant dưới `runs/` có dạng:

```text
<environment>_<timestamp>_<seed>_AC-ACO-V2-V6.csv
<environment>_<timestamp>_<seed>_AC-ACO-V2-V6_sensor-energy.csv
```

Original AC-ACO có suffix `AC-ACO`, nên không trùng tên variant.

## Kiểm chứng đã chạy

- **65 passed**, compileall source thành công; JUnit tại `validation.xml`.
- `smoke-spawn.py` gọi chính production `run_algorithm` trong process spawn mới, max_workers1, seed24. Smoke-only T_max1; production `src/run.py` vẫn T_max3500. T_max1 làm beta≈4.69657, vì vậy energy smoke không được dùng làm research comparison.
- Smoke: một physical round,40 feasible candidates,100 node sống, round energy **.014370245812214022J**. File `smoke-output/result.json`, hai CSV `integration-smoke_AC-ACO-V2-V6*.csv`.
- Smoke directory tạo bằng `exist_ok=False`: không overwrite lần smoke trước hoặc output production. Unit test đặt sentinel file với tên original AC-ACO và xác nhận không đổi.
- Lần smoke đầu phát hiện rho-bound floating-point error; đã sửa numerical guard, kiểm thử end schedule ở T1/T3500,κ0/.5 và genuine out-of-bounds. Regression chạy lại qua đúng production worker, không né endpoint bằng fixture khác.

## Giới hạn

Không chạy lifetime campaign trong integration. Không khẳng định lifetime improvement từ smoke. Kiến thức nghiên cứu/giới hạn V2+V6 ở report trước vẫn áp dụng; numeric endpoint fix chỉ làm đúng closed-bound contract. Không còn lỗi unresolved trong tests phạm vi integration; hai lỗi cũ về generator defaults của full test suite trước đây không thuộc thay đổi này.

Thư mục phụ `review-temp` do sandbox reviewer tạo chưa dọn: policy từ chối lệnh xóa. Đây không phải deliverable hoặc dữ liệu dùng để chạy thuật toán; không thử bypass policy. Review độc lập APPROVE tại `review.md`.
