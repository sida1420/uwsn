# Tuned ACO to AC-ACO: audit, mapping and validation

Branch `fix-ac-aco-long-time`; baseline HEAD `8930cb208548961bb43a714c51879206c95e9aa2`.
All statements below concern the current source, not the older repository memory.
Raw controls, old source and benchmark scripts: `aco-transfer-261007-0810/`.

## Root cause: the premise requires qualification

Matched five-seed early-round measurements **do not confirm that current tuned
ACO consumes less energy** than old AC-ACO or pre-tuning ACO. See validation
tables below. Low cumulative consumption after an early stop is not efficiency.
No transmissions, live sensors or accounting components were omitted in the
measured feasible trees. All trees pass full-coverage and independent packet
accounting checks, including radius and parent/cycle checks.

The latest tuning changes three things, not just parameters:

- `8930cb2`: ACO inverse-hop-energy exponent `beta: 1 -> 0.5`.
- `8930cb2`: ACO deposit scale `Q: 100 -> 0.07`.
- `8930cb2`: `SimpleACO.plan_round` now deposits for each successful ant,
  immediately, in addition to the winning-path deposit after evaporation.
- Earlier `7d0628b`: ants `20 -> 40`, retries `20 -> 10`, beta `3 -> 1`.
AC-ACO already has the current 40/10 search budget.

`src/run.py` currently selects NodeACO and PSO, neither SimpleACO nor AC-ACO.
Running that entry point unchanged cannot reproduce a claim about the two
algorithms audited here. Existing CSVs also lack a complete parameter/map/code
manifest. The focused harness selects the audited classes explicitly and saves
that provenance; historical output is not treated as a matched comparison.

ACO `_make_path` actually computes
`tau^alpha * (residual_e / inter_CH_distance)^gamma * E_m^-beta`.
AC-ACO `_transition_probabilities` computes
`tau^pheromone_exponent * (residual_e / inter_CH_distance)^beta(t)
* E_m^-energy_cost_exponent`, then chaotic mixing.
The exponent names are swapped. Copying ACO beta into AC-ACO beta would map
the wrong factor and disable/alter the intended adaptation.

Reducing the hop-energy exponent softens attraction to very short CH-path
edges. Reducing Q avoids extreme deposits relative to the model's ~0.02 J
route costs. These are plausible mechanisms, not proof of lower route energy.
Immediate deposits introduce stronger within-round exploitation, which can
also reinforce spatially concentrated CH paths. Ordered CH-path edges are
not necessarily actual routing-tree edges: pheromone learns a CH ordering,
while fitness scores the separate greedy tree. This proxy is a structural
limitation shared by both algorithms.

## A. Parameter audit and mapping

| Tuned ACO parameter | Before tuning | Tuned | AC-ACO before | AC-ACO after | Role/classification and reason |
|---|---:|---:|---|---|---|
| ants | 20 historically, then 40 | 40 | 40 | 40 | Static, SAFE TO MAP; already equal. Actual distinct starts capped at live count |
| retries | 20 historically, then 10 | 10 | 10 | 10 | Static, SAFE TO MAP; retries, not optimization iterations |
| CH proportion | .20 | .20 | .20 | .20 | Static fraction; count derived from live count; already equal |
| alpha | 1 | 1 | pheromone_exponent=1 | 1 | Static, SAFE TO MAP; no adaptive alpha exists in this code |
| beta on inverse E_m | 3 historically, then 1 | .5 | energy_cost_exponent=1 | .5 | Static, SAFE TO MAP by mathematical role, not label |
| gamma on residual/distance | 1 | 1 | adaptive beta 1..5 | adaptive beta 1..5 | MAP WITH MODIFICATION; tuned gamma=1 is already the adaptive lower/reference value |
| rho | .1 | .1 | adaptive .9 -> .1 | adaptive .9 -> .1 | DO NOT MAP as a constant; tuned .1 already matches the adaptive late bound |
| Q | 100 | .07 | 100 | .07 | Static deposit scale, SAFE TO MAP; same objective units, no Q adaptation |
| tau0 | 1 | 1 | 1 | 1 | Static initial value, already equal |
| tau_min/tau_max | .1/10 | .1/10 | .1/10 | .1/10 | Static bounds, preserved and now enforced after deposits too |
| hopping factor | .4 | .4 | .4 | .4 | Static router control, already shared |
| iterations | no inner loop | no inner loop | simulator T_max | simulator T_max | Derived horizon=3000; not copied from retry count |
| beta slope | absent | absent | 5 | 5 | AC-only adaptive control retained; very steep transition near round 1500 |
| chaos min/max | absent | absent | .05/.30 | .05/.30 | Cost-derived exploration strength retained |
| logistic r/seed | absent | absent | 3.61/.37 | 3.61/.37 | Deterministic chaotic sequence retained, distinct from RNG seed |

