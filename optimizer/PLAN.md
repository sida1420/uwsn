# D-ACO AutoTuner v2 — 90-Minute Continuation, 3,500-Round Horizon & Algorithm-Agnostic Architecture

> **Status:** Implementation plan only; no optimization was started here.
> **User-approved goal:** Maximize **completed full-service lifetime**, subject to **+2% energy** relative to the matched pheromone-only SimpleACO reference.
> **New execution limit:** **90 minutes (5,400 seconds) total wall-clock per approved tuning campaign**, including startup, trial execution, checkpoint flush and final report.
> **New horizon:** **3,500 network rounds** for trajectory scoring **and explicitly audit all formulas using `T_max`/total iterations**.
> **New engineering objective:** Refactor the AutoTuner into a reusable **algorithm-independent optimization engine** with thin adapters for D-ACO now and PSO/AC-ACO later.
> **Guardrails:** No production physics/routing changes, no default algorithm changes, no new PSO/AC-ACO tuning runs in this phase, no reset/push/commit, preserve historical studies and outputs.

---

## 1. Why this new campaign is necessary

The preceding 3,000-round constrained search identified an excellent **training incumbent**, **Trial 25**, but its outcome is capped at 3,000 rounds and does not identify true service termination or uniquely necessary hyperparameters. We should **continue the investigation**, not relabel old 3,000-round trials as 3,500-round observations.

### 1.1 Historical research context — keep provenance labels

| Item | Reported previous evidence | Consequence for v2 |
|---|---|---|
| Reference map/workload | 100 sensors, 3D `500×500×500 m`, radius 200 m, sink `(250,250,0)`, initial 0.6 J/node; paired seeds 24–26 | Verify map SHA and real runtime state before comparison |
| SimpleACO energy reference | `42.4661 J` accumulated during **2,611 common fully alive, fully served rounds** | Rounded policy cap: **43.315422 J = 42.4661 × 1.02**; rerun matched reference if provenance differs |
| Pre-optimization D-ACO baseline | Mean service about 2,747.33; energy about 43.648 J | Historical control; not current incumbent |
| Quarter-heuristic D-ACO | `beta=0.225, gamma=0.1`, service about 2,938; energy about 43.1655 J | Historical feasible anchor; do not infer unique optimum |
| 3,000-round AutoTuner | 32 reported trials; 5 feasible; **Trial 25** reached 3,000 rounds for all seeds, `E_2611≈38.290824 J` | **Seed first** in new v2 study; score again under `T_max=3500` |
| Trial 25 search space | Previous results reportedly tuned more than seven parameters: `theta`, `load_density_weight`, `load_power`, `density_decay`, etc. | Preserve full effective parameter vector; audit exact meanings before reuse |
| D-ACO vs PSO CSVs | Two single trajectories to round 3,000: D-ACO retained 100 nodes, PSO 98; D-ACO energy a little lower | Illustrative only; no equal-budget/generalization claim |
| Previous joint search | Old horizon 3,000; Optuna storage and prior trial artifacts may still exist | **Study migration audit required**; never silently merge objectives |

**Historical numbers above are summaries of earlier user-supplied files/conversation, not fresh verification against the current checkout.** Codex must inspect the local source, original CSVs, trial manifest, `PLAN.md`, `final-report.md`, `top-five-parameters.csv`, `top-five-trials.json`, and the optimizer storage DB to confirm exact values/configurations. Missing artifacts should be reported, not reconstructed.

### 1.2 Scientific objective, horizon and energy constraint

Let `θ` be one algorithm-specific configuration, `m` a fixed topology, `s` a seed, and `S_H` the number of successfully completed **full-service** rounds up to horizon `H`:

```text
max_θ mean_{m,s}[ S_3500(θ; m,s) ]
subject to mean_s E_2611(θ; m_reference,s) <= 1.02 * mean_s E_2611(SimpleACO; m_reference,s)
```

