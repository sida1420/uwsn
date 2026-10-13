# PLAN.md — Autonomous Constrained Global Optimization for D-ACO (UWSN 3D)

> **Date:** 2026-10-12  
> **Status:** Implementation-ready plan; **not evidence that any experiment has been run**.  
> **User decision:** **Maximize completed service lifetime** subject to **at most +2% energy versus pheromone-only SimpleACO: 42.4661 J over the first 2,611 all-alive rounds on the reference experiment**.  
> **Exact reference energy cap:** `42.4661 × 1.02 = 43.315422 J`.  
> **Execution mode:** Persistent, bounded, resumable **background multi-process optimization**; user explicitly authorizes starting a run only after inspecting the implementation, configuration, and resource budget.  
> **Scope:** Optimize D-ACO *parameters*, not algorithm semantics; no production-default promotion without independent validation and approval.

## 0. Read-first instructions for Codex / implementation agent

1. **Inspect reality first.** The reported writable checkout is `C:/Users/hgtfh/Code/uwsn/review_uwsn`; `C:/Users/hgtfh/Code/uwsn/uwsn` is a **read-only sibling reference**. Paths may have moved. Discover repo root; log `git status`, HEAD, branch, unstaged changes, Python/environment, actual runtime parameters, and SHA-256 fingerprints. Never treat this document as proof of current checkout contents.
2. **Do not revert or overwrite** any accumulated changes/artifacts. Do not `git reset`, commit, push, switch branches, or merge without explicit instructions. Do not alter AC-ACO, SimpleACO, PSO, NodeACO, routing, network topology, acoustic evaluator or simulator physics.
3. **Read existing evidence** before designing new experiments: `RESULTS.md`, `RESULTS(1).md`, `RESULTS(2).md`, `Pasted text(1).txt`, prior `plan.md` (archived as `plan_research_context_before_autotuner_20261012.md` in this deliverable), plus corresponding repo reports/source. Reported filesystem paths must be checked rather than assumed.
4. **Implement in phases, with approval gates.** Phase A–C deliver a working, tested tuner and a dry-run/pilot report. **STOP before launching the costly multi-hour optimization**. Once explicitly approved, the bounded background controller may autonomously propose and run trials within its agreed `max_trials`, `max_wall_hours`, `max_workers`, compute and storage limits; it may **not** modify production defaults.
5. **Success is a robustly validated feasible incumbent**, not a claim of mathematically proven global optimum or a forced victory over SimpleACO/PSO. All historical figures are from attached reports, not freshly reproduced in this plan.

---

## 1. Scientific question and exact optimization target

### 1.1 Decision variables

Let `θ` contain the **effective D-ACO hyperparameters**, independently optimized where meaningful:

`θ = (alpha, beta, gamma, Q, tau_max, rho_min, rho_max [, future approved parameters])`.

Do **not** constrain `beta` and `gamma` to move together as in the historical quarter-heuristic screen. Keep the existing density-depletion fitness and other production mechanisms fixed in the **primary study**; extending the variable set is a separate, versioned study.

### 1.2 Primary objective: capped completed service

For fixed deployment `m`, randomized simulation seed `s`, and time horizon `H=3000`, let:

- `S_H(θ;m,s)`: number of **successfully completed rounds serving the entire current live set**, until native simulator service termination or the cap `H`.
- `FND(θ;m,s)`: first physical node death, if observed.
- `E_K(θ;m,s)`: modeled *selected-route physical energy* accumulated over `K=2611` completed **100-node all-alive** rounds on the baseline deployment; not search-evaluation energy.

The intended target is

`maximize_θ  E_{(m,s)~D_train}[S_3000(θ;m,s)]`

subject to a fair, predeclared energy constraint. `S_3000=3000` is **horizon-capped**, not proof that service would terminate at 3000. `no_feasible_tree` is a simulator/search termination result, not automatically a certificate of physical graph disconnection.

### 1.3 Exact initial energy constraint

For the *historical reference cohort* (same map and seeds 24/25/26, with the full common workload):

`mean_s E_2611(θ,s) ≤ 43.315422 J`.

This is equivalent to `mean E_2611(θ) ≤ 1.02 × mean E_2611(SimpleACO)` using the historical **42.4661 J** mean. Because that mean is rounded in the report, the historical cap is correspondingly approximate; use raw per-seed reference CSVs to recover a full-precision cap for authoritative runs, while logging `43.315422 J` as the declared rounded-policy value and any exact-value difference.

