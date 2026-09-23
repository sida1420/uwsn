# UWSN repository memory

## Muc tieu

Repo mo phong mang cam bien khong day duoi nuoc (UWSN) trong khong gian 3D.
Moi vong mo phong chon cac cluster head (CH), tao cay dinh tuyen
`base station -> CH -> sensor thanh vien`, tinh nang luong tieu thu, tru nang
luong con lai va lap den khi tat ca node chet, khong con route hop le, hoac dat
`T_max`.

Repo hien la mot prototype Python nho, chua co README, file dependency hay test
suite. Entry point chinh la `src/run.py`.

## Ban do file

- `src/run.py`: nap map, khoi tao simulator, chay tung algorithm trong
  `ALGORITHMS`, ghi `results_<algorithm.name>.csv`, roi in tong ket.
- `src/network.py`: `NetworkInstance`, du lieu vat ly bat bien cua mot map va
  hai bang khoang cach duoc tinh san.
- `src/simulate.py`: loop theo round; trang thai nang luong/alive node nam tai
  day va duoc tao moi cho moi lan `run()`.
- `src/node.py`: node cua cay route mot round. Base co id `-1`; CH co
  `isCH=True`; `prev` la cha va `nxts` la danh sach con.
- `src/algorithms/base.py`: interface `ClusteringAlgorithm.plan_round()`.
- `src/algorithms/clustering.py`: gan sensor vao CH gan nhat va tao route truc
  tiep, khong co CH-to-CH/multi-hop.
- `src/algorithms/aco/aco.py`: implementation dang dung, ten `SimpleACO`.
- `src/algorithms/aco/aco_parameters.py`: tham so rieng cua ACO.
- `src/evaluate.py`: mo hinh nang luong cua mot cay route.
- `src/hparameter.py`: tham so chung cua simulation/mo hinh acoustic.
- `src/point.py`: vector/toa do 3D; `abs(Point)` tra khoang cach Euclid.
- `src/map_gen.py`: sinh `map.pkl` ngau nhien va `map_3d.svg`.
- `src/visual.py`: ve map/cay route bang matplotlib 3D.
- `src/module.py`: lop cu/khong duoc luong hien tai su dung.
- `src/enviroment.py`: file rong.
- `plan.md`: ghi chu thiet ke ban dau; encoding hien thi bi loi neu doc sai UTF-8.

## Du lieu va state

`map.pkl` la dictionary gom:

`width`, `height`, `depth`, `base_pos`, `sensors`, `init_energy`, `radius`.

Map hien tai co 100 sensor trong khoi 500 x 500 x 500 m, base tai
`(250, 250, 0)`, nang luong dau 0.6, ban kinh lien lac 100 m. File pickle tham
chieu `point.Point`, do do khi nap phai de `src` tren Python import path; chi nap
pickle tu nguon tin cay.

`NetworkInstance` chi giu state bat bien. `Simulator.run()` tao moi:

- `residual_e = [init_energy] * N`
- `live_nodes = [0, ..., N-1]`

Quy uoc id sensor chinh la index trong `sensors`, `residual_e`, `base_dists` va
`dist_matrix`. Khong duoc sap xep/xoa truc tiep cac list nay neu khong cap nhat
toan bo id.

## Luong chay

1. `run.main()` nap `map.pkl` thanh `NetworkInstance`.
2. Voi moi class trong `ALGORITHMS`, tao algorithm va goi
   `Simulator.run(algorithm)`.
3. Moi round, simulator goi `algorithm.plan_round(live_nodes, residual_e)`.
4. `ACOClustering` cho `num_ants` kien thu cac tap CH. So CH moi lan la
   `max(1, round(CH_proportion * so node song))`.
5. Xac suat chon node `i` ti le voi
   `pheromone[i]^alpha * (residual_e[i] / distance_to_base[i])^beta`.
6. `direct_routing()` gan moi non-CH vao CH gan nhat. Tat ca canh sensor-CH va
   CH-base deu phai `<= radius`; chi can mot canh vuot radius la candidate bi
   loai.
7. Candidate hop le co tong nang luong thap nhat trong round duoc chon. Mui
   pheromone bay hoi voi `rho`; cac CH thang duoc cong `Q / cost`, roi clamp
   vao `[tau_min, tau_max]`.
8. `Evaluator` tinh nang luong tung sensor, simulator tru khoi residual energy,
   loai node co energy `<= 0`, va ghi `round`, `alive_nodes`, `round_energy`.

Algorithm giu pheromone qua cac round, nhung moi algorithm instance chi nen
dung cho mot simulation run neu muon cac lan benchmark doc lap hoan toan.

## Mo hinh nang luong

Khoang cach trong map la met, nhung attenuation duoc tinh theo kilomet:

`d_km = d_m / 1000`

`A(d) = d_km^spreading_factor * attenuation_coeff^d_km`

`E_tx(d) = P_0 * A(d) * packet_size / transmission_rate`

`E_rx = packet_size * E_elec`

`E_da = packet_size * E_integrate`

