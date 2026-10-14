# Thiết kế nghiên cứu candidate construction AC-ACO

Ngày 14/10/2026, Asia/Bangkok. Audit chỉ đọc source; không sửa production, map hoặc CSV lịch sử. Mọi đề xuất hiệu quả dưới đây là giả thuyết; kết quả chạy nằm trong báo cáo thực nghiệm riêng.

## 1. Phát hiện quyết định trước khi triển khai

Working tree **khác latest audit**. HEAD `0f89c484dbd7997413167ab9759779650913a271`; thay đổi có sẵn gồm AC clustering, AC parameters, runner, `fitness.py` untracked và các thư mục nghiên cứu. Giữ nguyên tất cả.

Current defaults có `load_weight=.25`, `tau_min=1`; audit/HEAD có `load_weight=0`, `tau_min=.01`. Wrapper hiện vẫn thực thi normalized absolute load-CV khi weight khác 0. `load_power`, `reference_memory`, `calibration_ants` mới chưa được wrapper AC sử dụng; `fitness.py` chưa được import vào đường AC thực chạy. Comment "powered relative-load penalty" không mô tả actual code. Không đưa module hoặc score đó vào B0.

Tách hai contract:

- **Production-current**: constructor/default research wrapper phải giữ behavior hiện tại, kể cả CV option; không đổi defaults.
- **B0 audited-original energy-only**: runner chủ động cung cấp `load_weight=0`, `tau_min=.01`; mọi variant lấy cùng cấu hình này, chỉ đổi operator được khai báo. Đây là baseline khoa học matching audited configuration, không gọi nó là current-default. Kiểm tra seeded equivalence với production AC được cấp đúng hai override trước khi dùng kết quả.

Map audited hiện còn nguyên SHA-256 nhưng là **uniform, seed41**, không phải clustered như mô tả task. Metadata: N100, 500×500×500m, sink(250,250,0), .6J/node, radius200m, `num_cluster_points=0`. Latest audit ghi 19 node trực tiếp đến sink. Dùng map này để replay audit và công bố discrepancy; các topology clustered phải tạo thành artifact riêng với scenario seeds riêng, không overwrite `map.pkl`.

Hash map: `f5e6ebb66f9f361f5d91cceda44dff85e7eca4d1dc86877a74ab81a6216f1af8`.

Fingerprint source đã đọc:

| File | SHA-256 |
|---|---|
| `src/algorithms/ac_aco.py` | `41e1bbeedb405e3482a2ca8b9d8c55f4695ff5dd4e47871ef903a5b6f7418a6b` |
| `src/algorithms/clustering/ac_aco/ac_aco.py` | `7305bb88278491925d3ca146509421ef59d2a09c03e7ef88f7a32a2345df7cde` |
| `src/algorithms/clustering/ac_aco/parameters.py` | `a0e5f428c9910254786f290ce961f7c1438816fbb2c757fa805974575da68a92` |
| `src/algorithms/routing/routing.py` | `61cc27a9cc63ccd3a23cb024e1ac60d70489a6ea9f13fa32568a9389feeca338` |
| `src/evaluate.py` | `e448478de8710dc2f247cb801912954789bb2d2ca431abe71e0194c014a25f4c` |

Effective current parameters: ants40, attempts/ant10, CH proportion.2, alpha1, gamma.1, distance_weight1, beta[1,5], slope5, schedule raw; rho[.1,.6]; chaos[.05,.30], logistic r3.61, seed.37; Q.01, elite.1, load_weight.25, load_power2, reference_memory.8, calibration_ants40, tau0=1, floor1, ceiling20, hopping_factor.4. HyperParameters: T3500, P0=.1, L200, rate10000, E_elec=5e-8, E_integrate=5e-9, frequency30000Hz, spreading1.5. B0 overrides chỉ weight/floor đã nêu.

## 2. Bản đồ 10 chức năng và toán học actual

Line numbers theo snapshot đọc trong phiên này; xem manifest thực nghiệm để kiểm tra drift.

