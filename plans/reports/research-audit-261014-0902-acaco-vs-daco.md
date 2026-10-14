# Kiểm toán nghiên cứu AC-ACO và D-ACO trong repository hiện tại

Ngày: 14/10/2026, Asia/Bangkok. Repository: `C:\Users\LOQ\Desktop\uwsn`. Git HEAD: `0f89c484dbd7997413167ab9759779650913a271`.

Phạm vi: **chỉ đọc mã nguồn, cấu hình và dataset**. Chỉ tạo báo cáo, hai script chẩn đoán và JSON kết quả trong `plans/reports/`. Không sửa thuật toán, generator, notebook, tests hoặc map; không chạy full lifetime, optimizer campaign, commit hay push. Snapshot SHA-256 của mọi file `src/**/*.py` và `map.pkl` được ghi và xác nhận không đổi qua chẩn đoán tại `plans/reports/acaco-daco-audit-261014-0902/diagnostics.json:2136`.

Quy ước bằng chứng: **[MÃ]** quan sát trực tiếp source; **[THỰC NGHIỆM]** phép đo đã chạy hoặc tính lại từ dữ liệu; **[SUY LUẬN]** hệ quả toán học, chưa tự chứng minh tác động lifetime. Line numbers áp dụng cho checkout này; notebook dùng line của file JSON, không phải execution count.

## 1. Executive verdict

| Câu hỏi | Phán quyết | Căn cứ và giới hạn |
|---|---|---|
| AC-ACO hiện được cài đặt đúng? | **PARTIALLY VERIFIED** về nội bộ; **NO** nếu hiểu là bản tái lập nguyên vẹn paper | Transition, logistic, schedules, selection minimum, cập nhật state và evaluator nhất quán với biến thể UWSN được mô tả. Deposit ordering và outer lifecycle là những khác biệt cần công bố. Không phát hiện lỗi dấu, chuẩn hóa hoặc fitness đảo chiều trên đầu vào hợp lệ đã kiểm tra. `src/algorithms/ac_aco.py:40-115`; `src/algorithms/clustering/ac_aco/ac_aco.py:28-67,131-184,219-296`. |
| D-ACO đúng trong phạm vi đã xác minh? | **PARTIALLY VERIFIED** | Fitness, reference, coverage và winner/deposit dùng cùng score nhất quán; 13 D-ACO tests đạt. Chưa tìm thấy paper/đặc tả gốc có thẩm quyền cho D-ACO này. `src/algorithms/d_aco.py:70-119`; `src/algorithms/clustering/d_aco/fitness.py:15-33`. |
| Giải thích mạnh nhất cho bất lợi lifetime tiềm tàng của AC? | **STRUCTURAL LIMITATION: objective không trực tiếp bảo vệ residual depletion** | AC mặc định chọn minimum tổng chi phí round; D phạt `(cost_i/residual_i)^2.6 / density_i`. Cơ chế khác biệt đã chứng minh, nhưng tỷ lệ đóng góp vào lifetime gap hiện tại chưa đo được. `src/algorithms/ac_aco.py:103-115`; `src/algorithms/clustering/d_aco/fitness.py:25-33`. |
| Có khoảng cách năng lượng trên current source/map không? | **YES trong chẩn đoán ngắn** | Ba algorithm seeds, mỗi run 10 round: AC tiêu hao trung bình cao hơn D **6,6569%**, cùng physics và full service. Không có node chết. Đây không phải phép đo lifetime. JSON `diagnostics.json:105-150`, mục 6. |
| Có đủ bằng chứng về gap lifetime lớn trong đối chứng current công bằng không? | **INSUFFICIENT EVIDENCE** | Không có cohort full lifetime khớp current map/source/defaults. Historical maps và tham số khác; notebook có lỗi alive-curve và thiếu pairing/provenance. `plans/analysis/optimizer-results.md:5`; `plans/analysis/acaco-performance.md:3-7,134`; `src/analyze.ipynb:143-161,414-427`. |
| D được simulator ưu đãi riêng không? | **NO trong đường thực thi đã đọc** | AC và D dùng cùng router/evaluator, cùng trừ năng lượng và termination. Tuy nhiên D có calibration thêm và có lịch sử tuning riêng; so sánh defaults không chứng minh ưu thế intrinsic của algorithm. `src/algorithms/ac_aco.py:58-75`; `src/algorithms/d_aco.py:65-97`; `src/run.py:56-99`; `optimizer/README.md:54-57`. |

**Kết luận trọng tâm:** không có cơ sở để nói “AC-ACO kém vì một lỗi chaos” hoặc “D-ACO đúng vì điểm cao hơn”. Chênh lệch năng lượng đầu run được tái hiện; nguyên nhân lifetime cần tách objective, sampling/reinforcement, tuning và chất lượng đo lường. Bỏ riêng disturbance trong transition làm năng lượng đầu run **tăng 2,7456%**; giả thuyết “chaos có hại nên bỏ đi” không được chẩn đoán hiện tại ủng hộ. `diagnostics.json:2071-2135`.

## 2. Algorithm reconstruction

### 2.1. Reconnaissance và execution trace

Đã đọc complete AC/D wrappers, clustering/support/parameters; SimpleACO, PSO, NodeACO; network/node/point; map generator; router; evaluator; simulator; runner; notebook loader/metrics; optimizer adapters, trajectory, fitness aggregation và search policy; maintained tests và các báo cáo/CSV lịch sử liên quan. Tìm call sites bằng `rg` trong `src`, `optimizer`, `tests`. Memory AGENTS ban đầu về direct routing, không có tests và radius 100 không còn mô tả current implementation.

| Giai đoạn | Đường thực thi AC-ACO | Đường thực thi D-ACO |
|---|---|---|
| Experiment → map | `src/run.py:69-73` → `src/network.py:40-56` | Giống AC |
| Configuration | `src/hparameter.py:9-29`; `src/algorithms/clustering/ac_aco/parameters.py:12-37` | HyperParameters chung; `src/algorithms/clustering/d_aco/parameters.py:8-27` |
| Seed/instance | `src/run.py:74-90,56-60`; `src/algorithms/base/base.py:108-123` → AC constructor `src/algorithms/ac_aco.py:28-38` | Base constructor → `src/algorithms/d_aco.py:27-39` |
| Initial state | Tau NxN, edge cache, chaos, iteration 0 tại `src/algorithms/clustering/ac_aco/ac_aco.py:100-127` | Grid/node tau tại `src/algorithms/clustering/d_aco/d_aco.py:115-129`; references None tại wrapper `src/algorithms/d_aco.py:36` |
| Pre-search | One physical-round clock, filtered live và schedules: AC clustering `:131-153` | Throwaway calibration wrapper `:82-97`; evaporation, density, distinct starts D clustering `:133-146` |
| CH decision | AC wrapper `:46-55` → AC clustering `:204-258` | D wrapper `:106-107` → D clustering `:167-218` |
| Assignment → routing | `src/algorithms/clustering/clustering.py:5-37` → `src/algorithms/routing/routing.py:110-193`; AC wrapper `:58-68` | Cùng functions; D wrapper `:65-67` |
| Candidate cost/fitness | Evaluator AC wrapper `:73-85`; selection `:103-115` | Evaluator D wrapper `:70-77`; score/winner `:110-118` |
| Memory update | Ant deposit AC wrapper `:80`; AC post-round `:165-184,262-296` | Live node deposit D wrapper `:111`; elite/reference `:117-118`; D clustering `:220-249` |
| Execute selected tree | `src/simulate.py:38-63`: consumption returned hoặc evaluator fallback; physical energy chỉ trừ một lần | Giống AC |
| Lifetime/history | `src/simulate.py:40-44,73-87`; `src/run.py:105-117` | Giống AC |
| Report CSV/plot | `src/run.py:61-64,84-85`; `src/analyze.ipynb:143-178,301-320,414-427` | Giống AC |

