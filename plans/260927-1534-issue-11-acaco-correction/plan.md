---
title: "Sửa AC-ACO theo issue #11 và nguồn gốc"
description: "Đối chiếu issue, slide và bài báo gốc; sửa AC-ACO để dùng thuật toán có nguồn, tái sử dụng routing chung và kiểm chứng trên UWSN 3D."
status: completed
priority: P1
effort: 10h
issue: 11
branch: main
tags: [bugfix, algorithms, clustering, routing]
created: 2026-09-27
---

# Plan sửa issue #11: AC-ACO model inaccuracy

## Mục tiêu và ranh giới

Sửa implementation `src/algorithms/ac_aco` theo [issue #11](https://github.com/sida1420/uwsn/issues/11), dùng bài báo Zhou, Chen, Cao (2025), DOI [10.32604/cmc.2025.065561](https://doi.org/10.32604/cmc.2025.065561) làm nguồn thuật toán chính. File [`IT4906_WSN_final.pptx`](../../IT4906_WSN_final.pptx) là bản thuyết trình về paper, không phải đặc tả độc lập. Tích hợp vào UWSN acoustic 3D của repo; không tuyên bố tái tạo chính xác kết quả WSN radio 2D của bài báo.

**Quy tắc ưu tiên nguồn:** (1) issue #11 cho yêu cầu sửa và giá trị được chỉ định; (2) phương trình và Algorithm 1 của bài báo cho ngữ nghĩa; (3) slide cho bối cảnh; (4) code cũ chỉ cho interface/repo conventions. Gặp mâu thuẫn thì ghi quyết định, không âm thầm ghép mô hình. Chi tiết tại [đối chiếu nguồn](./source-audit.md).

## Kết quả phải đạt

- AC-ACO chọn đúng số CH mục tiêu từ node sống, dựng candidate theo xác suất pheromone/heuristic/energy có nguồn, áp dụng logistic và ba lịch thích ứng; không còn `_transition_log_weight`, `_repair_coverage`, `_assign_members`, objective và cây route riêng không phù hợp issue.
- Mỗi candidate đi qua `build_clusters()` và `multi_hop_routing()` hiện có; chỉ cây **đủ node, không chu trình, mọi cạnh ≤ radius, tới base** mới được chấm bằng `Evaluator`. `None` khi mạng thật sự không có route hợp lệ.
- Tham số issue được phân loại thành: AC-ACO sử dụng, cấu hình simulator chung, hoặc chỉ thuộc profile WSN radio. Không để tham số công bố nhưng không dùng; không sửa đại trà năng lượng acoustic của các algorithm khác.
- Test có seed và fixture nhỏ chứng minh xác suất, schedule, pheromone, routing, năng lượng một lần/round; tài liệu nói rõ khác biệt WSN/UWSN và những điều paper không đặc tả.

## Các pha theo thứ tự

| Pha | Việc chính | Ước lượng | Trạng thái |
|---|---|---:|---|
| 1 | [Chốt đặc tả và baseline](./phase-01-spec-and-baseline.md) | 2h | Completed |
| 2 | [Dọn interface, tham số và routing chung](./phase-02-parameters-and-shared-routing.md) | 2.5h | Completed |
| 3 | [Sửa lõi tối ưu AC-ACO](./phase-03-acaco-algorithm.md) | 3.5h | Completed |
| 4 | [Kiểm thử, tích hợp, tài liệu](./phase-04-verification-and-docs.md) | 2h | Completed |

## Chỉ dẫn cho GPT-5.6 Terra low

Đọc `source-audit.md` và **toàn bộ 4 phase file theo thứ tự** trước khi sửa. Mỗi bước chỉ thay file đã nêu; sau mỗi pha chạy test liên quan, ghi lại kết quả vào checkbox/ghi chú pha. Giữ thay đổi của người dùng; file PPTX đang untracked, chỉ đọc. Không dùng số liệu slide 49–58 làm expected output. Không đổi `map.pkl`, `radius`, `Simulator` hoặc model acoustic để ép kết quả tốt. Khi phương trình thiếu thông số (cửa sổ `E_total`, điều kiện hội tụ, `L_best`), dùng lựa chọn tối thiểu được mô tả trong pha và ghi là adaptation; dừng ở chỗ thiếu dữ kiện nếu lựa chọn khác làm đổi kết luận khoa học.

## Điều kiện hoàn tất

`python -B -m unittest discover -s tests -v` (dùng `C:\Users\LOQ\miniconda3\python.exe` trên máy này) qua các test liên quan, `-m compileall -q src` thành công; test baseline ngoài phạm vi phải được sửa nếu chạm shared routing hoặc báo rõ lý do còn fail. Review thủ công các invariant route/energy; chạy smoke trên fixture và map hiện tại. Graph `map.pkl` có 100/100 node kết nối tới base qua multi-hop, nên `None` ở round 0 cần được điều tra, không được gán cho topology rời rạc. Không benchmark/đóng issue dựa trên “tăng lifetime” khi chưa có protocol thử nghiệm tương đương.

## Cách bắt đầu thực thi

`$ck:cook C:\Users\LOQ\Desktop\uwsn\plans\260927-1534-issue-11-acaco-correction\plan.md`

## Câu hỏi còn mở

1. Có cần thêm profile **tái lập WSN 2D radio** riêng không? Mặc định plan chỉ sửa AC-ACO trong UWSN 3D.
2. Issue ghi `hopping_factor=0.4` nhưng lại ghi biên `[0.67, 0.9]`; giữ `0.4` của shared router cho đến khi có công thức/ý định rõ.
3. Paper không định nghĩa `L_best=1000`, cách tính fitness cụ thể và cửa sổ `E_total`; plan nêu adapter tối thiểu, không gắn nhãn “tái lập paper” cho các phần này.