| Chức năng | Hàm actual | Quy tắc |
|---|---|---|
| CH count | `ACACOClustering.prepare_round`, line136 | `k=min(n,max(1,round(.2*n)))`; Python round ties-to-even |
| Start node | `_construct_candidate`, line210 | uniform `rng.choice`; mỗi retry chọn start mới; các ant có thể trùng start |
| Transition | `_transition_probabilities`, line225 | log-space tau/residual/distance/E_m; additive chaos rồi normalize |
| Chaos generation | `logistic_step`, line28; constructor100 | N bước logistic liên tiếp từ .37; không lấy RNG draw; mỗi source sống advance một lần cuối physical round |
| Adaptive evaporation | `evaporation_rate`, line32; `prepare_round` | linear physical-round schedule, t1 tương ứng simulator round0 |
| Deposit | `deposit`, line268 | pairwise **construction-order edges**, Q/(40*energy); elite .1Q/energy |
| Cluster construction | `create_clusters`, line159 → `build_clusters`, clustering.py5 | nearest CH theo Euclid3D; ngoài radius thành outlier |
| Routing | `dropping_member_multi_hop_routing`, routing.py110 | greedy sink-closer relay; có thể drop member để unblock parent |
| Candidate energy | `ACACO.plan_round`, wrapper40 → `Evaluator.energy_consumption`, evaluate.py40 | một evaluator call khi router trả root; reject nonfinite/nonpositive |
| Winner | `ACACO._best_candidate`, wrapper103 | weight0: min(totalE,orderedCHtuple); weight>0: normalized E+CV |

Ký hiệu `L_t` sống, `A` chưa chọn, `i` CH trước đó, `r_j` residual, `x_i` logistic, `M=40`:

\[
\rho_t=.6-\mathrm{clip}(t/3500,0,1)(.6-.1),\qquad
\beta_t=1+4\sigma(5(t-1750)).
\]

Raw beta gần1 đầu run và gần5 cuối run; beta nhảy rất nhanh quanh t1750. Đây là physical clock, không phải số ant/evaluation. Không thay horizon thành số round trajectory ngắn: giữ T3500 để schedule không bị đổi khi giới hạn runtime.

\[
s_t=.05+.25\,\mathrm{clip}\frac{E_{best,t-1}-E_{low}}{E_{high}-E_{low}},
\]

với missing/suy biến bounds trả .05. Bounds là extrema của mọi feasible candidate trước đó, không rolling window. Trong first round s=.05.

\[
w_{ij}=\tau_{ij}^{\alpha}(r_j/d_{ij}^{\omega})^{\beta_t}E_m(d_{ij})^{-\gamma},
\quad p_{ij}=w_{ij}/\sum_{j\in A}w_{ij}.
\]

Distance cache clip≥1e-12. Log-softmax chống overflow; tau/residual/cost invalid bị loại khỏi trọng số. Nếu mọi log-weight invalid thì uniform fallback. Các available trong lifecycle chuẩn đều có residual>0.

\[
\widetilde p_j=\frac{p_j+c_i}{1+|A|c_i}
=(1-u_i)p_j+u_i/|A|,\quad c_i=s_tx_i,
\quad u_i=\frac{|A|c_i}{1+|A|c_i}.
\]

`x_i` thay đổi theo source, nhưng trong cùng transition disturbance như nhau cho mọi target. Nó pha uniform, không ưu tiên target có chaos khác. First source0 có x=.841491, n99, s=.05 cho u≈.8064. Đây là hệ quả số học, không chứng minh chaos gây hại.

Các ant deposit ngay sau feasible candidate; ant sau nhìn thấy deposit ant trước. Cuối round:

\[
D_{ij}=\sum_{a:(i,j)\in H_a}\frac{Q}{ME_a},\qquad
\tau^{mid}_{ij}=\mathrm{clip}((1-\rho_t)(\tau_{ij}+D_{ij})+s_tx_i,\tau_{min},\tau_{max}),
\]
\[
\tau^{next}_{ij}=\min(\tau_{max},\tau^{mid}_{ij}+\mathbf1_{(i,j)\in H^*}\theta Q/E^*).
\]

`H_a` là ordered CH path, không phải route edges. Ant mass chịu evaporation, elite mass không chịu evaporation trong round đó; per-ant tau tạm vượt ceiling được phép trước end-round clamp. Dead rows/diagonal không update; construction chỉ dùng live nodes.

## 3. Physical distance và mismatch construction–routing

Trong clustering, CH kế tiếp **không cần ở trong radius của CH trước**. Router dựng parent độc lập sau khi có cả CH set và members. Vì vậy d(i,j) trên construction path không trực tiếp trả một TX trong cây. Hai CH gần nhau có thể chỉ phục vụ cùng một vùng, để vùng xa thành outlier; ngược lại hai CH xa nhau có thể giảm nhiều member TX và relay packet load. Đây là mismatch surrogate cần đo, không theorem "mọi proximity bias đều xấu".

