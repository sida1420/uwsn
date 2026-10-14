# Báo cáo rà soát mã độc lập — AC-ACO candidate construction

Ngày rà soát: 14/10/2026. Kết luận: **APPROVE** cho phạm vi nghiên cứu đã yêu cầu. Không còn lỗi Critical, High hoặc Medium đã biết. Các hạn chế còn lại thuộc phạm vi diễn giải khoa học và độ tổng quát của bằng chứng, không chặn việc bàn giao.

## Phạm vi

- 14 file Python, 1.543 dòng: package `src/algorithms/research_acaco`, ba file test nghiên cứu, runner, proxy checker và ba script phân tích.
- Đối chiếu trực tiếp với AC-ACO production, shared cluster builder/router/evaluator, simulator lifecycle, `before.json`, `design.md`, `review.md` và artefact thí nghiệm.
- Scout tập trung vào dependents, budget evaluator, RNG/state mutation, dữ liệu thiếu, đồ thị rời rạc, cấu hình drift, ghép cặp thống kê, tính tái lập và ranh giới output.
- Fingerprint: 48/48 file nguồn/map ghi trong `before.json` còn nguyên; package nghiên cứu chỉ được gọi theo đường opt-in. Working tree production đã có thay đổi từ trước và không bị review này ghi đè.

## Đánh giá tổng thể

Thiết kế giữ đúng hai contract riêng: `ResearchOptions()` mặc định ủy quyền cho AC-ACO production hiện tại, còn B0 khoa học khai báo rõ cấu hình audited energy-only (`load_weight=0`, `tau_min=.01`, `tau0=1`). D-ACO, PSO, SimpleACO, router và evaluator dùng chung không bị sửa bởi package nghiên cứu.

Các variant được tách rõ và có thể chọn độc lập. V2 dùng surrogate tập hợp có giá trị hữu hạn cho empty/singleton/disconnected, biến đổi marginal dương và ổn định số học, đồng thời không gọi full router/evaluator trong construction. V3–V5 tách ba chính sách nhiễu xác suất. V6 loại cả nhiễu xác suất trực tiếp lẫn additive pheromone chaos và chỉ đưa chaos vào evaporation. V7 và R0 giữ đúng budget được khai báo. Instrumentation bọc các hàm đã được thuật toán gọi, không rút thêm RNG và không thêm tree-evaluator call ẩn.

Observer kiểm tra conservation, topology, radius và all-live coverage trước khi tính một candidate là feasible. Analyzer fail-fast khi probability/tree sai, metadata vật lý không tương thích, trùng khóa, hoặc cùng tên variant nhưng parameters/options bị drift. Ghép cặp dùng `(map_sha, algorithm_seed)`; topology là `map_sha`, nên alias scenario không thể tạo cặp giả.

## Critical

Không có.

## High

Không có.

## Medium

Không có lỗi chưa giải quyết. Trong quá trình rà soát, các lỗi sau đã được sửa và có regression coverage:

1. Cấu hình non-adaptive với `exploration_max < .02` từng làm feedback object không dùng đến vẫn lỗi khởi tạo.
2. Test B0 từng đặt nhầm `tau0=.01`; giá trị audited đúng là `tau0=1`.
3. Proxy với mạng rỗng từng có shape không hợp lệ.
4. Feasible pool/search index từng chỉ dựa trên energy dương hữu hạn thay vì toàn bộ invariant cây vật lý.
5. Analyzer từng có thể ghép scenario theo nhãn, trộn nhiều cấu hình dưới cùng tên variant, dùng B0 incomplete cho curve và hard-code độ dài 40.
6. Variant setup từng khởi tạo clustering hai lần, gây sai lệch runtime setup.
7. Provenance proxy, timing tách biệt, recursive source hashes và output isolation từng chưa đầy đủ.

## Low và giới hạn còn lại

