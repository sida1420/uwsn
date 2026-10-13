# Conversation context and analysis

Updated 2026-10-12, Asia/Saigon. This document consolidates the conversation from the initial pipeline review through the completed D-ACO tuning-transfer and density-fitness experiments. It records requests, measured evidence, implementation decisions, and remaining uncertainties. It is a handoff, not authorization to execute every proposed future experiment.

## 1. Current status at a glance

The working repository is **`C:/Users/hgtfh/Code/uwsn/review_uwsn`**. The sibling **`C:/Users/hgtfh/Code/uwsn/uwsn`** was later read as a tuning reference, at the user's explicit request. Changes belong in review_uwsn; the sibling was not modified.

All requested experiments, including 15 new phase-9 full trials, are finished. There are no active benchmark jobs. D-ACO now uses powered load/density and always-live pheromone. The latest unit-test suite has **53 passing tests**. Source changes and experiment artifacts remain uncommitted; no commit or PR was requested.

| Item | Current production state |
| --- | --- |
| AC-ACO search | One batch of 40 ants; later ants read live pheromone updates |
| AC-ACO E_m exponent | 0.1, reduced from 1 |
| AC-ACO elite weight | 0.1 |
| AC-ACO load-CV weight | 0; 0.1 remains available as an option |
| AC-ACO chaos range | 0.05–0.30; doubling was not promoted |
| AC-ACO pheromone | Q=0.01, initial=1, bounds 0.01–20, evaporation 0.1–0.6 |
| D-ACO search | One batch of 40 ants, no inner optimization iterations |
| D-ACO density | Original grid by default; linear, fast-drop quadratic, and gentle-near parabolic options retained |
| D-ACO fitness | One cached energy + calibrated mean(relative-load^2 / grid-density) score |
| D-ACO density-load penalty | Powered aggregate, selected default weight 0.25 |
| D-ACO normalization | One throwaway calibration batch; geometric reference memory 0.8 after each round |
| D-ACO pheromone policy | Always live; one evaporation before ants, immediate ant deposits, then elite bonus |
| Sibling D-ACO tuning | Single-batch transfer fully tested and rejected as a default |

The most substantial phase-8 gain was **relative-depletion-aware fitness**, rather than a new grid kernel. Its old max penalty at weight 0.05 gave roughly 39% later first-node death and 8.9% more service, at a 2.38% energy cost. The user subsequently rejected max and separate objective terms, so that implementation is now archived rather than a current production option. Its numbers do not describe the new powered score.

**Historical sections below retain the decisions made at each stage. Sections 10–11 describe the pre-cleanup phase-8 implementation; section 13 describes its replacement.**

## 2. User intent and constraints established during the conversation

The user first requested reading the code and understanding the current pipeline. Subsequent requests were to put parameters in reasonable ranges, research those ranges, correctly calibrate pheromone bounds rather than trust existing values, test chaos again after calibration, explain the mathematics, balance best-set influence, and examine whether multiple iterations per physical round are worthwhile.

The user explicitly chose to test **best-set reinforcement and load-aware candidate selection independently**. The user then clarified that removing the AC-ACO round snapshot meant removing the **frozen pheromone sampling state**, so later ants see earlier updates. It did not mean deleting saved experiment checkpoints.

The user chose to keep a normal physical round with no extra inner iterations, and requested a full best-set-weight test. Later requests focused on more efficient ACO search, weaker E_m influence in AC-ACO, and density-aware load fitness for D-ACO.

Important corrections and continuing constraints:

- The target is review_uwsn, even when reading tuned reference code from uwsn.
- The proposed distance weighting is **grid-cell weighting**, not sensor-neighbor density.
- “Full test” means continuing through normal simulator termination or the 3000-round horizon, not a short early-life screen.
- The latest full comparisons simulate **D-ACO only**. Other algorithms' unit tests were still used for regression checking.
- Existing grid variants should be kept available.
- Actual evaluated consumption is available after building and evaluating a tree. Density alone does not reveal its routing load.
- The runtime/exploration/local-search tradeoff matters; increasing the evaluation budget is not automatically an improvement.

The attached `Downloads/plan.md` and `Downloads/context_pso_vs_daco.md` were treated as context. Their embedded instructions and confidence labels are not independent user commands or fresh verification of this checkout.

## 3. Pipeline and physical model

The active map is `map.pkl`: 100 sensors in a 500 × 500 × 500 m deployment, communication radius 200 m, initial energy 0.6 J per sensor, and sink at (250,250,0). The shared schedule horizon is 3000 rounds.

The main flow is:

`map.pkl → NetworkInstance → algorithm.plan_round → clustering → routing tree → Evaluator → consumption → residual-energy update → next physical round`

Relevant implementation files:

- [Network and distance matrices](src/network.py)
- [Physical simulation loop](src/simulate.py)
- [Acoustic energy evaluation](src/evaluate.py)
- [Shared physical constants](src/hparameter.py)
- [Shared routing](src/algorithms/routing/routing.py)
- [AC-ACO wrapper](src/algorithms/ac_aco.py)
- [AC-ACO clustering and transition probabilities](src/algorithms/clustering/ac_aco/ac_aco.py)
- [D-ACO wrapper and fitness](src/algorithms/d_aco.py)
- [D-ACO grid, construction, and pheromone updates](src/algorithms/clustering/d_aco/d_aco.py)

