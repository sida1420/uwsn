# Điều tra hiệu năng AC-ACO

## Tóm tắt

- **Hiện tượng:** AC-ACO chạy hàng nghìn round, mỗi round dựng nhiều cây ứng viên; 500 round đầu của seed 39 mất 181,6 giây trên máy đo.
- **Nút thắt chính:** vòng tính xác suất chuyển CH trong `_transition_probabilities`; 0,298/0,374 giây (80%) của round đầu theo `cProfile`.
- **Nguyên nhân:** mỗi round thử 40 kiến, mỗi kiến chọn 20 CH. Với 100 node sống, có 760 bước chuyển và 68.400 lượt duyệt ứng viên. Mỗi lượt gọi `E_m` và nhiều phép `log`, `exp`, kiểm tra số trong Python. `E_m` phụ thuộc khoảng cách tĩnh nhưng được tính lại.
- **Trạng thái lúc đo:** các số liệu trên là baseline trước khi sửa mã nguồn; kết quả triển khai nằm ở phần cuối báo cáo.

## Đường thực thi

`Simulator.run` → `ACACO.plan_round` → tối đa 40 kiến × 10 thử/kiến → `create_clusters` → `_construct_candidate` → `_transition_probabilities` → `build_clusters` → `dropping_member_multi_hop_routing` → `Evaluator.energy_consumption` → `post_round`.

Mỗi kiến dừng retry ngay khi có route hợp lệ. `build_clusters` luôn trả bộ dữ liệu cụm và outlier trong trường hợp hiện tại; retry chủ yếu do routing thất bại.

## Bằng chứng

### Hồ sơ round đầu

Map hiện tại: 100 node, bán kính 200 m; `T_max=3000`, seed 39, 40 kiến, 20 CH/kiến. `cProfile` của `plan_round` đầu tiên:

| Hàm | Số lần gọi | Thời gian cộng dồn |
|---|---:|---:|
| `plan_round` | 1 | 0,374 s |
| `create_clusters` | 40 | 0,335 s |
| `_construct_candidate` | 40 | 0,308 s |
| `_transition_probabilities` | 760 | 0,298 s |
| `Evaluator.E_m` | 68.400 | 0,095 s |
| `build_clusters` | 40 | 0,027 s |
| `dropping_member_multi_hop_routing` | 40 | 0,024 s |
| `energy_consumption` | 40 | 0,008 s |
| `post_round` | 1 | 0,007 s |

Thời gian `E_m`, `build_clusters` nằm trong thời gian của hàm gọi cấp trên; không cộng các hàng với nhau. `math.log` được gọi 205.200 lần. `_update_pheromone` mất 0,006 s, không phải nút thắt chính ở map này.

### 500 round liên tiếp

Chạy seed 39 với trạng thái năng lượng cập nhật sau mỗi round, dừng phép đo tại mốc 500:

| Mốc | Thời gian tích lũy | Node sống | Số thử mới | Route lỗi mới |
|---|---:|---:|---:|---:|
| 250 | 89,912 s | 100 | 10.000 | 0 |
| 500 | 181,632 s | 100 | 10.000 | 0 |

Trong 500 round này mỗi kiến thành công ngay lần đầu; retry không giải thích độ chậm. Tệp `runs/2026093009_39_AC-ACO.csv` của lần chạy trước có 2.182 round: 1.476 round còn 100 node, 705 round còn 99 node, 1 round còn 98 node. Vì vậy khối lượng tính CH gần như không giảm theo thời gian. CSV chỉ ghi các round hoàn tất, không chứng minh lý do dừng sau round 2181.

### Đối chứng cache và NumPy