These mappings establish the requested baseline; SAFE means compatible roles
and accounting, not an empirical guarantee that every changed default lowers
energy. Ablations explicitly test that distinction.

## B. Component-by-component comparison

| Component | Tuned ACO | Current old AC-ACO | Difference | Should map? | Reason |
|---|---|---|---|---|---|
| starts | sample distinct live nodes | independent random choice per ant | duplicates possible | SAFE TO MAP | use distinct starts; reuse each ant's start on retries |
| CH path | ordered walk without repeats | ordered walk without repeats | same construction concept | already shared concept | retain unique CH IDs and insertion order |
| candidate filtering | live minus selected | positive residual live minus selected | AC filters dead energy more defensively | DO NOT MAP weaker filtering | retain AC protection |
| heuristic | residual/inter-CH distance | same ratio, adaptive exponent | exponent roles/schedules differ | MAP WITH MODIFICATION | keep beta adaptation over tuned baseline residual weighting |
| hop heuristic | inverse E_m^.5 cached | log(E_m), exponent 1 cached | different exponent | SAFE TO MAP | set energy_cost_exponent=.5, retain cached logs |
| probabilities | scalar products, random.choices | log/NumPy, normalized then chaos | AC numerically safer | DO NOT MAP scalar arithmetic | preserve stable max-subtracted log weights |
| within-round learning | list pheromone sees immediate ant deposits | NumPy snapshot never sees them | accidental divergence | SAFE TO MAP | synchronize the array when depositing |
| successful-ant deposit | Q/(cost*configured ants) | same formula | same rule, stale read in AC | SAFE TO MAP | retain deposit and correct visibility |
| best deposit | Q/cost after evaporation | same plus chaotic update | intentional AC addition | MAP WITH MODIFICATION | retain chaos and adaptive evaporation |
| clipping | only evaporation stage | only evaporation/chaos stage | both can exceed nominal bounds | DO NOT MAP defect | AC now clamps each deposit; ACO baseline preserved |
| evaporation | fixed .1, entire matrix | adaptive .9 -> .1, live edges | intentional feature | DO NOT MAP static rho | keep schedule and live-only update (dead nodes cannot revive) |
| chaos probabilities | none | (p+c)/(1+n*c) | candidate-count-dependent uniform mass | DO NOT MAP weaker exploration | preserve original rule; total-mass normalization trial shortened service in three paired seeds |
| chaos pheromone | none | source-dependent additive term | defining AC feature | DO NOT MAP absence | retain term and advance logistic map once per round |
| alpha adaptation | none | none | none | no change | debug alpha is static pheromone exponent; chaos strength is adaptive |
| beta adaptation | none | sigmoid 1..5 | defining AC feature | DO NOT MAP static gamma | retain sigmoid and horizon |
| rho adaptation | none | linear decrease | defining AC feature | DO NOT MAP static rho | retain linear decrease |
| chaos cost window | none | lifetime min/max feasible costs | intentional UWSN adaptation | retain | not changed to a new objective/window |
| cluster assignment | nearest CH within radius | same build_clusters | none | already shared | no balancing heuristic exists in either version |
| outliers/dropped members | greedy multi-hop route | identical router | none | already shared | outliers are routed/charged, not discarded |
| CH-BS selection preference | no explicit BS term | none in CH selection | none | no invented feature | BS-distance/residual terms exist in shared relay cost |
| relay choice | normalized energy + squared-distance cost | same | none | already shared | preserve hopping factor and greedy feasibility |
| objective | raw total round energy | raw total round energy | none | already shared | no normalization, load balancing or lifetime penalty introduced |
| best candidate | strict lower cost; first tie wins | minimum (cost, CH tuple) | deterministic tie convention | retain AC convention | equal-cost ties do not change objective value |
| route cost validation | no explicit finite check | finite and positive check | AC stronger | retain AC check | no copying weaker validation |
| failure update | returns before post_round if all fail | always post_round after nonempty live state | AC intentional robustness | retain AC behavior | schedules/chaos advance on failed search too |
| search convergence | one population per network round | same | no inner early-convergence rule | no change | retries stop at first feasible route, not local optimum |
| pheromone memory | persists across network rounds | same | none | no change | fresh instances needed per experiment |
| seed | global random only | local Random(seed) | inconsistent API/fallback | SAFE TO MAP infrastructure | both accept local explicit seed; no-seed callers honor random.seed |
| distance model | full 3D Euclidean | same NetworkInstance matrices | none | already shared | no coordinate dimensionality changes |
| energy model | shared Evaluator | same | none | already shared | do not alter accounting to favor an algorithm |
| shortcuts | static E_m cache | static log(E_m), NumPy snapshots | snapshot accidentally stale | MAP WITH MODIFICATION | retain cache/vectorization, correct mutable pheromone view |