1. `analysis/summarize-details.py` là script mô tả riêng cho holdout budget 40 nên còn hard-code `B0.feasible_count == 40`; script cũng không tự chạy lại toàn bộ validation của analyzer và không lọc `candidate_records` bằng `feasible_valid`. Artefact hiện tại đều hợp lệ nên kết quả hiện tại không sai, nhưng nên tái sử dụng validator chung nếu script được dùng cho budget/dataset khác.
2. V2 hướng dẫn từ CH thứ hai; CH đầu tiên vẫn được chọn đều. Deposit vẫn thưởng construction edge bằng `Q / final_tree_energy`, chưa gán marginal credit cho từng lựa chọn. Vì vậy kết quả chứng minh lợi ích của **marginal-guided construction**, chưa chứng minh pairwise pheromone learning đã được căn chỉnh hoàn toàn theo marginal energy.
3. Proxy-ranking campaign chỉ bao phủ mạng nhỏ, compact và connected. Surrogate có counterexample được test nơi projected relay rẻ hơn actual direct route; độ tương quan không được suy rộng sang mạng rời rạc hoặc deployment rộng.
4. Campaign chính được chạy trước một số bản sửa validation/provenance cuối. Metadata giữ source hash theo từng campaign, các sửa này không đổi search behavior, và đối chứng `V2+V6` chạy lại khớp 60/60 vòng. Báo cáo cuối cần nêu rõ snapshot thay vì trình bày mọi artefact như cùng một source hash.

## Edge cases do scout phát hiện và xác minh

- Empty network, singleton, residual thấp và disconnected graph có kết quả hữu hạn hoặc thất bại được ghi rõ; không phát sinh NaN/Inf trong probability.
- Tổng xác suất hữu hạn, không âm và bằng một; fallback uniform được test.
- Incomplete pools được giữ trong artefact, đưa vào feasibility/attempt statistics và loại khỏi so sánh equal-feasible-pool thay vì bù ngầm thêm budget.
- Cấu hình cùng nhãn variant nhưng params/options khác nhau bị analyzer từ chối.
- Scenario alias không làm hai map khác nhau bị ghép cặp vì khóa dùng checksum map.
- V6 first-round không được dùng làm bằng chứng cho evaporation: update xảy ra sau pool. Đối chứng nhiều vòng `κ=0` đã được thêm.
- Sáu quỹ đạo `V2+V6` chạy lại khớp tuyệt đối về selected energy, pool energy, feasibility, attempts, diversity và stagnation; dedup không coi chúng là deployment độc lập.
- `evaporation-control` có 120 record, 12 trajectory units, 40/40 candidate khả thi mỗi vòng, không có probability/tree violation. Round 0 của `V2+V6` và `V2+V6-k0` khớp 6/6; chín vòng sau cho cải thiện trung bình `-0,160%` so với `κ=0`, dao động `[-5,704%, 5,900%]`. Bằng chứng hiện tại không ủng hộ tuyên bố giảm evaporation tạo lợi ích nhân quả.
- Khoảng 98% construction-order CH edges không phải edge trong cây route cuối; đây là bằng chứng trực tiếp cho surrogate mismatch, nhưng không phải định lý rằng proximity luôn gây hại.

## Quan sát tích cực

- Telemetry/tree accounting đã được tách sang `tree_metrics.py`, còn operator/feedback tests được tách sang file test riêng. Tất cả file Python trong phạm vi nghiên cứu hiện không quá 198 dòng; phép tách không đổi đường dữ liệu hay trạng thái thuật toán.
- Default behavior được bảo toàn bằng delegation và seeded-equivalence tests; B0 audited được gắn nhãn/cấu hình riêng.
- Tất cả call evaluator tìm kiếm, calibration và diagnostic được đếm riêng; proxy chỉ dùng phép tính cache/vectorized và có cell-operation/runtime counters.
- Candidate records lưu unordered CH-set diversity nhưng vẫn giữ order dùng bởi router, phù hợp tính order-dependent của implementation.
- V6 thực thi đúng “chaos chỉ qua evaporation”; logistic state tiến đúng một lần mỗi physical round và tái lập theo seed.
- Holdout dùng 18 checksum topology độc lập với development; 17 topology có cặp pool hoàn chỉnh. Kết quả V2 `+2,474%` (CI 95% `[0,401%, 4,546%]`), V2+V5 `+6,730%` (`[5,881%, 7,578%]`) và V2+V6 `+7,094%` (`[6,040%, 8,148%]`) là paired topology-level evidence. V6 riêng `-1,872%` (`[-3,261%, -0,483%]`).
- Các kết luận được giới hạn đúng: development shared-seed grid chỉ mang tính thăm dò; short trajectories không phải full-lifetime evidence.