- The **3,500** cap changes the *lifetime objective*; the **2,611** common-workload energy checkpoint is intentionally **retained** from the previously selected +2% policy. It must not silently change to `E_3500` or get compared against `42.4661 J` at a different horizon.
- Energy is **selected routing-tree physical energy**, not optimizer CPU energy or rejected candidate evaluation energy.
- To satisfy the reference absolute energy constraint, all relevant runs must complete the same 2,611-round **100-node alive and served** workload. Early death, fewer served nodes or early stop => `energy_comparable=false`, **not** a low-energy victory. Preserve their lifetime observations separately and disclose this eligibility rule.
- If new topology/seed cohort: generate **new matched SimpleACO reference** and a preregistered comparable service window, then apply the **relative +2%** rule. Never reuse 43.315422 J across different maps, model versions or workloads.
- `S_3500=3500` is a **right-censored** lifetime, not observed termination or a proof of actual optimum beyond 3,500.
- Record `FND`, `served_count`, real connectivity and optimizer failure as separate metrics; physical disconnection requires a graph certificate, not merely a failed search.

---

## 2. Critical audit: 3,000 → 3,500 affects the optimization process itself

**Separate these concepts and make them explicit:**

1. `network_round_limit=3500`: simulator observation horizon.
2. `adaptive_total_rounds` / `T_max=3500` **only if** original D-ACO schedules are defined against network horizon and changing it is the intended experimental policy.
3. `optimization_inner_iterations`: optimizer steps/ants *within* a network round; **do not** set this to 3,500.
4. `global_tuner_timeout_seconds=5400`: external **wall-clock search budget**; no relation to either algorithm loop.

### 2.1 Parameter/schedule dependency inventory (must be executed before any full run)

Search every production/config/experiment location where any of the following appears: `T_max`, `total_rounds`, `max_iterations`, `network_round`, `current_iteration`, `beta`, `rho`, `theta`, elite update, aging, temperature/sigmoid schedules, warm-start, PSO inertia schedule, chaotic intensity and caching/termination logic.

Produce a table for every occurrence:

`file:line | equation/code | which clock it actually uses | value at 3000 | value at 3500 | expected effect | unit/regression test`.

At minimum inspect:

- Relative progress `p=t/T_max` versus absolute `t`; when `T_max` grows, a beta/rho transition can shift later **even before round 3000**.
- Threshold/halfway formulas such as `t − T_max/2` (center shifts from 1,500 to 1,750), including discontinuous near-step schedules.
- Cumulative pheromone/adaptive-state history, CH selection, deposit normalization and feasibility retries.
- `theta`: determine whether it is a scalar weighting the elite reward, a quality multiplier, a density factor, or something else in actual code. Do not assign a meaning from its name.
- Scores/fitness units: confirm whether a lower value is better; avoid multiplying raw scores by scales dependent on absolute network energy when intended as relative reinforcement.

**Required tests:** log schedule values at rounds `[1,600,1500,1750,2611,2999,3000,3500]`; confirm correctness and no off-by-one horizon errors; confirm selected-route-only physical deduction. **Do not copy old checkpoints into a 3,500-round run if adaptive schedules or any prefix decisions differ.** A valid 3,000-to-3,500 continuation requires a proven identical prefix, compatible source/config/T_max/physical/optimizer/RNG state, and successful deterministic replay; otherwise restart from round 0.

---

## 3. `theta` and other population/topology-dependent parameters

**Question:** Is the learned numerical `theta` value intrinsic, or does the *effective impact* depend on number of ants, sensor nodes, chosen CHs, eligible edges, selected-tree score and network geometry?

### 3.1 Trace actual implementation, do not impose an invented formula

Document the exact source formula: where `theta` multiplies quantities, the direction and units of `score`, number of times deposit is applied, normalization denominators, and whether clipping hides differences.

Instrument these dimensionless/scale-sensitive diagnostics per search and per round:

```text
n_sensors, n_live, n_ants, n_feasible_ants, n_selected_CH, n_rewarded_items,
score_raw, score_normalized, score_reference, elite_reward_raw,
per_ant_reward_raw, elite_to_ant_deposit_ratio, post_clamp_actual_delta,
pheromone_saturation, transition_entropy, coverage, selected_tree_energy
```

For additive pheromone dynamics, inspect generic

`tau_next = clamp((1-rho)*tau + Q*R_ant + theta*R_elite, tau_min, tau_max)`

as a **conceptual expression only**; map it to the exact source before making predictions or edits. If actual code uses a different order/normalization, preserve and document it.