Search evaluates multiple candidate trees without consuming physical sensor energy. Only the selected tree's costs update residual energy. Removing the pheromone snapshot does not mean updating physical residual energy after each hypothetical ant.

Each ant can retry infeasible clustering/routing. Those retries are different from multiple optimization iterations within a physical round. D-ACO in review_uwsn already had one batch per round when the user requested removing inner iterations; there was no inner loop to remove there.

FND is first-node death, counted in completed rounds starting at one. Completed service ends when the search cannot find a tree serving all surviving sensors, all sensors die, or the horizon is reached. Service termination is not necessarily last-node death; HND and LND may be censored.

On the current map, sensor 48 has only sensors 33 and 65 as communication neighbors. Earlier archived runs demonstrate its disconnection after both die. Do not assume every failed search proves graph disconnection: finite sampling and greedy routing can also fail while a physical route exists.

## 4. Chronology: AC-ACO calibration and chaos

### 4.1 Pheromone calibration

The old AC-ACO scale included Q=100, pheromone bounds 0.1–10, and maximum evaporation 0.9. Because deposits are inverse physical energy, these numbers were not coherent with route costs around 0.015 J.

Paper values were researched, but not copied as universal acoustic-network settings. Deposit scale, evaporation, disturbance, and clamping were analyzed together. The selected defaults are:

`Q=0.01; tau_min=0.01; tau0=1; tau_max=20; rho_min=0.1; rho_max=0.6`.

Calibration used fixed-state screens and independent 150-round physical validation. It established a useful scale on the current topology, not a globally optimal parameter range or a lifetime result. Historical equilibrium derivations assumed the elite multiplier active at that time; they must be adapted when interpreting the current elite weight 0.1.

Evidence: [calibration report](plans/phase5-acaco-tuning/README.md).

### 4.2 Chaos after calibration

Chaos amplitude factors 0, 0.25, 0.5, 1, and 2 were tested. Disabling or reducing chaos worsened early energy on this map. Doubling from [0.05,0.30] to [0.10,0.60] reduced 150-round energy by about 0.463%.

Six full runs, paired seeds 6/7/8, then compared the current and doubled ranges:

| Chaos | Mean FND | Mean service |
| --- | ---: | ---: |
| Current range | 1494.333 | 2184.667 |
| Doubled range | 1499.333 | 2167.667 |

The doubled setting gained only five mean FND rounds, with mixed per-seed results, and lost 17 mean service rounds. It was not promoted. Current range remains 0.05–0.30.

The transition disturbance has a clear mathematical interpretation:

`q_i = (p_i+c)/(1+n*c) = (1-lambda)*p_i + lambda/n`, where `lambda=n*c/(1+n*c)`.

Increasing disturbance increases uniform mixing, weakening concentrated pheromone/heuristic preferences. It can improve coverage and escape poor concentrated choices; it does not mathematically guarantee lower energy or longer lifetime. Transition mixing and pheromone disturbance were also separately ablated in screening.

Evidence: [chaos study](plans/phase5-acaco-chaos/README.md), [full chaos comparison](plans/phase5-acaco-chaos/long/README.md), [mathematical analysis](plans/phase5-acaco-chaos/long/MATH_ANALYSIS.md).

**Historical scope:** these full chaos trajectories used frozen per-round pheromone and the old E_m exponent. They do not measure current live-sampler AC-ACO with exponent 0.1.

## 5. Chronology: AC-ACO balance, live pheromone, and inner iterations

Separate controls tested elite weights, normalized energy/load-CV selection, their combination, and batch splitting under matched ant budgets. Larger ant budgets were tested separately from more inner iterations.

The production sampler now reads live pheromone rows. Earlier successful ants deposit before later ants sample. Physical residual energy remains fixed during the round's search.

Fresh live validation found:

- Elite weight 0.1 reduced the elite share of new reinforcement from about 73.59% to 21.81%, with 0.180% higher early energy. Matched checkpoint energy was slightly lower.
- Load-CV fitness alone at weight 0.1 lowered CV by about 2.234% and peak relative depletion by 4.916%, with 0.348% higher early energy.
- Combining the controls raised early energy by about 0.358%; reductions in load diagnostics did not establish a lifetime gain.
- Two batches of 20 used about 0.157% more energy than one batch of 40 in fresh validation.
- Two batches of 40 versus one batch of 80 differed by only about −0.003% energy. One batch of 80 improved energy by roughly 1.33% over 40 ants, at roughly twice the CPU.

The decision was one batch of 40 ants, elite weight 0.1, and load weight 0 by default. Extra inner iteration logic remains experimental, not production behavior.

A checkpoint-state aliasing bug was found: restored mutable pheromone state could be shared across configurations, confounding their order. Restoration was changed to deep-copy mutable fields. Invalid screens were archived, not treated as valid results, and corrected screens were rerun. Fresh trajectories were unaffected by that checkpoint bug.