Final router có thể khác theo insertion-order dù CH set giống nhau, do greedy queue và member dropping. Pairwise pheromone vẫn có thể học order có ích. Chỉ thay heuristic; chưa kết luận pairwise representation vô dụng.

Không loại physical distance khỏi evaluator, nearest-CH assignment hoặc range checks. Với d bằng m:

\[
T(d)=P_0(d/1000)^{1.5}a^{d/1000}L/R_b,\quad R=LE_{elec},\quad D=LE_{integrate}.
\]

Gọi q_i tổng packet-equivalents của con:

| Node | Packets gửi | Energy |
|---|---:|---|
| Member leaf | 1 | T(d) |
| Ordinary relay | 1+q_i | q_iR+(1+q_i)T(d) |
| CH, kể cả CH relay | **2** | q_i(R+D)+2T(d) |
| Sink | không charge | 0 |

CH rỗng vẫn TX2, DA0. CH DA **per received packet**, không một constant DA per CH. Source hiện tại khác memory AGENTS cũ. Mọi surrogate phải dùng packet convention actual hoặc khai báo approximation.

Router yêu cầu parent trong radius, residual>0 và sink distance giảm nghiêm ngặt. Greedy score `h*sumResidual/residual_parent+(1-h)*(hop²+base_parent²)/base_source²`. Không dùng T(d) để tối ưu chính xác route. Node đang là member của CH gây blocked condition; có thể tháo một member và đưa vào routing queue. Full-graph connected chưa guarantee router feasible nếu cần uphill hop.

Simulator chỉ trừ winner consumption sau search, clamp residual≥0; optimizer không trừ energy. Logged demand cuối đời có thể lớn hơn available energy; giữ contract và không gọi đó là actual drain. Fresh simulator run reset physical state nhưng không reset algorithm pheromone: mỗi độc lập run phải fresh algorithm instance.

## 4. V1: distance ablation có kiểm soát

Quét omega∈{0,.25,.5,1}, giữ gamma=.1 và tất cả tham số khác. omega0 chỉ bỏ **explicit** distance exponent; E_m vẫn chứa T(d). Không gọi V1 là "distance-free".

Đo mean/min/p10 totalE, CH coverage/outliers trước router, số dropped members, hop length, packet/RX/DA contributions, all-pairs CH distance và Jaccard. Giảm outlier nhưng energy tăng vẫn có thể xảy ra vì nhiều empty CH TX2 hoặc relay compression khác. Không thay default theo một mean trên một topology.

## 5. V2: partial energy surrogate và marginal transition

### 5.1. Graph cache không gọi final evaluator cho partial tree

Với L sống, dựng directed graph: sensor u→v iff d(u,v)≤radius và baseDistance(v)<baseDistance(u); sensor u→sink iff baseDistance(u)≤radius. Mỗi edge sensor→sensor có incremental one-packet cost T(d)+R, edge tới sink chỉ T(d); sink RX không charge. Directed strict sink decrease tạo DAG.

Cache shortest cost g_i đến sink bằng dynamic programming theo baseDistance. Cache TX pairwise có thể dùng evaluator **primitive E_tx**, không gọi `energy_consumption`. Compute g tốn O(N²) mỗi residual/live snapshot sau distance cache; không phụ thuộc partial CH set. Đó là projected single-packet forwarding qua ordinary relays, không certificate actual greedy feasibility.

Node unreachable dùng finite fallback:

\[
g_i^{fallback}=(N+1)(T(radius)+R+D).
\]

Đồng thời ghi disconnected mask. Không tuyên bố fallback là feasible energy; đó là penalty có đơn vị J. Scalar này tránh NaN/Inf và đủ lớn so với một đường đơn giản≤N hops tại radius, nhưng không guarantee router feasibility hoặc correct rank giữa unreachable choices.

### 5.2. Hàm partial set

Với S selected CH, gán ordinary u∉S tới nearest selected CH c(u) nếu trong radius; tie theo stable insertion order như builder. Gọi C(S) các member covered và O(S) các outlier:

\[
\widehat E(S)=
\sum_{u\in C(S)}[T(d(u,c(u)))+R+D]
+\sum_{j\in S}2g_j
+\sum_{u\in O(S)}g_u.
\]

Empty S: C=∅, O=L nên `Ehat(∅)=sum g_u`. Nó mô tả projected ordinary forwarding của toàn mạng, không gọi builder với empty CH. Singleton/partial/disconnected đều finite.