### 3.2 Compare *hypotheses* about dimensionless effective reinforcement

Candidate experimental parameterizations (not automatic production changes):

- `M0`: current literal `theta` (control).
- `M1`: normalize elite/per-ant reinforcement according to **number of actually feasible contributing ants** `A`, to control for ant-count changes.
- `M2`: normalize by **number of rewarded features** (CHs/pairs/edges), if total deposit increases merely because feature count grows with `N`.
- `M3`: normalize score relative to a **reference solution cost** on the same network/round; e.g. quality ratio `C_ref/(C+eps)` instead of raw score magnitude, *only if the source objective is a positive cost minimized*.
- `M4`: combined normalization if tests show independent ant-count and sensor-count scaling.

Do **not** blindly implement `theta ∝ score/(num_ants * n_sensors)`. It may double-normalize or change physical units if per-ant deposits already include `1/num_ants`. Test each proposal against the exact formula and units.

**Test cases:** synthetic, deterministic maps with `N=50,100,200` while keeping density/coverage/connectivity comparable as far as possible; `ants=20,40,80`; multiple score scales produced by valid scenario changes or by controlled unit-scale tests (without changing physical scoring). Compare invariant **effective elite-to-ant reinforcement**, clamped fractions and selection entropy, not just service lifetime. Exclude changing `ants` from the *primary fixed-40 D-ACO tuner*; use these as separate **scaling diagnostics**.

**Decision:** if `theta` needs topology-aware reparameterization, introduce it as a **versioned opt-in policy** (e.g. `elite_scaling_policy=raw|per_rewarded_item|relative_quality`); keep the previous search space/fitness semantics reproducible. Future algorithm adapters must be able to register parameter transforms dependent on context, but never silently transform previously stored trial parameters.

---

## 4. Refactor optimizer into a reusable architecture (D-ACO now; PSO/AC-ACO next)

### 4.1 Architecture principle

**Optimization engine** knows nothing about ant pheromone or PSO particles. It owns: search algorithm, trial scheduling, timeout, storage, caching, cohorts/seeds, constraint checks, metrics, audit trails and reporting. An **Algorithm Adapter** owns: parameter schema/search space, safe instantiation, native fitness identity, validation of algorithm-specific semantics, model/time dependencies and optional checkpoint/state handling.

**No monolithic `if algo == "DACO" ... elif ...` in the optimizer core. No copying the whole tuner for each algorithm.** Use registry/factory and typed boundaries. Avoid a giant rewrite of the simulator; wrap existing constructors/runners.

### 4.2 Proposed minimal interfaces (illustrative, refine after source audit)

```python
@dataclass(frozen=True)
class StudyContext:
    algorithm: str
    model_sha: str
    map_sha: str
    n_sensors: int
    n_ants_or_particles: int
    network_horizon: int           # 3500
    adaptive_total_rounds: int      # explicitly recorded
    energy_reference_window: int    # 2611 on reference map
    source_fingerprint: str
    evaluator_fingerprint: str

class AlgorithmAdapter(Protocol):
    name: str
    adapter_version: str
    def baseline_config(self, ctx: StudyContext) -> dict: ...
    def suggest_config(self, trial, ctx: StudyContext) -> dict: ...
    def validate_config(self, cfg: dict, ctx: StudyContext) -> None: ...
    def effective_config(self, cfg: dict, ctx: StudyContext) -> dict: ...
    def make_algorithm(self, network, hparams, cfg: dict, seed: int): ...
    def fingerprint_semantics(self, cfg: dict, ctx: StudyContext) -> str: ...
    # checkpoint/restore is optional; if unsupported restart from round 0

class TrialEvaluator(Protocol):
    def run_trajectory(self, adapter, cfg, seed, topology, horizon) -> dict: ...

class ConstraintPolicy(Protocol):
    def evaluate(self, trajectory_cohort, reference_cohort) -> dict: ...
```

Shared types: `ExperimentSpec`, `TrialSpec`, `SeedRunResult`, `TrialAggregate`, `ReferenceBaseline`, `ConstraintResult`, `Provenance`, `TerminationReason`, `BudgetState`. Use existing repo conventions rather than introducing multiple frameworks. In logs store **requested parameters and resolved effective parameters** separately; resolve map/population-aware scales via adapter only.