**Workload comparability is mandatory.** A candidate that dies before 2,611 rounds, serves fewer nodes, or stops early cannot claim an energy win from a smaller energy sum. Record `energy_status=not_comparable` (do not classify it as meeting the constraint); use an explicitly infeasible trial constraint for the primary comparable-workload study, **not** a zero-energy success. This introduces an eligibility requirement (100 nodes alive through K) to the fixed-window comparison; disclose it explicitly, retain those candidates' measured completed service, and seek approval if an alternative energy-normalization policy is desired.

For a *new seed cohort on the same map*: **rerun matched SimpleACO references** and set the constraint to `1.02 × that cohort's baseline mean E_2611`; never simply transplant the historical absolute 43.315422 J if sampling conditions change. For **new maps/topologies**, define a preregistered comparable full-service window `K_m`, run matched SimpleACO baselines, and enforce an energy *ratio* on that map; do not apply 42.4661 J to another topology.

Secondary robustness: report per-seed energy ratios, standard error/intervals and fraction of violating seeds. The **primary feasibility rule is the paired-cohort mean at +2%**; a stricter chance or upper-confidence energy constraint requires separate authorization, not a silent change in objective.

### 1.4 How to handle energy-vs-lifetime tradeoffs

- The optimizer's objective is **completed service**, not early energy, FND or a subjective weighted energy+service sum.
- Energy is a **hard constraint** on the declared comparable workload, not a term given an arbitrary penalty multiplier.
- Use FND, connectivity, alive/served counts, residual distribution, hottest node and CPU/search work as **diagnostics and tie-break evidence** only.
- Never compare total energy after one run has stopped early against another run still serving full load.
- Feasibility proof of a fully disconnected survivor requires a graph certificate (as in the node-48 study); a finite heuristic search failure alone is insufficient.

---

## 2. Full experimental context and provenance register

### 2.1 Current relevant pipeline and deployment

`map.pkl → NetworkInstance → D-ACO candidate CH sets (one batch, 40 ants) → shared multihop router → shared acoustic evaluator → best candidate selected under D-ACO's native fitness → physical residual-energy deduction → next round`.

- **Current Phase 10–12 reference map:** 100 sensors, `500 × 500 × 500 m`, communication radius `200 m`, each `0.6 J`, sink `(250,250,0)`.
- **Current Phase 10 source/map fingerprint:** `d9e086fde395ff10a4348122727bc2af6972dffa25d5f92afa37ed0d56ca4b05` (**map SHA-256** from Phase 10); compare with actual bytes.
- **Reference seeds:** `[24,25,26]`; 3000-round horizon; `K=2611` was an all-alive comparison window across all Phase 10–12 variants.
- D-ACO and pheromone-only SimpleACO: **one batch of 40 ants** per physical round, ≤10 feasibility attempts per ant, 20% CH; common router and evaluator. Their optimization objective, member-selection policy and pheromone structure differ; they are not an isolated one-factor comparison.
- Candidate evaluations are hypothetical; only the selected feasible routing tree deducts physical energy. Selected trees in the reported runs covered the entire then-live set.
- Execution time previously measured under concurrent processes, often with diagnostic overhead; **do not treat those CPU figures as calibrated speed proof**.

**Version precedence:** `Pasted text(1).txt` describes earlier Phase 5–8 and a checkout in which D-ACO's depletion-density weight default was `0`. **Phase 10–12 explicitly report a more recent current D-ACO** with quadratic relative-depletion/grid-density penalty weight **0.25**, geometric reference memory **0.8**, live node pheromone, and 40 throwaway initial calibration ants. Treat the newer reports as the latest *reported* state; inspect effective current code. Do not silently optimize the older baseline.

### 2.2 Current D-ACO reported parameter/method baseline

From Phase 10–12 reports (to verify in source):

| Setting | Latest reported value / policy |
|---|---|
| `alpha` | `1` |
| `beta` | `0.9` |
| `gamma` | `0.4` |
| `Q` | `5` |
| `tau_min`, `tau0`, `tau_max` | `1`, `1`, `8` |
| Evaporation | Existing adaptive schedule; historical range `rho_min=0.1`, `rho_max=0.6` (confirm actual values) |
| Fitness | Native D-ACO with quadratic relative depletion divided by structural grid density, weight `0.25`, plus its current normalizations |
| Geometric reference memory | `0.8` |
| Pheromone behavior | Live per-ant pheromone, native elite update; inspect exact order and units |
| Search | 40 ants, one batch, ≤10 retries/ant, 40 throwaway calibration ants at initialization |
| Density grid | Current reference grid unless explicitly changed in a separate experiment |

**Freeze during optimization:** physical model; routing; candidate-selection implementation; evaluation count; fitness formula and load penalty; density grid; geometric-reference memory; calibration-ant policy; pheromone deposit ordering; stopping criterion; seed handling. Changing any of these makes it a different study. Only expose parameter overrides where necessary **without changing default values**.