Member TX, CH RX và CH DA được charge đúng một lần cho member packet. CH2g dự đoán hai packets phát ra và incremental relay TX/RX. Outlier g dự đoán một packet riêng. Relay own source packet nằm trong term vai trò của node đó; không cộng một lần nữa cho từng path đi qua relay.

Thêm CH có thể giảm member distances/outlier forwarding nhưng tăng CH TX2; delta có thể âm,0 hoặc dương:

\[
\Delta_j=\widehat E(S\cup\{j\})-\widehat E(S).
\]

Candidate count vẫn đúng k; không dừng chọn CH chỉ vì mọi delta>0. No new final fitness.

### 5.3. Assumptions và failure cases

- g cho phép mọi alive node làm relay và chọn shortest cost; actual router greedy, blocked/drop có thể khác. Vì cùng sink-closer constraint nên proxy không đưa uphill path vào optimistic reference.
- Intermediate CH có compression và DA theo q; g giả sử ordinary incremental forwarding, bỏ role interactions. Có thể overestimate forwarding sau CH relay và underestimate DA tại intermediate CH.
- Cluster member bị router tháo sẽ thay packet path; proxy nearest assignment chưa mô phỏng dropping.
- Paths shared chưa cộng congestion/energy depletion; packet costs linear có thể cộng incremental load, nhưng không resolve physical simultaneous role/parent consistency.
- Ehat là set surrogate; final route có order dependence. Hai permutation cùng set có Ehat bằng nhau nhưng actualE khác.
- Residual chỉ quyết định sống/reachability; surrogate tối ưu energy theo task, chưa đưa residual-risk fitness. Low residual node vẫn có thể được chọn như baseline; không dự đoán lifetime benefit.

### 5.4. Positive monotone transformation

Tại mỗi transition, scale s=`max(median(abs(delta)),epsilon_phys)` có đơn vị J. Epsilon gắn machine epsilon với positive characteristic energy, tránh s0; không fit từ ba seeds cũ.

\[
\log H_j=\mathrm{clip}(-\Delta_j/s,-40,40),\quad
P(j\mid i,S)\propto\tau_{ij}^{\alpha}H_j^{\beta_t}.
\]

H>0, finite, nonincreasing theo delta ở fixed candidate-scale; clipping tạo plateaus ở extreme, không strictly decreasing toàn miền. Delta âm được thưởng, dương bị giảm; delta0 được H1. Softmax log-score sau trừ max tránh overflow. Vì scale từ cùng transition, rank được giữ trong miền không clipping; scale đổi khi candidate set đổi không làm mất unit invariance. Với all equal deltas, heuristic không phân biệt và tau còn quyết định.

V2 thay cả residual/inter-CH/E_m transition heuristic bằng H; vẫn tau pairwise và final E objective. Deposit tiếp tục Q/full-tree-energy để reward không bị âm hoặc đổi đơn vị. Đây là credit alignment một phần qua construction, **chưa phải marginal credit deposit**. Không deposit Q/delta.

### 5.5. Cost và accuracy diagnostic

Vectorized additions dùng nearest-distance cache của S: mỗi j cập nhật `min(currentNearest,d(:,j))`, loại j khỏi member/outlier term và thêm CH2g_j. Work O(N·|A|) mỗi transition, O(kN²) mỗi ant; incremental/vectorized toán học không miễn overhead runtime. Không full-router/evaluator calls trong construction. Log proxy call/vector element counts và setup/runtime riêng.

Diagnostic nhỏ riêng campaign: enumerate additions S+j trên networks nhỏ; final trees chỉ evaluate nếu router trả feasible, giữ same prefix order và append j. Spearman/Kendall ranks, top-choice/top-k agreement, proxy-final residuals, runtime, explicit diagnostic evaluator count. Không trộn extra diagnostic evaluations vào equal-budget main pool.

Fixture dễ kiểm chứng: mọi node và sink trực tiếp trong radius **và g_i bằng direct-sink TX, không có projected relay path rẻ hơn**; actual tree cost khớp Ehat(S) với nonempty S vì CH2TX và member RX/DA exact. Direct reachability riêng nó không đủ: proxy shortest path vẫn có thể chọn relay dù actual router nối CH trực tiếp sink. Counterexample hai node x100/200m, sink0, radius200, S={node200}: proxy .0004136518163J, actual .0006113871119J (−32,34%). Đây là approximation optimistic, không lỗi arithmetic. Fixture đa hop/outlier/disconnected nhằm phát hiện approximation failure, không lựa parameter cho correlation đẹp. Rank trên feasible-only subset phải ghi fraction excluded; high correlation có selection bias nếu nhiều additions infeasible.

