# Review độc lập framework AC-ACO candidate research

Ngày 14/10/2026, Asia/Bangkok. Đã đọc package `src/algorithms/research_acaco`, runner, proxy enumeration và 21 test cases. Review chỉ đọc source; chỉ viết báo cáo này và sửa claim quá rộng trong `design.md` theo yêu cầu điều phối. Không sửa algorithm, tests, scripts, maps hoặc historic CSV.

## Phán quyết hiện tại

**Không phát hiện critical defect làm sai campaign audited-map đã hoàn tất.** Có ba điểm phải sửa/ghi rõ trước final scientific claim: proxy không exact chỉ vì mọi node trực tiếp sink; proxy artifacts thiếu self-contained provenance; audited regression fixture dùng sai tau0 so với B0. Có API boundary bug ở nonadaptive exploration_max thấp và một robustness issue trong cách đếm feasible candidates.

Đã thông báo từng finding cho điều phối trước holdout. Campaign mới không cần hủy vì các default options đã chạy không chạm API boundary; counterexample surrogate là giới hạn estimator, không hidden evaluator/fitness change.

## Findings theo ưu tiên

### Important: điều kiện proxy exact quá rộng — đã sửa design

`surrogate.py:21–25` khởi tạo direct-sink TX nhưng vẫn lấy min với relay path. Actual router ưu tiên direct sink khi trong radius, không tìm cheaper energy path. Vì thế all-direct network vẫn có approximation error đáng kể.

Đã chạy counterexample độc lập: sensors(100,0,0),(200,0,0), sink0, radius200, S={node200}. `T200=.0002619283743J`, g200=.0001630607265J, proxy total=.0004136518163J, actual total=.0006113871119J; proxy thấp32,34%. Direct reachability không guarantee equality.

Correct claim: exact fixture cần direct-sink paths cũng là shortest projected paths g_i, cộng assignment không có outlier/role interactions. Tiny x1..8m fixture hiện có thỏa điều kiện do RX cost lớn so với gains TX ngắn. Không cần thay V2 implementation để che failure; report error và cân nhắc direct-first proxy control trong nghiên cứu sau. `design.md` đã sửa theo điều kiện đúng và thêm counterexample.

### Important: standalone proxy enumeration thiếu provenance

`check-proxy-ranking.py:84` output hiện chỉ groups/comparisons/count/time/note. Thiếu command, source fingerprint, generator hash, physics/params, actual topology coordinate/map hash. Development main metadata có hash script nhưng chưa tự bind JSON proxy output vào source state thực chạy.

Khuyến nghị thêm provenance và rerun enumeration vào file mới, giữ artifact cũ. Record hash topology canonical hoặc pickle riêng; không cần sửa production generator. Nếu chỉnh script sau main campaign, phân biệt source snapshot main vs proxy rerun thay vì khẳng định cùng source hash tuyệt đối.

### Important về validation claim: audited regression chưa dùng effective B0

`tests/test_ac_aco_research.py:43` audited=True cung cấp tau0=.01. Runner B0 thực dùng tau0=1, tau_min=.01. Test chứng minh observer/default-wrapper equality trên một scale hợp lệ khác, không exact audited config được mô tả.

Khuyến nghị bỏ tau0 override khỏi audited fixture hoặc thêm exact B0 case. Current-production default equality đã được test đúng. Main B0 vs V1-1 duplication là positive control tốt nhưng cả hai đều qua observer, không thay plain-vs-observer equality.

### Moderate API boundary: accepted nonadaptive option có thể fail constructor

`ResearchOptions.__post_init__` chỉ yêu cầu exploration_max≥.02 cho adaptive policy, nhưng `ResearchClustering.__init__` và `pre_round` luôn tạo `ProgressFeedback(maximum=exploration_max)` với minimum=.02. Đã reproduce `ResearchOptions(chaos_policy='normalized',exploration_max=0)` được accepted rồi ResearchACACO constructor raise ValueError. Các nonadaptive policy khác gặp cùng vấn đề.

Khuyến nghị chỉ validate/instantiate controls thực dùng hoặc clamp unused feedback controls hợp lý; thêm boundary test. Current defaults .25 không bị ảnh hưởng.

### Moderate robustness: positive energy chưa đồng nghĩa feasible/accepted

`diagnostics.py:203` lọc pool theo stage/search + positive_finite. D `_run_ant` còn có thể reject tree coverage hoặc nonfinite penalty sau evaluator. Observer vẫn có thể tính positive energy đó như feasible pool candidate. AC production không central reject mọi malformed tree, nên cũng cần phân biệt measured, physically valid, algorithm-accepted.

Current audited artifacts không có invalid tree/conservation/coverage/radius flags nên kết quả đã chạy không bị finding này. Để framework an toàn với scenarios/params mới, assert invalid records trước analysis hoặc count physically-valid pool riêng; ghi rõ evaluator records vs accepted candidates. Đừng ngầm drop defect rồi gọi đó là feasibility rate của algorithm.

### Minor: timing enumeration không hoàn toàn tách estimator/full route

`check-proxy-ranking.py:67` full_seconds bao cả `proxy.energy(chs)` và xây comparison record sau final evaluate, trong khi proxy_seconds chỉ chứa setup/additions. Ratio thời gian diagnostic đó hơi có lợi cho proxy. Dùng nó như coarse diagnostic, không precise computational-speedup claim; đưa estimator energy timing vào proxy bucket hoặc time router/evaluator riêng nếu công bố speed ratio.