Optimizer là entry point khác: `optimizer/adapters.py:38-44,74-78` tạo fresh algorithms; `optimizer/trajectory.py:56-77,91-134` chạy vòng đời, ghi FND/HND/LND và provenance; `optimizer/metrics.py:5-30` tính cohort score; `optimizer/engine.py:71,139-144` tối đa hóa mean completed service, với energy constraint. **Fitness nội bộ D không phải score Optuna.** AC adapter tồn tại nhưng campaign chỉ cho D tuning: `optimizer/engine.py:31`; SimpleACO reference adapter đặt beta=gamma=0 tại `optimizer/adapters.py:52-54`, khác SimpleACO mặc định trong `run.py`.

### 2.2. Network, workload và energy model hiện tại

Current trusted `map.pkl`: scenario seed **41**, uniform, 100 sensors, cube **500×500×500 m**, base **(250,250,0)**, radius **200 m**, energy **0,6 J/node**. Hash:

`f5e6ebb66f9f361f5d91cceda44dff85e7eca4d1dc86877a74ab81a6216f1af8`

Có **19** nodes trực tiếp trong bán kính sink. Chẩn đoán connectivity ban đầu xác nhận graph connected và mọi node có đường giảm khoảng cách đến base qua từng hop. Metadata/generator tại `src/map_gen.py:21-110`; distances tại `src/network.py:28-38`; measurement tại `diagnostics.json:5-18`.

Với `d` bằng m, `L=200` bits và transmission rate `R_b=10000`:

\[
d'=d/1000,\quad A(d)=(d')^{1.5}a^{d'},
\]
\[
E_{tx}(d,n)=P_0 A(d)Ln/R_b,\quad E_{rx}(n)=L E_{elec}n,
\quad E_{da}(n)=L E_{integrate}n.
\]

`src/evaluate.py:19-38`; `src/hparameter.py:11-29`. Thorp dùng kHz đúng; Point dùng đủ x,y,z: `src/point.py:18-23,34-38`. Cache AC clip distance xuống `1e-12` để xử lý hai sensors đồng vị trí, `src/algorithms/clustering/ac_aco/ac_aco.py:108-115`. Đây không phải lỗi dùng 2D.

Gọi `q_i` là tổng packet-equivalents các con gửi vào node i:

| Vai trò | Packet-equivalents gửi lên parent | Chi phí round |
|---|---:|---|
| Member leaf | 1 | `E_tx(d,1)` |
| Relay thường | `1+q_i` | `E_rx(q_i)+E_tx(d,1+q_i)` |
| CH, kể cả CH làm relay | **2** | `E_rx(q_i)+E_da(q_i)+E_tx(d,2)` |
| Base | Không charge | 0 |

Chính xác tại `src/evaluate.py:64-87`. CH rỗng cũng gửi 2 packet-equivalents; CH đông không gửi nhiều hơn 2. Đây là chính sách aggregation cố định đã mô tả tại `README.md:162-166`, không tự kết luận implementation bug. Có charge aggregation theo số packet-equivalents nhận, nhưng không theo số original readings đã được CH phía dưới nén.

Không có application payload, delivery acknowledgments, loss/retry, collision, MAC scheduling hoặc control-packet transmission trên đường evaluator này. `P_0` là hệ số TX, không phải một control packet được charge riêng. Vì vậy “full service” trong mã nghĩa là **mọi live sensor xuất hiện trên cây/cost dictionary**, chưa chứng minh mọi reading đến sink với energy khả dụng.

### 2.3. AC-ACO: toán học thực sự chạy

Ký hiệu `r_i` là residual energy; `x_i` là chaos state; `a` pheromone exponent; `g` acoustic-cost exponent; `w_d` distance weight; `s_t` chaos strength; `M=40` ants. Mọi công thức dưới đây tái dựng từ source hiện tại.

**Initialization/solution construction.** Tau mọi phần tử bằng 1. Chaos `x_i` được tạo bằng N bước liên tiếp của `x←3.61x(1-x)`, khởi đầu `.37`; không seed random riêng cho chaos. Ant chọn CH đầu bằng uniform `rng.choice`, rồi chọn không hoàn lại:

\[
k=\min(|L_t|,\max(1,\operatorname{round}(.2|L_t|))).
\]

`src/algorithms/clustering/ac_aco/ac_aco.py:107-127,141,204-217`. Mỗi ant có tối đa 10 attempts; lấy attempt đầu feasible; tối đa 40 feasible candidates/round, không inner optimization loop: wrapper `src/algorithms/ac_aco.py:46-86`.

**Adaptive schedules.** `t=1` tương ứng simulator round 0; `T=3500` lấy current HyperParameters, không phải 3000 trong tài liệu cũ:

\[
\rho_t=.6-\min(\max(t/T,0),1)(.6-.1),
\]
\[
\beta_t=1+4\sigma\big(5(t-T/2)\big),\quad \sigma(z)=1/(1+e^{-z}).
\]

`src/algorithms/clustering/ac_aco/ac_aco.py:32-54,145-149`; `src/hparameter.py:10`. Sigmoid nhánh riêng cho z âm/dương tránh overflow. Option `normalized` thay đối số bằng `5(t/T-.5)`, **không rescale endpoints**. Defaults raw chuyển từ beta 1,02677 ở t1749 → 3 ở t1750 → 4,97323 ở t1751; 10–90% transition width là `2 ln(9)/5≈0,879` rounds. Đây là PARAMETER/TIMESCALE ISSUE, không phải overflow hay sai dấu.

**Chaos adaptation.** Nếu chưa có chi phí, bounds suy biến hoặc round trước fail: `s_t=.05`. Còn lại:

\[
s_t=.05+.25\operatorname{clip}\left(
\frac{E_{best,t-1}-E_{low}}{E_{high}-E_{low}},0,1\right).
\]

`E_low/E_high` là minimum/maximum của **tất cả feasible candidates từ trước tới nay**, không rolling window; cập nhật sau search, `previous_cost` dùng winner energy. `src/algorithms/clustering/ac_aco/ac_aco.py:57-67,150-152,174-180`. Khi live giảm, scale total round energy giảm theo workload; extrema cũ có thể khiến chaos gần floor. Đây là một giả thuyết adaptation mất độ nhạy, chưa đo terminal trajectories current.

**Transition trước chaos.** Với `d_ij=max(distance,1e-12)`:

\[
u_{ij}=\tau_{ij}^{a}\left(r_j/d_{ij}^{w_d}\right)^{\beta_t}
 E_m(d_{ij})^{-g},\quad p_{ij}=u_{ij}/\sum_{j\in A}u_{ij}.
\]

Current `(a,g,w_d)=(1,.1,1)`. `E_m=E_tx+E_rx+E_da`, một link surrogate, **không phải energy cây route**. Log-score chính xác `a log(tau)+beta(log(r)-w_d log(d))-g log(E_m)` rồi `exp(logscore-max)` tại `src/algorithms/clustering/ac_aco/ac_aco.py:219-256`. Các chỉ số hợp lệ yêu cầu tau>0, residual>0 và finite positive cached E_m. Không có fitness maximization nhầm.

**Transition sau chaos và hệ quả.** Code cộng cùng hằng số `c=s_t x_i` cho mọi candidate rồi chuẩn hóa:

\[
\widetilde p_{ij}=\frac{p_{ij}+c}{1+mc}
=\lambda p_{ij}+(1-\lambda)/m,\quad \lambda=\frac1{1+mc}.
\]

`m=|A|`; `src/algorithms/clustering/ac_aco/ac_aco.py:257-258`. **[SUY LUẬN]** Chaos không tạo preference khác nhau giữa targets cùng row; nó pha trộn về uniform và làm yếu cả heuristic lẫn pheromone. Tỷ trọng phụ thuộc network size, không chỉ nominal `.05`.

**[THỰC NGHIỆM]** Với source node0, m99, t1: x0=.841491, s=.05 → uniform share **80,6403%**; probabilities min .00892715, max .01734198. Hằng `.05` không tương đương 5% exploration. `diagnostics.json:77-95`.

**Objective/winner.** Mặc định:

\[
C^*=\arg\min_C(E(C),\text{ordered CH tuple}).
\]

Option load_weight `w>0`:

\[
CV(C)=\mathrm{std}(e_i)/\mathrm{mean}(e_i),\quad
f(C)=(1-w)E(C)/\overline E+w\,CV(C)/\overline{CV}.
\]