### 4.3 Adapter responsibilities and initial registry

| Adapter | Tunable parameters (examples, inspect source) | Do not assume |
|---|---|---|
| `DACOAdapter` | `alpha,beta,gamma,Q,tau_max,rho_min/max,theta,load_density_weight,load_power,density_decay`, dependent groups if existing study used them | Raw score units, elite updates and `theta` scaling; preserve current primary study's actual search space when continuing |
| `PSOAdapter` (implement interface + smoke tests **only**) | inertia/schedule, cognitive/social terms, swarm size, velocity bounds, mutation/reset if actually present | PSO “iteration” means ACO ant count; changing particles also changes evaluation budget; same internal fitness |
| `ACACOAdapter` (implement interface + smoke tests **only**) | pheromone, chaos, adaptive beta/rho, CH distance, deposit parameters | Identical beta/rho semantics or chaos equations to D-ACO |

Every adapter declares `parameter_space_version`, `time_dependency_version`, `optimizer_native_fitness_id`, `evaluation_budget_policy`, `state_schema_version`, and explicitly which candidate search parameters vary CPU effort. Reject invalid configs early. Common reporting uses the **physical selected-tree energy and completed full-service rounds** regardless of native algorithm fitness, but **do not change native fitness functions during a comparison**.

### 4.4 Reusable core modules — proposed layout

```text
plans/optimizer_core/
  __init__.py
  contracts.py                # typed configs / results / interfaces
  registry.py                 # algorithm -> adapter registry
  adapters/
    daco.py
    pso.py                    # interface + smoke only
    acaco.py                  # interface + smoke only
  search/
    optuna_engine.py          # TPE and search configuration
    prior_trials.py           # historic-run importer / compatibility evaluator
  execution/
    controller.py             # global wallclock + worker concurrency
    worker.py                 # independent per-trial process
    checkpoint.py             # optional deterministic state restore
  evaluation/
    trajectory.py             # shared simulator wrapper; selected-tree-only energy
    constraints.py            # full-load energy +2% policy
    references.py             # matched reference baselines
    metrics.py
  persistence/
    study_store.py
    artifacts.py
    provenance.py
  reporting/
    summary.py
    plots.py
  tests/

plans/phase13-daco-autotuner-v2/
  study-config.yaml           # immutable snapshot when launched
  README.md                   # verified launch/status/stop/resume commands
  reports/
  runs/<study-id>/            # collision-safe; old runs untouched
```

If existing optimizer has equivalent modules, **refactor incrementally** rather than duplicating or relocating everything. Minimize changes to scientific behavior. Use configuration-driven study selection e.g. `algorithm: daco|pso|acaco`, `adapter_version`, `study_version`, `objective_version`, `constraint_version`.

### 4.5 Tests demonstrating generality

- Same `ExperimentSpec`/runner/metrics can run a 5–10 round *smoke-only* trial for each of D-ACO, PSO and AC-ACO, with independent seeded network state.
- Changing adapter does not require modifying optimizer-core modules; register new adapter through a factory/registry.
- D-ACO's trial on old config with same seed/topology/horizon yields identical result before and after refactor (deterministic equivalence), accounting for any existing behavior changes separately.
- PSO and AC-ACO adapters **do not initiate full tuning**, and their production defaults/equations remain unchanged.
- Adapter introspection reports effective values (including context-dependent `theta`) and differentiates `num_ants`, `swarm_size`, `inner_iterations` and `network_horizon`.

---

## 5. Reuse old Optuna runs safely (highest priority for 90-minute budget)

### 5.1 Old runs are potentially reusable, not automatically valid under the new objective

Build a **RunCompatibilityChecker** that reads old SQLite/Journal/RDB storage, trial/user attrs, CSVs, checkpoints and manifests **read-only**. Classify every existing run into these categories:

| Tier | Conditions | Permitted reuse |
|---|---|---|
| **A — exact reuse** | Same algorithm code + adapter + map + energy/routing + seeds + **3500 horizon AND identical adaptive `T_max`** + objective/constraint definition + complete evidence | Can include results in **new** study after checking full trial/censor/energy validity (avoid duplicate count) |
| **B — deterministic continuation** | Same prefix for all rounds, `T_max` and all effective schedules identical, complete checkpoint includes physical state, pheromone/swarm, RNG and optimizer state, validated by replay | Resume from checkpoint then collect **new 3500** score; do not pretend to resume if schedule changed |
| **C — parameter-only warm start** | Historical 3000-horizon or different `T_max`/fitness/adapter but legal parameters under current space | Enqueue/retest top settings and diversity anchors in new study; old service/energy are **metadata, not new objective observations** |
| **D — incompatible** | Missing fingerprints, corrupted/partial state, incompatible physics/topology/score semantics | Archive for provenance only; exclude from surrogate training and ranking |

**Important:** If `T_max` changes from 3000 to 3500 and beta/rho/aging decisions depend on it, **even rounds 1–2611 from old runs may not be exactly reusable**. No `study.add_trial` transfer as if 3000 values were 3500 values. Instead seed new study with old *parameter configurations* (`enqueue_trial` with stable dedupe) and evaluate anew. The Optuna interface supports enqueueing/adding trials, but cross-study objective semantics must be validated at application level. Verify installed Optuna APIs/storage behavior. See official source: https://github.com/optuna/optuna/blob/master/optuna/study/study.py .

### 5.2 Migration policy

1. Freeze legacy database (read-only snapshot + SHA); keep old study and trial IDs intact.
2. Build `legacy-trials-compatibility.csv` with `old_trial_id`, theta, full params, old `T_max`, objective metric, map SHA, seed set, adapter/fitness schema and tier A/B/C/D with reason.
3. Create **new** study `daco_service3500_energy2pct_v2` with separate DB/storage; never overwrite the 3000 study.
4. Seed Trial 25, Trial 30, D-ACO baseline, quarter-heuristic, other top-five and random/diverse configs; dedupe by canonical config+context fingerprint. Re-evaluate under new clock.
5. If old data are used as auxiliary multifidelity modeling features, clearly label fidelity/selection bias and verify learning is not pretending they are true 3500 outcomes; simplest safe default is `parameter-only warm start`.
6. New objective if more than one parameter space version exists: `study_version` and `adapter_version` must be pinned; no silent mixing of incompatible spaces, native fitness or adaptive schedules.

---

## 6. Background search controller: hard 90-minute budget

### 6.1 Global hard limits and execution behavior

- **Single global deadline:** monotonic clock, `5400 seconds` from explicitly authorized `start` command; includes worker startup, references/calibration if needed, trial execution, flush, report generation and shutdown. No “each worker gets 90 minutes” loophole.
- **Grace reserve:** target no new costly trial launches after `T−300 s`; leave ≥5 minutes to flush/mark incomplete safely. At `T=5400`, controller requests graceful stop, then bounded termination of hung workers; **never pretend interrupted 3500 trajectory was completed**.
- **Concurrency:** begin `max_workers=2`; raise to ≤4 only if memory/CPU pilot proves stable, process-level isolation on Windows `spawn`. Avoid nested 3-seed workers × N outer workers that oversubscribe.
- **No unrestricted retries:** max retry per failed trial, limited by the same global clock. Background process has PID, logfile, atomic checkpoint artifacts, robust study storage and `status/stop/resume` interface.
- **Restart semantics:** `resume` continues the **existing budget ledger** and preserves its original 90-minute total. Starting a fresh 90-minute campaign requires an explicitly new study/campaign ID and user authorization; do not reset elapsed time on resume.
- **No longer workloads if impossible:** track observed trajectory throughput. If a 3-seed full-3500 evaluation does not fit the remaining time, do not launch it; stop or run labeled short diagnostics without treating them as fully evaluated trial objectives.

### 6.2 Intelligent search allocation within the 90-minute cap

Initial rough **suggestion**, not a fixed number of trials:

| Window | Up to | Activities |
|---|---:|---|
| 0–10 min | 600 s | Compatibility audit, source fingerprint, smoke & representative 3500 timing estimate. If full reference already compatible, reuse it. |
| 10–75 min | 3900 s | Prioritized re-evaluation of known high-performing configs; then constrained TPE proposals, diverse exploration; fully budgeted seed cohorts. |
| 75–85 min | 600 s | Complete already-started cohorts, evaluate a promising configuration only if it can reliably finish, consolidate feasible leaderboard. |
| 85–90 min | 300 s | Graceful stop, save DB/checkpoints, report and verification manifest. |