### 2.3 Historical evidence — retained as anchors, not all on one code epoch

| Study / context | Result | Limits |
|---|---|---|
| Historical AC-ACO Phase 1–4 | Elite tau bounds correctness fix; D0 600-round energy improvement ~0.474%; original beta B0 retained; PSO native 600-round energy below AC-ACO | **Different AC-ACO checkout/config epoch**; not directly comparable to latest D-ACO data |
| Post-FND graph audit | PSO seeds 0/1: nodes 33 & 65 die together, isolate live node 48, 97 of 98 survivors reachable | Proves full-survivor physical disconnection **only in those checkpoints**; no inference about current D-ACO service on new seeds |
| AC-ACO calibration / chaos / live-pheromone / weaker E_m | Calibrated AC-ACO Q=0.01, live pheromone, elite weight 0.1, E_m exponent 0.1 | AC-ACO-specific, **not values to transplant to D-ACO** |
| D-ACO Phase 7 grid | Linear decay slightly improved service; parabolic did not; all alternatives retained | Older D-ACO fitness epoch |
| D-ACO Phase 8 density fitness | Weight 0.05 gave +8.90% mean service / +38.89% FND vs its older baseline at +2.38% energy | Older weight/default epoch, **not current baseline**; much gain also achieved by density-free depletion control |
| D-ACO Phase 10 (fresh latest policy) | Pheromone-only SimpleACO has lower energy and longer service than current D-ACO; D-ACO has somewhat later FND | Exactly seeds 24/25/26 and current map |
| D-ACO Phase 11 | Quarter heuristic `(beta=0.225,gamma=0.1)` gives strongest service improvement among tested D-ACO variants | Beta and gamma **changed together**, so neither independent derivative nor global optimum shown |
| D-ACO Phase 12 | Increasing Q with cap 8 helps some; increasing cap 8→32 worsens energy, FND and service in tested comparisons | Clipping reduction alone does not imply benefit; do not assume monotonicity |

### 2.4 Phase 10 baseline: current D-ACO vs pheromone-only SimpleACO

All below are means across seeds `[24,25,26]`; energy uses full common all-alive 2611-round exposure:

| Metric | Current D-ACO | SimpleACO pheromone-only |
|---|---:|---:|
| FND rounds | 2675.000 | 2636.000 |
| Completed service rounds | 2747.333 | **2936.000** |
| `E_2611` (J) | **43.6483** | **42.4661** |
| Original report's CPU mean (s, indicative) | 307.755 | 290.594 |

SimpleACO has `beta=gamma=0` for *its own sampling*, but it still evaluates/uses physical energy in candidate selection and pheromone deposits; routing remains ordinary. **Do not assert that D-ACO beta=gamma=0 is the same algorithm.** Current D-ACO's `E_2611` exceeds the selected +2% SimpleACO constraint, but this does not invalidate it as an essential baseline for comparison.

Source: attached `RESULTS.md`; repo `plans/phase10-daco-vs-pheromone/`.

### 2.5 Phase 11: Q and heuristic-strength experiments

| D-ACO variant | Q | beta / gamma | Mean FND | Mean service | `E_2611` J | Meets rounded +2% cap? |
|---|---:|---|---:|---:|---:|---|
| Current baseline | 5 | 0.9 / 0.4 | 2675.00 | 2747.33 | 43.6483 | **No** |
| Q=10 / cap 8 | 10 | 0.9 / 0.4 | 2674.00 | 2790.67 | 43.4428 | **No** |
| Q=20 / cap 8 | 20 | 0.9 / 0.4 | 2742.67 | 2830.33 | 43.4092 | **No** |
| Heuristics ×0.5 | 5 | 0.45 / 0.2 | 2734.33 | 2815.67 | 43.2557 | **Yes** |
| **Heuristics ×0.25** | 5 | **0.225 / 0.1** | **2782.67** | **2938.00** | **43.1655** | **Yes** |
| SimpleACO control (not a D-ACO parameter trial) | 0.07 | 0 / 0 | 2636.00 | 2936.00 | 42.4661 | Reference |

Quarter-heuristic is the **best reported feasible D-ACO incumbent on this exact cohort**. Its mean service improvement versus SimpleACO is only **+2 rounds**, with paired differences `+13, −13, +6`; do not claim reliable superiority based on this three-seed mean.

Pheromone saturation evidence over the same 2611 rounds:

| D-ACO variant | Mean live nodes at `tau_max` | Lost deposit mass |
|---|---:|---:|
| Q=5 / cap 8 | 2.26% | 1.08% |
| Q=10 / cap 8 | 16.93% | 8.27% |
| Q=20 / cap 8 | 54.66% | 30.67% |
| Quarter-heuristic / Q=5 / cap 8 | 0.55% | 0.19% |

Source: attached `RESULTS(1).md`; repo `plans/phase11-daco-concentration/`.

### 2.6 Phase 12: Q × pheromone ceiling interactions

| D-ACO variant | Q | `tau_max` | Mean FND | Mean service | `E_2611` J | Meets +2% cap? |
|---|---:|---:|---:|---:|---:|---|
| Q=20 / cap 8 | 20 | 8 | 2742.67 | 2830.33 | 43.4092 | No |
| Q=20 / cap 32 | 20 | 32 | 2638.67 | 2702.33 | 43.7611 | No |
| Q=30 / cap 8 | 30 | 8 | 2761.00 | 2849.00 | 43.4038 | No |
| Q=30 / cap 32 | 30 | 32 | 2644.33 | 2733.67 | 43.6668 | No |
| Quarter-heuristic Q=5 / cap 8 | 5 | 8 | 2782.67 | 2938.00 | **43.1655** | **Yes** |

Cap 32 greatly reduced clipping but worsened all three mean outcomes at Q=20 and Q=30. Empirical evidence **does not support monotonic Q, tau_max or heuristic tuning**. A large cap may give overly concentrated learned choices, but this is a hypothesis until transition entropy/selection diversity are measured.

Source: attached `RESULTS(2).md`; repo `plans/phase12-daco-higher-cap/`.

### 2.7 Generalization and experiment provenance warnings

- Current evidence: **one map, three seeds**, many comparisons already selected on those seeds; high overfitting/selection-bias risk.
- Comparisons from different code epochs (older AC-ACO phases, earlier D-ACO weight=0 or 0.05, newer weight=0.25) **must not be pooled**.
- The original Phase 4 map hash `ebe729…` differs from the latest Phase 10–12 reported `d9e086…`; inspect actual map identity; do not equate physical topologies by description alone.
- Reference baseline numbers should be **reproduced from source+map+effective config** or marked as historical and re-run when they do not fingerprint-match.
- No paper-derived constants are universal acoustic-network optima. Avoid claiming statistical significance from n=3.

---

## 3. Mathematical and methodological foundation

### 3.1 Why a global adaptive optimizer, not continued one-factor tuning?

A simplified D-ACO transition distribution at a **fixed internal state** is:

`p_i(θ) ∝ exp(alpha·log(tau_i) + beta·log(eta_E,i) + gamma·log(eta_density,i))`,

with actual implementation potentially adding normalization/history terms. Even when an exponent moves linearly, the resulting `p_i` is a nonlinear softmax; a different CH selection changes routing topology, candidate fitness, future residuals and pheromone. Observed service is discontinuous/censored at graph and routing thresholds.

For one fixed-state scale `k` of combined heuristics (`H_i` fixed), `d E[C] / dk = Cov_p(C,H)`; covariance can change sign. This explains **non-monotonicity**, not the direction of the global optimum. Therefore optimize the measured black-box trajectory `S_3000(θ)` under energy constraints and quantify its noise.

The goal is the **best validated feasible point under a finite budget**, not a mathematical certificate of global optimum. A GP's smoothness assumptions may be poor for 3000-round discrete stochastic simulation; **Optuna TPE with recorded constraints** is the recommended initial adaptive engine, with a fixed-budget Sobol/random baseline and optional Differential Evolution comparator.

### 3.2 Acquisition and constraints (implementation-level)

A `trial` is **one complete parameter configuration**, evaluated on a declared cohort of paired seeds (each individual run is a separate `trial_run` child record). Do not present 3 seeds as 3 independent parameter suggestions.

Store in the Optuna trial user attributes:

- `mean_service_capped`, `service_per_seed`, `mean_fnd_observed_only`, `service_terminations`;
- `energy_K_mean`, `energy_K_reference_mean`, `energy_constraint_delta_j`, `energy_ratio`, `energy_comparable`;
- `cpu`, `wall`, `attempts`, `routing_attempts`, `feasible_candidates`, `calibration_cost`;
- map/source/config hashes, seed ids, checkpoint paths, error type and stop reason.

Use Optuna `TPESampler(multivariate=True, constraints_func=...)` **if the installed version supports it**. `constraints_func` must read frozen-trial attributes and return a constraint such as `[energy_K_mean - reference_cap]`, ≤0 feasible; **do not encode impossible/incomplete evaluations as feasible**. Expose noncomparable/no-full-workload cases as strictly positive constraint values with a separate status explaining why; retain their lifetime observations outside the feasible leaderboard. Explicitly test constraints behavior against the installed Optuna version and its treatment of pruned/failed trials.

