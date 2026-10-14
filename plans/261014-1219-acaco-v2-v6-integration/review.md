# Review tích hợp AC-ACO-V2-V6

Ngày 14/10/2026. Kết luận: **APPROVE**. Không còn lỗi Critical, High hoặc Medium trong phạm vi tích hợp.

## Phạm vi

- `src/algorithms/ac_aco_v2_v6.py`: preset production có tên, khai báo ở top level để multiprocessing `spawn` pickle được.
- `src/run.py`: registry/factory và đường chạy CSV production.
- `tests/test_ac_aco_v2_v6_runner.py`: registry, defaults, exact research equivalence, class/instance pickle, endpoint và Windows-spawn smoke.
- `src/algorithms/research_acaco/operators.py`: sửa độ bền số học tại biên evaporation được phát hiện bởi smoke.
- Đối chiếu `before.json`: hai file có sẵn thay đổi là `src/run.py` và experimental `operators.py` (numeric guard); 43 file nguồn/map/CSV khác giữ nguyên. Preset/test/smoke script là file mới.

## Đánh giá

Tại thời điểm review, `ALGORITHMS` là `[ACACO, DACO, ACACO_V2_V6]`. Working tree sau đó đổi registry sang `[PSO, ACACO_V2_V6]`; chủ nhiệm giữ nguyên lựa chọn mới và kiểm thử khả năng chọn độc lập cả ba class yêu cầu thay vì khóa default registry. Preset có tên `AC-ACO-V2-V6`, dùng `num_ants=40`, `load_weight=0`, `tau_min=.01`, `tau0=1`, `tau_max=20`, marginal heuristic, evaporation-only chaos và `kappa=.5`. So sánh trực tiếp với factory `V2+V6` của campaign cho thấy toàn bộ dataclass params/options, hai vòng energy, RNG state và pheromone đều trùng.

Class và instance sau khi chạy đều pickle/replay được. Production worker tạo hai CSV mang tên variant riêng; smoke dùng thư mục mới cô lập và xác nhận sentinel CSV của AC-ACO không bị ghi đè. AC-ACO mặc định vẫn bằng `ACACOParameters()` hiện tại.

## Vấn đề phát hiện và đã sửa

Smoke đầu tiên phát hiện `evaporation_rate` có thể trả `0.09999999999999998` tại endpoint toán học `0.1`; kiểm tra chặt trong `evaporation_only` đã từ chối giá trị đó. Với named V2+V6, lỗi có thể xuất hiện ở vòng vật lý cuối của horizon.

Sửa cuối chỉ chấp nhận `rho` nằm trong tối đa 8 ULP ngoài closed bounds, sau đó clamp vào `[low, high]` trước công thức vốn có. Giá trị sai đáng kể như `.099` hoặc `.601` vẫn bị từ chối. Đây là sửa floating-point robustness, không đổi schedule, tham số, xác suất chọn, công thức evaporation hoặc defaults của AC-ACO.

## Critical / High / Medium

Không có lỗi chưa giải quyết.

## Low

- `src/run.py` còn import `SimpleACO`, `NodeACO` và `PSO` dù registry mới không dùng chúng. Đây là cleanup lint, không ảnh hưởng hành vi, pickling hay kết quả.
- Preset lấy các tham số không override từ `ACACOParameters()` hiện hành. Điều này khớp chính xác factory nghiên cứu và yêu cầu tích hợp hiện tại; nếu production defaults đổi trong tương lai, nên có regression dataclass đầy đủ để ngăn scientific preset drift. Test hiện tại đã so sánh đầy đủ với factory của repository.

## Edge cases và an toàn

- Registry test khóa cả membership lẫn order, tránh tái diễn việc bỏ sót D-ACO.
- Seed mặc định và seed explicit được truyền đúng; không dùng global RNG mới.
- Horizon `T_max=1` chạy qua đúng endpoint, cùng một `HyperParameters` cho simulator và algorithm.
- Endpoint được test cho horizon 1/3500 và `kappa` 0/.5; input thực sự ngoài bound vẫn lỗi.
- CSV output nằm trong directory/prefix được truyền vào, variant name khác AC-ACO nên không đụng tên file cùng run.
- Không có network input, command construction, credential hoặc deserialization mới. Map pickle vẫn theo trust contract có sẵn của repository.

## Xác minh

- Canonical JUnit artefact: **65 passed / 65**, 11,681 giây, gồm integration và toàn bộ targeted AC/research suite.
- Durable Windows-spawn smoke qua `run.run_algorithm`: 1 physical round, 100 node sống, energy `0.014370245812214022 J`, hai CSV riêng và `result.json` trong `smoke-output`.
- Exact research preset: 2 vòng ở horizon production 3500 trùng energy/RNG/pheromone; class và instance pickle thành công.
- Lần chạy reviewer trong sandbox đạt 64 test; fixture spawn còn lại không setup được vì pytest không có quyền truy cập temp root của phiên reviewer. JUnit canonical và durable spawn script đều xác nhận test đó pass; đây là giới hạn môi trường review, không phải failure của code.
- Compileall đã được task owner chạy thành công.

## Kết luận

Preset production giữ đúng scientific identity đã báo cáo và có thể chọn cùng AC-ACO/D-ACO trên Windows spawn. Sửa endpoint cần thiết để đường chạy production không lỗi ở vòng cuối, đồng thời giữ nguyên toán học nghiên cứu. Không có kết quả campaign mới và không có tuyên bố lifetime mới từ phần tích hợp này.