Nếu mean CV=0, contribution thay bằng constant 1. `src/algorithms/ac_aco.py:82-85,103-115`. CV dùng absolute loads, không dùng residual; với residual không đồng đều, CV thấp vẫn có thể giết node yếu. Deposits luôn dựa trên E, kể cả winner dựa f; đây là objective/reinforcement inconsistency của **option**, không lỗi mặc định w0.

**Pheromone update.** Mỗi feasible ant deposit live trên **các cặp CH liên tiếp trong ordered construction path**, không các cạnh cây truyền dữ liệu:

\[
D_{ij}=\sum_{k:\,(i,j)\in H_k} Q/(M E_k),\quad Q=.01.
\]
\[
\tau_{ij}^{mid}=\operatorname{clip}((1-\rho_t)(\tau_{ij}+D_{ij})+s_tx_i,.01,20),
\]
\[
\tau_{ij}^{next}=\min(20,\tau_{ij}^{mid}+
\mathbf1_{(i,j)\in H^*}\, .1Q/E^*).
\]

`src/algorithms/ac_aco.py:80`; clustering `src/algorithms/clustering/ac_aco/ac_aco.py:182-184,262-296`. Ant deposits tạm thời có thể vượt tau_max trước cuối round; bound được enforce cuối evaporation rồi elite. Không được gọi đây là post-elite overflow cũ: current elite đã clamp. Dead-node edges và diagonals không update nhưng cũng không tham gia construction từ filtered live.

Physical residual không bị giảm trong search; chỉ simulator giảm winner cost. Pheromone/chaos/cost extrema/iteration giữ qua rounds. Simulator tái tạo physical state nhưng không reset algorithm state: phải fresh instance cho mỗi independent run; `src/simulate.py:32-40`; runner đã làm đúng tại `src/run.py:56-60`.

### 2.4. D-ACO: toán học thực sự chạy

Grid cell side `s=(width·height·depth/(.2N))^(1/3)`. Gọi d_iq khoảng cách node–tâm cell, a_q nửa đường chéo cell, R communication radius:

\[
F^0_{iq}=\min(1,V_{sphere}/V_{cube})\max(1-d_{iq}/(R+a_q),0)^3.
\]

Override F0=1 khi cell nằm trọn trong cầu, =0 ngoài support; default parabolic decay:

\[
F_{iq}=F^0_{iq}\max(1-(d_{iq}/(R+a_q))^2,0).
\]

`src/algorithms/clustering/d_aco/d_aco.py:21-54,58-88`. Đây là trọng số overlap xấp xỉ, không exact sphere-box intersection. Helper exact integration trong `helper.py:8-55` không được gọi trên đường density hiện tại.

\[
D_q=\sum_{i\in L}F_{iq},\quad \ell_q(S)=\sum_{j\in S}F_{jq},
\quad h_i(S)=\sum_qF_{iq}\max(D_q-\ell_q(S),0).
\]

Density/reset/loss tại `src/algorithms/clustering/d_aco/d_aco.py:85-109,170-183,216`. Ants bắt đầu từ các live nodes distinct sampled, tối đa min(40,|L|), rồi chọn không hoàn lại:

\[
p_i(S)\propto\tau_i^{1.8}r_i^{.04}h_i(S)^{.6}.
\]

Log-space stabilization tại `:185-212`, target CH tại `:171`. Pheromone vector node, không edge path. Candidate coverage kiểm tra rõ `set(consumption)==set(live)` tại `src/algorithms/d_aco.py:71`.

Fitness dùng structural density trước candidate loss `b_i=Σ_q F_iq D_q`:

\[
P(C)=\frac1{|L|}\sum_i\frac{(e_i/\max(r_i,10^{-12}))^{2.6}}
{\max(b_i,10^{-12})},
\quad f(C)=E(C)+.84 E_{ref}P(C)/P_{ref}.
\]

`src/algorithms/d_aco.py:41-43,73-77,110`; `src/algorithms/clustering/d_aco/fitness.py:25-33`. P/reference dimensionless ratio; E_ref là J nên f cũng J. Reference ban đầu mean của 40 throwaway calibration ants; không physical deduction, không deposits hoặc schedule advancement; wrapper `:82-97`. Qua round, mỗi reference cập nhật hình học:

\[
R_{t+1}=\exp(.8\log R_t+.2\log\overline R_{observed,t}).
\]

`fitness.py:15-22`; wrapper `:104,118` freeze scales trong round. Winner và deposits đều dùng cùng cached f, `:110-117`.

\[
\rho_t=.52-\min(t/T,1)(.52-.36),\quad
\tau_i\gets\operatorname{clip}((1-\rho_t)\tau_i,1,25).
\]

Evaporate **trước** ant batch, `src/algorithms/clustering/d_aco/d_aco.py:133-146,238-249`. Successful ant adds `9.5E_ref/(40f)` vào mỗi CH; elite adds `.84·9.5E_ref/f`; clamp trên25 tại `:220-236`. Q của D có scale khác Q của AC; so sánh raw 9.5 với .01 không cho biết reinforcement strength.

### 2.5. Phạm vi đối chiếu paper

Đã đọc [PDF chính thức Zhou–Chen–Cao, DOI 10.32604/cmc.2025.065561](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf).

| Paper, trang PDF tính từ 1 | Đối chiếu current source |
|---|---|
| Eq11,13,14; tr.10–11 | Logistic, linear rho, raw sigmoid: khớp dạng. |
| Eq18,20; tr.13 | Residual/distance, tau, inverse E_m: khớp. |
| Eq12,21; tr.10,14 | Paper: `(1-rho)tau+Delta+chaos`; code attenuate ant Delta trước elite. |
| Eq10; tr.9 | `Q/L_k`; code dùng energy cây và chia M. |
| Eq15; tr.11 | Có iteration window; quy tắc window/lag chưa đầy đủ. |
| Algorithm1; tr.11–12 | Code chuyển thành batch/physical-round; khác global-best/convergence. |

Không xác nhận nguyên bản toàn thuật toán. README tự khai báo adaptation UWSN tại `src/algorithms/clustering/ac_aco/AC_ACO_README.md:3-7,19-20`. Cần sửa phát biểu “paper leaves window undefined” (`:108`): chưa rõ **quy tắc** window. Diễn giải gamma trong `plans/analysis/acaco-performance.md:29-33` không nên thay thế Eq20. [Nguồn đối chiếu](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf).

## 3. Implementation correctness matrix

“Expected” dưới đây dùng local UWSN contract, trừ các hàng ghi rõ paper. PASS là đúng trong tested valid scope, không phải chứng minh optimum.

