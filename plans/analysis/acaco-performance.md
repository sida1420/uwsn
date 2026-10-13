# AC-ACO performance evidence and mathematics

Historical calibration, elite-weight and chaos comparisons follow. Their explicit
parameters and round policies define their scope; current production uses live
per-ant pheromone updates, no inner rounds and acoustic-cost exponent 0.1.
The full elite/chaos comparisons below used acoustic exponent 1, so they do not
establish outcomes under the later 0.1 setting.

The exact chaos/uniform-mixture identity remains useful. The minimum-of-independent
candidates calculation in the historical math probe assumes a fixed sampling
state. With live deposits, subsequent ants see updates; independence is not an
unconditional model of a current physical round. Short energy improvements alone
are insufficient evidence for a lifetime improvement.


---

Historical source: `plans/phase5-acaco-tuning/README.md`. Its implementation and defaults may differ from current production.

# AC-ACO pheromone calibration — 2026-10-11

This is a bounded calibration requested by the user, not execution of every
stage in the supplied Downloads/plan.md. That document's reports describing
46/51 tests and later audits are absent from this checkout; they are historical
context, not reproduced evidence. The initial checkout had 17 passing tests.

## Sources and interpretation

- [Zhou, Chen and Cao (2025), Table 2 and equations 11–20](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf):
  reference alpha=1, beta=3, rho=.2, initial pheromone=1, chaos coefficient=.1,
  logistic r=3.58. Its radio network differs from this acoustic 3D model. Its
  gamma is a chaos coefficient, not this implementation's acoustic exponent.