For asynchronous workers, only **completed valid cohorts** should influence final recommendation. Do not overstate statistical independence of repeated identical checkpoints or repeats.

### 3.3 Proposed search space (to finalize after source inspection)

| D-ACO parameter | Initial suggested domain | Sampling | Notes |
|---|---|---|---|
| `alpha` | `[0.25, 3.0]` | continuous | pheromone exponent |
| `beta` | `[0, 1.5]` | continuous | vary independently of gamma |
| `gamma` | `[0, 1.0]` | continuous | vary independently of beta |
| `Q` | `[0.1, 60]` | log continuous | units depend on current deposit implementation |
| `tau_max` | `[4, 32]` | continuous/validated | retain `tau_min=tau0=1`; `tau_max>tau0` |
| `rho_min` | `[0.05, 0.4]` | continuous | verify current evaporate formula and bounds |
| `rho_max` | `[0.4, 0.9]` | continuous | require `rho_min < rho_max` and both in valid range |

These are **candidate exploration intervals**, not paper-certified ranges. Preserve `tau_min`, `tau0`, 40 ants, ≤10 retries, load penalty weight 0.25, depletion power 2, geometric memory 0.8 and calibration policy in primary study. Before search, verify parameter names/ranges and whether `tau_max`, Q, rho are defined in these units. Reject illegal combinations deterministically rather than coercing them silently. Include discrete exact `beta=0`, `gamma=0` and known anchor configurations, because a continuous sampler will otherwise almost never hit exact zero.

**Known D-ACO anchors (evaluate first and reuse only fingerprint-matched data):** current baseline, quarter heuristics, half heuristics, Q20/cap8, Q30/cap8. SimpleACO pheromone-only is an **external reference**, never inserted into the D-ACO hyperparameter study as a D-ACO trial.

**Optional later expansion** (new study/version, approval required): density weight, depletion power, grid decay, elite weight, reference-memory weight, `tau_min`/`tau0`, number of ants, new selection/reinforcement logic. Do not mutate objective/search budget within this initial study.

---

## 4. Automation architecture and proposed code layout

Implement an isolated experiment package in the writable repo, for example:

```text
plans/phase13-daco-autotuner/
  README.md                    # setup, objective, constraints, run/resume/stop
  config.example.yaml          # map, train/validation seeds, limits, paths
  config.schema.json           # optional strongly typed settings
  autotune.py                  # CLI orchestration (init/worker/status/stop/report)
  search_space.py              # bounds and anchor configs
  evaluate_trial.py            # one config, independent complete seed cohort
  reference.py                 # matched SimpleACO baseline + energy cap
  metrics.py                   # service/FND/energy/CPU validation
  storage.py                   # atomic per-seed persistence and provenance
  report.py                    # feasible frontier and final evaluation
  tests/                       # experiment harness tests
  runs/<study-id>/
    study.db / journal / DB URL # choose supported robust backend
    config.snapshot.yaml
    provenance.json
    trials/<trial-id>/<seed>/metrics.json
    trials/<trial-id>/<seed>/rounds.csv(.gz)
    trials/<trial-id>/<seed>/checkpoint.pkl  # trusted local outputs only
    logs/*.log
    status.json
    plots/
    final-report.md
```

Paths/filenames are **proposed outputs**, not existing files. Keep original study assets untouched and ensure output paths are collision-safe.

### 4.1 Main process and workers

- **Controller:** validates config, freezes provenance and seed splits, creates/loads persistent study, enforces global trial/wall/disk limits, exposes summary/status, does not directly mutate production algorithms.
- **Worker process:** acquires one trial/parameter set, spawns/isolates seed runs (or executes them sequentially inside its isolated worker process), saves each seed atomically; reports one complete valid aggregate result to the optimizer.
- **Per-seed runner:** creates fresh network, D-ACO instance and RNG; applies *explicit* parameter overrides; follows actual simulator service termination or horizon 3000; captures selected-route energy, full-service rounds, FND, physical connectivity and search failures.
- **Reference runner:** runs version-matched pheromone-only SimpleACO under explicit `beta=gamma=0`, native 40-ants policy, captures 2611 full-all-alive energy and round counters, hashes evidence.
- **Reporter:** feasible/infeasible counts, best feasible incumbent with provenance, paired seed differences, failures, uncertainty, energy-cap violations, parameter importances (exploratory only), reproducible plots.

### 4.2 Reliable background multi-process execution