## C. Infrastructure and accounting audit

Confirmed shared `Point.__abs__` includes x/y/z; `NetworkInstance` holds
immutable sensor-indexed distances. Neither algorithm renumbers/removes sensor
coordinates. Both route through `dropping_member_multi_hop_routing`, which
enforces radius, moves blocked members out of clusters and routes them onward.

`Evaluator` is shared, unchanged, and differs materially from old repository
memory: ordinary nodes send one own packet; non-CH relays send one own packet
plus received packets; CHs always transmit TWO packets, receive all child
packets and aggregate all received packets; base is free. Empty CHs still send
two packets, with zero aggregation cost. CH aggregation assumes fixed output
size, including traffic forwarded by other CHs. These are model choices needing
scientific confirmation, not algorithm-specific improvements.

`E_tx` converts metres to kilometres, and HyperParameters converts Thorp
frequency Hz to kHz. Both fixes predate the latest tuning and affect all
algorithms equally. All measured node costs include TX, RX and CH aggregation.
Control traffic, clustering computation and MAC/retransmission costs are absent
for both. No model changes were transferred.

Old AC-ACO demonstrated live pheromone 126 after one example deposit while
the read snapshot remained 1. The nominal maximum was 10. At N=100, first-step
old probability chaos put **80.64%** of mass on uniform exploration for source
0, strength .05. This is strong exploration, not an accounting bug. An initial
`(p+c/n)/(1+c)` trial kept logistic chaos but weakened its probability mass.
In seeds 0/1/2 it stopped after 1831/1740/1629 rounds, versus tuned ACO's
2210/2327/2335. The final patch therefore **preserves original probability
chaos**; no weaker-exploration rule is transferred merely to resemble ACO.
The trial source/results are archived under `trial-total-mass` / `normalized`.
Seeds 3/4 of that rejected variant were stopped; no result is imputed for them.

The reference [Zhou et al. paper, Eq. 11–15 and 20–21](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf)
provides logistic chaos, adaptive rho/beta and energy-dependent disturbance.
The final implementation preserves these mechanisms and its original
normalized additive probability perturbation. The tested, rejected
candidate-count adjustment is not attributed verbatim to the paper.

## Reproducibility and experiment controls

Seeds predeclared: 0,1,2,3,4. Every algorithm is freshly instantiated with the
same seed. `SimpleACO` now supports explicit seed; supplying it isolates its
random state. AC-ACO also uses explicit seed, and neither generates unrelated
seeds internally. Fixed logistic initialization is a deterministic control.
`run.py` defaults to seed 0 and accepts `--seed`; ALGORITHMS remains the branch's
NodeACO/PSO list. The focused comparison harness explicitly selects ACO/AC-ACO.