The **controller must adapt timing to observed throughput**; on slow hardware, prioritize one full valid cohort over many incomplete ones. Any calibration/time spent after `start` counts against the 90 minutes. If preflight/refactor is not ready, **do not start the budget clock prematurely**; finish implementation and obtain approval to launch.

### 6.3 Search/adaptation strategy

- Preserve original **completed service** objective, hard **2% energy constraint**, paired seeds and common-workload policy.
- Optuna constrained TPE or existing verified search engine, with source-compatible trial constraints; include old high-performing parameters as anchors and controlled exploration. Never claim Bayes optimization proves exact global optimum.
- Tune **only D-ACO for this campaign**. Additional algorithm support is an architectural deliverable, not simultaneous PSO/ACACO tuning.
- Use multiple fidelity levels only for scheduling/diagnostics: checkpoints at e.g. 600/2611/3000 and a full 3500 completion. Do not rank a 3000-censored result as a completed 3500 trial.
- Safely stop clearly invalid candidates. Do not prune solely because early round energy is higher: lifetime can improve later. Energy exceeding a nonnegative cumulative cap in a *strictly comparable* window may be a legitimate infeasibility signal, but confirm units and monotonicity.
- Final ranking only from complete, valid matched seed cohorts; mark incomplete/censored properly and show all per-seed raw outputs.
- Holdout seeds/topologies remain untouched during the 90-minute optimization unless explicitly allocated to final validation **after freezing the candidate**.

---

## 7. Testing and acceptance criteria

**Correctness tests**

- [ ] Original D-ACO source behavior preserved when loaded through new adapter with baseline parameters (equal seed, map, horizon).
- [ ] 3500 is a **network horizon**, not a change to ants per round or count of inner optimization iterations.
- [ ] All adaptive expressions depending on 3000/T_max have been inventoried, tested for 3500 and logged at boundary/midpoint.
- [ ] Theta formula/units explained from actual code; normalization variants do not silently change score interpretation or double-normalize by `n_ants*n_nodes`.
- [ ] Valid params and probabilities, legal rho/tau bounds, consistent elitist update and finite fitness under candidate extremes.
- [ ] Rejected search candidates do not deduct physical network energy; selected tree accounting matches shared evaluator.
- [ ] Same map + seeded run reproducible; checkpoint resume restores all relevant algorithm/physical/RNG state.
- [ ] Old trial compatibility checker assigns A/B/C/D correctly; 3000 data not silently imported as 3500 complete objectives.
- [ ] Energy policy: matched 2611 all-alive/all-served rounds and cap `43.315422 J` on reference cohort; early death/incomplete workload never passes energy constraint.
- [ ] App never confuses FND, optimizer failure and graph disconnection; 3500 cap correctly marks censored service.
- [ ] D-ACO/PSO/AC-ACO adapters share same engine/evaluator infrastructure; only D-ACO enters active tuner.
- [ ] Controller survives worker crash and restart without duplicate completed studies; total elapsed wall ledger ≤5400s across resume and start.
- [ ] Any background metrics include CPU+wall and attempted/unique/feasible counts; no unreported oversubscription.
- [ ] No simulator/routing/energy model or unrelated algorithm production file changed; unchanged algorithm defaults remain valid.

**Benchmark checks**

- [ ] Confirm previous Trial 25 parameter vector/source fingerprint and re-evaluate under new `T_max=3500` rather than asserting continued superiority.
- [ ] Save original `3000` results unchanged; report how many legacy trials were compatible versus parameter-only warm-start.
- [ ] At least one valid full-3500 paired-seed D-ACO cohort completed **if runtime permits**; otherwise explicitly state no full proof and do not select a new winner.
- [ ] Report all feasible/infeasible/failed/incomplete trials; do not hide the negative outcomes.
- [ ] Do not promote production defaults automatically; keep 90-minute best as research candidate pending held-out validation.

---

## 8. Phased implementation order and deliverables

### Phase A — Inspect & derive (no background run)