Evidence: [live balance study](plans/phase5-acaco-balance/README.md), [invalid-screen archive explanation](plans/phase5-acaco-balance/invalid-screen-state-alias/README.md).

### Full best-set test

Six full live-sampler trajectories, paired seeds 15/16/17, compared elite weights 1 and 0.1:

| Elite weight | Mean FND | Mean service |
| --- | ---: | ---: |
| 1 | 1504.667 | 2193.667 |
| 0.1 | 1505.000 | 2191.667 |

FND differences were −16/+25/−8 rounds; service ended two rounds earlier in every weight-0.1 pair. Equal-round energy with weight 0.1 was about 0.285% higher at 150 rounds and 0.199% higher at 1400 rounds.

Weight 0.1 is a reinforcement-balance choice, not a demonstrated energy/lifetime improvement. The full results support keeping one batch, but do not prove the new elite weight improves service.

Evidence: [full best-set report](plans/phase5-acaco-balance/full/README.md).

**Historical scope:** these six runs use `energy_cost_exponent=1`. Historical balance runners and fixtures explicitly retain that exponent to avoid silently changing the old experiments when production defaults change.

## 6. PSO versus ACO discussion and source corrections

The user supplied an earlier PSO/D-ACO analysis and asked how ACO could search more efficiently, rather than simply perform more iterations. The working hypotheses were better contextual heuristics, candidate memory, or bounded local modifications such as one-CH swaps.

The uploaded analysis mixes user-reported logs, reconstructed experiments, and hypotheses. Claims labelled “VERIFIED” there were not all independently reproduced against the current review_uwsn pipeline. Its earlier PSO/ACO energy and lifetime numbers must not be presented as a fresh current-code comparison.

Current review_uwsn PSO code uses a lifetime score `total_energy + 5*max(consumption_i/residual_i)`, a swarm of 20, up to 20 iterations with patience 5, retention of 75% of particles across physical rounds, mutation, and load-aware assignment. The user supplied intuition about preserving good solutions and randomizing some is useful, but particle positions/velocities and ACO pheromone are different kinds of memory. Neither automatically implements efficient discrete local search.

No new bounded CH-swap/local-search operator was implemented or fully benchmarked in this conversation. Better fitness can guide selection and reinforcement without changing how proposals are generated.

### SimpleACO scope correction

The user stated that their SimpleACO results were pheromone-only. A temporary checkout confusion led to inspecting sibling code and making an overbroad statement about the active configuration. The user corrected the target back to review_uwsn.

Current review_uwsn default ACOParameters has beta=0.5 and gamma=1; the selection implementation uses beta for the E_m factor and gamma for residual-energy/distance, despite misleading parameter comments. Those defaults do not establish which overrides produced the user's earlier pheromone-only results. Confirm the actual run configuration before discussing those results; do not infer it from a sibling checkout or default comments.

No new full SimpleACO or PSO comparison was performed in the later D-ACO experiments.

## 7. Weaker AC-ACO E_m influence

The user requested reducing E_m influence to exponent 0.1 and removing D-ACO inner iterations. In review_uwsn:

- AC-ACO `energy_cost_exponent` changed from 1 to **0.1**.
- D-ACO already used one ant batch per round, so no inner loop needed removal.
- A lifecycle regression test confirms one D-ACO density computation and one pheromone update per round.

AC-ACO transition log weight includes:

`alpha*log(tau) + beta*[log(residual)-distance_weight*log(distance)] - gamma*log(E_m)`.

Changing gamma from 1 to 0.1 weakens the E_m contribution tenfold in log space. If one candidate's hop cost is ten times another's, its relative E_m factor changes from 0.1 to approximately 0.794, holding other terms equal. Actual physical energy evaluation is unchanged. The explicit distance heuristic remains at distance_weight=1; reducing E_m does not remove it.