- Default **`max_workers=2`** until a memory/CPU pilot passes; allow a configurable max of 4 when hardware permits. Never spawn unlimited processes or let many Optuna workers launch overlapping 3-seed process pools unintentionally.
- Prefer **processes**, not threads: Python global RNG/network/algorithm mutable state must be isolated. For Windows use the `spawn` process model and a `__main__` guard.
- Persistence options: **PostgreSQL RDBStorage** for robust multi-host/high-concurrency deployment; on one machine, use an Optuna **JournalStorage or suitably configured local RDB** implementation compatible with the installed Optuna version. Test locking, retries, stale trial recovery and a kill/restart before trusting concurrency. Avoid network-shared SQLite DB files.
- Each experiment writes to `*.tmp`, then atomic rename on successful validation. Checkpoint storage follows safe, versioned/trusted pickle policy; never load arbitrary external pickles.
- Worker lease/heartbeat + retry counters. A crashed trial must not be reported as success or silently counted twice; resumed full trajectories must restore complete physical, optimizer, Python/NumPy RNG and calibration state deterministically.
- `--status`, `--stop` (graceful), OS process ID/log location, signal handling, flush on Ctrl+C, load-aware worker admission. Parent/background process exit must not corrupt results.
- Track process CPU, wall time, memory peak and I/O separately. Compare CPU after controlled re-measurement, not concurrent historical timings.

### 4.3 CLI design (proposed; implement and document, not existing commands)

```powershell
# From writable repo root, after implementation and explicit approval.
python -m plans.phase13_daco_autotuner init --config path/to/study.yaml
python -m plans.phase13_daco_autotuner worker --study <study-id> --workers 2
python -m plans.phase13_daco_autotuner status --study <study-id>
python -m plans.phase13_daco_autotuner stop --study <study-id> --graceful
python -m plans.phase13_daco_autotuner report --study <study-id>
```

**Note:** directory/module names must be made Python-importable or CLI changed accordingly; these are design examples, not copy/paste runnable commands. Provide real verified Windows PowerShell `Start-Process` and Linux `nohup`/`tmux` usage in `README.md`, with PID and logs. Do not launch until the study limits are confirmed.

---

## 5. Experimental strategy: autonomous, cost-aware, and statistically honest

### Stage A — Baseline/constraint reproduction (gate A)

1. Discover actual D-ACO source and baseline effective values, reference map hash, seeds and exact Phase 10–12 runner semantics.
2. Check whether old `RESULTS.md` etc. match current source/map epoch; reproduce one baseline trajectory exactly if deterministic artifacts exist. Re-run full three-seed reference when hashes/config differ; **do not retrofit old data into new code**.
3. Run pheromone-only SimpleACO reference for same map/seed/cohort when not exactly reusable; recompute `E_ref,K` and cap at full precision.
4. Validate accounting: 100 live+served for every one of the `K` comparison rounds; correct physical energy deduction; actual FND/termination semantics; guard all finite values; no energy deduction for hypothetical ant trials.
5. Anchor comparison: current D-ACO, `beta=0.225,gamma=0.1,Q=5,tau_max=8` and SimpleACO reference. Fail this gate if effective params, source identity or reference energy cannot be verified.
6. Output `baseline-reproduction.md` with hashes and explicit **PASS/FAIL**. STOP on failure.

### Stage B — Infrastructure, validation and crash-resume (gate B)

1. Implement typed config/search space, storage, worker isolation, trial-aggregate evaluator, energy feasibility rule, status/report and reference cache with source/map hash keys.
2. Unit/integration tests: seed resets; full candidate/physical accounting; aggregation over exact paired seeds; energy bound; early FND marked noncomparable; horizon censor; `no_feasible_tree` not called physical disconnection; crashes/timeouts; deterministic resume; no overwrite.
3. Run a cheap smoke test (tiny horizon) **only for infrastructure**, labeled non-scientific and never ranked against full-horizon studies.
4. Pilot 2 concurrent workers with ≤2–3 small sandbox trials, interrupt and resume, verify same results as uninterrupted runs where possible. Record CPU/RAM/disk/wall throughput.
5. Output `implementation-review.md`, reproducibility logs and executable manual. **STOP for approval before large sweeps.**

### Stage C — Autonomous adaptive optimization (gate C = explicit user launch)

**Proposed initial bounded budget, adjustable before launch:**

