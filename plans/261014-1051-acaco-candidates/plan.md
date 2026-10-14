# Nghiên cứu candidate construction AC-ACO

Ngày 14/10/2026. Không thay source baseline, router, evaluator, D-ACO hoặc dữ liệu lịch sử.

- [x] Đọc working tree, audit, tests, router/evaluator/lifecycle; lưu `before.json`.
- [x] Phát hiện default current khác audit: load_weight=.25, tau_min=1; map uniform seed41, hash đúng audit.
- [x] B0 dùng tham số audit load_weight=0,tau_min=.01,tau0=1, giữ current-default riêng qua regression (`validation-acaco.xml`).
- [x] Package opt-in: V1 (0,.25,.5,1), V2 marginal, V3 reduced, V4 normalized, V5 feedback, V6 evaporation, V7 starts, R0 random (`src/algorithms/research_acaco`).
- [x] Observer không RNG/extra tree evaluations; CLI, fingerprints/parameters/seeds và provenance (`README.md`, campaign metadata).
- [x] Tests toán học, baseline equality, conservation, edge cases/reproducibility và statistical pairing: 56/56 targeted pass (`validation-acaco.xml`).
- [x] Audited seeds24–33/budget40; development grid18 maps; holdout18 independent maps/seeds74–75; proxy enumeration108 groups/1080 reference trees.
- [x] Combinations V2+V5/V2+V6 sau singles; physical trajectories10 rounds; κ0 causal controls. Không chạy full lifetime campaign.
- [x] Review độc lập APPROVE; báo cáo thống kê/khuyến nghị tiếng Việt (`code-review.md`, `final-report.md`, `final-analysis/details.json`).

Đơn vị suy rộng là topology; candidate/round trong một run không phải independent deployment. D comparator ghi rõ calibration thêm. Incomplete pools giữ trong artifacts, không ngầm bù search budget. Defaults production không đổi.

Deliverables A–F hoàn tất: thiết kế toán học, variants, scripts tái lập, unit tests/validation, pool analysis/figures, khuyến nghị có giới hạn bằng chứng. Hồ sơ kiểm chứng cuối ở `final-manifest.json`.

Giới hạn chưa xác minh: lifetime/FND/HND/LND, generalization ngoài scenarios đã thử, marginal pheromone credit, causal benefit của adaptive feedback/evaporation. Full tests83 pass/2 failures có sẵn về generator defaults; optimizer suite thiếu optuna. Không đánh dấu các giới hạn này là task đã chứng minh. Chi tiết ở cuối final report.