| Component | Expected behavior | Actual behavior | Verdict | Code evidence |
|---|---|---|---|---|
| 3D distance | Euclidean x,y,z; symmetric sensor distances | Đúng; meter→km trong TX | PASS | `src/point.py:34`; `src/network.py:28-38`; `src/evaluate.py:26-28` |
| Probability normalization AC | Nonnegative finite, sum1 | Log-max + normalize + normalize chaos | PASS cho fixtures/defaults | AC clustering `src/algorithms/clustering/ac_aco/ac_aco.py:219-258`; `tests/test_ac_aco_equations.py:30-47` |
| Probability numerical boundaries | Zero distance/large beta không overflow thông thường | Cached clipped distances; stable sigmoid; uniform fallback nếu logmax invalid | PARTIALLY VERIFIED; không exhaustive mọi float input | AC clustering `:38-54,108-115,247-254`; `tests/test_ac_aco_vectorization.py:88-114` |
| Fitness direction AC/D | Minimum chi phí/fitness | Cả hai min; tie-break deterministic | PASS | `src/algorithms/ac_aco.py:103-115`; `src/algorithms/d_aco.py:116` |
| Objective dấu/weights | Energy/risk tăng thì score tăng, weights hợp lệ | Nonnegative weighted components | PASS; objective khác nhau | AC parameters `:66-69`; D fitness `:25-33`; D params `:40-44` |
| AC rho/beta | Local raw schedules một lần/round | Đúng; beta jump quanh1750 | PASS toán; PARAMETER ISSUE về clock | AC clustering `:133-149`; hp `src/hparameter.py:10` |
| AC strength window | Local documented expanding feasible bounds, previous cost | Đúng; không finite rolling window | PASS local; paper PARTIALLY VERIFIED | AC clustering `:57-67,174-180`; AC README `:104-108` |
| AC tau initialization | tau0 trong bounds | Matrix1; bounds validated | PASS | AC clustering `:107`; AC params `:49-71` |
| AC final tau bounds | Final round tau≤20, ≥.01 | Evap clamp và elite clamp; ant phase chưa clamp | PASS local; không bound mọi substep | AC clustering `:273-295`; `tests/test_ac_aco_pheromone.py:25-52` |
| Paper deposit placement | `(1-rho)tau+Delta+chaos` | `(1-rho)(tau+antDelta)+chaos`, rồi elite | MATHEMATICAL MISMATCH literal; adaptation được mô tả | AC wrapper `:80`; AC clustering `:182-184,291-295`; mục2.5 |
| Candidate full coverage | Mọi live node phục vụ đúng một lần | D có coverage guard; AC không có guard riêng | D PASS; AC VALIDATION GAP, chưa thấy actual omission | `src/algorithms/d_aco.py:71`; `src/algorithms/ac_aco.py:76-78`; probes full coverage |
| Dead nodes | Không dùng dead nodes trong selected tree | Simulator live filter; AC residual filter; D dựa valid caller | PASS caller path; manual stale inputs chưa exhaustive | `src/simulate.py:63`; AC clustering `:134`; D wrapper `:99-103` |
| Range/prev/cycles | Parent links nhất quán, mọi link≤radius, tree đầy đủ | Shared builder/router enforce ranges; greedy/drop logic; probes validate selected trees | PASS observed; router không complete search | cluster `:23-35`; routing `:167-191`; diagnostic `tree_checks` |
| D fitness/reference | Một f dùng winner/ant/elite; frozen refs/round | Đúng; geometric EMA sau round | PASS | D wrapper `:104-118`; D fitness `:15-33` |
| AC optional load fitness | Search reinforcement nên phản ánh selection score nếu claim single objective | Winner uses f, deposits use energy E | OBJECTIVE MISMATCH option w>0; không phải paper correctness fix mặc định | AC wrapper `:80-85,109-115`; AC clustering `:174-184` |
| Optimization energy ↔ simulator | Selected cost khớp Evaluator | Shared evaluator; độc lập recompute khớp 120 selected trees | PASS observed; simulator thiếu independent guard | AC wrapper `:73-75`; D wrapper `:70`; `src/simulate.py:46-51` |
| Energy availability/delivery | Nếu gọi completed service thì đủ energy thực hiện | Overdraw rồi clamp; vẫn ghi complete | ACCOUNTING/MODEL LIMITATION | `src/simulate.py:60-78`; `optimizer/trajectory.py:103-109` |
| State reset/RNG | Fresh instance cho independent run; local RNG với explicit seed | Runner đúng; reused instance giữ optimizer memory | PASS runner; API cần dùng đúng | `src/run.py:56-60`; base `:108-129`; AC clustering `:105,124-127` |
| Plot alive after failed service | Censor/unobserved survivors; không invent deaths | Missing tail bị fill0% | CONFIRMED BUG | `src/analyze.ipynb:414-427` |
| Comparison provenance | Match map/source/parameters/cohort | Ordinary CSV/notebook thiếu identity/pairing; optimizer tốt hơn | EXPERIMENTAL BIAS RISK | `src/run.py:61-64,84-85`; notebook `:143-161`; optimizer trajectory `:61-77,122-134` |
| Normal map tests | Gọi đúng distribution khi test normal | Hai tests gọi default uniform | CONFIRMED TEST/SPEC DRIFT | `tests/test_map_seeding.py:30-48`; `src/map_gen.py:31,65-79` |

Trong bảng, viết tắt “AC clustering/parameters” chỉ đúng file `src/algorithms/clustering/ac_aco/ac_aco.py` / `parameters.py`; “D wrapper/fitness” chỉ `src/algorithms/d_aco.py` / `src/algorithms/clustering/d_aco/fitness.py`.

## 4. AC-ACO versus D-ACO differences

### 4.1. Objectives và lifetime alignment

**[MÃ]** AC mặc định minimize `Σ e_i`; không minimize FND, completed service, maximum relative depletion, residual variance hay terminal connectivity. D cũng không trực tiếp maximize lifetime, nhưng penalty convex theo depletion bảo vệ node ít residual; density nhằm ưu tiên bảo vệ vùng ít redundancy. `src/algorithms/ac_aco.py:107-108`; `src/algorithms/clustering/d_aco/fitness.py:25-33`.

**[SUY LUẬN]** Giữ load/density, residual giảm1/2 khiến penalty D tăng `2^2.6=6,06287` lần; residual còn1/10 tăng `398,10717` lần. CV absolute của AC option không đổi khi chỉ residual giảm. Fixture A total .01 với loads [.009,.001] và B total .011 với loads [.0055,.0055]: AC chọn A dù peak drain cao hơn **63,636%** tại residual bằng nhau. Phép thử operator không chứng minh A/B là hai cây của current topology; nó xác nhận decision rule. `diagnostics.py:117-135`.

D có thể từ chối minimum-energy candidate: references .01/.0001, penalty A .00036 và B .0001 → fA=.04024, fB=.0194. Chi phí B cao10% vẫn được chọn. `tests/test_d_aco_fitness.py:59-83`. Density cũng không phải exact articulation-point/bottleneck indicator; node density lớn vẫn có thể là cut vertex trong physical graph. D chưa có guarantee FND/service.

### 4.2. Search representation và budgets

| Đặc điểm | AC current | D current | Ý nghĩa |
|---|---|---|---|
| Memory | NxN directed CH transitions | N CH-node pheromones | N100 có 9900 usable edge features vs100 node features; D tập trung credit trực tiếp vào CH identity |
| Reinforced items | k−1 consecutive CH pairs | k CH nodes | Không trực tiếp reward relay/outlier choices của cây truyền dữ liệu |
| Starts | 40 draws có hoàn lại | min(40,live) distinct | Expected AC unique starts33,10 khiN100; observed32,9 trong fixed-state probes |
| Spatial heuristic | Ưa distance nhỏ tới CH trước, residual/distance | Density coverage còn lại sau loss | Candidate distributions khác, không chỉ “chaos vs no chaos” |
| Round clock | rho giảm .6→.1; beta1→5; chaos theo energy | rho .52→.36; exponents fixed | AC late search có regime change, D không có beta jump |
| Main candidates | Tối đa40 feasible | Tối đa40 feasible khi live≥40 | Không có hidden inner rounds trong hai defaults |
| Retries | 10 attempts/ant, start có thể thay | 10 attempts/ant, start giữ | Attempts không bằng feasible evaluations |
| Initial extra budget | 0 | 40 calibration ants, ≤400 attempts | Cần tính vào budget/time; calibration không trừ battery |

Sources: AC clustering `src/algorithms/clustering/ac_aco/ac_aco.py:107,204-258,273`; D clustering `src/algorithms/clustering/d_aco/d_aco.py:121,146,167-236`; D wrapper `src/algorithms/d_aco.py:46-97`.

Không được gọi CH path là actual transmission route: ant path không bị radius constrain; final tree mới kiểm tra range. Cũng không được coi mọi permutation cùng CH-set là tương đương: router queue giữ insertion order và drop-member phụ thuộc trạng thái, `src/algorithms/routing/routing.py:155-191`. Synthetic fixture cùng4CH, 24 orders cho energy chênh34,03%; mục6. Đây giới hạn ý nghĩa của credit edge, đồng thời cho thấy order có thực sự ảnh hưởng fitness.

### 4.3. Integration: cùng cây thì cùng chi phí

AC/D dùng cùng build_clusters, router và Evaluator. Assignment non-CH vào CH gần nhất trong radius; không tới CH thì thành outlier và vẫn được routing. “dropping member” nghĩa là tháo member khỏi cluster để làm routing node, **không bỏ sensor khỏi service**: `src/algorithms/clustering/clustering.py:25-37`; `src/algorithms/routing/routing.py:179-191`.

Routing minimization đối với candidate parent j:

\[
.4\frac{\sum_{c\in pool}r_c}{\max(r_j,10^{-12})}
+.6\frac{d_{ij}^2+d_{jB}^2}{\max(d_{iB}^2,10^{-12})}.
\]