## Hành động khuyến nghị cho báo cáo cuối

1. Trình bày effect candidate energy trên 17 topology có paired complete pools; báo feasibility của đủ 18 topology ở bảng riêng, tránh diễn giải 40 ant là 40 deployment độc lập.
2. Xếp V2 là bằng chứng dương độc lập mạnh nhất về thay heuristic. Xếp V2+V5 và V2+V6 là combinations hứa hẹn, đồng thời nêu interaction chưa được causal decomposition đầy đủ.
3. Không tuyên bố V6/giảm evaporation có lợi: V6 riêng giảm chất lượng và đối chứng `κ=0` ngắn không cho tín hiệu dương.
4. Không tuyên bố tăng network lifetime. Bước tiếp theo hợp lý là preregister một full-lifetime holdout nhỏ cho V2 và một combination, nếu có thêm ngân sách.
5. Nếu tiếp tục nghiên cứu pheromone alignment, tách một experiment marginal credit/deposit riêng; không đổi identity của B0 hoặc gộp nó vào kết luận hiện tại.

## Metrics xác minh

- Targeted research tests sau khi tách module: **56 passed / 56**. Suite kết hợp với integration preset đạt **65 passed / 65** trong artefact JUnit riêng.
- Production/source fingerprint: **0/48** file trong `before.json` thay đổi.
- Artefact holdout: 324 pool rows, 18 map hashes; probability/tree validity đạt 100%; 19 pool incomplete được giữ và xử lý minh bạch.
- Artefact proxy: 108 ranking groups, 1.080 full reference evaluations, tách khỏi main search budget.
- Type coverage: không áp dụng; project Python không cấu hình static type-coverage.
- Test coverage theo dòng: chưa cấu hình coverage; không suy ra phần trăm từ số test.
- Lint issues: chưa có linter project chính thức; không ghi nhận lỗi runtime/compile trong phạm vi đã chạy.
- Full suite: không tuyên bố xanh. Hai assertion map-generator mặc định và dependency `optuna` thiếu là vấn đề có trước, ngoài phạm vi thay đổi này.

## Câu hỏi chưa được xác minh

- Lợi ích first-round có chuyển thành lifetime/FND/HND/LND tốt hơn trên holdout mới hay không?
- Proxy ranking giữ được chất lượng đến đâu trên topology thưa, disconnected hoặc N=200?
- Marginal deposit có cải thiện learning sau nhiều physical rounds mà không làm tăng evaluator budget hay gây hội tụ sớm không?

`plan.md` vẫn còn các checkbox cũ tại thời điểm review. Chủ nhiệm task cần đánh dấu các hạng mục đã hoàn tất sau khi chốt báo cáo khoa học; trạng thái file đó không phản ánh trạng thái thực tế của implementation và campaign.

### Bổ sung khi bàn giao

Sau review, tree accounting được tách nguyên trạng sang `tree_metrics.py`, tests operators sang file riêng, mọi Python file trong phạm vi dưới200 dòng. Reviewer kiểm tra lại modularization, xác nhận read-only semantics/budgets giữ nguyên và56/56 tests đạt; chỉ yêu cầu hai chỉnh sửa diễn đạt báo cáo (không suy causal từ combinations; topology là replicate). Chủ nhiệm đã áp dụng cả hai và cập nhật plan checklist. Final source/validation fingerprint được ghi riêng ở `final-manifest.json`; bản review phía trên giữ bằng chứng theo snapshot lúc viết.
