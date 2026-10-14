# Chạy lại nghiên cứu AC-ACO

Kết quả và giới hạn: [final-report.md](final-report.md). Công thức: [design.md](design.md). Source baseline/physics/map/historic CSV không đổi. Production defaults hiện khác audit; runner explicit energy-only `load_weight=0,tau_min=.01,tau0=1` và ghi effective parameters.

Chạy từ repo root. Dùng output directory **chưa tồn tại**, nằm trong plan này; không overwrite campaign/map cũ. Dependencies bổ sung ở `research-requirements.txt` (môi trường hiện tại đã có).

```powershell
$researchPython = 'C:\Users\LOQ\miniconda3\python.exe'
& $researchPython plans/261014-1051-acaco-candidates/run-experiments.py --output plans/261014-1051-acaco-candidates/reproduction-audit --variants B0 V1-0 V1-.25 V1-.5 V1-1 V2 V3 V4 V5 V6 V7 R0 D0 D40total --seeds 24 25 26 27 28 29 30 31 32 33 --budget 40
& $researchPython plans/261014-1051-acaco-candidates/analysis/run-holdout.py --output plans/261014-1051-acaco-candidates/reproduction-holdout --seeds 74 75
& $researchPython plans/261014-1051-acaco-candidates/check-proxy-ranking.py --output plans/261014-1051-acaco-candidates/reproduction-proxy.json
& $researchPython plans/261014-1051-acaco-candidates/run-experiments.py --output plans/261014-1051-acaco-candidates/reproduction-short --variants B0 V2 V5 V6 V6-k0 V2+V5 V2+V6 V2+V6-k0 --seeds 74 75 --rounds 10
& $researchPython -m pytest -q -p no:cacheprovider tests/test_ac_aco_research.py tests/test_ac_aco_research_operators.py tests/test_ac_aco_research_analysis.py tests/test_ac_aco_equations.py tests/test_ac_aco_pheromone.py tests/test_ac_aco_calibration.py tests/test_ac_aco_vectorization.py
```

Chọn topology mới bằng `--skip-audited --distributions clustered uniform normal --nodes 50 100 200 --scenario-seeds ...`; không dùng lại cùng scenario seed giữa cells nếu muốn independent inference. Default map hash bắt buộc khớp audit; map metadata uniform được công bố, không regenerate để ép clustered. `--expected-map-sha` chỉ dùng khi chủ động đổi map đã được xác minh, phải công bố baseline khác.

```powershell
& $researchPython plans/261014-1051-acaco-candidates/analysis/analyze-results.py plans/261014-1051-acaco-candidates/reproduction-audit/pools.jsonl --output plans/261014-1051-acaco-candidates/reproduction-audit/analysis
```

Analyzer nhận nhiều JSONL paths và `--independent-topologies` **chỉ** khi topology RNG streams độc lập. Pairing theo map SHA+algorithm seed; không ghép snapshots source/physics khác nhau hoặc effective config khác nhau dưới cùng variant. Incomplete pools không được bù hidden budget. D0=40 search+40 calibration, D40total=20+20; partial proxy không có full evaluations nhưng vẫn tốn CPU và có counters/time riêng.

API opt-in, không sửa ALGORITHMS production:

```python
from dataclasses import replace
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.research_acaco import ResearchACACO, ResearchOptions

parameters = replace(ACACOParameters(), load_weight=0, tau_min=.01)
algorithm = ResearchACACO(network, hparameters, parameters, seed=74,
    options=ResearchOptions(heuristic="marginal", chaos_policy="adaptive"))
root, consumption = algorithm.plan_round(live_nodes, residual_e)
```

Omit options để giữ đúng current production behavior. `chaos_policy` selectable: baseline/reduced/normalized/adaptive/evaporation; `heuristic` baseline/marginal; starts và random_sets là independent options. Tên biến thể phải phản ánh cấu hình, không gắn heuristic mới nhãn original AC-ACO. Fixed-budget comparison không đồng nghĩa equal runtime; chưa có lifetime claim.

Câu hỏi còn mở và failures sẵn có được liệt kê ở cuối final report.