- **Pilot:** first 8 valid parameter configurations, up to 2 workers, training cohort of three paired seeds; learn actual wall/CPU cost.
- **Main:** maximum **80 complete parameter configurations** (including anchors) or **24 hours wall time**, whichever happens first; at most 2 workers initially, configurable to 4 after pilot; enforce disk/memory ceilings.
- **Warm-up space coverage:** ~16–24 Sobol/random candidates plus required anchor configs (count anchors toward total), then Optuna TPE proposals. This is a **proposed allocation**, not a guarantee 80 full runs fit within 24h.
- **Each candidate's authoritative result:** all three training seeds, same map, full 3000-horizon or native termination. Intermediate single-seed runs can be inspected diagnostically, but must not be silently treated as validated parameter winners.
- Prioritize new configurations when earlier ones finish; update tuner without human micromanagement **within approved cap**.
- **Pruning:** safe for invalid params, verified infeasible workload, or a known positive accumulated energy exceedance under a fixed comparable K; not based on a naive monotonic inference from 150/600-round energy or FND. Incomplete service trajectories still logged. Prefer full cohort completion for scientifically meaningful service ranking.
- **No elite cherry picking:** report all attempted configs, no hidden retries to replace bad seeds. Use paired common random numbers and exact effective seeds for all candidates.
- Run independent random/Sobol-only search for a **separately capped matched-budget control** if compute permits; else mark optimizer advantage untested.
- Status file keeps `trials_total`, `complete`, `infeasible`, `failed`, `running`, `best_feasible`, `energy_margin`, `ETA_estimate` (uncertain), resource usage and study source hash.

### Stage D — Independent validation and robustness (approval after Stage C shortlist)

1. **Freeze top K feasible candidates** (e.g., 3–5), based solely on the training cohort; do not refit/select on validation data.
2. Holdout *new* seeds on the reference map (suggest `[40,41,42]`, confirm no prior tuning used them) and matched fresh SimpleACO energy baselines.
3. If new topology fixtures can be generated reproducibly, hold out multiple geometries: dense, sparse, bridge/cut-set-vulnerable, varied base location and communication radius, with map-specific baseline and preregistered comparable full-service window `K_m`.
4. Compute pairwise mean/median service changes, energy ratios/constraint pass rate, observed/censored FND, service stop reasons, residual distributions and CPU/search budget; use trajectory or topology/seed pairs as units, not rounds as independent samples.
5. Sensitivity check of energy constraint on **0%, 2%, 5%** as *post-hoc reporting*, **not** changes to the user-selected +2% primary rule.
6. Only claim a new default if it passes reference and holdout policy and receives explicit approval. Otherwise keep original defaults and report best conditional research candidate.

---

## 6. Decision policy, stopping conditions, and scientific outputs

### 6.1 Feasible leaderboard

Primary ranking: among `energy_comparable=True` trials with `mean E_K ≤ 1.02 × mean E_ref,K`, choose highest `mean S_3000`; identify ties and actual delta from SimpleACO/quarter-heuristic. Show FND and physical energy side by side, but **do not reweight the objective after the fact**.

If `mean service` hits the horizon 3000 in all three training seeds, further apparent service gain is unobservable at that horizon; focus next evaluations on stability/holdouts, not fictitious improvements beyond 3000. For training configurations near boundary, report uncertainties, seed-level effects and number of fully observed versus horizon-censored service outcomes.

Optional conservative ranking: energy upper confidence bound ≤ cap, and a robust service lower bound; **report separately** from the chosen expected-mean criterion. n=3 is insufficient for tight claims.

### 6.2 Mandatory metrics per seed/round

- `round`, `alive_before/after`, `served`, `service_success`, `service_failure_reason`, optional graph reachability certificate when suspicious;
- `selected_tree_physical_energy`, `total_energy_to_round`, `energy_per_served_sensor_round`, `residual_sum/min/quantiles/std`, `FND/HND/LND` if observed;
- CH/member/non-CH relay costs, peak relative depletion and node hotspots (including nodes 33, 65, 48 as diagnostics **only on relevant known topology**);
- ants attempted, CH constructions, router calls, actual feasible energy evaluations, repeated/cached CH sets, retry exhaustion;
- pheromone summary: cap fraction, clipped updates, lost deposit mass, entropy of actual CH-choice probabilities when implementable without changing selection;
- `cpu_process`, `wall`, init/calibration vs per-round search timing, memory; fingerprints of map/config/source/harness + seed + trial id.

### 6.3 Stop/abort protections

- Stop after `max_trials`, `max_wall_hours`, operator stop request, confirmed repeated invalidity or storage/process instability. Don't silently extend caps.
- Failed/hung workers: bounded retries, preserve failure logs, skip final ranking of incomplete cohorts, no zombie processes.
- No automatic new topology generation or code changes while optimizer runs.
- No full production deployment default change without manual review and approval.

### 6.4 Required deliverables