- Tra cứu `E_m` từ bảng tính sẵn theo khoảng cách: khoảng 1,05 so với 1,42 giây CPU cho 10 round đầu trong một cặp đo; cặp đo sau là 2,45 so với 3,56 giây. Chi phí năng lượng giống nhau. Tốc độ máy dao động rõ rệt, nên chỉ xem đây là dấu hiệu, không phải mức tăng tốc bảo đảm.
- Bọc `E_m` bằng `functools.lru_cache`: 1,36 triệu hit / 4.950 miss qua 20 round nhưng chậm hơn baseline trong phép đo. Không nên mặc định chọn cách này.
- Cô lập một lần `_transition_probabilities` với dữ liệu round đầu trên Python 3.12, NumPy 2.5.3: 2.000 lần gọi mất 0,2656 giây CPU bằng Python hiện tại, 0,0312 giây bằng NumPy với ma trận khoảng cách và `E_m` đã chuẩn bị. Sai khác xác suất lớn nhất `3,47e-18`.
- Một round đầy đủ trên cùng Python 3.12: code hiện tại 0,125 giây CPU; bản NumPy thử nghiệm trong bộ nhớ 0,0469 giây (lặp hai lần), năng lượng tổng round đầu giống nhau. **Số đo chưa gồm chi phí tạo các mảng tĩnh và chưa xác nhận tốc độ toàn bộ 2.182 round.** Phép đo 20 round bị dao động tốc độ CPU lớn, không đủ tin cậy để suy ra tỷ lệ tăng tốc dài hạn.

## Kết luận và đề xuất

1. **Ưu tiên:** giữ chi phí cạnh tĩnh (`E_m`, tốt hơn là `log(E_m)`) trong ma trận tính một lần khi khởi tạo; tránh gọi mô hình acoustic trong vòng duyệt ứng viên. Dùng tra cứu mảng trực tiếp thay cho cache bọc hàm.
2. **Có cơ sở dùng NumPy:** vector hóa toàn bộ phép tính xác suất trên tập node còn lại, chuẩn bị `dist_matrix`, chi phí cạnh, pheromone và residual dưới dạng mảng. Chỉ đổi kiểu ma trận nhưng vẫn lặp từng ứng viên trong Python sẽ không xử lý được nút thắt. Cần đồng bộ pheromone sau mỗi round và giữ quy tắc seed/tie-break khi so sánh kết quả.
3. **Đo sau khi sửa:** benchmark cùng map, seed, interpreter, số round, số lần thử, tổng năng lượng và trạng thái node; đo riêng chi phí khởi tạo và toàn bộ run. Thêm khai báo dependency nếu đưa NumPy vào mã chính. Sau đó mới xem xét tối ưu routing/clustering vì chúng hiện chiếm ít thời gian hơn.

## Kết quả triển khai

- Đã tính sẵn `log(E_m)` từ khoảng cách đã chặn tối thiểu `1e-12`, và dùng NumPy tính xác suất theo mảng. `residual_e` vẫn truyền tường minh vào hàm chọn CH dưới dạng mảng snapshot của round.
- Đối chứng độc lập 5 lần, cùng Python 3.12, map và seed 39: một round từ 0,125194 xuống 0,050634 giây CPU (**2,47 lần** cho thực thi); gồm cả khởi tạo từ 0,125252 xuống 0,059861 giây CPU (**2,09 lần**). CH path và năng lượng round đầu giống nhau.
- Đối chiếu 500 round đầu với CSV lịch sử seed 39: năng lượng từng round và số node sống đều khớp; 20.000 lần thử, 0 lỗi routing. Bốn unit test và một phép chạy `Simulator.run` hai round đều qua.
- Test riêng hai node trùng vị trí và chi phí điện tử bằng 0 xác nhận chi phí cạnh tính sẵn giữ đúng quy tắc chặn khoảng cách. `requirements.txt` khai báo NumPy cùng các dependency mô phỏng hiện có.

## Câu hỏi còn mở

- Mục tiêu thời gian chạy cho một map/seed và số map cần benchmark là bao nhiêu?
- Các cấu hình map lớn hơn hoặc nhiều routing failure có thể đổi nút thắt; chưa đo trường hợp đó.