Original map SHA256:
`ebe729265598746b30af09715e239a9891b2ac95ac66656096dc712e6c34fdcc`.
N=100, cube 500 m, BS=(250,250,0), radius=200 m, initial energy .6 J/node.
All HyperParameters unchanged: T_max=3000, P0=.1, packet=200, rate=10000,
E_elec=5e-8, E_integrate=5e-9, frequency=30000 Hz, spreading=1.5.
The harness runs the same live/residual loop and stopping conditions as
Simulator, plus diagnostics and assertions; it does not change CSV metrics.

Validation records modeled energy AND actual clamped residual depletion,
because the existing last-round accounting can exceed a dying node's residual.
Lifetime is reported as completed rounds and stop reason; first death is
separate. A T_max stop is censored lifetime, not measured network death.
`no_feasible_route` means this algorithm exhausted its candidate search,
not proof that no routing tree exists in the physical communication graph.
The original radius graph is connected with ten BS-adjacent sensors and no
single-sensor articulation disconnecting remaining nodes. Under a stricter
monotone-to-BS graph, removing sensor 33 blocks sensor 48; this illustrates
the router's sensitivity but does not identify which sensors died in these
recorded runs. Actual cluster constraints/search add further restrictions.

## Controlled ACO ablations (first 100 rounds)

Mean ± sample SD across the five predeclared seeds; all 100 nodes remain alive.
The pre-tuning control restores Q=100, hop exponent=1 and removes per-ant
deposits, preserving all other current conditions.

| ACO configuration | Energy J (100 rounds) |
|---|---:|
| Before latest tuning (restored controls) | 1.519621 ± .014490 |
| Tuned except Q restored to 100 | 1.722666 ± .016791 |
| Tuned except hop exponent restored to 1 | 1.870046 ± .030032 |
| Tuned except per-ant deposit removed | 1.674385 ± .007723 |
| Current tuned baseline | 1.792357 ± .012207 |

Lower hop exponent helps relative to its isolated reversal. Lower Q and the
new per-ant feedback do not improve early energy in these controls. This
interaction prevents attributing the complete tuning package to lower energy.

| AC-ACO control | Energy J (100 rounds) |
|---|---:|
| Old unchanged | 1.675484 ± .003845 |
| Old with Q=.07 only | 1.675685 ± .002927 |
| Old with hop-energy exponent=.5 only | 1.667571 ± .004272 |
| Old with both scalar mappings | 1.667182 ± .004060 |

The stale snapshot and heavy original chaotic mixing mute the immediate
behavioral effect of Q. Correcting those changes exploitation, so the full
patch must be assessed independently rather than inferred from two scalars.

## Structural evidence (first 100 rounds, five-seed means)

| Metric | Pre-tuning ACO control | Tuned ACO | Old AC-ACO |
|---|---:|---:|---:|
| node-to-CH distance, m | 107.963 | 120.591 | 106.271 |
| geometric CH-to-BS distance, m | 268.827 | 278.218 | 297.075 |
| member-count SD across clusters | 2.595 | 2.833 | 2.452 |
| nodes outside direct CH membership | 3.334 | 8.758 | 3.404 |
| TX energy per round, J | .0137734 | .0164591 | .0152725 |
| RX energy per round, J | .0013104 | .0013513 | .0013697 |
| aggregation per round, J | .0001124 | .0001132 | .0001127 |

Geometric CH-BS distance is not actual transmission distance in multi-hop
routing; the artifact also records CH-to-parent hop distance. Nodes outside
direct CH membership still participate, often as relays. Cluster sizes count
direct non-CH children after the router's membership changes; forwarded traffic
is separately reflected in packet accounting. Both use 20 CHs while all alive.

## Changed files/functions

- `src/algorithms/ac_aco.py`: `plan_round` iterates distinct starts and passes
  the same start through retries.
- `src/algorithms/clustering/ac_aco/ac_aco.py`: `RoundState`, `__init__`,
  `pre_round`, `create_clusters`, `_construct_candidate`,
  `_transition_probabilities`, `deposit`, `_update_pheromone`.
- `src/algorithms/clustering/ac_aco/parameters.py`: defaults Q/energy exponent
  and unused import removal; adaptive controls unchanged.
- `src/algorithms/aco.py`: `__init__`, `init_params` forward explicit seed.
- `src/algorithms/clustering/aco/aco.py`: `__init__`, `pre_round`, `_make_path`
  route draws through local seed; unchanged formula/parameters/deposit behavior.