`src/algorithms/routing/routing.py:142-153`. Đây greedy residual/distance surrogate, không là ACO route search hoặc shortest-energy-path. Vì sum residual phụ thuộc pool, balance energy/distance thay theo cardinality; tác động chung, chưa isolate AC/D gap.

### 4.4. Experimental fairness

Một `run.main()` dùng chung loaded network/hparameters, fresh residual và fresh algorithms; không scenario RNG khi simulator thực thi. Scenario seed41 khác algorithm seeds24/25/26. D tiêu thụ RNG cho calibration và sampling distinct; AC rng.choice/choices khác draw order. Cùng integer seed bảo đảm replay của từng algorithm, **không** bảo đảm từng ant/candidate dùng common random numbers. `src/run.py:69-99`; `src/map_gen.py:42-45`; base `src/algorithms/base/base.py:108-129`; D wrapper `:90-96`; AC clustering `:204-215`.

Current D defaults khớp historical rounded parameter vector tại `plans/analysis/optimizer-results.md:89-113`; optimizer chỉ tune D, `optimizer/engine.py:31`; không held-out seeds, `optimizer/README.md:54`. So sánh as-configured sản phẩm là hợp lệ nếu công bố cấu hình; claim intrinsic algorithm superiority cần comparable tuning budgets và held-out maps/seeds.

Whole-trajectory energy từ `src/run.py:111` phụ thuộc số round/node còn sống. Algorithm dừng sớm có thể có total thấp vì làm ít công việc. Energy efficiency phải so sánh common fully alive/served prefix K hoặc joule/reading với delivery định nghĩa rõ. Optimizer đã kiểm tra all-alive/full-service K tại `optimizer/trajectory.py:123-129`; ordinary notebook không tự có bảo đảm này.

## 5. Ranked root causes

Ranking ưu tiên bằng chứng và ảnh hưởng có thể có; **không xếp một giả thuyết thành causal fact về lifetime chưa đo**.

### R1 — Objective không bảo vệ node gần cạn

**STRUCTURAL LIMITATION; severity cao; confidence cao về cơ chế, trung bình về contribution vào lifetime.** Code path: AC `_best_candidate` → minimum total E (`src/algorithms/ac_aco.py:103-108`) → energy-only ant/elite deposits (`:80`; AC clustering `:267-271`) → simulator deduct (`src/simulate.py:60-63`). Nhiều vòng chọn rẻ toàn mạng có thể tập trung load vào critical relay. D có residual-normalized convex penalty cả winner và reinforcement, `src/algorithms/d_aco.py:110-118`.

Impact đã định lượng ở operator: cùng tổng thấp hơn10% có peak drain cao hơn63,6% trong fixture. **Chưa** đo số round FND/service bị mất. Test nhỏ nhất: cùng feasible candidate pool tại vài frozen residual snapshots, score bằng E và relative-depletion surrogate, đo rank reversal/peak risk; sau đó paired full trajectories để kiểm tra actual lifetime. Không thể lấy CV absolute làm thay thế đầy đủ.

### R2 — Sampling/reinforcement hiện tại tạo candidate pool khác chất lượng

**STRUCTURAL LIMITATION / PARAMETER INTERACTION; severity cao tiềm tàng; confidence cao về observed early energy, trung bình về attribution từng thành phần.** Code: edge-path tau + residual/distance + uniform chaos tại AC clustering `:204-258,262-296`, so với D node tau/density/live deposits tại D clustering `:167-249`.

Current fixed-state AC winners energy .01677639J/decision, D .01579367J. AC đúng là chọn candidate rẻ nhất. D sau round đầu chọn cao hơn own-pool minimum trung bình **0,5947%**, nhưng winner vẫn rẻ hơn AC. Vì vậy early gap không do AC accidentally chọn max hoặc simulator charge khác; candidate generation/memory/policy cung cấp D các cây rẻ hơn trong probes. Không đủ để quy riêng cho density, node pheromone hay Q.

Hypothesis edge credit bị dilute có cơ sở representation: 19 edges/ant giữa9900features vs20nodes/100features. Nhưng một edge vẫn có thể học router order effects; không gọi memory “vô tác dụng”. Test tối thiểu: frozen-state candidate capture, controls chỉ đổi một thành phần hoặc replay chung pool; log entropy, physical route-edge overlap và winner-cost distributions.

### R3 — Báo cáo alive curve gán search stop thành death

**CONFIRMED BUG; severity cao về kết luận khoa học; confidence cao.** `src/analyze.ipynb:414-427` giữ zero tail; `src/simulate.py:40-44` dừng khi rootNone, còn survivors có thể rất nhiều. Đã thực thi chính function trích từ notebook: hai histories terminal98 và continuing97 → mean alive curve48,5%, dù một terminal snapshot vẫn98. Đây downstream measurement distortion, không làm đổi algorithm hoặc `len(history)`.

D không tự tránh lỗi plot: algorithm nào sống/service lâu hơn sẽ bị penalty tail ít hơn. Test xác nhận/falsify đã chạy trong `integration-probes.py:57-74`. Correction phải dùng explicit censoring hoặc label service-active separately; carry98 minh họa trạng thái terminal, không khẳng định mạng đã tiếp tục phục vụ round sau.

### R4 — Thiếu current paired provenance và tuning bất đối xứng

**EXPERIMENTAL BIAS; severity cao cho claim generalization; confidence cao.** Notebook filter/group thiếu map/epoch pairing (`src/analyze.ipynb:143-161,301-320`), CSV cùng giờ overwrite (`src/run.py:61-64,84-85`), historical maps khác (mục6). D-only search policy `optimizer/engine.py:31`; held-out absent `optimizer/README.md:54`.

Không chứng minh một current matched run đã bị gian lệch physical conditions. Chứng minh **không được suy current fair lifetime gap từ aggregates hiện có**. Minimal resolving experiment: cohort có manifests map/source/config/hash; separate scenario seeds và algorithm seeds; held-out seeds/maps; common horizon/schedules; report training/tuning cost riêng. D calibration40 không biến thành40 packets tiêu hao battery.

### R5 — Raw beta có step gần1750 và local proximity bias

**PARAMETER ISSUE; severity trung bình–cao tiềm tàng; confidence cao toán học, thấp–trung bình về actual damage.** `src/algorithms/clustering/ac_aco/ac_aco.py:38-54,234-245`; default `parameters.py:19-22`. Khi beta1→5, residual/distance odds bị lũy thừa mạnh hơn, đổi exploration/exploitation trong khoảng chỉ vài rounds. D không có beta jump.

Không lỗi overflow, không sai phương trình local. Một sensitivity experiment phải freeze physical snapshot t≈1748–1752, so sánh candidate concentration/cost/risk trước và sau; chọn raw slope có unit “per round” và width định trước nếu muốn giữ công thức. Normalized schedule là variant có sẵn, không tương đương raw vì không đạt endpoints.

**Đối chứng phản bác suy diễn quá mức:** current 10-decision selected mean CH pair distance AC323,15m **lớn hơn** D292,67m. Không có bằng chứng early winners AC bị spatially clustered hơn D. Bỏ distance bias chỉ giảm mean energy0,3695%, với paired changes không đồng dấu; cần đo late regime.

### R6 — Literal deposit placement khác và scale phụ thuộc physics

**MATHEMATICAL MISMATCH so với literal global update; severity trung bình về fidelity; confidence cao về arithmetic, chưa biết lifetime impact.** AC antDelta bị nhân `(1-rho)` trong post-round, `src/algorithms/ac_aco.py:80`; clustering `:291-295`; elite thêm sau tại `:184`. Tại t1 current rho≈.599857, giữ **40,0143%** ant mass; D ant deposits sau evaporation không chịu attenuation cùng round, D clustering `:142,220-249`.

Current README mô tả ordering, do đó không kết luận implementation trái local spec. Đổi ordering mà giữ Q có thể tăng exploitation/clipping; cần định danh faithful-order control, thử operator với cùng tau/D/chaos, đo raw/retained deposits và paired outcomes. Không bảo đảm đổi này cải thiện AC.