## 6. Các chaos policies độc lập

### V3: reduced legacy chaos

Chỉ probability disturbance dùng `.1*s*x`; additive pheromone disturbance giữ baseline. Effective uniform share vẫn n*c/(1+n*c), tức **vẫn phụ thuộc cardinality**. Không ngụy trang nó thành V4. Nếu cả selection và tau chaos cùng giảm thì đó là một variant khác, phải label thêm.

### V4: cardinality-independent mixture

\[
\lambda_i=s_tx_i,\qquad p'_j=(1-\lambda_i)p_j+\lambda_i/|A|.
\]

Không còn n khuếch đại coefficient; actual lambda≤.30. Giữ additive pheromone baseline để isolate direct selection policy. Entropy có thể còn phụ thuộc shape p và n, nhưng coefficient không tự lớn theo N.

### V5: observed-progress feedback

Feedback update **sau mỗi feasible candidate được observed**, before construction candidate sau. Best initialized ở first observed cost; không dùng future candidate, residual vật lý hoặc extra evaluator. Relative improvement q=clip((oldBest-newBest)/oldBest,0,1), EMA z←.8z+.2q; h reset0 nếu cải thiện vượt numeric tolerance, ngược lại h←h+1. Reset feedback mỗi physical round vì objective/residual có thể đổi; failed routes không cung cấp energy feedback.

\[
b_h=.02+(.25-.02)(1-z)\frac{1-\cos(2\pi(h\bmod8)/8)}2,
\quad\lambda_i=b_hx_i.
\]

Dùng actual lambda trong mixture cardinality-independent. b∈[.02,.25] nhưng **actual lambda∈[0,.25]**, floor .02 không phải actual exploration floor vì nhân x. Pulse tránh permanently maximum khi stagnation, deterministic theo observations/chaos. Phase modulo8 là design choice chưa chứng minh tối ưu; EMA nhận q nhỏ nên 1-z thường gần1, feedback improvement yếu. Cần log b, lambda, z, h và best-so-far để tránh gọi schedule thuần cyclical là strongly adaptive.

Additive pheromone disturbance giữ baseline để isolate direct probability adaptation. V5 không advance logistic mỗi ant; x_i vẫn state physical round. Không combine V5/V6 vì khác hypothesis.

### V6: chaos chỉ điều khiển evaporation

\[
\rho^{eff}_{i,t}=\mathrm{clip}(\rho_t(1-.5x_i),\rho_{min},\rho_{max}),
\]
\[
\tau^{mid}_{ij}=\mathrm{clip}((1-\rho^{eff}_{i,t})(\tau_{ij}+D_{ij}),\tau_{min},\tau_{max}).
\]

Giữ elite update baseline. **Không direct probability mixture, không additive tau chaos**; x_i chỉ qua rho_eff. Logistic source advance một lần sau end-round update như baseline, không RNG draws. Per-source signal giữ deterministic x_i representation có sẵn; global scalar sẽ đổi design và cần separate ablation. Row-wise memory heterogeneity là hệ quả per-source, không synonym uniform global retention.

First round rho≈.6 nên x≈.84 cho rho_eff≈.35; cuối schedule rho_base=.1 thì rho_eff bị clip về .1 với mọi x: chaos hết tác dụng giảm evaporation. Memory retention cao có thể duy trì bad paths, tăng concentration và stagnation; không assume gain. Log entropy/diversity/floor/cap/row concentration/rho_eff và best energy qua nhiều rounds. First-round pool không thấy end-round evaporation vì chỉ xảy ra sau pool; V6 khác first pool chủ yếu do bỏ direct probability chaos. Muốn test memory hypothesis phải short trajectories hoặc fixed residual repeated search rounds.

## 7. V7, R0, D comparator và ngân sách

V7 distinct start nodes per ant batch (cycle mới khi M>N), retry của cùng ant giữ start đã chỉ định. Điều này thay sampling policy; không copy D density/fitness. Report distinct initial starts, retry treatment và total starts observed. B0 expected distinct starts≈N*(1-(1-1/N)^M)≈33.1 cho N100/M40.

R0 uniform ordered CH samples không hoàn lại trong một candidate, evaluate cùng router/energy, ngân sách feasible40 và cap attempts công bố. Set uniqueness ignore order; giữ original order cho actual routing. Không dùng R0 từ uniform set nhưng sort ids vì sort sẽ đổi router-order distribution.