## Những contract đã xác minh

- ResearchOptions mặc định để `ResearchACACO.init_params` giữ production clustering instance, không extra RNG hoặc policy logic. Runner B0 explicit weight0/floor.01; baseline production giữ default cũ hiện tại.
- V1 bỏ explicit omega exponent; E_m vẫn chứa distance, shared physics/router không bị sửa.
- V2 proxy additions đúng finite set-difference với strict nearest assignment/tie order, CH2 packets và member RX+DA. Softmax log-quality positive và scale-aware; không full route/tree evaluations trong construction. Pairwise tau và deposits full-tree-energy giữ nguyên.
- V3 giữ n-dependent legacy mixture scaled .1; V4/V5 cardinality-independent coefficient; V5 observe tại per-ant deposit sau một feasible evaluated cost, không future feedback hoặc residual deduction.
- V6 no direct probability chaos/no additive tau chaos; logistic per-source step đúng một lần cuối physical round, rho_eff bounded. First pool chưa chứng minh evaporation learning benefit; multi-round evidence bắt buộc.
- V7 retries cùng start cho một ant, chuyển ant sau successful deposit hoặc exhausted max attempts; khi ants>N reuse permutation theo cycle. Distinct start làm RNG trajectory đổi có chủ ý.
- R0 uniform ordered samples, không sort ids, không pheromone deposits. Additive baseline tau update vẫn diễn ra nhưng không ảnh hưởng random sampling.
- Observer dùng instance wrappers, không patch shared classes, không RNG calls hoặc second final evaluator call. Topology packet accounting độc lập chỉ đọc cây. Tests so sánh cả RNG state, tau, chaos, selected tree/cost với plain production.
- Per-physical-round residual không đổi trong search; runner chỉ subtract winner sau plan, giữ T3500 dù short trajectory. Setup/pre-round surrogate cache time và estimated proxy operations được log.
- D calibration counts và energy distributions tách khỏi search pool; D winner giữ fitness riêng, không bị gọi minimum energy. Equal-total budget D40total chia20 calibration+20 search ở first round; không so20 pool với40 pool mà giấu calibration.

## Kiểm chứng thực chạy

Lệnh reviewer:

```powershell
& 'C:\Users\LOQ\miniconda3\python.exe' -B -m pytest tests/test_ac_aco_research.py -q
```

Kết quả: **21 passed**, .47s test time. Một warning pytest cache do sandbox/path hiện hữu, không failed assertion. Đã chạy hai API/proxy reproduction nhỏ ngoài test suite; không ghi artifacts hoặc đổi algorithm state campaign.

Đọc lại raw `development-audited/pools.jsonl` và metadata:

- 140 runs, **1 topology audited-uniform-100-41**, seeds24–33.
- Tất cả AC/R0 singles search40/evaluator40/attempt40; D0 evaluator80 gồm calibration40, search40; D40total evaluator40 gồm calibration20, search20.
- Invalid probability count0; không record nào sai conservation/topology/radius/all-live coverage.
- B0 và V1-1 candidate_records **exact equal trên cả10 seeds**.
- Rehash48 initial files trong `before.json`: **0 changed**; main metadata source_unchanged=true.
- Proxy artifact108 groups,1080 full evaluations; mọi group10 additions feasible. Extra calls thuộc diagnostic riêng, không candidate budget main.

Không chạy full lifetime hoặc optimizer campaign. Điều phối báo broader legacy suite66pass/2failed do old normal-map tests gọi current uniform default; production map generator fingerprint unchanged. Đây là thông tin từ điều phối, không fresh execution của reviewer. Missing optuna collection cũng là môi trường/legacy scope riêng, không coi suite toàn repo green.

## Thống kê và khả năng suy rộng

Audited campaign chỉ một deployment; 10 paired algorithm seeds đo stochastic variation conditional topology. Không coi40 ant hoặc108 proxy prefix groups là independent topology replicates. Proxy diagnostic gồm9 compact N12 deployments, prefixes trong cùng topology correlated; all1080 feasible nên chưa kiểm tra ranking trong wide/disconnected regimes.

Broader development reuse scenario seeds51/52 qua distribution/count: các graphs có thể phụ thuộc draws chung, nên không gọi18 independent units hoặc dựng deployment CI như i.i.d. Điều phối đã thống nhất label exploratory và dùng holdout18 unique scenario seeds11–28 trên các distribution/count cells; reserved algorithm seeds74–77. Average paired seed effects trong mỗi topology rồi mới mean/CI trên topology. Phân tầng distributions/N vẫn cần trình bày, vì heterogeneous scenarios là fixed design, không representative random sample toàn UWSN.

Combinations phải giữ corresponding singles trong same cohort; development lựa combinations là selection stage, holdout không retune. V6 multi-round cohort cần matching B0/V6 và V2/V2+V6; khác first-round energy chưa chứng minh retained-memory benefit. Full-lifetime implication vẫn unverified.

## Câu hỏi/chỉnh sửa còn lại

1. Thêm provenance proxy rerun, corrected audited test và boundary controls rồi báo result fresh.
2. Final analyzer có assert all topology/coverage/finite flags và đúng independent topology unit không? Chưa có analyzer khi reviewer đọc.
3. Nếu V2 rank gain chỉ xuất hiện compact N12, có tồn tại trên500m/relay/outlier-heavy scenarios không?
4. V6 memory hypothesis có được hỗ trợ bằng multi-round tau concentration/entropy/diversity/stagnation, hay chỉ probability policy difference?
