# Bài báo D-ACO: cần những đồ thị và môi trường mô phỏng nào

Tổng hợp từ các bài báo đã đọc về clustering/routing cho mạng cảm biến dưới nước (UWSN) và WSN dùng ACO/metaheuristic. Mục đích: xác định một bài về **D-ACO** (ACO chọn cluster head theo mật độ lưới + fitness năng lượng/tải, định tuyến đa chặng 3-D) cần những hình gì và cấu hình môi trường ra sao để đạt chuẩn tạp chí Q1/Q2.

Theo yêu cầu, kế hoạch **không thêm thí nghiệm nhiều seed**: mỗi kịch bản dùng một map cố định.

> **Lưu ý về phạm vi**:
> - Nội dung dưới đây dựa trên các bài đọc được toàn văn hoặc trích đoạn qua web (mục 6), không phải khảo sát hệ thống.
> - Hạng Q1/Q2 ghi theo hiểu biết chung về tạp chí, chưa tra lại SJR/JCR cho từng năm.
> - Một số bài (PB-ACR, ACAR, MDPI Algorithms 2020, Sensors 2022 PMC8876173) chỉ đọc được tóm tắt. Thông tin về chúng chỉ dùng để định hướng.

---

## 1. Các bài đã đọc và điều chúng báo cáo

| Bài | Tạp chí (năm) | Môi trường mô phỏng | Hình / chỉ số chính | Baseline |
|---|---|---|---|---|
| EECMR – Energy-Efficient Clustering Multi-Hop Routing in a UWSN | *Sensors* 21(2):627 (2021) | 3-D **500×500×500 m**, 50–450 node, 1 sink ở **tâm mặt nước**, E0 = 5 J, tầm 150 m và 200 m, gói 200 bit, **30 kHz**, Thorp, 1000 round, node trôi 1–3 m/s | Topology sau clustering (CH / member / relay); số node chết theo round và theo N; năng lượng dư trung bình; số gói nhận ở sink. Mỗi hình có 2 tầm liên lạc × (theo round, theo N) | LEACH, DBR, EERBLC |
| MCR-UWSN – Metaheuristic Clustering with Routing for UWSN | *Sensors* 22(2):415 (2022) | 3-D L×L×L, 300–500 node; mô hình năng lượng E_elec, E_DA = 5 nJ/bit | Số node sống theo round; **FND/HND/LND**; tổng năng lượng tiêu thụ theo round; số round đến khi cạn năng lượng; số gói nhận | LEACH, **LEACH-ANT**, CUWSN, EOCA, **ACOCR** (2 baseline dùng ACO) |
| HDLCA – Hunger Driven Lion Clustering | *Scientific Reports* 15:33292 (2025) | 3-D, 100–300 node, sink ở tâm, E0 = 5 J (đồng nhất) / ngẫu nhiên (không đồng nhất), gói 200 bit, tầm 150 m, 30 kHz, hệ số lan truyền k = 2 | Deployment, clustering, routing; năng lượng dư trung bình theo round; số node chết theo round; năng lượng truyền mỗi round; throughput; **số round theo bán kính cluster**; **số round theo N (100–300)**; mạng đồng nhất / không đồng nhất; môi trường có nhiễu; thời gian tính & độ phức tạp | EECMR, EERBLC, LEACH, K-means |
| WOA – Walrus Optimization CH selection for UWSN-IoT | *Frontiers in Communications and Networks* 7 (2026) | 500×500 m², 100/200/300 node, E0 = 1 J, 5–10 % CH, 3000 round | Lifetime theo N; throughput theo N; năng lượng dư theo round; thời gian ổn định (FND) theo N; **FND/HND/LND** theo thuật toán | ZFO-SHO, TIOCHR, M-PSO |
| MACOA – modified ACO for WSN | *EURASIP JWCN* (2025) – chỉ đọc bảng | — | **Bảng độ nhạy tham số ACO**: α, β, q₀, ρ thích nghi, 30–90 kiến, 100 vòng lặp | — |
| PB-ACR – Priority-based ACO cooperative routing for UWSN | *IEEE Access* 9 (2021) – chỉ đọc tóm tắt | — | Throughput, năng lượng tiêu thụ, **cân bằng năng lượng / energy hole**, độ phức tạp | ACAR |
| ACAR – ant colony routing for UWASN | *IET Communications* (2020) – chỉ đọc tóm tắt | Pheromone kết hợp thông tin độ sâu | Lifetime, tỉ lệ gửi gói thành công, độ trễ | — |