1. Read current optimizer package, Optuna DB schema and latest report/data; confirm the exact actual search space, Trial 25/30 and `theta` uses, `T_max` formulas, map/count dependence.
2. Validate selected energy policy/cap and old run reuse tiers.
3. Design adapter contracts/registry; propose minimal file diff and a correct 3500 study fingerprint.
4. Produce `plans/reports/daco-v2-architecture-and-provenance.md`, `theta-scaling-audit.md`, `legacy-trials-compatibility.csv`, `adaptive-horizon-inventory.csv`.
5. **Do not launch 90-minute job yet.**

### Phase B — Implement generic engine & adapters (no costly sweep)

1. Extract common engine from D-ACO tuner with small refactor; keep CLI compatibility or provide migration wrapper.
2. Build D-ACO adapter, PSO/AC-ACO adapters (test/instantiate only), study registry, versioned search space and robust parameter overrides.
3. Implement 90-minute global resource/deadline ledger, graceful stop/resume, read-only migration/parameter anchor importer.
4. Run regression tests, tiny smoke trajectories and kill/restart test. Produce `plans/reports/daco-v2-optimizer-refactor-validation.md` and exact launch/config README.
5. **STOP and obtain explicit user approval before launching expensive tuner.**

### Phase C — 90-minute D-ACO tuning campaign (explicitly approved run)

1. New immutable campaign ID. Log deadline, limits, source SHA, seed cohort, physical model, `T_max=3500`, energy cap and parameter space.
2. Seed prior best Trial 25/30 and anchors; calibrate throughput; run autonomous constrained search with ≤2 workers initially.
3. Run best feasible 3500 trials on all agreed paired seeds, preserve incomplete outputs but no fake winners; obey hard timeout.
4. Produce `plans/reports/daco-v2-90min-3500-results.md`, entire study DB, trial metadata CSV, best-feasible config, energy/service/FND plots, resume manifest.
5. **STOP: no PSO/AC-ACO tuning and no default promotion.**

### Phase D — Post-hoc scientific validation (separate approval and budget)

1. Freeze best fully completed feasible D-ACO configuration from Phase C.
2. Compare against matched SimpleACO, previous D-ACO/Trial 25, and optional PSO using native and controlled evaluation budgets clearly separated.
3. Holdout seeds/maps not used during tuning, longer horizons only with approval; connectivity certificate where needed.
4. Evaluate whether any `theta` normalization policy generalizes across node counts or merely fits the reference map.
5. Recommend promotion **only after** independent reproducibility, energy, service and CPU evidence. Report uncertainty/noise.

---

## 9. Final outputs and explicit stop conditions

Proposed outputs (create only when phases execute):

```text
plans/optimizer_core/                            # Generic reusable engine
plans/phase13-daco-autotuner-v2/
  config.example.yaml
  README.md
  runs/<campaign-id>/
    provenance.json
    legacy-trials-compatibility.csv
    adaptive-horizon-inventory.csv
    theta-scaling-diagnostics.csv
    study.db / journal
    trial-results.csv
    per-seed-results.csv
    incomplete-trials.csv
    best-feasible-config.yaml
    plots/*.png
    logs/*.log
plans/reports/
  daco-v2-architecture-and-provenance.md
  theta-scaling-audit.md
  daco-v2-optimizer-refactor-validation.md
  daco-v2-90min-3500-results.md
```

**All artifacts must include config/source/topology fingerprints and unique directories; do not overwrite previous research results.** Real CLI commands must be documented and tested on the user's current OS. On Windows use `multiprocessing` spawn protection, separate worker logs and trustworthy storage locking; choose a concurrency-compatible Optuna backend supported by the installed version.

### Final operational contract for Codex

**Proceed incrementally.** First implement **Phase A and B** with regression tests and no long-running jobs. Inspect and tell the user whether any old 3000-horizon trial can truly resume as 3500; if not, enqueue parameter sets without migrating scores. Finish with an explicit proposed launch command and resource settings. **STOP for approval** before Phase C. Once approved, run the **whole background campaign under one strict 90-minute global deadline**, then STOP before PSO/AC-ACO tuning or any default changes.

**Success:** A correct, reusable optimizer architecture plus an honest, time-bounded D-ACO search at a 3500-round algorithmic horizon, with valid energy constraints, reliable provenance, and no disguised reuse of incompatible 3000-round results.