- [Stützle et al., Parameter Adaptation in Ant Colony Optimization](https://lopez-ibanez.eu/doc/StuLopPelMau2010adaptiveACO.pdf):
  deposit is proportional to inverse solution cost; pheromone bounds and
  evaporation interact, and suitable parameter settings depend on the variant
  and computational budget. It does not supply universal UWSN bounds.
- [Logistic-map periodic-window study](https://pubmed.ncbi.nlm.nih.gov/39820460/):
  the accepted interval for r is not uniformly chaotic. Retaining r=3.61 is a
  controlled choice, not a claim that every accepted r is suitable.

The numeric search limits below are an adaptation derived from our actual
equation, not parameter intervals prescribed by these papers.

## Full-update scale

Ant deposits occur before evaporation; the elite deposit occurs after it.
Let D=Q/E_ref. If all 40 ants and the elite repeatedly reinforce the same
edge at E_ref, and disturbance is c, the unclamped recurrence is

```
tau_next = (1-rho) * (tau + D) + c + D
tau_equilibrium = ((2-rho)*D + c) / rho
```

For logistic r=3.61, every iterated value is at most r/4=.9025, so
c <= chaos_max*r/4=.27075. At minimum evaporation .1 and reference route
cost .015 J, Q=.01 gives an equilibrium envelope of 15.3741667. A ceiling
of 20 leaves headroom. Q=.003 gives 6.5075, motivating a ceiling of 8.
Ceilings 2 and 5 are also measured as controls but cannot accommodate these
reference worst cases at late evaporation. The original ceiling 10 coupled
with Q=100 is orders of magnitude below its deposit scale.

**.015 J is a reference scenario, not a proven lower bound on route costs.**
Small deployments or different physics can still reach the ceiling; clamping
remains necessary. The stress test verifies the recurrence, not lifetime.

The logistic invariant interval for this r has lower endpoint
r*(r/4)*(1-r/4)=.3176574375. With minimum chaos .05 and maximum evaporation
.6, the minimum-disturbance background equilibrium is about .02647. A floor
of .01 lies below it; .1 can flatten naturally distinct low pheromone levels.
Floors .001/.01/.05 and initial levels 1/2 are screened explicitly. This
argument is conditional on the specified r and chaos/evaporation bounds.

## Reproduction and experimental limits

The bundled Python runtime was used because `python` is absent from PATH.
`results.json` contains full explicit configurations, seeds, map SHA, git SHA,
source fingerprints, per-round costs, CPU timings, feasible evaluation counts,
floor/ceiling occupancy and depletion diagnostics. Existing matching results
are reused; delete or move that artifact for a fresh run.

Screening: 20 searches at fixed physical state, optimizer memory retained,
seeds 0/1/2, 40 ants per search, maximum 10 attempts per ant. Validation:
independent 150-round energy-depleting trajectories, seeds 3/4/5. Schedule
horizon remains 3000. No mutation of shared routing, physics, simulator,
topology or other algorithms. Every successful round independently checks
tree energy and exact live-node service. Diagnostic probability calculations
consume no RNG and do not advance persistent iteration or chaos state.

The initial pilot selected two finalists from small ceilings before the
late-equilibrium guard was added. Their validation results are retained as
exploratory controls. The extended run includes wider ceilings and reranks
using the equilibrium guard. Its final contenders are reported separately.

CPU measurements include evaluation counting instrumentation, exclude the
after-search diagnostics, and were collected sequentially. They are practical
checks, not a precise performance benchmark. The validation seeds were not
used for screening, but all experiments use one existing topology. This is
not independent topology validation, a global optimum, or evidence about
FND, HND/LND, post-death service, or late-round energy performance.

<!-- RESULTS -->

## Completed results

| Validation configuration | Mean 150-round energy (J) | Change vs historical | Mean CPU (s) | Floor occupancy | Ceiling occupancy |
| --- | ---: | ---: | ---: | ---: | ---: |
| historical | 2.510832058 | +0.000% | 29.620 | 81.479% | 7.044% |
| moderate_heuristic | 2.489096505 | -0.866% | 53.875 | 0.000% | 0.000% |
| q0.01_max2.0_rho0.6 | 2.500538060 | -0.410% | 29.828 | 0.000% | 0.000% |
| moderate_heuristic_wide | 2.489096505 | -0.866% | 30.661 | 0.000% | 0.000% |
| q0.01_max20.0_rho0.6 | 2.500538060 | -0.410% | 22.562 | 0.000% | 0.000% |

| Seed | Historical energy (J) | New defaults (J) | Change |
| --- | ---: | ---: | ---: |
| 3 | 2.512037836 | 2.501974943 | -0.401% |
| 4 | 2.505098702 | 2.497558622 | -0.301% |
| 5 | 2.515359637 | 2.502080614 | -0.528% |

Screened 22 configurations; completed 142,800 feasible evaluations including exploratory controls and validation.
All measured rounds served all 100 live sensors, with no observed deaths or routing failures.

Applied defaults: `Q=.01`, `tau_min=.01`, `tau0=1`, `tau_max=20`, `rho_min=.1`, `rho_max=.6`. Other parameters retain their explicitly inventoried values.
The lower acoustic exponent remains experimental: it saved slightly more early energy, but late-round behavior and lifetime are unvalidated. Repeated timings varied markedly even for identical trajectories, so the initial apparent CPU regression is not reliable. Beta_max=3 was exploratory only; these 150-round trials cannot assess the raw schedule near round 1500.

Maximum observed single-round relative depletion: historical 0.001923080, selected 0.002120219 (+10.25%). This is a remaining lifetime risk, not proof of earlier death. The change is adopted for numerical scale and preserved early feasibility, not a claimed lifetime improvement.

Floors .001/.01/.05 gave the same screening energies in their matched controls; .01 is chosen from the background-disturbance scale, not a measured optimum. Wide and small ceilings also yield identical early trajectories when neither clips; the wider value is chosen for late recurrence headroom.

Validation seed results do not certify generalization across topologies. No 600-round or full-lifetime experiment was performed.

Verification: 21 unit tests pass, including historical elite-clamp regression, inverse-cost discrimination, sustained late reinforcement, finite normalized probabilities and exact full service across coupled scales.

Map SHA-256: `ebe729265598746b30af09715e239a9891b2ac95ac66656096dc712e6c34fdcc`. Starting git SHA: `da40055a9f34a7c8ecf31f7a23736bb338098c1d`.

---

Historical source: `plans/phase5-acaco-balance/full/README.md`. Its implementation and defaults may differ from current production.

# Full lifetime test: best-set weight 1 versus 0.1

Historical scope: all six runs use `energy_cost_exponent=1`. They do not measure the subsequent production change to 0.1.

Six independent production trajectories use fresh paired seeds 15/16/17 on the same 100-node map. Each physical round has one batch of 40 ants and ten routing attempts per ant. Pheromone is live, so later ants see earlier deposits. There are no inner iterations. Only `elite_weight` changes; `load_weight=0`, chaos [.05,.30], Q=.01, evaporation [.1,.6], and pheromone bounds [.01,20] are fixed. The horizon is 3000 rounds.

| Seed | Weight 1 FND | Weight 0.1 FND | Paired FND change | Weight 1 service rounds | Weight 0.1 service rounds | Paired service change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 15 | 1519 | 1503 | -16 | 2196 | 2194 | -2 |
| 16 | 1508 | 1533 | 25 | 2205 | 2203 | -2 |
| 17 | 1487 | 1479 | -8 | 2180 | 2178 | -2 |

Mean first-node death: 1504.667 → 1505.000 rounds (+0.022%).

Mean completed service: 2193.667 → 2191.667 rounds (-0.091%).

For these completed runs, reducing the best-set weight provides no demonstrated lifetime gain: FND changes are mixed, and service ends two rounds earlier in every pair. Weight 0.1 remains the deliberate reinforcement-balance setting from the earlier study; it should not be described as an energy or lifetime improvement. One batch of 40 ants remains the production round structure.

FND uses one-based completed-round counting. Service ends when the production search cannot find a tree that serves all surviving nodes, when all nodes die, or at the horizon. It is not equivalent to last-node death. HND/LND are censored if service stops before those events.

## Energy at equal exposure

| Completed rounds | Weight 1 mean energy (J) | Weight 0.1 mean energy (J) | Change |
| --- | ---: | ---: | ---: |
| 150 | 2.494214407 | 2.501311688 | +0.285% |
| 600 | 9.666044727 | 9.669132974 | +0.032% |
| 1400 | 22.354601667 | 22.399148048 | +0.199% |

Energy after survivor counts diverge includes different physical states and cannot isolate efficiency. Whole-run cumulative energy is not used to rank efficiency because service durations differ.

## Death events and terminal topology

| Weight / seed | Deaths (completed round: node IDs) | Termination | Survivors | Disconnected survivor IDs | HND | LND |
| --- | --- | --- | ---: | --- | --- | --- |
| 1.0 / 15 | 1519: [33]; 2196: [65] | no_feasible_route | 98 | [48] | censored | censored |
| 0.1 / 15 | 1503: [33]; 2194: [65] | no_feasible_route | 98 | [48] | censored | censored |
| 1.0 / 16 | 1508: [33]; 2205: [65] | no_feasible_route | 98 | [48] | censored | censored |
| 0.1 / 16 | 1533: [33]; 2203: [65] | no_feasible_route | 98 | [48] | censored | censored |
| 1.0 / 17 | 1487: [33]; 2180: [65] | no_feasible_route | 98 | [48] | censored | censored |
| 0.1 / 17 | 1479: [33]; 2178: [65] | no_feasible_route | 98 | [48] | censored | censored |

A nonempty disconnected list proves that a full-survivor route is impossible in the communication graph. An empty list at failure instead indicates that finite ant sampling/greedy routing could not find a feasible route.

## Critical-node residuals after round 1400

| Seed | Weight 1 node 33 (J) | Weight 0.1 node 33 (J) | Weight 1 node 65 (J) | Weight 0.1 node 65 (J) |
| --- | ---: | ---: | ---: | ---: |
| 15 | 0.049421 | 0.042037 | 0.297438 | 0.299813 |
| 16 | 0.046000 | 0.056553 | 0.293833 | 0.292443 |
| 17 | 0.036893 | 0.031916 | 0.294058 | 0.302936 |

Node 48 has only nodes 33 and 65 as communication-range neighbors on this map. Their deaths can isolate it even while most other sensors still have energy.

## Late search and pheromone bounds

| Seed | Weight | Common late rounds | Mean feasible candidates | Mean routing attempts | Maximum floor occupancy | Maximum ceiling occupancy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 15 | 1.0 | 694 | 30.099 | 226.857 | 0.000% | 0.000% |
| 15 | 0.1 | 694 | 29.820 | 232.493 | 0.000% | 0.000% |
| 16 | 1.0 | 703 | 29.878 | 230.619 | 0.000% | 0.000% |
| 16 | 0.1 | 703 | 30.334 | 223.909 | 0.000% | 0.000% |
| 17 | 1.0 | 678 | 30.007 | 232.298 | 0.000% | 0.000% |
| 17 | 0.1 | 678 | 29.777 | 232.690 | 0.000% | 0.000% |

Late averages use equal round exposure within each seed pair, beginning at round 1501. Physical states evolve separately and may have different survivor counts briefly around their respective first deaths.

## Validation and limitations

Elite weight changes reinforcement on the ordered CH path, not relay edges or a residual-aware lifetime objective. Selection still minimizes total round energy. A smaller best-set bonus balances ant versus elite reinforcement, but it does not explicitly protect the critical relays that determine service termination.

Every selected tree was independently reevaluated and served every live node. Across all runs, 484,304 feasible candidates were evaluated. Search leaves physical residual energy unchanged, energy is deducted once per completed round, and all pheromone entries are checked for finite values and calibrated bounds. Raw per-round costs, death events, routing attempts, snapshots and terminal connectivity are saved. Source/map/helper/runner hashes and explicit parameter values are stored per run; the runner rejects source changes during execution.

These seeds are fresh relative to the early balance study, but this remains one map and three paired seeds. No statistical significance or universal optimum is established. Search CPU excludes the failed terminal search and comes from concurrent runs; it is not a dedicated timing benchmark.

Reproduce each trajectory with `python -B plans/phase5-acaco-balance/full_lifetime.py SEED elite_1` or `elite_01`, for seeds 15/16/17. Existing completed runs are reused only with matching provenance. Then run `full_report.py`.

---

Historical source: `plans/phase5-acaco-chaos/long/README.md`. Its implementation and defaults may differ from current production.

# Longer chaos validation

Historical scope: these runs used frozen per-round pheromone. The sampler now exposes earlier ants' deposits immediately; the live balance study (historical reference) compares that change at matched states. These archived lifetime results are not measurements of the new live sampler.

Current chaos bounds [.05,.30] versus doubled bounds [.10,.60], with all other calibrated parameters fixed. Independent physical trajectories use seeds 6/7/8 on the same 100-node map, up to 3000 rounds. These extend the earlier 150-round seeds; they are not a new holdout. Routing, physics and the production defaults are unchanged.

| Seed | Current FND | Doubled FND | Current completed rounds | Doubled completed rounds |
| --- | ---: | ---: | ---: | ---: |
| 6 | 1510 | 1510 | 2192 | 2169 |
| 7 | 1485 | 1483 | 2182 | 2153 |
| 8 | 1488 | 1505 | 2180 | 2181 |

Mean FND: 1494.333 versus 1499.333 rounds (+0.335%). Mean completed full-survivor service: 2184.667 versus 2167.667 rounds (-0.778%).

Retain production chaos bounds [.05,.30]. The doubled [.10,.60] setting remains an experimental candidate: its energy gain is small and FND does not improve consistently across seeds. Mean full-survivor service also regresses. This single-map, three-seed comparison establishes neither statistical significance nor an optimal strength range.

FND is the number of completed rounds at the first death, using one-based counting. HND and LND are censored when not observed. A failed routing search ends service in this simulator; this does not mean all sensors have died.

| Equal exposure | Current mean modeled energy (J) | Doubled mean (J) | Change |
| --- | ---: | ---: | ---: |
| 150 rounds | 2.498649410 | 2.487085613 | -0.463% |
| 600 rounds | 9.671843289 | 9.647333454 | -0.253% |
| 1400 rounds | 22.375407325 | 22.338751565 | -0.164% |

Full-run cumulative energies are not compared as efficiency scores because trajectories can have different durations or survivor counts.

## Critical-node energy at round 1400

| Seed | Current node 33 residual (J) | Doubled node 33 (J) | Current node 65 residual (J) | Doubled node 65 (J) |
| --- | ---: | ---: | ---: | ---: |
| 6 | 0.045296 | 0.046783 | 0.297619 | 0.292228 |
| 7 | 0.036239 | 0.036821 | 0.300493 | 0.292961 |
| 8 | 0.037053 | 0.044496 | 0.296040 | 0.300746 |

Node 48 has only neighbors 33 and 65 within communication range. After node 33 dies, preserving node 65 is necessary for full-survivor service. Lower total energy does not guarantee preserving this node.

## Termination and bounds

| Configuration / seed | Termination | Survivors | HND | LND | Max floor / ceiling occupancy |
| --- | --- | ---: | --- | --- | --- |
| calibrated_x1 / 6 | no_feasible_route | 98 | censored | censored | 0.000% / 0.000% |
| calibrated_x1 / 7 | no_feasible_route | 98 | censored | censored | 0.000% / 0.000% |
| calibrated_x1 / 8 | no_feasible_route | 98 | censored | censored | 0.000% / 0.000% |
| calibrated_x2 / 6 | no_feasible_route | 98 | censored | censored | 0.000% / 0.000% |
| calibrated_x2 / 7 | no_feasible_route | 98 | censored | censored | 0.000% / 0.000% |
| calibrated_x2 / 8 | no_feasible_route | 98 | censored | censored | 0.000% / 0.000% |

## Terminal connectivity

- calibrated_x1, seed 6: disconnected surviving node IDs [48]; failed search attempts 400.
- calibrated_x1, seed 7: disconnected surviving node IDs [48]; failed search attempts 400.
- calibrated_x1, seed 8: disconnected surviving node IDs [48]; failed search attempts 400.
- calibrated_x2, seed 6: disconnected surviving node IDs [48]; failed search attempts 400.
- calibrated_x2, seed 7: disconnected surviving node IDs [48]; failed search attempts 400.
- calibrated_x2, seed 8: disconnected surviving node IDs [48]; failed search attempts 400.

An empty disconnected list means the undirected communication graph still reaches the base; the greedy router and finite search budget can nevertheless fail. A nonempty list proves that full-survivor service is physically impossible on this graph.

## Late search feasibility

The ant count and ten-attempt limit are fixed, but failed ants can leave fewer feasible candidates to compare. The following averages use rounds 1501 through the shorter trajectory endpoint within each pair. These are different evolving physical/optimizer states; survivor counts can differ briefly around the paired FND times. They do not isolate transition mixing alone.

| Seed | Common late rounds | Current feasible candidates / attempts | Doubled feasible candidates / attempts |
| --- | ---: | ---: | ---: |
| 6 | 669 | 29.931 / 231.688 | 30.957 / 222.859 |
| 7 | 653 | 29.980 / 231.902 | 31.142 / 222.067 |
| 8 | 680 | 29.871 / 232.187 | 31.094 / 223.222 |

## Verification and reproduction

Every selected route independently reevaluated and served every live sensor. Total feasible candidate evaluations: 483,305. Residual energy is clamped to zero on death, so modeled cost can exceed physically deducted energy in a death round. Per-round modeled/deducted energy, deaths, attempts, pheromone occupancy and checkpoints are saved. All 28 repository tests passed, including checkpoint restoration, connectivity cuts and the exact mixture/order-statistic identities. Search CPU is indicative and excludes the failed terminal search; concurrent jobs make wall-time comparisons unsuitable.


See the mathematical analysis (historical reference) for the exact mixing identity, coverage mechanism and limitations.

---

Historical source: `plans/phase5-acaco-chaos/long/MATH_ANALYSIS.md`. Its implementation and defaults may differ from current production.

# Why increasing chaos can help this AC-ACO implementation

Historical scope: these measurements used the frozen per-round pheromone sampler. Production now reads live deposits from earlier ants. The conditional transition-mixture identity still holds, but candidates are dependent and the independent-sampling order-statistic argument is not exact for the live sampler. See the live balance study (historical reference) for matched-state comparisons after this change.

This is a derivation from the current code and a controlled empirical check. It explains a plausible mechanism for the observed energy improvement; it does not prove that every increase improves energy or lifetime. The long-run report (historical reference) contains the paired lifetime results. No production chaos default is changed by these experiments.

After pheromone calibration, removing chaos raised frozen-state energy by 5.801%, compared with 17.333% under the legacy parameter scale. Doubling chaos still improved the calibrated 150-round energy by .463% on average across three seeds. The calibration changes deposit size, evaporation and bounds together, so these controls show an interaction with the overall calibration rather than identifying one parameter as the cause. The transition-mixture identity below holds under both scales; the baseline probabilities being mixed have changed.

The completed follow-up finds a .164% mean energy saving through 1400 rounds. Mean first-node death moves from 1494.333 to 1499.333 rounds, with paired changes of 0, -2 and +17. Mean full-survivor service falls from 2184.667 to 2167.667 rounds, a .778% regression; paired changes are -23, -29 and +1. Thus the observed energy benefit does not justify promoting doubled chaos as a lifetime improvement. Current bounds [.05,.30] remain in production.

Implementation sources: [clustering and probabilities](../../src/algorithms/clustering/ac_aco/ac_aco.py), [ant orchestration](../../src/algorithms/ac_aco.py), [physical energy evaluator](../../src/evaluate.py). All formulas below use these implemented rules.

## 1. Chaos is an exact mixture with uniform sampling

For a given source CH, let `n` be the number of available candidates and `p_j` the normalized pheromone/heuristic probability of candidate `j`. The implementation adds the same scalar `c = strength * chaos[source]` to every candidate:

$$q_j(c)=\frac{p_j+c}{1+nc}=(1-\lambda)p_j+\frac{\lambda}{n},\qquad \lambda=\frac{nc}{1+nc}.$$

Thus increasing strength increases a **uniform exploration mixture**, conditional on the same optimizer state. The first CH is already sampled uniformly; this expression applies to subsequent CH selections.

$$\frac{d\lambda}{dc}=\frac{n}{(1+nc)^2}>0,\qquad
\frac{dq_j}{dc}=\frac{1-np_j}{(1+nc)^2}.$$

Candidates with below-uniform baseline probability gain probability. Above-uniform candidates lose probability. Rankings remain unchanged, while their differences contract:

$$q_i-q_j=\frac{p_i-p_j}{1+nc}.$$

At an identical state, doubling strength gives

$$\lambda_2=\frac{2\lambda_1}{1+\lambda_1},\qquad
q_j(2c)-\frac1n=\frac{1}{1+\lambda_1}\left(q_j(c)-\frac1n\right).$$

For example, with `n=90`, logistic value `.6` and strength `.05`, `nc=2.7` and `lambda=.729730`. Doubling strength raises lambda to `.843750`. Deviation from uniform falls from `.270270` to `.156250` times the original baseline deviation. Doubling amplitude therefore does not double exploration; the effect has diminishing returns and depends strongly on candidate count.

The earlier trajectory diagnostics averaged lambda about `.770` for current chaos and `.883` for doubled chaos. These averages involve different adaptive histories and hypothetical source distributions; the exact doubling identity applies to individual matched states, not to those two averages.

For interpreting a reasonable strength range, invert the identity:

$$s=\frac{\lambda}{nz(1-\lambda)},\qquad z=\text{chaos[source]}.$$

With `n=90` and `z=.6`, uniform-mixture fractions `.8` and `.9` correspond to strengths `.074074` and `.166667`. Nominal strength is not itself an exploration percentage. A fixed amplitude also mixes more strongly on larger networks; these tuned bounds should not be treated as topology-independent constants.

## 2. The baseline strongly favors nearby CHs

The implemented unnormalized weight is

$$w_j=\tau_{ij}^{\alpha}\,e_j^{\beta}\,d_{ij}^{-\beta\omega}\,E_m(d_{ij})^{-\gamma}.$$

Here `e_j` is residual energy, `omega` is `distance_weight`, and `E_m=E_tx+E_rx+E_da`. Both the explicit distance term and the acoustic energy term penalize distant candidates. Holding pheromone and residual energy fixed, the exact local distance elasticity is

$$-\frac{d\log w}{d\log d}=\beta\omega+
\gamma\frac{E_{tx}}{E_m}\left(k+\frac{d}{1000}\log a\right),$$

because `E_tx(d)=C*(d/1000)^k*a^(d/1000)`. With the current positive exponents, every term is nonnegative. The raw beta schedule rises sharply from approximately 1 to approximately 5 around iteration 1500, making the explicit distance penalty much stronger late in the run.

For equal pheromone and residual energy, compare candidates 50 m and 200 m from the current CH. The production evaluator gives `E_m(50)=0.0000355972691 J` and `E_m(200)=0.0002729283743 J`. With gamma=omega=1, the closer candidate's baseline weight is **30.668 times** larger at beta=1, and **7851.126 times** larger at beta=5. This is an illustration using two distances, not the measured distribution over all candidates.

The CH sequence is a construction order, not the actual physical routing path. Favoring a short step to the next CH can produce many CHs in one region. That local preference need not minimize the final tree's reception, aggregation and relay costs. Uniform mixing gives remote regions a larger chance to receive a CH, which can reduce the burden subsequently faced by the shared router.

## 3. Coverage explains when the mixture helps

Let `H` be an available subset of `h` nodes whose selection would cover a poorly covered region. Summing the probabilities gives

$$q(H)=(1-\lambda)p(H)+\lambda\frac{h}{n},\qquad
\frac{dq(H)}{d\lambda}=\frac{h}{n}-p(H).$$

Increasing chaos improves the probability of selecting that region **if the baseline underweights it**, `p(H)<h/n`. This condition is essential. A well-targeted heuristic can instead lose useful preference when mixing increases.

In a simplified model with constant independent probability `q(H)` over `K` choices, the chance of missing the region is `(1-q(H))^K`, which decreases as `q(H)` increases. For exactly uniform selection of `K` distinct CHs from `N` nodes, the exact miss probability is

$$P(\text{no CH in }H)=\frac{\binom{N-h}{K}}{\binom{N}{K}}.$$

The actual sequential sampler removes selected nodes and changes its source, so the independent approximation is not an exact prediction for this implementation. Both expressions explain the direction of the coverage mechanism under their stated assumptions.

Observed clustering outliers fell from 5.063 to 4.572 per round in the earlier 150-round comparison. Outliers are nodes outside all CH communication radii. They still participate in routing and are served; these are coverage counts, not packet loss or discarded sensors.

## 4. The objective depends on the low-cost tail

AC-ACO selects the lowest-cost feasible tree from up to 40 ants. Conditional on a fixed round state, candidates sample the same probability model; pheromone deposits are not reflected in the round's probability snapshot. If feasible candidate costs have CDF `F_s(E)` and 40 independent feasible candidates are obtained, then

$$P(E_{best}>E)=(1-F_s(E))^{40},\qquad
\mathbb E[E_{best}]=\int_0^\infty(1-F_s(E))^{40}\,dE.$$

Stronger chaos helps selection when it improves the low-cost tail at the energies relevant to this minimum. Higher entropy or lower mean candidate cost alone does not establish that. Late failures can leave fewer than 40 feasible candidates; then, conditional on the count and independent conditional feasible costs, the exponent is the actual candidate count. The ten attempts per ant impose a finite search budget.

Let `f` be the fixed-state probability that one attempt produces a feasible tree, and let `A=10`. Under independent attempts, one ant succeeds with probability `h=1-(1-f)^A`; the expected number of feasible candidates is `40h`. Thus increasing feasibility from `.05` to `.10` would increase expected candidates from `16.051` to `26.053`, without changing the 40-ant budget. These illustrative feasibility values are not measurements. More generally, using the conditional feasible-energy CDF `F`, the probability that none of the 40 ants produces a route costing at most `E` is

$$P(\text{no candidate}\le E)=[1-hF(E)]^{40}.$$

This exposes two potential benefits: improving feasibility `h`, and improving the feasible low-energy tail `F(E)`. Increasing chaos guarantees neither, but reduced spatial clustering can improve both. The long-run report measures actual feasible candidate counts and attempts after iteration 1500.

The matched-state probe restores the current-chaos seed-6 physical and optimizer checkpoints, doubles only transition strength, and samples 400 candidates for each factor with the same RNG seed. Pheromone, energy, logistic values, beta and cost window are held fixed. No deposits or optimizer evolution occur between samples. This isolates transition mixing; the full trajectories additionally change pheromone evolution and future states. All these probe candidates were feasible. The next-round beta values for checkpoints 600, 1499 and 1501 are approximately 1, 3 and 4.999818, respectively.

<!-- PROBE_TABLE_BEGIN -->
| Completed checkpoint | Factor | Mean candidate energy (J) | Empirical expected best of 40 (J) | Mean outliers | Mean CH pair distance (m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 600 | 1.0 | 0.018144373 | 0.015651759 | 4.9100 | 311.808 |
| 600 | 2.0 | 0.017996195 | 0.015743482 | 4.5950 | 313.509 |
| 1499 | 1.0 | 0.019136835 | 0.016271718 | 5.8375 | 308.419 |
| 1499 | 2.0 | 0.018812734 | 0.016189654 | 4.8225 | 312.242 |
| 1501 | 1.0 | 0.019258399 | 0.016334099 | 5.6800 | 310.249 |
| 1501 | 2.0 | 0.018909420 | 0.016061968 | 4.7875 | 314.256 |
<!-- PROBE_TABLE_END -->

The empirical expected minimum is calculated exactly for sampling 40 times from the empirical distribution, not by selecting one lucky group of 40. For sorted sample costs `E_(i)`, `i=0..M-1`, its value is

$$\sum_{i=0}^{M-1}E_{(i)}\left[\left(1-\frac{i}{M}\right)^{40}-\left(1-\frac{i+1}{M}\right)^{40}\right].$$

At checkpoint 600, doubled chaos lowers mean candidate cost but slightly raises the estimated best-of-40 cost by .586%. At checkpoints 1499 and 1501, it lowers both, with estimated best-of-40 improvements of .504% and 1.666%, respectively. At 1501, the fraction of candidates at or below the current-chaos 10th-percentile cost rises from 10% to 14.25%. These observations support a better low-cost tail near the stronger late-beta locality, while the 600 result shows why a universal claim would be wrong. There are only 400 samples per state and one checkpoint trajectory; no statistical significance is established. Adjacent checkpoints do not isolate beta by themselves because residual and optimizer states also change.

## 5. Pheromone disturbance also flattens preferences

The second chaos mechanism adds a common source-row offset after evaporation and accumulated ant deposits, before the elite deposit. For two positive pre-offset values `a>b`,

$$\frac{d}{dc}\frac{a+c}{b+c}=\frac{b-a}{(b+c)^2}<0.$$

Thus the offset reduces pheromone ratios toward 1, while the elite deposit subsequently reinforces selected edges. The earlier frozen-state ablation found removing transition chaos increased energy by 6.581%; removing pheromone disturbance increased it by only .087%. Those controls support transition mixing as the main observed early mechanism, rather than proving its dominance at all ages.

For a conservative shared-edge recurrence, let `D=Q/E_ref` bound all-ant deposits and the elite deposit separately:

$$\tau_{t+1}\le(1-\rho)(\tau_t+D)+c+D,
\quad \tau_*\le\frac{(2-\rho)D+c}{\rho}.$$

The logistic update has `z<=r/4` for values in `[0,1]`. At doubled maximum strength `.6`, `r=3.61`, reference route cost `.015 J`, `Q=.01` and minimum evaporation `.1`, this envelope is `18.081667`, below `tau_max=20`. The reference route cost is a scenario, not a guaranteed lower bound; actual floor and ceiling occupancy must still be measured. The lifetime report supplies those observations.

## 6. Energy savings do not imply longer life

Total tree energy and first-node death are different objectives:

$$E_{total}(t)=\sum_i E_i(t),\qquad
T_{FND}=\min_i\inf\left\{T:\sum_{t=1}^{T}E_i(t)\ge e_i(0)\right\}.$$

A lower sum can still exhaust one heavily used relay earlier. Greater CH dispersion can improve coverage without removing a relay bottleneck near the base. In addition, `q_j >= lambda/n`: even a depleted node with baseline probability approaching zero retains a positive CH-selection probability. Increasing exploration therefore weakens the protection supplied by the residual-energy heuristic as well as weakening the distance bias. The final selection minimizes total energy and has no explicit minimax-depletion constraint.

The round-1400 checkpoints demonstrate the objective tradeoff. Mean total energy falls from 22.375407325 J to 22.338751565 J across seeds. Yet node 65's residual energy falls from .297619 J to .292228 J in seed 6, and from .300493 J to .292961 J in seed 7. In seed 8 it rises from .296040 J to .300746 J. Saving total energy therefore does not uniformly preserve the node that later controls connectivity.

Full-survivor service can also end while many sensors retain energy if a required connection disappears or the finite greedy routing search fails. On this map, node 48 has only two communication neighbors within the 200 m radius: node 33 at 91.519 m and node 65 at 185.485 m. In the current-chaos seed-6 trajectory, node 33 dies at completed round 1510; node 65 dies at 2192, disconnecting surviving node 48. Service stops after 2192 successful rounds while 98 nodes are alive. Once both neighbors die, no CH sampler can reconnect node 48. This is a physical connectivity limit for serving every survivor, not an all-node-death time. Hence the paired FND and service-duration results must govern any lifetime claim.

Increasing chaos indefinitely sends `lambda` toward 1 and suppresses useful residual-energy and pheromone preferences. These experiments establish neither an optimal amplitude nor a requirement for a chaotic logistic sequence specifically: positive uniform mixing itself explains the probability mechanism. Different maps, constant disturbances, other schedules and larger amplitudes require separate comparisons.