1. Runnable parameter-only autotuning harness with verified CLI (Windows + Ubuntu).
2. `README.md`: architecture, source/version lock, objective/constraint, reproduction commands, launch/status/stop/resume, resource budgets, troubleshooting.
3. Full seed- and trial-level CSV/JSON exports, Optuna study DB, hashes/checkpoints/logs and an automatic **`best-feasible-config.yaml`** (recommendation only).
4. Plots: service vs energy with **+2% constraint line**; feasible incumbent vs completed trial number; parameter parallel coordinates/importance; service survival/censoring; energy/load/entropy and optimizer performance vs compute budget.
5. `final-report.md`: all trials, feasible rate, best incumbent, paired differences vs SimpleACO, D-ACO default and quarter-heuristic, heldout generalization, numerical uncertainty, runtime and failure modes, unresolved limitations.
6. Full regression suite passes; no original production-source change except narrowly approved parameter exposure with identical defaults/semantics; no files overwritten.

---

## 7. Verification checklist (acceptance criteria)

- [ ] **Correct checkout:** current HEAD, status, map SHA, actual code/defaults and reference config fingerprinted. No mix of old D-ACO load-weight-0 epoch and current weight-0.25 epoch.
- [ ] **Objective:** correct `S_3000` physical completed full-service rounds; censored at 3000; separate observed FND and route/search failure.
- [ ] **Constraint:** exactly **+2% energy**, `K=2611`, same full-service workload, full-precision matched SimpleACO reference and hard-fail for noncomparable early deaths.
- [ ] **Param semantics:** beta and gamma independent; Q log scale; legal tau/evaporation bounds; no implicit fitness/search-budget changes.
- [ ] **Anchors:** fresh quarter-heuristic and D-ACO baseline reproduce earlier outcomes when fingerprints match, or mismatch is disclosed and new baseline established.
- [ ] **Scientific correctness:** selected-tree physical energy only; evaluations do not deduct energy; no double counting with killed/checkpoint-restored runs.
- [ ] **Autonomy:** multiple workers can complete trials, report to persistent optimizer, propose new ones, stop at agreed budget and safely resume without duplicates.
- [ ] **Crash test:** interrupt mid-trial; restart with complete RNG/network/optimizer state; compare deterministic outcome with uninterrupted control.
- [ ] **Statistical integrity:** training vs validation separation; no cherry-picking seeds; no treating 2611 rounds as 2611 independent replicates.
- [ ] **Limits:** resource caps enforced; no massive sweep launches before explicit go/no-go approval.
- [ ] **Reporting:** track raw/capped lifetime, energy status, feasibility, confidence/uncertainty, wall and CPU; mark non-global-optimum guarantee.
- [ ] **Default safety:** no edits to SimpleACO/AC-ACO/PSO, shared physics, D-ACO behavior or committed defaults without approval.

## 8. Immediate ordered next actions for Codex

**Phase A:** Audit current D-ACO code/parameters and reproduce historical reference cap + quarter heuristic with matching provenance. Show exact executable environment and raw energy calculation. **STOP for review if mismatch.**  
**Phase B:** Implement tuner infrastructure, constraints and test suite, run controlled smoke/crash/resume pilot. Report measured worker throughput and suggested resource caps. **STOP for user approval.**  
**Phase C (only after approval):** Launch bounded background exploration, autonomous adaptive optimization, persistent dashboard/status and reports. Stop at approved limits.  
**Phase D (after shortlist review):** Run heldout seeds/topologies, choose the best validated feasible configuration and write final scientific report. Do not apply defaults automatically.

---

## 9. Reference sources used for this plan

- Attached `RESULTS.md` — Phase 10: D-ACO versus pheromone-only SimpleACO, seeds 24–26, latest map SHA.
- Attached `RESULTS(1).md` — Phase 11: Q variations, quarter/half heuristic, pheromone saturation, 12 runs + controls.
- Attached `RESULTS(2).md` — Phase 12: Q × ceiling interaction, nine new full trials, cap 8 vs 32.
- Attached `Pasted text(1).txt` — historical research context and earlier checkout status (through D-ACO Phase 8); **older effective defaults differ**.
- Previously created research context plan archived alongside this plan: `plan_research_context_before_autotuner_20261012.md`.
- Repo-reported historical report directories: `plans/phase10-daco-vs-pheromone/`, `plans/phase11-daco-concentration/`, `plans/phase12-daco-higher-cap/` plus earlier phases enumerated in the archived context.

**Scope of evidence:** This document was drafted from supplied reports and conversation. It has **not** inspected the user's live Windows checkout or executed scientific simulations. The very first implementation step is to validate current source, parameters, map and run provenance.