Historical Q100/tau_max10 đã thay bằng .01/20; current elite clamp cũng đã sửa. Không được tái dùng “Q100 saturates” hoặc “elite overflow” làm root cause current. Parameters tại `src/algorithms/clustering/ac_aco/parameters.py:31-36`; regression `tests/test_ac_aco_pheromone.py:25-52`.

### R7 — Chaos uniform mixing mạnh, nhưng chưa chứng minh có hại

**STRUCTURAL PROPERTY / PARAMETER ISSUE; severity trung bình; confidence cao identity, thấp về adverse lifetime.** `src/algorithms/clustering/ac_aco/ac_aco.py:257-258` tạo uniform share80,64% ở probe đầu. Điều này attenuate learned preferences nhưng cũng chống local-proximity bias. D không có mixture này.

Test falsification đã chạy: tắt riêng transition disturbance, giữ pheromone disturbance/schedules/params, fixed-state3seeds×10 → energy **+2,7456%** so với default. Vì vậy không xếp “chaos causes current energy deficit” là confirmed root cause. Test cần thêm: same snapshots ở late state, sweep nonzero chaos bounds với equal budget; đo entropy/winner/critical-node risk, rồi lifetime nếu đáng làm.

### R8 — Shared route incompleteness, terminal overdraw và service semantics

**STRUCTURAL LIMITATION / ACCOUNTING LIMITATION; severity cao về diễn giải metric; confidence cao; differential contribution chưa biết.** Router chỉ parent gần base hơn tại `src/algorithms/routing/routing.py:169`; graph connected không đủ để greedy route feasible. Fixture4sensor có path hợp lệ nhưng routerNone. Có thể fail vì search budget hết, greedy restriction hoặc physical disconnect: ba nguyên nhân khác nhau.

Simulator charge demand trước rồi clamp tại `src/simulate.py:60-78`. Fixture1node available.00001J nhưng demand.0001530607J được đếm completed1round. Reported energy là **model demand**, không luôn bằng energy actually deducted. Cả AC/D cùng bị; không chứng minh nó ưu tiên D. Minimal test: terminal states, independent connectivity certificate và selected-cost funding check; phân rã stop reason.

### R9 — Validation gaps và baselines phụ trợ

**CONFIRMED VALIDATION GAP; severity trung bình; confidence cao; không chứng minh actual AC missing-service defect.** AC chỉ finite positive total (`src/algorithms/ac_aco.py:76-78`), simulator trust nonempty dict (`src/simulate.py:46-63`); D coverage guard tại wrapper `:71`. Probes current tất cả full coverage, tree unique/consistent/range hợp lệ.

PSO cache `tuple(sorted(CHs))` tại `src/algorithms/pso.py:72-81` trái order-sensitive route evaluation; nên kiểm tra trước dùng PSO làm ground truth. SimpleACO elite không clamp ngay (`src/algorithms/clustering/aco/aco.py:71-81`), khác AC/D; chưa lượng hóa default-bound violation. Hai map tests là test/default drift, không normal-generation bug (mục6). Các vấn đề này không giải thích trực tiếp AC<D.

## 6. Experimental evidence

### 6.1. Kiểm thử đã thực thi

Interpreter `C:\Users\LOQ\miniconda3\python.exe`, Python3.14.7, NumPy2.5.3; Windows. Không cài thêm dependencies.

```powershell
& 'C:\Users\LOQ\miniconda3\python.exe' -B -m unittest discover -s tests -v
```

Fresh full suite: **47 tests, 45 PASS, 2 FAIL, 0 ERROR**; lần chạy ngoài sandbox7,232s. Lần đầu sandbox có thêm2 PermissionErrors ở Windows tempfile; chạy lại ngoài sandbox loại bỏ hai environment errors, hai assertion failures giữ nguyên. Không sửa tests để làm xanh.

Failures: `test_normal_follows_sink_and_stretches_depth`, `test_surface_normal_is_underwater_and_shallower_than_uniform`. `tests/test_map_seeding.py:30-48` không truyền `distribution='normal'`, trong khi `gen` default uniform (`src/map_gen.py:31`). Probe cùng kwargs: uniform mean z248,75352m; explicit normal99,29301m, thỏa intended shallow assertion. Đó là drift giữa fixture/default/spec. Algorithm/energy diagnostics không phụ thuộc generator failure vì đọc fixed current map.

Separately executed D suite: **13 PASS**, .078s. AC arithmetic/bounds/vectorization/calibration tests trong full suite đều PASS. Các tests này xác nhận operators/state, không paper-level completeness hoặc lifetime superiority. Không chạy optimizer full suite/campaign; import diagnostic module trên interpreter này thiếu `psutil`, nên connectivity kiểm tra độc lập thay vì cài dependency.

### 6.2. Current paired probes: 3 seeds × 10 decisions