**Các điểm chung nhất:**
- Mô phỏng 3-D, sink ở tâm mặt nước.
- Tần số 30 kHz, mô hình hấp thụ Thorp, gói 200 bit.
- Lifetime đo bằng **FND/HND/LND**.
- Có đường cong theo round cho node sống/chết, năng lượng dư/tiêu thụ và throughput.
- Có thí nghiệm **scalability theo số node** và **theo tầm liên lạc / bán kính cluster**.

---

## 2. Danh sách hình cần có cho bài D-ACO

✅ = làm được ngay từ log/mã hiện có; 🟡 = cần thêm ghi log hoặc chạy thêm; ❌ = cần viết thêm mã.

### A. Mô hình hệ thống (bắt buộc – cả 4 bài đầy đủ đều có)

| # | Hình | Nội dung | Trạng thái |
|---|---|---|---|
| A1 | System model | Sơ đồ UWSN 3-D: sink mặt nước, CH, member, relay, cạnh định tuyến đa chặng | ❌ sơ đồ vẽ tay/TikZ |
| A2 | Network deployment | 3-D + hình chiếu (top/side), tầm sink | ✅ `image/log_figures/*_network_topology.png` |
| A3 | Clustering & routing result | Một round của D-ACO: CH, member, relay, các hop tới sink | 🟡 `src/visual.py` vẽ được cây route; cần script xuất 1 round |
| A4 | Lưới mật độ (đặc thù D-ACO) | Lưới 3-D và mật độ phủ để minh hoạ heuristic mật độ — điểm mới cần làm nổi bật | 🟡 lấy `Grid.density` từ `DACOClustering` |
| A5 | Flowchart D-ACO | Calibration → kiến dựng tập CH → routing → fitness → deposit/evaporation | ❌ sơ đồ |

### B. Network lifetime (bắt buộc)

| # | Hình | Trạng thái |
|---|---|---|
| B1 | Alive (hoặc dead) nodes vs. round, đánh dấu FND | ✅ `*_network_lifetime_fnd.png` |
| B2 | FND / HND / LND theo thuật toán (bảng + biểu đồ cột/đường) | 🟡 Hiện chỉ có FND; HND/LND **chưa đạt** trong 3,500 round (xem mục 4) |
| B3 | Lifetime (FND, HND, LND) vs. số node | 🟡 Có FND (500³: N = 50–200); thiếu HND/LND |
| B4 | Lifetime vs. tầm liên lạc / bán kính cluster (EECMR: 150/200 m; HDLCA: theo bán kính) | 🟡 chạy thêm với `radius` = 150/200/250 m |
| B5 | Lifetime theo kiểu triển khai (clustered / uniform / normal) | ✅ `500_500_500_100_fnd_by_deployment.png` |

### C. Năng lượng (bắt buộc)

| # | Hình | Trạng thái |
|---|---|---|
| C1 | Năng lượng tiêu thụ tích lũy vs. round | ✅ `*_cumulative_energy_consumption.png` |
| C2 | Năng lượng dư (tổng hoặc trung bình mỗi node) vs. round | ✅ `*_residual_energy.png` |
| C3 | Năng lượng tiêu thụ mỗi round | ✅ `*_energy_per_round.png` |
| C4 | **Cân bằng tải**: phân bố năng lượng theo sensor / phương sai năng lượng dư — đây là luận điểm chính của fitness tải/mật độ của D-ACO (PB-ACR nhấn mạnh energy hole) | ✅ `*_sensor_energy_distribution.png`; 🟡 thêm phương sai năng lượng dư theo round |
| C5 | Năng lượng vs. số node | ✅ `*_total_energy_vs_number_of_nodes.png` |

### D. Hiệu năng truyền dữ liệu (hầu hết các bài đều có)

| # | Hình | Trạng thái |
|---|---|---|
| D1 | Số gói nhận ở sink (throughput) vs. round | 🟡 Mô phỏng đòi hỏi mọi node sống đều có trong cây route ở mỗi round khả thi, nên số gói cảm biến tới sink ở round r = `alive_nodes(r)`. Throughput tích lũy = Σ alive_nodes. Tính được từ log, nhưng cần ghi rõ giả định không mất gói. |
| D2 | Throughput vs. số node | 🟡 như D1 |
| D3 | PDR / độ trễ | ❌ Mô hình hiện tại không mô phỏng mất gói hay thời gian truyền. Nên nêu là giới hạn thay vì vẽ. |