D dùng node pheromone, distinct starts, density depletion và load^p/density fitness; chỉ independent comparator. Calibration thêm tối đa40 feasible reference candidates; counters và time phải include calibration. Pool-min-E statistic có thể lấy từ D observations nhưng không gọi D winner là minimum energy nếu objective của D khác.

Main comparison feasible40 có thể work khác khi routing failure khác: báo attempts/routing/evaluator calls, wall time; thêm total-route/evaluation cap comparison. V2 extra vectorized proxy work không tăng full evaluator count, nhưng vẫn tăng CPU cost; equal evaluator count không bằng equal runtime. Cache initialization cần tính vào end-to-end time và tách setup time.

Instrumentation không thêm RNG draws, không ghi tau/cost/residual, không rebuild route để collect diagnostics. TX/RX/DA split được đọc từ cây/packet accounting đã evaluated; nếu re-evaluate phục vụ validation, tính riêng và không feedback. Failed routing attempts không energy sample. Diversity Jaccard mean trên cặp feasible CH sets; uniqueness unordered nhưng min tie-break vẫn ordered. Outlier trước router khác với node không delivered: router có thể giữ mọi outlier trên cây.

Không coi 40 ant correlated có pheromone live là 40 deployments độc lập. Pair seeds24–33 cho development trên audited map; independent scenario seeds là generalization unit. Reserve algorithm holdout seeds. CI qua seeds một map chỉ nói stochastic variability conditional map; CI qua multiple independent scenarios mới hỗ trợ deployment-generalization. Không chọn combination solely để maximize development seeds; report singles cùng combinations và interaction.

## 8. Nguồn, kiểm chứng và identity

Nguồn repository đã đọc: latest `plans/reports/research-audit-261014-0902-acaco-vs-daco.md`, diagnostics/integration provenance; AC README; AC wrapper/clustering/parameters; D wrapper/clustering; shared builder/router/evaluator/simulator/network/map generator/hyperparameters; `test_ac_aco_equations.py`, `test_ac_aco_pheromone.py`, `test_ac_aco_vectorization.py`, `test_ac_aco_calibration.py`.

Repository không chứa paper PDF trong file inventory; paper gốc được liên kết từ README/audit. Đã mở [PDF chính thức Zhou–Chen–Cao (2025)](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf). Paper dùng radio WSN; repo khai báo adaptation underwater3D. Không coi kết quả paper là bằng chứng các variant mới. Existing audit chỉ ra khác update ordering (ant deposits chịu evaporation), energy-as-cost, per-physical-round lifecycle và window interpretation. Các lựa chọn marginal/feedback/evaporation-only ở đây là thiết kế nghiên cứu mới, không equation được paper xác nhận.

| Variant | Identity | Mathematical claim có thể kiểm tra | Performance chưa tự suy ra |
|---|---|---|---|
| B0 | Audited UWSN energy-only AC baseline | seeded equivalence/operators | không guarantee optimal/lifetime |
| V1 | knob ablation AC | explicit d exponent giảm | E_m vẫn distance |
| V2 | new marginal-heuristic AC | positive monotone H, finite partial surrogate | proxy/final ranking và lifetime |
| V3/V4/V5 | selection-chaos policy variants | normalized finite probability, bounds/determinism | exploration có hữu ích hay không |
| V6 | evaporation-only chaos AC | rho bounds, no additive/direct chaos | memory gain phải đo multi-round |
| V7 | start-policy AC | distinct starts contract | coverage/energy improvement |
| R0 | random comparator | uniform ordered sampling, budget | không là AC variant |

## Câu hỏi chưa giải quyết

1. Marginal ranking còn tốt khi relay có role compression và dropping nhiều không?
2. Pairwise construction credit còn là bottleneck sau khi heuristic tốt hơn không? Đây là follow-up separate representation experiment, không được lẫn vào hiện tại.
3. V6 cải thiện retained learned information hay chỉ thay first-round randomness? Cần fixed-state repeated rounds và physical trajectories.
4. Pulse8/EMA có adaptation thực chất hay gần cyclical exploration? Cần observed response plots và heldout tests, chưa tuning theo ba seeds cũ.
5. Candidate-pool gain có giữ qua clustered/uniform/normal và N50/100/200, feasibility/lifetime không? First-round evidence chưa trả lời lifetime.