Script `plans/reports/acaco-daco-audit-261014-0902/diagnostics.py`; raw `diagnostics.json`. Dùng current map/default params/**T_max3500 không đổi**; algorithm seeds24/25/26; một scenario seed41. Hai modes độc lập, fresh instance mỗi run:

- **Fixed state:** physical residual .6 và live100 giữ nguyên; optimizer memory tiến10calls. Đây không lifetime trajectory.
- **Depleting:** sau mỗi selected tree, trừ cost theo simulator rule; 10rounds. Đây bounded prefix, chưa FND/service termination.

Mỗi selected tree được kiểm tra unique IDs, coverage, prev/nxt consistency, radius; Evaluator độc lập recompute đúng consumption; finite nonnegative energy; `plan_round` không mutate residual đầu vào. Có **120** successful selected decisions; D first call quan sát80 evaluators gồm40calibration+40search, các calls khác40; không thấy death/routefailure. Thời gian chạy script hoàn chỉnh khoảng12s, không dùng số này để xếp tốc độ algorithms.

| Mode, energy cho10decisions J | AC mean ± sample SD | D mean ± sample SD | Mean paired AC−D ± SD | AC energy cao hơn | Paired Cohen d_z |
|---|---:|---:|---:|---:|---:|
| Fixed state | .167763900 ± .000155600 | .157936677 ± .000702399 | .009827223 ± .000550548 | **6,2223%** | 17,8499 |
| Depleting10 | .167155306 ± .000441694 | .156722509 ± .001372480 | .010432797 ± .001681709 | **6,6569%** | 6,2037 |

Evidence `diagnostics.json:105-150`. SD qua **3 algorithm runs**, không qua300/120 independent rounds. `d_z=mean(paired difference)/sample SD(paired difference)`; rất lớn do cohort nhỏ và variance seed nhỏ trên một map. **Không dùng d_z này như bằng chứng statistical significance/generalization**; không có topology replication, held-out cohort hoặc lifetime event.

| Seed | AC depleting10 J | D depleting10 J | AC−D J |
|---:|---:|---:|---:|
| 24 | .1676002634 | .1564768925 | .0111233709 |
| 25 | .1671487043 | .1554894199 | .0116592844 |
| 26 | .1667169491 | .1582012140 | .0085157351 |

Fixed-state diagnostics means: AC max-relative-depletion .001012538, D .000953548; AC loadCV .868102, D .838959. Đây mean của maximum **per-round demand ratios**, không cumulative maximum hoặc FND estimate. CH pair distance AC323,150m, D292,668m. `diagnostics.json` → rows; computation ghi tại script `short_runs`.

### 6.3. Controlled AC ablations, fixed-state only

Mỗi variant là fresh instance,3seeds×10calls, same map/horizon/default budgets; chỉ thay in-memory tùy chọn công bố. **Không đổi production configuration.** Raw `diagnostics.json:2071-2135`; script function `ablations`.

| Variant | Mean energy10 J | Δ vs AC default | Mean peak depletion/decision | Mean CH pair distance m |
|---|---:|---:|---:|---:|
| Current AC default | .167763900 | 0% | .001012538 | 323,150 |
| Tắt chỉ chaos ở transition; vẫn disturbance tau | .172370056 | **+2,7456%** | .001008808 | 313,851 |
| `distance_weight=0`, giữ E_m term | .167144003 | −.3695% | .000989084 | 327,389 |
| `load_weight=.1`, giữ energy deposits | .168263254 | +.2977% | .001009242 | 321,328 |

Transition-no-chaos energy tăng ở cả3seeds. Distance-zero changes mixed: seed25 tăng,24/26 giảm; lợi ích mean nhỏ chưa bền. LoadCV option làm energy tăng nhẹ, peak risk gần như không đổi. Không variant nào được xác nhận lifetime gain. Ablations đổi RNG trajectory vì probabilities đổi; shared seed là paired replication, không matched candidate draws hay independent sample guarantee.

### 6.4. Tiny manually checkable integration tests

Raw `integration-probes.json`; script `integration-probes.py`:

1. Empty CH ở100m gửi2packets-equivalents, cost **.0001530607265J**. TX formula độc lập khớp `2E_tx(100)`.
2. Node chỉ có.00001J vẫn ghi full completed round demand.0001530607265J rồi chết: log demand lớn hơn available **15,3061 lần**. Không có actual-delivery oracle.
3. All-CH4sensor: `(2,0,0),(2.1,.6,0),(1.3,.9,0),(.6,.4,0)`, baseorigin, radius.9. Valid chain hops `.608276,.854400,.860233,.721110`; routerNone vì hop0→1 tăng distance-to-base. Common algorithm limitation.
4. Chính function alive-curve notebook với terminal98/continuing97 cho48,5% tail; terminal-state carry minh họa97,5%, còn poststop service **censored**.
5. Order-sensitive routing fixture reproducible `Random(1729)`, case12,12nodes radius1.5, same4CH24permutations: min .000265438604J, max .000355763407J, **+34,0285%**. Đây fixture tổng hợp, không phép đo current100-node lifetime.

### 6.5. Historical evidence đọc lại và provenance audit

| Artifact | Quan sát | Có dùng để kết luận current lifetime? |
|---|---|---|
| `plans/analysis/optimizer-results.md:5,54-58,89-113` | Map b7e43b90…; D tuning đối chiếu SimpleACO, không AC; defaults D khớp rounded trial5 | **Không**: current map f5e6… |
| `plans/analysis/daco-performance.md:187` | Historical map d9e086… và defaults cũ | **Không** |
| `plans/analysis/acaco-performance.md:3-7,134,142` | Historical map ebe729…; một số studies exponent1/frozen updates | **Không** |
| `plans/261011-0055-acaco-deep-audit/short-main/summary.csv:2,6,11,15,20,24` | AC-original và DACO seeds0/1/2,150rounds, alive100 | Early historical energy, không lifetime; thiếu matched source/map manifest |
| `plans/analysis/README.md:20-22` | Tài liệu nói raw outputs còn optimizer/runs | Folder không có trong checkout; không thể replay claims đó |

Tính lại historical CSV: AC150 energy `[2.4827693610,2.5001818412,2.4909373237]J` → mean2.4912961753, SD.0087117849. D `[2.4355265904,2.4357693965,2.4441379174]J` → mean2.4384779681, SD.0049031631. Paired delta mean.0528182072J, SD.0100433510, d_z5.2590, AC+2,1660%. Mọi run cap-censored150, chưa death: không suy lifetime.

Các mô tả historical “node48 chỉ có neighbors33/65” không áp dụng current map: current node48 base163,30377m, trực tiếp sink, có13sensor neighbors. `plans/analysis/acaco-performance.md:254,433-435` là historical narrative, không current structural proof.

### 6.6. Reproducible commands

Từ repository root, dùng hai script audit **chỉ viết JSON cạnh script**, không ghi production runs/maps:

```powershell
& 'C:\Users\LOQ\miniconda3\python.exe' -B plans/reports/acaco-daco-audit-261014-0902/diagnostics.py
& 'C:\Users\LOQ\miniconda3\python.exe' -B plans/reports/acaco-daco-audit-261014-0902/integration-probes.py
& 'C:\Users\LOQ\miniconda3\python.exe' -B -m unittest discover -s tests -v
& 'C:\Users\LOQ\miniconda3\python.exe' -B -m unittest discover -s tests -p 'test_d_aco*.py' -v
```

Tests dùng temporary folders; sandbox có thể chặn Windows temp. Script diagnostics chứa fingerprint để báo source/map snapshot thực chạy. Không coi lệnh `python src/run.py` là cheap diagnostic: nó chạy cả5algorithms đến3500rounds và có thể overwrite CSV; **không thực thi lệnh đó trong audit**.

## 7. Corrective action plan

Đây là đề xuất nghiên cứu, **chưa áp dụng**. Không guarantee performance gain. Identity risk: thấp=operator/protocol clarification; vừa=objective/policy variant vẫn giữ adaptive chaotic edge ACO; cao=đổi representation/router/physical problem.

### P0 — Correctness fixes và xác định contract

| Affected file/function | Current → proposed | Justification/mechanism | Identity risk | Validation bắt buộc |
|---|---|---|---|---|
| `src/analyze.ipynb:408-427`, mean_alive_percentage_curve | Zero tail → explicit censored/missing tail; initial N từ manifest; service-active curve riêng | Không biến route failure thành death; statistical cohort denominator đúng | Thấp, chỉ reporting | Fixture histories terminal98/continuing97; empty history; first-round death; never silently fill0 |
| `src/simulate.py:46-63`; AC `plan_round:73-78` | Trust positive total → central full-tree/cost validation; coverage/uniqueness/live/prev/range/finite/nonnegative | Bắt defect trước khi report full service; AC/D contract đồng nhất | Thấp | Adversarial partial/duplicate/dead/NaN/negative/overrange tree; independent selected-energy recompute |
| AC `post_round/_update_pheromone`, clustering `:182-184,282-296`; README | Chốt rõ local pre-evap deposit adaptation; nếu cần faithful global-update control, dùng evaporation→ant aggregate→chaos→elite với scaling công bố | Current ant mass chịu1−rho; yêu cầu fidelity phải định nghĩa ordering, không gọi đổi Q là sửa toàn bộ | Thấp–vừa; thay trajectory, cần variant label | Known tau/D/rho operator; final bounds; raw retained mass; compare both ordering with matched budgets |
| AC README `:32,104-108`; maintained analysis `plans/analysis/acaco-performance.md:29-33`; README `:149,179` | Bỏ claim CV following current D; mô tả actual expanding bounds; sửa outdated horizon3000 | Spec phải mô tả current D power-density và current T3500 | Thấp | Doc-to-source inventory; default config dump |
| `tests/test_map_seeding.py:30-48` | Normal tests dùng defaultuniform → explicit normal distribution, giữ separate default contract test | Fix fixture/spec drift; chưa cần đổi generator | Không | Hai failing assertions chạy explicitnormal; uniform replay vẫn đúng |

Không có P0 bằng chứng buộc phải đổi AC transition sign, probability normalization, gamma default hoặc elite clamp hiện tại. Restore Q100 hoặc copy D fitness không phải correctness fix.

### P1 — Objective và simulation alignment

| Affected file/function | Current → proposed | Mathematical justification và expected mechanism | Identity risk | Test |
|---|---|---|---|---|
| AC `_best_candidate`, `src/algorithms/ac_aco.py:103-115` | Energy-only/CV option → thêm **named residual-aware AC variant**, ví dụ `f=E/E_ref+λ mean((e_i/r_i)^p)/P_ref` hoặc energy+risk constraint | Relative depletion phản ánh danger khác residual; giữ edge pheromone/chaos/schedules. Không nhất thiết copy density D | Vừa: đổi objective, báo variant; chưa phải faithful-original claim | Same-pool rank reversal; frozen snapshots; paired FND/service; energy common K |
| AC deposit `src/algorithms/ac_aco.py:80`; clustering `:174-184,262-271` | Khi chọn f composite nhưng depositE → cho variant dùng cùng normalized f và frozen references | Winner và learning reward cùng quality; tránh reinforce candidate kém risk chỉ vì rẻ | Vừa; Q/bounds phải calibrate lại | Coupled score/deposit ordering, inverse quality test, saturation/deposit mass; lifetime ablation |
| `src/simulate.py:60-78`, optimizer trajectory `:103-109` | Chỉ log demand → log demand, actual drain=`Σmin(r_i,e_i)`, deficit riêng; nếu đổi completed-delivery rule, áp dụng mọi algorithm | Energy conservation: demand không bằng actual drain khi underfunded. Accounting addition giữ cũ; physical completion change là protocol mới | Thấp nếu thêm metrics; cao nếu đổi delivery semantics | Tiny underfunded fixture; cumulative actual drain≤initial total; fair rerun AC/D nếu đổi protocol |
| `src/run.py:61-64,84-85`; notebook loader `:143-161,301-320` | Hour-prefix/algorithm grouping → unique runID + map/source/config hashes + explicit paired cohort manifest | Không mix workload/epoch, tránh overwrites; separate scenario/algorithm seeds | Thấp | Different radius/maps same dims must not collide/mix; parameter/horizon mismatch rejected |
| `run.summarize`, `src/run.py:105-117`; optimizer metrics `:14-19` | rounds_survived/wholeenergy → completed service + reason/censoring + FND/HND/LND + energyK | Service stop, death và horizon khác events; observed-only FND mean cần censored-count công bố | Thấp | Off-by-one first death; all-dead vs search-fail; cap-censored reports |

Residual-aware objective có thể cải thiện risk alignment nhưng không đảm bảo service gain: service còn phụ thuộc connectivity và router. Reference scale phải freeze trong round; tránh dùng denominator tùy candidate tạo ranking không nhất quán.

### P2 — Parameter improvements giữ core AC identity

| Affected function/parameter | Proposed behavior | Justification/mechanism | Identity risk | Test |
|---|---|---|---|---|
| AC heuristic_weight; `parameters.py:21-22` | Sweep raw slope theo transition width định trước; normalized schedule chỉ là explicit control | `width10-90=2ln9/slope`; tránh step chỉ1round nếu clock là physical rounds | Thấp khi tuning raw slope; vừa normalizedpolicy | Capture t1748–1752 with frozen physical state; full trajectory held-out |
| AC chaos min/max; transition `:257-258` | Tune **nonzero** strengths theo desired uniform share; relation `s=u/[m(1-u)x_i]` dùng chẩn đoán scale | Nominal s không phải explorationpercentage; lớnN dilute learning. Không đề xuất bỏ chaos mặc định | Thấp fixedbound tuning; vừa size-adaptive strength rule | Multi-N entropy/share; probability normalization; late snapshots; lifetime |
| AC Q/tau/rho, deposit `:262-296` | Tune coupled scales theo observed E và retained mass, giữ calibrated finite bounds | Q/E, evaporation, chaos background cùng quyết định tau range; current headroom test chỉ conditional .015J | Thấp | Floor/cap occupancy, actuallostmass, no saturation assumption; common energyK/FND |
| AC distance_weight/g/ch_proportion | Small matched sweeps existing knobs; include default | Current distance-zero mean gain nhỏ/mixed; CH proportion affects aggregation/relay burden | Thấp tuning; changeCH fractions phải giữ declared search identity | 3D multiple maps; same budgets; same-pool vs full-policy interpretation |
| AC `_construct_candidate:204-207` | Control distinct starts per batch; giữ probabilistic walk/chaos | Default expected33.1distinct vs40; improve start coverage without taking D density/node pheromone | Thấp–vừa: sampling-policy variant | Explicit start diversity, retry treatment; paired equal evaluations; test late live<40 |
| Comparative runner | Publish calibration-inclusive evals/time; equal tuning budget + held-out seeds/maps | D thêm40initial candidates; tuning trainseed reuse creates selection optimism | Không đổi algorithm | Native-budget and matched-total-budget comparisons reported separately |

Không chọn tham số bằng performance trên chính validation seeds rồi gọi kết quả independent. Không tái dùng default train seeds24/25/26 làm toàn bộ validation khoa học.

### P3 — Research extensions, phải đặt tên variant/model mới

| Affected file/function | Extension | Mechanism và giới hạn | Identity risk | Validation |
|---|---|---|---|---|
| AC pheromone initialization/deposit/transition | Node pheromone hoặc actual routing-edge credit thay CH-path credit | Có thể improve credit alignment; khác solution memory của AC hiện tại và gần NodeACO/D | **Cao** | Factorial representation ablation; equal budget/objective; independent deployment tests |
| Shared `dropping_member_multi_hop_routing` | Graph route search cho uphill paths/backtracking hoặc lifetime-aware routing | Resolve demonstrated incompleteness; đổi feasible searchspace cho mọi algorithms | **Cao**, problem variant | Tiny uphill-path graph, no cycles, range, allcoverage; rerun all baselines |
| Evaluator `energy_consumption` | Workload-dependent aggregation cap, control overhead, loss/retry/delivery | Thay fixed2CHpackets và proxy service bằng protocol rõ; không sửa riêng AC | **Cao**, model variant | Packet conservation/original-reading delivery, demand/drain, fair calibration toàn bộ |
| AC outer lifecycle | Inner optimization convergence + per-physical-round clock riêng, global-best replay với revalidation | Tách search iterations khỏi physical rounds; tăng budget, khác current online policy | **Vừa–cao** | Fixed evaluated-candidate budget, state reset, dead-node revalidation, clock invariants |

## 8. Final scientific assessment

| Khả năng | Trạng thái khoa học |
|---|---|
| AC-ACO implemented incorrectly | **Chưa chứng minh lỗi core arithmetic trên current valid path.** Có literal-update khác và adaptation chưa đủ để claim paper fidelity; reporting bug là thật. |
| AC-ACO correct but poorly configured | **PARTIALLY SUPPORTED.** Beta timescale gắt và chaos share cao đã đo. Không có optimum evidence; bỏ transition chaos làm early energy xấu hơn. |
| AC-ACO optimizing inappropriate objective | **DEMONSTRATED về mismatch với lifetime goal.** Minimum total E không equal minimum danger; chưa quantify actual lifetime loss. |
| AC-ACO structurally inferior for current formulation | **SUPPORTED cho early-energy policies đã đo**, không chứng minh intrinsic/general inferiority. Candidate pools/memory/objective/params tương tác; chưa full lifetime. |
| D-ACO benefiting from unfair evaluation | **Có tuning/provenance/reporting risks; không thấy D-specific physical advantage** trong current shared simulator. Calibration extra phải công bố. |
| Multiple interacting causes | **Giải thích phù hợp nhất.** Objective alignment + sampling/reinforcement + adaptive clock + asymmetric tuning + reporting/model semantics. Chưa attribution percentages. |

Có thể viết defensible research statement: “Trên current fixed deployment, ba paired algorithm seeds cho thấy AC UWSN variant tiêu hao đầu10rounds cao hơn D variant6,66%; cost và tree coverage được kiểm tra độc lập. AC/D khác objective và search policy; không có dữ liệu current full lifetime để kết luận D có lifetime cao hơn hoặc AC sai nguyên bản.”

Không thể viết defensible statement: “AC-ACO original kém D-ACO vì chaos lỗi”, “tăng Q/bỏ chaos chắc chắn cải thiện lifetime”, “node48 historical là bottleneck current”, hoặc “mọi node đã chết khi notebook curve về0”.

### Câu hỏi chưa giải quyết và phép thử nhỏ nhất

1. **Current lifetime gap thực tế bao nhiêu?** Cần paired full trajectories trên frozen current map/source/config; report FND/service/reason/censoring/common K. Đây sustained computation chưa thực hiện; cần authorization riêng trước mở campaign tốn tài nguyên.
2. **Objective hay sampling đóng góp nhiều hơn?** Capture cùng candidate pool tại initial/mid/late residual snapshots; scoreE và residual-risk, so rank/winner/risk. Sau đó mới full-policy ablation.
3. **Beta jump có làm node quan trọng chết sớm?** Frozen snapshots ngay quanh t1750, kiểm tra entropy/CH choices/peakrisk; terminal-state evidence nếu run tới đó.
4. **Chaos strength mất adaptation do historical extrema?** Log bounds/previouscost/u-share trước và sau first deaths; rolling-window control là declared policy variant.
5. **Service stop có phải physical disconnect?** Terminal residual/tree state + independent full-graph reachability certificate và retry/protocol diagnostics; searchNone đơn lẻ chưa đủ.
6. **D có original research specification riêng?** Cần paper/spec với equations/algorithm mapping; hiện chỉ internally verified implementation.
7. **Deployment-wide generalization?** Separate scenario seeds, held-out algorithm seeds và maps/distributions; equal tuning budget; report uncertainty qua maps, không coi các round là independent samples.