### E. Hình đặc thù của thuật toán ACO (tạp chí Q1 thường yêu cầu)

| # | Hình | Trạng thái |
|---|---|---|
| E1 | Hội tụ: fitness tốt nhất / trung bình trong một round (theo số kiến) hoặc qua các round | 🟡 cần ghi `fitness` các candidate trong `DACO.plan_round` |
| E2 | Độ nhạy tham số: α, β, γ (mật độ), ρ, số kiến, CH_proportion → FND và năng lượng | 🟡 chạy lại với `DACOParameters` khác nhau (MACOA trình bày dạng bảng) |
| E3 | Ablation: D-ACO không có thành phần mật độ (γ = 0), không có fitness tải (load_density_weight = 0) | 🟡 chỉ cần đổi tham số. **Rất nên có**, vì chứng minh đóng góp của từng thành phần. |
| E4 | Số CH mỗi round | 🟡 log hiện chưa có. Script `image/scripts/run_experiments.py` đã ghi được cột `num_cluster_heads`. |
| E5 | Thời gian tính mỗi round vs. số node (độ phức tạp) | ✅ `*_runtime_vs_number_of_nodes.png` + phân tích O(·) trong bài |

### F. Bảng (bắt buộc)

1. Bảng tham số mô phỏng (mục 3).
2. Bảng tham số thuật toán (D-ACO và các baseline).
3. Bảng FND/HND/LND.
4. Bảng năng lượng: tích lũy tại round cố định, năng lượng khi FND, phần trăm năng lượng đã dùng.
5. Bảng thời gian tính và độ phức tạp.

**Tối thiểu cho một bài Q2:** A1, A2, A5, B1, B2, B3, C1, C2, C4, D1, E3, E5 và các bảng F.
**Nên thêm cho Q1:** A3, A4, B4, B5, D2, E1, E2.

---

## 3. Môi trường mô phỏng đề xuất

Đối chiếu với tham số trong `src/hparameter.py` / `src/map_gen.py` và với các bài trên. Mỗi kịch bản dùng **một map cố định, seed 46** — đây là seed của map gốc `map.pkl` và của phần lớn log. Không quét nhiều seed.

| Tham số | Giá trị trong repo | Trong các bài | Đề xuất cho bài D-ACO |
|---|---|---|---|
| Không gian | 500×500×500 m (+300³, 800³ trong log) | EECMR: 500³ m; HDLCA: 3-D | **500×500×500 m** làm kịch bản chính |
| Số node | 50–250 | 50–450 (EECMR), 100–300 (HDLCA, WOA) | **50, 100, 150, 200, 250** |
| Sink | 1, tâm mặt nước (250, 250, 0) | Tâm mặt nước (EECMR) | Giữ nguyên |
| Kiểu triển khai | clustered (5 tâm), uniform, normal | Ngẫu nhiên đều | Chính: clustered; phụ: uniform, normal (B5) |
| Tầm liên lạc | 200 m | 150 m và 200 m (EECMR), 150 m (HDLCA) | **150 / 200 / 250 m** (B4) |
| Năng lượng ban đầu E0 | 0.6 J | 5 J (EECMR, HDLCA), 1 J (WOA) | Giữ 0.6 J hoặc dùng 5 J (xem mục 4) |
| Tần số / hấp thụ | 30 kHz, Thorp | 30 kHz, Thorp (EECMR, HDLCA) | Giữ nguyên |
| Hệ số lan truyền k | 1.5 (thực tế) | 1, 1.5, 2 | 1.5 |
| Gói tin | 200 bit, 10 kbps | 200 bit | Giữ nguyên |
| E_elec / E_DA | 50 nJ/bit / 5 nJ/bit | E_DA = 5 nJ/bit | Giữ nguyên |
| Tỉ lệ CH | 0.2 (D-ACO) | 5–10 % (WOA) | Giữ 0.2 và đưa vào phân tích độ nhạy (E2) |
| Số round tối đa | 3,500 | 1,000–3,000 | **Đủ dài để đạt LND** (mục 4) |
| Baseline | AC-ACO, SimpleACO, NodeACO, PSO | LEACH, LEACH-ANT, DBR, EERBLC, EECMR, ACOCR, K-means | Giữ 4 baseline hiện có. **Nên thêm LEACH** (bài nào cũng có); EECMR/DBR nếu cài được. |

Tóm tắt các kịch bản (không có trục seed) ở `paper/experiment_matrix.json`.