- Sensor thuong: `E_tx(distance_to_CH)`.
- CH: `member_count * E_rx + E_da + E_tx(distance_to_base)`.
- Base station khong bi tinh nang luong.

Luu y: CH hien chi tra `E_da` mot lan, khong nhan voi so packet/member; packet
gui tu CH cung khong tang kich thuoc theo so member. Day la lua chon/han che cua
mo hinh hien tai, can xac nhan truoc khi doi.

## Trang thai da kiem chung (2026-09-23)

Lenh:

```powershell
python -m compileall -q src
python src/run.py
```

Code compile thanh cong, nhung map hien tai dung ngay round 0:

`[SimpleACO] round 0: no feasible routing found, stopping`

Nguyen nhan cau truc: route bat buoc moi CH noi truc tiep toi base trong ban
kinh 100 m, trong khi map hien tai chi co 1/100 sensor cach base <= 100 m
(min 43.83 m, mean 337.37 m, max 555.61 m). ACO chon khoang 5 CH cho 100 node;
gan nhu moi tap CH se co CH vuot ban kinh, va mot CH gan base cung khong the phu
toan bo 500 m cube. Vi vay `results_SimpleACO.csv` chi co header/khong co round.

Huong sua can quyet dinh theo muc tieu nghien cuu, khong nen ngam thay doi:

- tang `radius`/thu nho map;
- sinh deployment phu hop voi direct routing;
- hoac them multi-hop sensor/CH routing (thay doi bai toan va energy model).

## Cach mo rong algorithm

1. Tao subclass cua `ClusteringAlgorithm`.
2. Implement `plan_round(live_nodes, residual_e)` va tra `Node(-1)` root hoac
   `None` neu khong co route hop le.
3. Bao dam cay chi chua node dang song, moi sensor xuat hien toi da mot lan,
   `prev`/`nxts` nhat quan va id dung index goc.
4. Them class vao `ALGORITHMS` trong `src/run.py`.
5. Neu algorithm co state ngau nhien, set seed tai lop benchmark/test de ket qua
   tai lap; code hien tai chua set seed.

## Lenh huu ich

Chay tu repository root:

```powershell
python src/run.py
python src/map_gen.py
python -m compileall -q src
```

Dependencies quan sat duoc: `pandas`, `matplotlib` (ngoai Python standard
library). Chua co cach cai dependency chinh thuc trong repo.

## Rui ro va viec con thieu

- Khong co automated tests, dependency manifest, CLI/config hay random seed.
- `radius` duoc enforce cho ca sensor-CH va CH-base; day la invariant quan trong.
- `Simulator` tru chi phi roi moi danh dau node chet, nen mot node co the tieu
  thu nhieu hon residual energy trong round cuoi; metric `round_energy` van ghi
  toan bo chi phi tinh toan.
- ACO toi uu tong energy cua rieng round hien tai, khong truc tiep toi uu network
  lifetime/can bang tai giua CH.
- `rounds_survived = len(history)` trong summary thuc ra la so round da ghi,
  khong phan biet dung vi het node, het `T_max`, hay khong tim duoc route.
- `Visual.route()` co san nhung luong `run.py` khong goi no.
- Mot so comment tieng Viet dang hien mojibake; can giu file UTF-8 khi sua.
- Worktree luc tao memory da co cac file `.pyc` tracked bi xoa. Day la thay doi
  co san cua nguoi dung; khong restore/commit chung neu khong duoc yeu cau.

<!-- codex-kit-managed-start -->
## Codex Kit

This project has a local Codex kit installed.

- Project signals detected by installer: backend, documents
- Skills are available under `.agents/skills`; use the most relevant skill before specialized work.
- Skill support files such as install scripts and shared helpers are available under `.agents/skills`.
- Custom agents are configured under `.codex/agents`; spawn subagents only when the task benefits from delegation.
- Hooks may enforce privacy, scout checks, and post-edit simplification reminders.
- Workflow rules are available under `.codex/rules`; read relevant rules before planning or implementation.
- Helper scripts are available under `.codex/scripts`; use these project-local paths for kit utilities.
- Active plan state, when set, is stored at `.codex/state/active-plan.json`; check it before implementing plan-driven work.
- Plan templates are available under `plans/templates`; create plans/reports in this kit target directory unless the user explicitly asks for a child repo plan.
- CodexKit reference docs are available under `.codex/docs`; use them for agent-team guidance, code standards, architecture, skill maps, and research notes.
- Output style references are available under `.codex/output-styles`; use them as tone/detail guides when the user asks for a specific level.
- Keep changes scoped to the user's request and preserve existing project conventions.

Installed agents: brainstormer, planner, researcher, code_reviewer, tester, debugger, git_manager, docs_manager, fullstack_developer

Installed skills: ask, brainstorm, plan, cook, research, scout, code-review, test, debug, fix, git, docs, problem-solving, context-engineering, backend-development, databases, docx, pdf, pptx, xlsx

Enabled hooks: session-init, subagent-init, dev-rules-reminder, privacy-block, scout-block, cook-after-plan-reminder, post-edit-simplify-reminder, descriptive-name
<!-- codex-kit-managed-end -->
