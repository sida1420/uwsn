# Review độc lập — optimizer smoke AC-ACO-V2-V6

Ngày 14/10/2026. Kết luận: **APPROVE** cho mục tiêu kiểm tra pipeline parameter search nhỏ. Không còn lỗi Critical, High hoặc Medium. Kết quả này không phải bằng chứng chọn tham số tối ưu và không thay thế holdout/full-lifetime validation.

## Phạm vi

- `optimizer/v2_v6_smoke.py`: orchestration baseline-first, Optuna ask/tell, Windows spawn, giới hạn budget và xuất artefact.
- `optimizer/adapters.py`: `ACACOV2V6Adapter`, search space và khóa scientific identity.
- `optimizer/__main__.py`: lệnh opt-in `smoke-v2-v6`.
- `optimizer/tests/test_v2_v6_smoke.py`, campaign `optimizer/runs/acaco-v2-v6-check-261014-verified` và provenance tương ứng.
- Đối chiếu `before.json`: trong các file đã có trước task, chỉ `optimizer/adapters.py` và `optimizer/__main__.py` thay đổi. D engine, controller scientific, production algorithms/defaults, router, evaluator và physics giữ nguyên.

## Đánh giá tổng thể

Đường smoke được tách khỏi controller D-ACO. `initialize()` vẫn từ chối `algorithm=acaco_v2_v6`, nên lệnh mới không thể vô tình chạy theo policy lifetime/+2% hoặc quảng bá tham số sang production. Output bắt buộc là directory mới nằm dưới `optimizer/`; map được copy byte-for-byte, rồi source/map/runtime configuration được fingerprint và bảo vệ bằng `EpochGuard`.

Adapter giữ cố định energy-only V2+V6: 40 ant, `load_weight=0`, tau `(.01,1,20)`, marginal heuristic, evaporation-only chaos và `kappa=.5`. Chỉ năm tọa độ được mở: alpha/`pheromone_exponent`, `beta_min`, `Q` log-scale, `rho_max`, `elite_weight`. Mọi field khác, field lạ và giá trị ngoài range đều bị từ chối. Baseline adapter trùng hoàn toàn named production preset và trajectory/RNG checkpoint resume được kiểm tra.

Objective là mean tổng năng lượng vật lý được chọn trên cùng short all-alive horizon, map và development seeds. Một run chỉ comparable khi hoàn tất đủ vòng và mọi vòng phục vụ đủ toàn bộ N node trước/sau. Search ghi riêng số full evaluator calls; fixed 40-ant/10-attempt policy không bị thay đổi. Baseline luôn là trial đầu, sau đó mới có sampler proposals.

## Vấn đề phát hiện và đã sửa

1. Baseline không comparable từng không chặn proposals, nên một proposal có thể bị gọi là `provisional_best` mà không có reference hợp lệ. Bản cuối dừng sau trial baseline, đặt `pipeline_status=failed`, ghi `abort_reason` và để `provisional_best=null`.
2. `Future.result(timeout=120)` từng nằm trong context manager nhưng không chấm dứt worker đang chạy; `shutdown(wait=True)` có thể làm smoke treo vô hạn. Bản cuối yêu cầu Python 3.14 trước khi tạo output, gọi `terminate_workers()` khi timeout/broken pool và dừng pipeline. Hai đường failure có unit tests.

## Critical / High / Medium

Không có lỗi chưa giải quyết.

## Low và giới hạn

- Lệnh smoke cố ý yêu cầu Python 3.14+ vì dùng `ProcessPoolExecutor.terminate_workers()`. Đây là preflight rõ ràng và không tạo thư mục dở dang trên interpreter cũ, nhưng hạn chế portability.
- Hai thư mục artefact tồn tại: `acaco-v2-v6-check-261014` là development run trước các guard cuối; `acaco-v2-v6-check-261014-verified` mới là canonical. Báo cáo/người dùng phải luôn trỏ tới thư mục `-verified` để tránh nhầm schema cũ.
- Checkpoint lưu trajectory/RNG chính xác, nhưng smoke directory phải mới nên không cung cấp CLI resume toàn campaign sau khi controller bị gián đoạn. Điều này chấp nhận được cho 2–3 trial smoke; không nên suy rộng thiết kế đó sang campaign dài.
- `provisional_best` chỉ là minimum trong ba trial trên một topology và hai algorithm seeds. Tên và warning hiện đã giới hạn đúng ý nghĩa; không được copy tham số này vào preset/default.

## Edge cases và failure handling

- Từ chối trials ngoài 2–3, rounds ngoài 1–10, hơn ba seed, seed trùng/bool/âm và map có N ngoài 1–200 hoặc radius graph disconnected.
- Từ chối output tồn tại, ngoài `optimizer/`, hoặc thiếu worker-termination API trước khi ghi artefact.
- Baseline failure, incomplete horizon, node chết/mất service, timeout và broken worker không tạo winner.
- SQLite study dùng ask/tell; trial lỗi được đánh dấu `FAIL`. JSON cập nhật atomically sau từng trial; source/map drift bị chặn ở trial boundary và bên trong `run_seed`.
- Một Windows spawn worker tránh chia sẻ RNG/algorithm state. Identity cache gồm config, params, seed, kind, energy window, adapter version và native fitness id.
- Local checkpoint pickle chỉ được đọc từ trusted study directory; không có network input, secret hoặc command construction mới.

## Artefact và số liệu smoke

Canonical run `acaco-v2-v6-check-261014-verified` hoàn tất 3 trial × 3 vòng × 2 seeds trong 7,407 giây, tổng 720 full candidate evaluations. Provenance của toàn bộ source/harness hiện tại khớp artefact, không có drift.

- Baseline reported: `0.04620775637117039 J`.
- Proposal 1: `0.04567106912479005 J`, thấp hơn baseline `1,161%`.
- Proposal 2: `0.04448217877816456 J`, thấp hơn baseline `3,734%`.

Đây là pipeline output trên một map với hai development seeds. Hai proposals không tạo ước lượng generalization, confidence interval, lifetime gain hay bằng chứng rằng từng coordinate gây cải thiện. TPE cũng chưa có đủ trial để được xem là parameter optimization khoa học.

## Xác minh

- Canonical JUnit cuối: **89 passed / 89**, 20,66 giây; gồm test adapter/smoke mới và targeted AC-ACO/research/integration suite.
- Tests mới kiểm tra exact preset, khóa budget/objective/operators, search ranges, checkpoint/RNG resume, invalid scope/output, controller D guard, actual exported smoke, baseline-failure và timeout termination.
- Existing `optimizer/tests/test_optimizer.py` không nằm trong validation này vì repository thiếu legacy fixture có sẵn; task không tạo dữ liệu lịch sử giả để ép suite xanh.
- `optuna 4.6.0` và `psutil 7.2.2` được cài trong interpreter hiện tại; versions được ghi trong provenance. Dependency manifest đã pin Optuna và khai báo psutil từ trước.

## Khuyến nghị

Giữ nguyên production preset. Nếu người dùng muốn tối ưu thật, cần một protocol mới được phê duyệt: nhiều topology development độc lập, holdout topology/seeds chưa dùng, ngân sách đủ lớn, phân tích feasibility/runtime và sau đó mới chạy lifetime. Không dùng proposal 2 của smoke làm “winner” hoặc default.