---

## 4. Những điểm bài báo sẽ bị phản biện hỏi (phát hiện từ log hiện có)

1. **HND/LND chưa quan sát được.** Mọi bài đều báo cáo FND/HND/LND, nhưng log hiện tại có hai trở ngại:
   - T_max = 3,500 round, trong khi ở 500³ N=100 mới dùng 49–83 % năng lượng.
   - Simulator **dừng cả mạng** khi một node mất đường định tuyến.

   Cần:
   - (a) tăng T_max;
   - (b) chọn và nêu rõ định nghĩa: tiếp tục mô phỏng và coi node mất kết nối là "disconnected" (`image/scripts/run_experiments.py` đã có chế độ extended này), hoặc định nghĩa lifetime theo kết nối.
2. **800³ m không có round khả thi nào** với tầm 200 m. Hoặc bỏ kịch bản này, hoặc dùng nó để minh hoạ giới hạn kết nối.
3. **E0 = 0.6 J** nhỏ hơn nhiều so với 5 J trong EECMR/HDLCA. Không sai, nhưng cần nêu lý do, hoặc chạy lại với 5 J để dễ so sánh với các bài đó.
4. **Thiếu LEACH** — baseline gần như bắt buộc trong các bài đã đọc.
5. **Đánh đổi cân bằng tải**: log cho thấy D-ACO tiêu ít năng lượng nhất ở 7/10 cấu hình, nhưng CV năng lượng theo sensor của nó cao hơn AC-ACO/SimpleACO/NodeACO ở 9/10 cấu hình. Fitness của D-ACO có thành phần tải/mật độ, nên phản biện sẽ hỏi điểm này. Cần thảo luận và có ablation (E3).
6. **Tái lập kết quả**: log D-ACO/AC-ACO không tái tạo được từng bit trên Linux (`image/log_figures/experiment_report.md`, mục 4). Nên ghi rõ nền tảng/phiên bản khi chạy kết quả cuối cho bài báo.

---

## 5. Thứ tự thực hiện đề xuất

1. Chốt định nghĩa lifetime (mục 4.1) và T_max.
2. Chạy kịch bản chính 500³ clustered với N = 50–250. Dùng `image/scripts/run_experiments.py`, đã ghi sẵn năng lượng dư, số CH, số node kết nối/mất kết nối.
3. Chạy kịch bản tầm liên lạc (150/200/250 m) và kiểu triển khai (uniform/normal) ở N = 100.
4. Chạy ablation và độ nhạy tham số cho D-ACO (E2, E3).
5. Vẽ bằng các script hiện có:
   - `image/scripts/plot_results.py` cho dữ liệu chạy mới;
   - `image/scripts/plot_logs.py` cho log dạng `run.py`.

   Style chung ở `image/scripts/plot_style.py` theo ảnh mẫu.

---

## 6. Nguồn

- [EECMR – Energy-Efficient Clustering Multi-Hop Routing Protocol in a UWSN, *Sensors* 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7831061/)
- [MCR-UWSN – An Efficient Metaheuristic-Based Clustering with Routing Protocol for UWSN, *Sensors* 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8779958/)
- [HDLCA – Hunger driven lion clustering algorithm for UWSN, *Scientific Reports* 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12475414/)
- [WOA cluster head selection for UWSN-based IoT, *Frontiers in Communications and Networks* 2026](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2026.1783248/full)
- [MACOA parameter sensitivity table, *EURASIP JWCN* 2025](https://jwcn-eurasipjournals.springeropen.com/articles/10.1186/s13638-025-02449-w/tables/5)
- [PB-ACR, *IEEE Access* 2021 (abstract)](https://doaj.org/article/7b1d50184be44b82a1a57c5a4e050397)
- [ACAR – ant colony routing for UWASN, *IET Communications* (abstract)](https://digital-library.theiet.org/content/journals/10.1049/iet-com.2020.0160;jsessionid=529er6d31lggw.x-iet-live-01)
- [Improved Metaheuristics-Based Clustering with Multihop Routing for UWSN, *Sensors* 2022 (chưa đọc được toàn văn)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8876173/)
- [Improved-ACO clustering routing for underwater sensor networks, *Algorithms* 2020 (chưa đọc được toàn văn – HTTP 403)](https://www.mdpi.com/1999-4893/13/10/250)
- [Residual-energy CH selection (định nghĩa stability = FND, lifetime FND→LND), arXiv](https://arxiv.org/pdf/1902.01445)