The [AC-ACO paper](https://www.techscience.com/cmc/v84n3/63163/html) uses gamma for the E_m exponent in equation 20, but describes gamma=0.1 as a chaos disturbance factor in its simulation text. The terminology is inconsistent. The implemented 0.1 follows the user's requested weak E_m influence; it is not an unambiguous reproduction of every paper parameter.

There is **no full lifetime validation of AC-ACO's current combined defaults with gamma=0.1** in this conversation. The change was equation/regression tested; subsequent full simulations focused on D-ACO.

Evidence: [change and analysis note](plans/phase6-single-round/README.md).

## 8. D-ACO grid-distance experiments

The user observed that a 200 m communication radius can make density too broad or flat, and proposed higher weight near a sensor and lower weight farther away. The user explicitly corrected an initial sensor-neighbor implementation: the desired model is still **grid density**.

The sensor-density implementation and its partial experiment were stopped and reverted. Their files were removed. No sensor-neighbor density feature remains from that attempt.

The existing grid builds a sensor-to-cell overlap matrix F. Fully reachable cells receive weight 1; partial overlap has an approximate cubic falloff. Grid density is formed from live sensors, candidate scores weight the remaining grid density by F, and selecting a CH subtracts its coverage from remaining demand.

The tested variants multiply the original F consistently in grid density, candidate scoring, and coverage loss. Define `u = sensor_to_cell_center_distance / (communication_radius + cell_half_diagonal)`:

| Option | Added factor | Shape |
| --- | --- | --- |
| none | 1 | Original grid |
| linear | max(1−u,0) | Constant-slope decay |
| quadratic | max(1−u,0)^2 | Fast near the sensor, then flattens |
| parabolic | max(1−u^2,0) | Gentle nearby, increasingly steep farther away |

The extended reach preserves cells that are only partially within communication range. The user specifically requested the gentle-near behavior after recognizing that `(1-u)^2` has the opposite curvature.

Twelve full D-ACO runs, paired seeds 15/16/17, kept 40 ants, one batch, routing, energy model, and fitness fixed:

| Grid option | Mean FND | Mean service | Energy change over first 1642 all-alive rounds |
| --- | ---: | ---: | ---: |
| Original | 1658.333 | 2190.667 | — |
| Linear | 1678.000 | 2199.667 | +0.378% |
| Fast-drop quadratic | 1696.000 | 2197.667 | +1.176% |
| Gentle-near parabolic | 1651.000 | 2182.667 | +0.118% |

Linear improved service by +4/+8/+15 rounds. Fast-drop quadratic improved it by +2/+8/+11, with a larger energy cost. Parabolic service changes were −7/+3/−20, so the requested gentle-near shape did not improve the full comparison.

The original grid stays the default; the user requested keeping the alternatives, and all remain selectable. The parabolic production option was added after its full adapter-based trials; a regression test verifies matching grid weights, density, and coverage-loss scores.

Evidence: [grid experiment report](plans/phase7-daco-grid/README.md), [machine-readable summary](plans/phase7-daco-grid/summary.json).

## 9. Transferring tuned D-ACO from the sibling uwsn checkout

The user then requested keeping the grid variants, checking tuned D-ACO from uwsn, adopting it if better, and adding/testing density-load fitness. Full tests were explicitly D-ACO only.

The sibling preset is more than numeric tuning. It has four iterations of 20 ants, absolute fitness, immediate per-ant deposits, elite reinforcement expressed in per-ant units, elite-before-evaporation order, and partial-grid coverage scaling.

| Control | review_uwsn baseline | Sibling tuning source |
| --- | ---: | ---: |
| Ants | 40 × one batch | 20 × four iterations |
| Residual exponent beta | 0.9 | 0.2 |
| Density exponent gamma | 0.4 | 0.1 |
| Fitness | normalized 0.9 energy / 0.1 CV | absolute 120 energy + 1 CV |
| Evaporation range | 0.1–0.6 | 0.1–0.2 |
| Q | 5 | 60 |
| Elite theta | 0.1, total-deposit units | 3, per-ant units |
| Initial/floor pheromone | 1 | 0.5 |
| Ceiling pheromone | 8 | 20 |
| Maximum feasibility attempts | 10 | 5 |
| Partial coverage strength | 1 | 0.3 |

The full transfer experiment preserves matching objective/deposit semantics but uses **one batch of 40 ants**, honoring the earlier no-inner-iteration decision and equal ant budget. It is a single-batch adaptation, not a reproduction or rejection of the sibling's original 80-ant/four-iteration algorithm. Copying energy_weight=120 into the normalized baseline formula would not preserve its original meaning.

Three fresh baseline and three transferred runs completed. The fresh baselines matched all three phase-7 baseline trajectories exactly, including per-round records.

| Configuration | Mean FND | Mean service | All-alive energy change |
| --- | ---: | ---: | ---: |
| Current baseline | 1658.333 | 2190.667 | — |
| Tuned single-batch transfer | 1609.333 | 2191.667 | +2.604% |

Transferred FND changes were −86/−28/−33. Service changes were −21/+26/−2. It increased energy in every seed and did not give a meaningful service gain. It was not promoted.

The transfer remains reproducible in the experiment runner and copied reference source. Production supports its absolute-fitness/live-deposit/elite-unit/coverage controls as options, while baseline defaults remain unchanged.

Evidence: [transfer and fitness setup](plans/phase8-daco-tuned/README.md), [tuning summary](plans/phase8-daco-tuned/tuning_summary.json), [copied sibling parameters](plans/phase8-daco-tuned/source_uwsn/parameters.py).

## 10. Phase-8 density-aware load fitness (historical, replaced)

The user's idea was to penalize a sensor especially strongly when its evaluated load is high and its surrounding density is low. This affects candidate selection and later reinforcement; it does not directly add local proposal moves.

For each physical round, compute structural density from the same grid used by D-ACO:

`D_i = F_i dot grid_density`.

This is computed **before CH coverage loss**. Remaining density during CH construction is order-dependent and unsuitable as a stable measure of sensor scarcity.

Let `D_scale` be median positive live-sensor density, `e_i` evaluated consumption, and `r_i` pre-round residual energy. The penalty is:

`P = max_i [(e_i/r_i) * (1 + kappa/(1 + D_i/D_scale))] / (E_total/sum_i r_i)`.

Add `density_load_weight * P` to existing energy/CV fitness. All live sensors contribute, including members and relays. The denominator is ideal equal relative depletion, making P dimensionless. The scarcity factor is bounded, avoids a zero-density singularity, and puts more pressure on low-density sensors. It remains a proxy for alternatives, not a graph-criticality proof.

Three fitness variants were fully tested on the retained baseline:

- `risk_control`: weight 0.10, kappa=0, relative depletion without density weighting.
- `density_005`: weight 0.05, kappa=1.
- `density_010`: weight 0.10, kappa=1.

With the six tuning comparison runs, this stage contains **15 full D-ACO trajectories**. Energy percentages below all use the same first **1589 rounds**, before any death in any configuration:

| Configuration | Mean FND | Mean service | Energy change | Mean total clustering attempts |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 1658.333 | 2190.667 | — | 185662 |
| Tuned transfer | 1609.333 | 2191.667 | +2.604% | 143447 |
| Depletion without density | 2309.333 | 2380.333 | +3.304% | 117305 |
| Density weight 0.05 | 2303.333 | 2385.667 | +2.380% | 120224 |
| Density weight 0.10 | 2333.667 | 2372.333 | +4.791% | 108249 |

Weight 0.05 service changes were +193/+178/+214 rounds; FND changes were +630/+647/+658. Mean gains are **645 FND rounds (+38.89%)** and **195 service rounds (+8.90%)**. It required about **35% fewer total clustering attempts** than baseline despite completing more physical rounds.

Weight 0.10 delays first-node death a little further but consumes more energy and gives less completed service. Of the tested density variants, 0.05 is the better service/energy tradeoff.

The density-free control produces nearly the same lifetime benefit. Most demonstrated improvement is therefore relative-depletion awareness; the experiment does not establish a large additional density benefit. Moreover, adding the scarcity multiplier changes both spatial weighting and overall penalty magnitude: the control is not matched to the weighted variant's mean penalty strength. Do not claim that it cleanly isolates geometry alone.

The denominator in P depends on candidate energy. A more expensive tree can lower its relative concentration score; the separate energy term penalizes that expense. The measured energy increase is a tradeoff, not an energy improvement.

Defaults remain baseline, with density fitness opt-in. To use the low-weight tested option:

```python
params = DACOParameters()
params.density_load_weight = 0.05
# density_load_kappa=1 and density_decay="none" already match the tested option.
algorithm = DACO(network, hparameters, params)
```

Evidence: [full results and analysis](plans/phase8-daco-tuned/RESULTS.md), [complete summary](plans/phase8-daco-tuned/summary.json), [full experiment runner](plans/phase8-daco-tuned/full_run.py).

## 11. Phase-8 parameter and verification snapshot (D-ACO replaced in section 13)

AC-ACO defaults also retain pheromone exponent 1, distance_weight=1, CH proportion 0.2, raw beta schedule with beta range 1–5 and slope 5, logistic r=3.61 and seed=0.37, and hopping factor 0.4. Read [AC-ACO parameters](src/algorithms/clustering/ac_aco/parameters.py) for the complete current configuration.

D-ACO defaults remain alpha=1, beta=0.9, gamma=0.4, CH proportion=0.2, energy/load weights 0.9/0.1, Q=5, theta=0.1, pheromone initial/floor=1 and ceiling=8, evaporation 0.1–0.6, hopping factor 0.4, ten feasibility attempts, density_decay="none", and coverage_strength=1. Its default modes are normalized fitness, batch deposits, and elite_per_ant=False. Density-load weight is zero; kappa defaults to one.

Read [D-ACO parameters](src/algorithms/clustering/d_aco/parameters.py) and [fitness implementation](src/algorithms/d_aco.py) rather than assuming sibling defaults apply.

The last test run passed **50 tests**. Tests cover AC-ACO equations, live sampler, calibration, chaos controls, checkpoint isolation and historical fixtures; PSO regressions; D-ACO's one-batch lifecycle; grid kernel shapes/support and loss; parabolic adapter equivalence; scarcity/residual penalties; fitness-driven selection; consistency of live deposits with selection scores; and tuned elite units.

The Python executable used is:

`C:/Users/hgtfh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

From review_uwsn in PowerShell:

```powershell
& 'C:/Users/hgtfh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -m unittest discover -s tests
```

Full-run artifacts record map/source hashes, explicit controls, seeds, per-round energy/deaths/survivors, residual energy, termination, and CPU/counter diagnostics. Existing mismatched provenance is rejected. Later source changes do not invalidate historical measurements, but prevent treating them as fresh measurements of the changed implementation. Preserve archived results instead of overwriting them to bypass guards.

CPU timings were collected with overlapping runs and uncontrolled hardware frequency. They are indicative; actual clustering-attempt counts give firmer evidence of search work. Fewer attempts are not necessarily a better per-candidate search operator: delaying critical-node death also postpones expensive feasibility retries.

All main full comparisons use one topology and three paired seeds. They are not multi-topology validation, proof of optimal parameters, or statistically established general improvement. Different stages use different energy-comparison windows; do not mix their percentages without checking the reference and physical state.

## 12. What remains unresolved

These are possible follow-up directions, not unfinished authorized benchmark jobs:

1. Whether to enable density weight 0.05 by default for lifetime, accepting about 2.38% more energy. It is currently opt-in.
2. Whether density contributes beyond penalty magnitude when compared with a strength-matched density-free control.
3. Whether the relative-depletion improvement generalizes to other topologies, radii, sensor counts, and sink placements.
4. Whether a graph-aware scarcity/criticality measure outperforms grid density, particularly for high-density bridge nodes.
5. Whether a bounded CH-swap operator or candidate archive improves energy at equal evaluation and runtime budgets. No new local-search operator was implemented here.
6. Full lifetime performance of current AC-ACO gamma=0.1 with live pheromone and elite weight 0.1. Older gamma=1 full results cannot answer it.
7. A fresh controlled SimpleACO/PSO/D-ACO comparison using the exact intended SimpleACO pheromone-only preset and matched objectives/budgets. The uploaded historical PSO analysis does not substitute for it.

The context-generation request was followed by a new explicit implementation/cleanup/test request, described next. Archived experiment data remain retained.

## 13. Latest request: unified powered fitness, live feedback, and cleanup

The user objected to per-ant/best-ant scoring disagreement, required live pheromone, rejected energy/load/density as three independent objectives, and specified `fitness = total energy + load/density`. The user proposed throwaway calibration and smoothing of normalization estimates. After rejecting max load in favor of an exponent, the user explicitly requested implementation, testing, and removal of obsolete production parameters/functions.

The implementation uses relative depletion as load, exponent 2, and one combined quantity:

`P = mean_i [(consumption_i/residual_i)^p / max(structural_grid_density_i, epsilon)]`

`F = total_energy + load_density_weight * E_ref * P/P_ref`

The initial prototype used weight 0.10; after full testing the production default is 0.25. A throwaway initial batch of up to 40 ants sets references from mean evaluated energy and combined penalty. It advances neither physical energy nor schedule and makes no pheromone deposits; its computation and RNG draws are explicitly recorded. All ants within a physical round share immutable references. Each score is computed once, deposited immediately, and reused verbatim for best-ant selection and elite deposit.

After the round, references use geometric smoothing `previous^0.8 * observed^0.2`, computed in log space. Ant deposits are `Q*E_ref/F/num_ants`; the elite bonus is `theta*Q*E_ref/F`. Evaporation happens once before ants, so later ants see earlier deposits. There are no batch/live or normalized/absolute mode switches.

Removed from production: CV scoring, max-depletion objective, energy_weight, load_weight, density_load_weight, density_load_kappa, fitness_mode, deposit_mode, elite_per_ant, and rejected coverage_strength tuning. Existing grid decay variants remain. Prior implementations are frozen only under [phase-9 archive](plans/phase9-daco-power/archive/README.md); old phase-7/phase-8 runners explicitly use them. Their source hashes and first-ten-round replay match the six baseline/max-reference full runs.

The new [fitness implementation](src/algorithms/clustering/d_aco/fitness.py) and [parameter schema](src/algorithms/clustering/d_aco/parameters.py) are the active source of truth. Old or unknown parameter fields are rejected by production validation. The latest suite has 53 passing tests.

Phase-9 tests run five configurations with paired seeds 15/16/17: energy-only live, linear-load p=1, and squared-load p=2 at weights 0.10, 0.25, and 1.0. Weight 1.0 gives equal typical energy and calibrated penalty scales. Each has 40 physical ants plus its explicitly counted throwaway calibration batch and continues to normal termination or 3000 rounds. Earlier six completed full trajectories are historical reference controls. No AC-ACO or sibling uwsn source is changed in this phase.

All fifteen new full trials are complete. Energy changes below use the same first 1617 all-alive rounds, compared with the old baseline. The old max row is a completed phase-8 reference; it is not a current production mode.

| Configuration | Mean first death | Mean service | Energy change |
| --- | ---: | ---: | ---: |
| Old baseline | 1658.333 | 2190.667 | — |
| Old max weight 0.05 | 2303.333 | 2385.667 | +2.411% |
| Energy-only live | 1626.000 | 2160.667 | +0.191% |
| Linear load, weight 0.10 | 1659.667 | 2189.667 | +0.272% |
| Squared load, weight 0.10 | 1784.333 | 2263.667 | +0.466% |
| Squared load, weight 0.25 | 1896.667 | 2318.000 | +0.601% |
| Squared load, weight 1.0 | 2081.333 | 2366.667 | +1.834% |

The selected new default is weight 0.25: about 127.3 extra service rounds (+5.81%), 238.3 later first-death rounds (+14.37%), and 0.60% more all-alive energy versus old baseline. Service improves in every paired seed. Weight 1.0 gives longer service, but its additional energy cost is much larger. Old max still has stronger first-death/service results at higher energy cost; do not claim power universally dominates max. The same-weight p=1/p=2 comparison supports the exponent within the new policy.

Normalization and live deposits are part of the new policy, so the historical max comparison does not isolate exponent alone. Q stays fixed as objective weights change; larger weights also lower inverse-fitness deposit magnitudes. Calibration contributes exactly 40 extra attempts per new trial, included in counts and CPU. Timings remain indicative due to concurrency.

See [phase-9 design](plans/phase9-daco-power/README.md), [full results](plans/phase9-daco-power/RESULTS.md), and [summary](plans/phase9-daco-power/summary.json). Raw source hashes describe the tested prototype; explicit power_025 parameters match the promoted default. No full comparisons are left running.

## Phase 10: current D-ACO versus pheromone-only SimpleACO

User requested a full comparison of the current powered-fitness D-ACO against SimpleACO using only pheromone. The map had changed since phase 9, so both algorithms were run fresh on the current map rather than reusing historical trajectories. Map SHA-256 is `d9e086fde395ff10a4348122727bc2af6972dffa25d5f92afa37ed0d56ca4b05`; physical dimensions remain 500 m cubed, 100 sensors, 200 m radius, sink (250,250,0), initial energy 0.6 J. Earlier results concern a different map epoch and cannot be mixed with these.

Six full trajectories used paired seeds 24/25/26 and the normal 3000-round horizon. Every run stopped earlier for no feasible complete tree. D-ACO uses current defaults (load power 2, weight 0.25, reference memory 0.8, live pheromone). The experiment explicitly sets SimpleACO beta=gamma=0 without altering production parameters. Its actual sampling weights were checked to equal pheromone^alpha and remain unchanged when residual energies and distances change. Physical energy still scores SimpleACO candidates; shared routing retains distance/residual inputs. Both have 40 ants in one batch per round, max 10 feasibility attempts per ant, 20% CHs, hopping factor 0.4. Other algorithm-specific defaults remain distinct, including node versus edge pheromone and reinforcement policies. This compares whole algorithms, not an isolated heuristic ablation.

| Mean metric | Current D-ACO | Pheromone-only SimpleACO |
| --- | ---: | ---: |
| First node death | 2675 | 2636 |
| Completed service rounds | 2747.333 | 2936 |
| Energy, first 2611 all-alive rounds (J) | 43.6483 | 42.4661 |
| CPU seconds per completed round | 0.1120 | 0.0990 |
| Clustering attempts per completed round | 40.1602 | 41.9737 |

D-ACO delays first death by 39 rounds (+1.48%) but has 188.67 fewer service rounds (-6.43%) and uses 2.78% more energy over the common all-alive window. Each paired seed shows the same directions: later first death for D-ACO, lower energy and longer service for SimpleACO. D-ACO CPU per round is 13.18% higher despite fewer feasibility attempts; calibration is included. Timing is indicative because three seed processes ran concurrently. Results do not establish performance across maps or explain the causal contribution of individual components. Both algorithms stop with live sensors remaining; service is not last-node death.

All selected trees covered exactly the live nodes, and energy costs were finite and nonnegative. Source/map hashes stayed unchanged throughout every run. No production defaults were changed. See [full comparison](plans/phase10-daco-vs-pheromone/RESULTS.md), [summary](plans/phase10-daco-vs-pheromone/summary.json), and [reproducible runner](plans/phase10-daco-vs-pheromone/full_run.py). All six jobs have completed.

## Phase 11: stronger deposits or lighter D-ACO heuristics

User proposed stronger pheromone deposits or lighter heuristic weights and authorized independent full tests. Twelve new variant trials used seeds 24/25/26 on exactly the phase-10 map/source epoch. Three extra instrumented baseline replays reproduced the previous complete trajectories and residual energies exactly. Existing pheromone-only SimpleACO trials were reused after verifying source/map hashes. All jobs completed normally before the 3000-round horizon.

Tested Q=10 and Q=20 versus current Q=5, retaining beta=0.9/gamma=0.4. Independently tested half heuristics (beta=0.45/gamma=0.2) and quarter heuristics (beta=0.225/gamma=0.1), retaining Q=5. Fitness formula and its parameters, calibration, live pheromone, evaporation, bounds [1,8], ant budget, routing, and physics were unchanged. Geometric fitness references adapt normally to the candidates each variant samples. No production defaults were changed.

Energy below compares the first 2611 rounds, when all nodes remain alive in every trajectory.

| Variant | Mean first death | Mean service | Energy (J) | Energy vs current D-ACO |
| --- | ---: | ---: | ---: | ---: |
| Current D-ACO | 2675.000 | 2747.333 | 43.6483 | — |
| Q=10 | 2674.000 | 2790.667 | 43.4428 | -0.471% |
| Q=20 | 2742.667 | 2830.333 | 43.4092 | -0.548% |
| Half heuristics | 2734.333 | 2815.667 | 43.2557 | -0.900% |
| Quarter heuristics | 2782.667 | 2938.000 | 43.1655 | -1.106% |
| Pheromone-only SimpleACO | 2636.000 | 2936.000 | 42.4661 | -2.708% |

Quarter heuristics are the best tested D-ACO variant on all three mean outcomes: +107.67 first-death rounds (+4.02%), +190.67 service rounds (+6.94%), and -1.11% energy versus baseline. All three seeds improve these outcomes relative to baseline. Against SimpleACO, quarter weights essentially match service (+13/-13/+6 paired rounds, mean +2), delay first death by 146.67 rounds (+5.56%), and use 1.65% more all-alive energy. Do not claim convincingly better service than SimpleACO.

Q=20 improves service by 3.02% and energy by 0.55%, but has substantial clipping: averaged over the common all-alive window, 54.66% of live nodes are at the cap after a round and 30.67% of requested deposit mass is lost. Baseline cap fraction is 2.26% and quarter-heuristic cap fraction is 0.55%. Increasing Q does affect retained pheromone and results despite clipping; it cannot be dismissed as entirely ineffective. Lighter heuristics perform better than increasing Q alone in this test. This supports the parameter direction on one map, not a universal optimum or proof of local search.

CPU data include significant instrumentation overhead. Deposit/control trials had up to nine concurrent tasks, whereas the heuristic wave mostly had six; cross-wave CPU differences must not be interpreted as causal parameter speedups. The reused SimpleACO timings lack this instrumentation. Selected-tree coverage and finite/nonnegative energy assertions passed, every source/map epoch matched, and the instrumented baseline replay preserved randomness and outcomes exactly.

See [full results](plans/phase11-daco-concentration/RESULTS.md), [summary](plans/phase11-daco-concentration/summary.json), and [runner](plans/phase11-daco-concentration/full_run.py). Defaults still use Q=5, beta=0.9, gamma=0.4; no tests remain running.

## Phase 12: ×4/×6 deposits with a higher pheromone ceiling

User requested ×4 with a higher upper bound and also ×6. Tested tau_max=32 versus current 8, held the same high cap for Q=20 (×4) and Q=30 (×6), and added Q=30/cap-8 to isolate the cap change at ×6. Nine fresh full trials used paired seeds 24/25/26, the same map/source epoch, 40 ants in one batch, and the normal 3000-round horizon. All terminated earlier for no complete feasible tree found. Current fitness and heuristic exponents beta=0.9/gamma=0.4 were fixed; tau_min=tau0=1, alpha, evaporation, calibration, and normalization policy were unchanged. The verified phase-11 runner/observer was reused, with its hash and the new driver hash recorded.

All-alive energy compares the same first 2611 rounds. Existing current D-ACO, ×4/cap-8, quarter heuristics, and SimpleACO controls were reused after source/map hash verification.

| Variant | Mean first death | Mean service | Energy (J) | Energy vs current D-ACO |
| --- | ---: | ---: | ---: | ---: |
| Current D-ACO | 2675.000 | 2747.333 | 43.6483 | — |
| ×4, cap 8 | 2742.667 | 2830.333 | 43.4092 | -0.548% |
| ×4, cap 32 | 2638.667 | 2702.333 | 43.7611 | +0.258% |
| ×6, cap 8 | 2761.000 | 2849.000 | 43.4038 | -0.560% |
| ×6, cap 32 | 2644.333 | 2733.667 | 43.6668 | +0.042% |
| Quarter heuristics | 2782.667 | 2938.000 | 43.1655 | -1.106% |
| Pheromone-only SimpleACO | 2636.000 | 2936.000 | 42.4661 | -2.708% |

At fixed Q=20, cap 32 loses 128 service rounds (-4.52%) and uses 0.81% more energy than cap 8. At fixed Q=30, cap 32 loses 115.33 service rounds (-4.05%) and uses 0.61% more energy. Raising the ceiling worsens first death, service, and equal-round energy in every paired seed at both Q levels.

Clipping falls sharply with the higher cap: Q=20 lost deposit mass drops from 30.67% to 1.21%; Q=30 drops from 47.93% to 4.14%. Mean end-round cap fractions are respectively 54.66%→2.50% and 76.31%→8.59% over the common all-alive window. Thus less clipping does not imply better search, and clipping cannot be treated as simply suppressing a beneficial stronger-deposit policy. These tests favor retaining cap 8 in this parameter setting; no detailed failure mechanism was isolated.

Q=30/cap-8 gains only 18.67 service rounds (+0.66%) over Q=20/cap-8, with practically identical energy (-0.012%). Paired service changes are -1/+46/+11, so the small mean gain is not consistent in every seed. Quarter heuristics still have the best mean first death, service, and energy among tested D-ACO variants. No production defaults changed, and no variant was adopted automatically.

Selected-tree coverage and finite/nonnegative physical energy checks passed; each new case changes only Q and, where declared, tau_max; source/map hashes remained unchanged through every run. Stored CPU includes observer overhead and nine concurrent processes, so timing is not a controlled comparison with earlier waves. See [full results](plans/phase12-daco-higher-cap/RESULTS.md), [summary](plans/phase12-daco-higher-cap/summary.json), and [runner](plans/phase12-daco-higher-cap/full_run.py). All nine jobs have completed.