- `src/algorithms/clustering/aco/parameters.py`: correct swapped role comments
  only; numerical tuned baseline unchanged.
- `src/run.py`: seed default, factory/main propagation and CLI.
- `tests/test_ac_aco_vectorization.py`: replace stale recorded trajectory with
  deterministic repeatability, coverage, cost recomputation and budget checks.
- `tests/test_aco_baseline_mapping.py`: targeted mechanisms/seed/failure tests.
- `tests/test_aco_energy_accounting.py`: independent packet and 3D tree checks.
- `src/algorithms/clustering/ac_aco/AC_ACO_README.md` and
  `docs/aco-ac-aco-baseline.md`: current defaults, preserved mechanisms,
  normalization choice and reproduction instructions.
- Research plan/report and benchmark/snapshot/artifact files listed in the
  companion generated validation report.

No PSO, Evaluator, Simulator, shared router or map changes.

## Validation status and scientific conclusion

The 23-test suite passes. Independent review found no remaining critical or
important source issues (initial review score 9.3/10; final focused review
confidence 97%). Targeted checks
for deposits, invalid costs and distinct starts fail against preserved original
AC-ACO and pass against the patch. The probability-chaos test now verifies the
original rule, following rejection of the experimental normalization.
In-memory compilation passes for source, tests and
benchmark scripts; git diff whitespace check passes. The original nine-test
suite had a pre-existing stale trajectory failure (second seed-39 cost
.017620360174250654 vs recorded .017200815068502497) before implementation.
The replacement tests preserve actual reproducibility and accounting
requirements instead of updating magic energies to match changed behavior.

All 15 full lifetime cases (three algorithms, seeds 0–4) are complete. The
[generated validation report](validation-261007-0810-tuned-aco-transfer.md)
provides paired fixed-horizon energy, total modeled/depleted energy, residual,
first death, completed rounds, alive traces, cluster sizes, objective/convergence
and evidence of adaptive/chaotic execution. Source hashes and package versions
are saved in the artifact manifest; original AC-ACO and the rejected trial are
preserved separately. Every measured route has full live-node coverage and
independently verified per-node packet accounting.
The final saved traces also pass component-sum, cluster-member and best-fitness
consistency checks across all 33,213 completed rounds; the manifest matches the
43 recorded current source/test/research files. Documentation links resolve.

Updated AC-ACO averages 1.669851 J in the matched first 100 rounds, versus
tuned ACO's 1.792357 J and old AC-ACO's 1.675484 J: 6.83% and 0.34% less,
respectively. It beats old AC-ACO in four energy seeds, with a small mean gain
that does not establish general superiority. Mean routing service is 2184.0
rounds, versus 2279.2 for tuned ACO and 2179.4 for old AC-ACO. All runs stop
on unsuccessful full-network route search with 95–99 nodes still alive.
The current objective optimizes round energy, not relay lifetime or future
routing feasibility. Tuned ACO's longer service means its greater final total
energy is not evidence of worse lifetime; totals cover different durations.
AC-ACO's shorter member hops (105.856 m versus 120.591 m), more even direct
cluster sizes (SD 2.418 versus 2.833), and lower TX cost explain its measured
energy advantage, despite longer geometric CH-to-BS distances.

The transfer preserves AC-ACO's adaptive beta/rho and both chaotic mechanisms:
logistic state changes in all 10,920 completed updated rounds, beta reaches
5, and rho declines to about .315. Its benefit over old AC-ACO is modest and
not a demonstrated lifetime breakthrough. Strong path exploitation
can concentrate CHs, producing expensive outlier relay traffic, while uniform
exploration can spread CHs and reduce node-to-CH distances. A round-energy
objective also lacks a lifetime/connectivity penalty for critical relays.

## Unresolved research questions

1. Are two packets per CH (including empty CHs) and fixed-size aggregation of
   transit traffic the intended physical model? Unchanged in this patch.
2. Should future studies optimize round energy, first death or routing service
   lifetime? Current objective remains raw round energy.
3. Do results generalize to other 3D deployments/radii? Five seeds on one
   unchanged map do not establish topology-wide superiority.
