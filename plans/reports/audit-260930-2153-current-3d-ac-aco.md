## 1. Executive diagnosis

AC-ACO still improves round-energy clustering on this map. Its reported lifetime is dominated by a sparse 3D relay bottleneck and by search exhaustion, which are different outcomes from clustering quality.

For seed 39, AC-ACO saves 4.21% energy over the first 1,000 rounds and delays the first death from round 1442 to 1476. Nevertheless, ACO records 2210 rounds against AC-ACO's 2182. After node 33 dies, node 48 can remain served only when node 65 is a CH and node 48 is a member. AC-ACO exhausts node 65; ACO sometimes keeps it alive longer. Across all six measured seeds, AC has lower mean energy over the first 1,000 rounds. The useful companion CH, node 77, occurs much less often in AC-ACO's selected solutions. AC-ACO's chaos dilutes proximity and pheromone preferences, while both methods rank only total round energy rather than the drain on critical relays.

There is also a measurement problem: ACO seed 39 stops after 400 unsuccessful attempts while a valid routing tree still exists. Rebuilding the previous round's CH set at that exact final state succeeds. Thus `len(history)` measures completed rounds before death, routing failure, search exhaustion, or the round cap. It is not a pure physical network-lifetime measurement.

No remaining 2D distance calculation, algorithm-to-simulator distance disagreement, RNG order leakage, or shared energy-state leakage was found. All 10,000 stored sensor-pair distances exactly equal manually calculated 3D distances. The recent NumPy conversion agrees with its predecessor to within 1.67e-16 across 900 probability calculations.

Scope: current HEAD `e9c773f`, branch `fix-ac-aco-long-time`; current `map.pkl` SHA-256 `ebe729265598746b30af09715e239a9891b2ac95ac66656096dc712e6c34fdcc`. Implementation and original results were not modified. Diagnostics are separate JSON artifacts under `plans/reports/audit-260930-2127-diagnostics`. Four existing tests pass. Full seed-39 and seed-47 traces reproduce the original CSV alive counts exactly, with maximum energy difference 1.74e-17.

The user's clarified 2D experience is background evidence about clustering, not an equivalent 2D benchmark. The available history already has correct 3D coordinates before AC-ACO was added. Consequently, this audit identifies mechanisms in the current 3D experiment; it cannot attribute an historical performance reversal to a single matched 2D-to-3D commit.

## 2. 2D → 3D regression findings

**Finding 1 — Total round energy does not protect the critical relay.**

- **Severity:** High.
- **Category:** OBJECTIVE MISMATCH; EXPECTED ALGORITHMIC BEHAVIOR exposed by 3D sparsity.
- **File:** `src/algorithms/ac_aco.py`, `src/algorithms/aco.py`, `src/algorithms/routing/routing.py`, `src/evaluate.py`.
- **Function/Class:** `ACACO.plan_round`, `SimpleACO.plan_round`, `dropping_member_multi_hop_routing`, `Evaluator.energy_consumption`.
- **Location:** AC-ACO line 78; ACO line 74; router lines 134, 150, 169; evaluator line 64.
- **Current behavior:** Both algorithms minimize the sum of actual per-node round costs. No objective term protects the remaining energy or connectivity importance of node 65. Nearest-CH assignment can make node 77 a member of CH 65, which blocks it as an immediate relay for 65; the router then uses node 18.
- **Expected behavior:** A clustering-energy benchmark should report energy and node-death metrics separately. A lifetime objective must account for critical relay depletion.
- **Evidence:** Seed 39, round 2000: selected route has `77 -> 65 -> 18`; node 65 costs 0.000469419. Swapping CH 86 for CH 77 keeps 20 CHs, produces `65 -> 77 -> 89`, lowers node-65 cost to 0.000172148 and total cost from 0.016932526 to 0.016621775. A different valid swap, CH 96 for 77, costs slightly more overall, 0.017006236, while saving the same critical-relay energy; the current objective would prefer the original to this particular alternative.
- **Why it appeared or became important in 3D:** Flattening the same coordinates increases average neighbors from 18.02 to 35.28 and node 48's neighbors from two to ten. In genuine 3D, losing nodes 33 and 65 isolates node 48 and stops everyone.
- **How it can cause ACO >= AC-ACO:** AC-ACO can save energy elsewhere while exhausting node 65 earlier. ACO's more local CH paths more often include the useful pair 65/77.
- **Exact correction required:** Preserve the current objective if the study evaluates clustering energy, and report energy/FND separately from service duration. If lifetime is the study's explicit objective, add a defined residual-normalized drain/connectivity criterion using actual tree consumption. This is an objective decision, not a distance fix; do not silently change the energy model.

**Finding 2 — Search exhaustion is counted as network lifetime.**

- **Severity:** High.
- **Category:** OBJECTIVE MISMATCH; METRIC RESOLUTION/TIE EFFECT.
- **File:** `src/simulate.py`, `src/run.py`, both ACO orchestrators.
- **Function/Class:** `Simulator.run`, `summarize`, `plan_round`.
- **Location:** simulator lines 33–38; runner lines 83–90; ACO line 83; AC-ACO line 92.
- **Current behavior:** A round with zero successful sampled candidates immediately ends the run. CSVs contain no stopping reason. The summary calls `len(history)` rounds survived.
- **Expected behavior:** Distinguish search exhaustion, physical disconnection, complete death, and cap termination.
- **Evidence:** Final ACO39 state: 99 live nodes, node 65 energy 0.002454119. All 400 sampled attempts fail. Rebuilding the last selected CH set succeeds, costs node 65 only 0.000172148, and consumes 0.018472352 overall. AC39 ends differently: both 33 and 65 have zero energy, and 48 has no live neighbor.
- **Why it appeared or became important in 3D:** Following node 33's death, the valid CH combinations narrow sharply. Random search can miss the necessary CH/member roles despite physical connectivity.
- **How it can cause ACO >= AC-ACO:** The final ranking mixes relay endurance with candidate-finding reliability. Either method can end at a random search failure; near-equal stopping rounds need not indicate equivalent clustering.
- **Exact correction required:** Record explicit termination reasons. Before stopping on search exhaustion, reconstruct and reevaluate a previous valid CH configuration when its CHs remain live, using fresh route nodes and current residual energy. Label unresolved search exhaustion separately even if such a fallback fails; do not claim physical infeasibility from sampled failures alone.

**Finding 3 — Chaos is a large, candidate-count-dependent uniform mixture.**

- **Severity:** High.
- **Category:** NUMERICAL SCALING ISSUE; HYPERPARAMETER SENSITIVITY.
- **File:** `src/algorithms/clustering/ac_aco/ac_aco.py`.
- **Function/Class:** `ACACOClustering._transition_probabilities`.
- **Location:** lines 209–237.
- **Current behavior:** After normalizing heuristic weights to probabilities, the same `c = strength * chaos[source]` is added to every target. For `m` available targets, the resulting distribution is `p' = lambda*p + (1-lambda)/m`, where `lambda = 1/(1+m*c)`.
- **Expected behavior:** If chaos strength is meant to be a mixing percentage, its actual influence should be explicit and independent of target count. The current additive definition must at least be evaluated as the mixture it actually produces.
- **Evidence:** With 99 targets, strength 0.05 and current logistic values, lambda ranges 0.1829–0.3887, mean 0.2563. Initial transition probability variance falls from 0.00088984 to 0.000059538. Mean probability of a CH-construction jump over 200 m rises from 0.2650 to 0.6772. Across six initial seeds, AC-ACO construction jumps average 268–280 m for seeds 21/39/42/47/48, versus 146–157 m for ACO. These are construction edges, not necessarily physical route edges.
- **Why it appeared or became important in 3D:** The flattening coefficient itself does not depend on z. Its consequences grow as fewer neighboring candidates and more long-distance candidates are available.
- **How it can cause ACO >= AC-ACO:** It weakens the useful CH-neighborhood and reinforced-edge preference. In the common last 705 rounds of seed 39, AC-ACO selects both 65 and 77 in 181 rounds, ACO in 404; the directed construction edge 65->77 is reinforced 78 versus 362 times.
- **Exact correction required:** If a bounded mixing fraction is intended, replace the additive per-target disturbance by an explicit bounded mixture, or divide the added mass by target count. Validate this meaning before selecting its magnitude. Do not remove chaos wholesale: the first-round ablation worsens energy for all four tested seeds, and chaos also preserves feasibility by keeping low-energy necessary CHs selectable.

**Finding 4 — Reinforcement saturates, losing cost-sensitive magnitude.**

- **Severity:** Medium.
- **Category:** NUMERICAL SCALING ISSUE.
- **File:** both clustering modules and their parameter files.
- **Function/Class:** `_update_pheromone`.
- **Location:** AC-ACO lines 241–263; ACO lines 103–117; AC parameters lines 27–31.
- **Current behavior:** `Q=100`, `deposit=Q/round_energy`, and `tau_max=10`. Every reinforced edge immediately clips to 10.
- **Expected behavior:** If graded cost-sensitive reinforcement is intended, the deposit scale must match the objective's units and pheromone bounds.
- **Evidence:** AC39's first deposit is 5944.813. On the same CH path, the earlier `Q/path_length` rule would give 0.0184373 because the construction path is 5423.776 m. Actual reinforced pheromone is 10 for both algorithms regardless of these thousands-sized deposits. AC39 after round 1 has 99.63% of live off-diagonal entries at tau_min; approximately 0.192% are at tau_max. Baseline pheromone decays much more slowly, with rho=0.1 versus AC's initial rho≈0.9.
- **Why it appeared or became important in 3D:** History changes reinforcement from path length in meters to tiny acoustic round-energy values without matching Q to the new units. This is not required by a third coordinate. Increasing 3D cost does not make deposits ineffective by becoming too small; they remain far beyond the clipping ceiling.
- **How it can cause ACO >= AC-ACO:** The cost-dependent reinforcement magnitude disappears, and AC's high early evaporation gives substantially shorter trail memory. Both algorithms retain information about which edges won, but not deposit-size differences between winners.
- **Exact correction required:** Normalize cost against a documented reference scale or rescale Q against the unchanged tau bounds, consistently for both algorithms. Confirm graded updates without clipping before tuning adaptive evaporation. A full lifetime ablation of this mechanism was not performed; saturation itself is proved.

**Finding 5 — The adaptive schedule is coupled to T_max and switches abruptly.**

- **Severity:** Medium.
- **Category:** NUMERICAL SCALING ISSUE; HYPERPARAMETER SENSITIVITY.
- **File:** `src/algorithms/clustering/ac_aco/ac_aco.py`, `src/hparameter.py`.
- **Function/Class:** `heuristic_weight`, `ACACOClustering.pre_round`.
- **Location:** clustering lines 38–46, 96, 125–142; general parameters line 10.
- **Current behavior:** Beta uses `sigmoid(5*(iteration-T_max/2))` on raw simulation-round index. It is 1 for roughly half the run and then nearly 5 within four iterations. Evaporation starts near 0.9 and only approaches 0.1 at the cap.
- **Expected behavior:** Search/adaptation horizon should have explicitly defined units. A simulation cap should not silently relocate the optimizer's exploration/exploitation transition.
- **Evidence:** Beta at iterations 1498/1499/1500/1501/1502: 1.00018/1.02677/3/4.97323/4.99982. Commit 95e6934 changes T_max from 350 to 3000, moving the transition from 175 to 1500. With AC39's observed round-2000 residuals and uniform tau, mean probability of selecting required CH 65 drops from 0.00109456 at beta 1 to 0.0000175405 at beta 5 before chaos. With strength 0.08, chaos raises it to 0.00835204, demonstrating that the floor is active.
- **Why it appeared or became important in 3D:** Network rounds are now the adaptation clock, and the transition coincides with the first critical-relay deaths around rounds 1400–1500. Earlier history had several internal search iterations per network round.
- **How it can cause ACO >= AC-ACO:** Most early rounds have the same eta/energy exponents as baseline ACO before chaos, with shorter trail memory. The late exponent increase heavily suppresses depleted yet necessary CHs; chaos partly rescues feasibility.
- **Exact correction required:** Decouple schedule horizon from the termination cap. If a smooth schedule is intended, use normalized progress and a slope expressed in progress units. Restoring multiple internal search iterations is a separate algorithm/budget decision; it is not automatically required.

**Finding 6 — Failure counters are not comparable.**

- **Severity:** Low.
- **Category:** IMPLEMENTATION BUG in diagnostics.
- **File:** `src/algorithms/aco.py`, `src/algorithms/ac_aco.py`.
- **Function/Class:** `plan_round`.
- **Location:** ACO lines 46–69; AC-ACO lines 48–74.
- **Current behavior:** AC counts each failed routing attempt; ACO increments its counter once when an entire ant exhausts retries.
- **Expected behavior:** A shared counter name should count the same event.
- **Evidence:** ACO39 reports 8803 failed routing attempts, while instrumented actual attempts minus feasible evaluations equals 154026. AC39's corresponding counter and measured quantity both equal 141887.
- **Why it appeared or became important in 3D:** Retries expand sharply after a bottleneck node dies, amplifying the accounting discrepancy.
- **How it can cause ACO >= AC-ACO:** It does not change the ranking. It can falsely suggest that ACO has vastly fewer infeasible candidates, misleading the diagnosis.
- **Exact correction required:** Increment per-attempt routing failures inside ACO's retry loop and count exhausted ants separately.

**Finding 7 ? PSO caches an order-dependent evaluation using an unordered key.**

- **Severity:** Medium.
- **Category:** IMPLEMENTATION BUG; comparison limitation specific to PSO.
- **File:** src/algorithms/pso.py, src/algorithms/routing/routing.py.
- **Function/Class:** PSO.plan_round, dropping_member_multi_hop_routing.
- **Location:** PSO lines 72?81; router line 155.
- **Current behavior:** Cache key sorts CH IDs, but evaluation preserves the decoded order. Routing processes CHs in that order and may detach different blocked members.
- **Expected behavior:** Cache keys must include every input that affects the evaluation, or evaluation must canonicalize those inputs.
- **Evidence:** Same initial current 3D state and CH set [38,82,18,81,50] costs 0.0273540685 in that order, 0.0275876250 reversed. Both evaluations use the same shared model and radius.
- **Why it appeared or became important in 3D:** Greedy dropping-member routing is order-dependent; sparse relay choices make the dependency relevant. The third coordinate itself does not cause the key error.
- **How it can cause ACO >= AC-ACO:** It does not: neither ant algorithm uses this cache. It compromises interpretation of the additional PSO comparator.
- **Exact correction required:** Use tuple(CHs) as key, or sort CHs before every evaluation and key them identically. Preserve per-round cache isolation.

No confirmed 3D ADAPTATION BUG in distance calculation or EXPERIMENT FAIRNESS BUG between ACO and AC-ACO was found. The mechanisms above should not be relabeled as missing z coordinates.

Relevant history, rather than a matched old 2D benchmark:

| Commit | Meaningful change | Required for 3D? | Possible loss of an earlier advantage |
|---|---|---|---|
| 04d30b3 | Point and deployment already include z and correct 3D norm | Yes, coordinate support | No distance omission in current implementation |
| ac370db | Initial AC-ACO: five internal iterations, coverage repair, normalized energy/residual/distance/load objective | AC-ACO introduced after 3D coordinates | Establishes that earlier repository AC code differs substantially from today's |
| 88a4908 | Replace that objective/coverage treatment by actual shared routing-energy evaluation; change heuristics and probability chaos | No, algorithm/model alignment | Removes explicit load/residual penalties and changes search behavior |
| 7bc69e4 / c29e197 | Move schedules to network rounds; one best batch per round; change Q/path_length to Q/energy | No | Changes timing, trail memory and reinforcement units |
| 7d0628b | 40 ants; ten attempts; baseline energy-cost exponent 3 -> 1 | No | Changes baseline robustness and effective comparison budget |
| 95e6934 | T_max 350 -> 3000 | No | Relocates AC's beta transition through its coupled schedule |
| e9c773f | Vectorize AC probabilities and cache static edge costs | No | Numerically equivalent on measured cases; not supported as root cause |

## 3. ACO vs AC-ACO implementation comparison

The actual execution path is:

1. `run.main` loads one trusted pickle into one `NetworkInstance` and creates one shared `HyperParameters` object.
2. Before each algorithm, global Python random is reset to the same SEED; fresh Simulator and algorithm instances are created. AC receives that seed for its local Random object.
3. Each Simulator run initializes a fresh residual-energy list and live-ID list. Network sensor Points have no energy/alive/CH state.
4. Ants choose ordered CH paths. ACO fixes distinct starts for the round. AC chooses a uniform first CH per attempt, then disturbed transition probabilities.
5. Shared `build_clusters` assigns each non-CH to its nearest CH within radius; unassigned nodes become outliers.
6. Shared dropping-member router connects CHs/outliers to sink or to a live, in-range node closer to sink. It can detach a blocked member only when no unblocked parent exists. Ordinary members may themselves be relays.
7. Shared Evaluator recursively calculates actual tree consumption. Both ant algorithms retain the minimum sum; pheromone updates once after the successful batch. AC also updates historical cost extrema and logistic state.
8. Simulator uses the returned consumption dictionary directly, subtracts each cost with a zero floor, filters energy<=0 nodes, and records round, alive_nodes and full modeled round_energy.
9. Repeat until no candidate, all nodes die, or 3000 rounds. Summary prints integer `len(history)` and summed modeled consumption formatted to four decimals. Notebook lifespan also uses `len(history)`; its display may round means to whole numbers.

PSO position is an N-dimensional sensor-selection score vector, not a physical 2D position. PSO's distinct search path: 20 particles have one score dimension per live sensor; decode selects the highest-scored CH IDs. It tries up to 20 iterations, stops after three non-improving iterations once a feasible tree exists, and caches evaluations by CH set inside that round. Eighty percent of particles warm-start the next round with ID-keyed positions/velocities, while fitness is reset. It uses the same cluster builder, router, Evaluator and simulator update.

Current physical inputs: 100 sensors, 500x500x500 m deployment, sink (250,250,0), initial energy 0.6, communication radius 200 m. All algorithms share P0=0.1, packet_size=200, rate=10000, E_elec=5e-8, E_integrate=5e-9, spreading exponent 1.5, 30 kHz absorption and attenuation coefficient 6.7303522. None regenerates the map in a benchmark.

| Component | ACO | AC-ACO | Consistency |
|---|---|---|---|
| Sensor-CH distance/assignment | Network dist_matrix; shared nearest assignment | Same | 3D; meters; identical helper |
| CH-sink distance | Network base_dists | Same | 3D; meters |
| Routing and connectivity | Shared dropping-member router | Same | Radius and strict closer-sink checks identical |
| Energy/fitness distance | Evaluator on actual tree | Same | Converts meters to kilometers exactly once |
| Construction eta | residual/distance | Same | 3D inter-CH construction distance |
| Energy heuristic | E_m(distance)^-beta; default beta 1 | E_m(distance)^-gamma; default gamma1 | Same one-packet acoustic helper |
| Fitness | Sum of actual node consumption | Same | No optimizer/simulator power-law discrepancy |
| Pheromone | Edge trails; rho 0.1; best path; clipping | Edge trails; adaptive rho; best path plus source chaos; clipping | Same bounds/Q; different memory |
| Randomness | Global Random; distinct starts | Local Random; starts with replacement | Same numeric seed, different sampling trajectories |

Default construction weights, before AC chaos:

`ACO: tau^1 * (residual/distance)^1 * E_m^-1`

`AC-ACO: tau^1 * (residual/distance)^beta(t) * E_m^-1`

AC applies a 1e-12 distance floor; ACO applies a 1e-9 floor. Every distinct sensor pair in this map is at least30.43 m apart, so these floors have no current effect. AC breaks equal-cost candidate ties by ordered CH tuple; ACO keeps the first minimum. They therefore share the same three pre-chaos factors early in the run. Baseline ACO is not a distance-only comparator; it already contains the residual-energy and acoustic edge-cost terms.

The actual energy law is `E_tx(d,k)=0.002*k*(d/1000)^1.5*6.7303522^(d/1000)`. There is no d²/d⁴ radio threshold. E_rx=1e-5 per received packet and E_da=1e-6 per aggregated received packet. CHs transmit two packets; ordinary relays forward 1+received_packets; ordinary leaves transmit one. CH processing takes precedence over the relay flag. Sink costs nothing. CH packet behavior is a shared model choice, although several comments/docs describe it inaccurately; changing it needs a separate model specification. The squared distances in routing are a preference surrogate, not the fitness or energy model, and both ant algorithms use them equally.

Fairness and budgets:

- ACO and AC-ACO share the same CH count constraint, `round(0.2*live_count)`, initially 20, the same route rules, energy law, state reset, maximum rounds and stopping policy.
- Both try 40 ants with up to ten construction/routing attempts each: up to 400 attempts but at most 40 feasible energy evaluations per round. They stop each ant at its first feasible route; there is no extra inner search-iteration budget and no convergence early stopping.
- ACO has only min(40,live_count) ants if fewer than 40 survive; AC still tries 40. This does not affect the measured 98–100-live runs.
- Before the first death in seed 39: 40 attempts and 40 fitness evaluations per round for each. Rounds1500–1999: AC averages 231.17 attempts/30.09 feasible evaluations; ACO196.11/33.01. Rounds2000 onward: AC231.13/30.14 versus ACO291.90/20.04 over their respective endings. AC has fewer usable evaluations in the middle phase, more near the end. It is not uniformly under-budgeted.
- Lifetime-wide seed 39 means: AC36.81 and ACO36.03 feasible evaluations per recorded round. They spend many more attempts than that finding those evaluations.
- PSO uses 5% CHs, initially five, versus twenty for the ant methods. Its nominal maximum of 400 particle evaluation requests are reduced by caching/early stopping. Actual seed 42 first ten rounds have 751 unique evaluations; the tenth has 80 requests, 36 unique evaluations and four iterations. It shares the environment, but CH count and search budgets are not equal to ACO/AC-ACO.

## 4. Seed audit

`run.SEED=random.randint(0,100)` is chosen at module import. It controls algorithm stochastic choices; it does not control the already-loaded map. Recalling the seed is insufficient to reproduce a run after replacing map.pkl or changing parameters/code.

The runner reseeds global Python random before every algorithm. ACO and PSO use that generator. AC uses `random.Random(SEED)` internally. No NumPy RNG is used; NumPy only performs deterministic array calculations. Map generation uses independent global-random uniform draws when map_gen is executed, without a recorded deployment seed.

Equal numeric seeds do not give equal initial solutions: ACO samples 40 distinct starting IDs; AC samples starts with replacement across attempts and consumes different random draws. For seed 39's first round AC has 33 distinct starts versus ACO40, although both evaluate 40 feasible candidates. This is a search-method difference, not an execution-order seed bug.

Actual Simulator seed 42 runs of ten rounds reproduce histories/counters exactly in orders AC->ACO->PSO and PSO->ACO->AC. A fingerprint covering coordinates, sink, distance tables and static settings remains unchanged. Per-run residual/alive lists and freshly created route Nodes provide state isolation; no deep copy of sensor objects is required because those Points are never mutated by algorithms.

CSV provenance is incomplete: names store hour, seed and algorithm, but not map checksum, parameters or revision. Repeats of the same seed in one hour can overwrite the filename. That is an experimental recordkeeping limitation; there is no evidence that it caused the observed seed 39/47 comparisons.

## 5. Pheromone / heuristic diagnosis

Initial 3D off-diagonal statistics, 9,900 directed pairs:

| Term | Minimum | Maximum | Mean | Standard deviation |
|---|---:|---:|---:|---:|
| distance, m | 30.4294 | 694.8791 | 316.3461 | 119.4561 |
| residual/distance | 0.00086346 | 0.0197178 | 0.00233001 | 0.00146265 |
| 1/E_m | 228.889 | 44943.093 | 2620.109 | 3469.528 |
| tau at initialization | 1 | 1 | 1 | 0 |
| eta/E_m unnormalized weight, beta 1 | 0.197636 | 886.178 | 11.1369 | 37.8123 |
| logistic source term | 0.317723 | 0.902478 | 0.647829 | 0.220281 |
| probability before chaos | 0.00018461 | 0.657011 | 0.0101010 | 0.0298302 |
| probability after chaos, strength 0.05 | 0.00633006 | 0.221590 | 0.0101010 | 0.00771610 |

For beta 5 with the same initial equal residuals, raw weights range 1.10e-13 to 1.34e-4. Log-space calculation preserves them correctly; there is no underflow-based degeneration in these measurements. Normalized maximum probability can reach 0.9981 before chaos, 0.36885 afterward. Multiplying all distances by a common factor in the eta term would cancel during normalization; the changed spatial distribution and nonlinear E_m ratios matter, rather than the small absolute eta value alone.

AC-specific mechanisms:

| Mechanism | Changes in execution? | Numerical influence and seed dependence |
|---|---|---|
| Adaptive beta | Yes, sharply around iteration 1500 | Strongly changes distance/residual discrimination; same time schedule across seeds |
| Adaptive rho | Yes, from≈0.9 toward0.1 | Early trail retention≈0.1 versus baseline0.9; same schedule across seeds |
| Logistic sequence | Yes, every successful/failed batch update on live IDs | Fixed r3.61 and seed 0.37; shared starting sequence across experiment seeds, no geometry information |
| Cost-dependent chaos strength | Yes | Uses previous best and lifetime-wide feasible-cost extrema; AC39 observed snapshots mostly0.061–0.084, not the full nominal0.05–0.30 range |
| Probability chaos | Yes | Strong uniform mixing; AC39 sampled signal retention means about0.17–0.22 after the first rounds |
| Pheromone chaos | Yes | Adds the same source disturbance to all outgoing targets, including unreinforced edges; later raises the background floor |
| Alpha/gamma | No adaptation | Both fixed1; neither is an additional adaptive mechanism |
| Residual-energy factor | Yes through changing residuals | Already exists in baseline; AC beta 5 makes its contrast much stronger |

AC39 tau snapshots: round 0 mean0.1516, max10; round 1 mean0.1207 with 99.63% at minimum; round 1000 mean0.1327; round 2000 mean0.1989 and no entries at minimum because chaos raises background; last successful round mean0.2156. Selected edges continue to discriminate at the maximum. Thus trails are active, but mostly bounded low/high values, with short early memory and heavy probability dilution. AC does not collapse into identical ACO behavior.

Chaos provides both benefit and cost. First-round no-chaos ablation raises energy for seeds21/39/47/48; for39, 0.0168214 becomes0.0178194. A frozen final ACO39 state, with identical replayed ACO pheromone used for both methods and AC beta 5/strength 0.08, fails for ACO on2/40 seeds but for AC on0/40. This is a construction-robustness experiment, not a full lifetime comparison. Removing chaos has not been established as a correction.

## 6. Tie diagnosis

No exact uncapped 3D lifetime tie is present in the available original CSV pairs, and the user could not identify an exact tied seed. Native exact-tie frequency is therefore unconfirmed. Seed21 is a measured near tie, AC2171 versus ACO2175, a difference of four rounds, while their death times/energy trajectories differ.

The controlled flattened seed 39 experiment gives an exact reported tie: 3000 versus 3000, both terminated by T_max. AC retains100 nodes and spends29.863584 energy; ACO retains99, first death at 2808, and spends32.144071. They have zero identical CH sets, zero identical route hashes and zero exactly identical energy values across the3,000 corresponding rounds. This tie is censorship by the cap.

Genuine 3D seed 39 also has zero identical CH sets, route hashes and exact round-energy values across the common2182 rounds. Similar stopping rounds are not reused/cached solutions or identical RNG trajectories. The integer completion metric and shared narrow relay-lifetime range can mask sizeable energy/clustering differences. Notebook mean labels introduce additional whole-number display rounding; CSV energy itself is not rounded by the summary formatting.

For native seed 42, AC records 2201 rounds against ACO2036. ACO stops with node 65 still holding 0.0201607 energy; rebuilding its previous CH set succeeds. This gives a concrete winning-seed contrast to seed 39, while seed 48 is a second AC win driven by later physical relay depletion.

The flattening experiment is not a reconstruction of the user's differently configured historical 2D study. It establishes sensitivity to depth/connectivity, not a claim that AC regained an old matched 2D lifetime advantage.

## 7. Losing-seed case study

Measured seed groups:

| Seed | AC-ACO rounds | ACO rounds | AC first-death index | ACO first-death index | Result |
|---|---:|---:|---:|---:|---|
| 0 | 2166 | 2250 | 1474 | 1416 | ACO wins |
| 21 | 2171 | 2175 | 1493 | 1452 | Near tie; ACO +4 |
| 39 | 2182 | 2210 | 1476 | 1442 | ACO wins |
| 42 | 2201 | 2036 | 1499 | 1434 | AC wins; ACO ends with node 65 still alive |
| 47 | 2176 | 2285 | 1507 | 1415 | ACO wins; both original CSVs reproduced |
| 48 | 2204 | 2123 | 1497 | 1515 | AC wins |
| 39, z=0 diagnostic | 3000 | 3000 | None | 2808 | Capped tie |

Round/death indices above are zero-based. Original CSVs contain only seeds39/47. Other rows are new temporary diagnostic runs; Both algorithms on seed 47 are also reproduced. Stored notebook outputs cover another machine/path and lack full provenance; they were not treated as a paired experiment from this checkout.

Seed39 trace:

1. Initial state: identical100 sensors at 0.6. AC's first best CH path is `[22,32,73,19,77,74,82,41,94,85,96,49,43,2,72,40,86,60,64,63]`; ACO's is `[82,55,79,25,52,54,17,95,56,21,26,37,10,80,58,3,46,13,61,35]`. Both have40 feasible candidates. Costs are0.016821386 and 0.018416381.
2. Before1000: both evaluate40 routes each round; mean costs AC0.015966567, ACO0.016668375. AC's high evaporation and clipping rapidly produce near-minimum background pheromone; ACO retains winning construction edges longer.
3. Node33 dies at 1442 in ACO and 1476 in AC. Node48's only physical neighbors are33 at 91.519 m and 65 at 185.485 m. Sink distances are493.760 m for48 and 522.020 m for65. A CH/outlier48 cannot route to 65 because it is farther from sink. For a valid tree,65 must be a CH and 48 a non-CH member;65 then forwards through18 or77.
4. Feasible candidate counts fall to roughly30–33 even though attempts rise above190–230 per round. Whole-map coverage is no longer sufficient; specific leaf-support CH roles determine feasibility.
5. During common rounds1477–2181, AC chooses CH 77 alongside required CH 65 in 181/705 rounds; ACO404/705. The earlier noted one-CH swap proves that useful configurations can be missed. The long65->18 link is183.787 m, versus 65->77 at 103.087 m; actual single-packet acoustic transmit cost is2.78 times larger on the long link.
6. At AC round 2000, remaining65 energy is0.0717298, while48 still has0.311889. The selected route sends65 to 18, costing65 0.000469419. A feasible one-CH swap to 77 costs 65 0.000172148 and lowers total round energy as well. It would be accepted if sampled.
7. AC node 65 dies in round 2181. Next round all400 attempts fail on node 48 with empty candidates/droppable lists: both neighbor energies arezero. Network residual energy is24.8576 and 98 nodes remain alive.
8. ACO ends at round 2210 with 33 dead but65 alive at 0.002454119. Its failed sampled candidate leaves48 as an outlier;65 is rejected as farther from sink. Reusing the previous CH set still yields a valid tree. This stop is candidate-search exhaustion, not physical disconnection.

Contrasting seed 48: AC node 33 dies at 1497 and 65 at 2203. ACO node 33 survives until 1515 but65 dies at 2122, soAC records 81 more rounds. Even first-node-death ordering can disagree with final service-duration ordering. Across measured AC seeds 0/21/39/42/47/48, the same65 exhaustion after 33 loss puts results in the narrow2166–2204 range. ACO has a more seed-dependent mixture of depletion and failed-search endpoints.

A second losing-seed trace, seed 47, confirms the same relay mechanism: AC delays node 33 death to 1507 from ACO1415, but at those respective deaths node 65 already has only0.271881 in AC versus 0.300433 in ACO. During the following phase, AC selects CH77 in 148/668 rounds versus ACO596/869. AC node 65 dies at 2175; ACO keeps it until 2284. Both final failures have node 48 isolated. Seed42 is a second winning-seed contrast: ACO stops at 2036 with 65 energy 0.0201607 and a reconstructible previous route, while AC continues until 65 depletion at 2200. These cases distinguish critical-relay drain from candidate-search failure.

## 8. Root causes supported by evidence

| Root cause | Evidence | Mechanism | Observed consequence |
|---|---|---|---|
| Sparse 3D leaf support | Node48 has only33/65 as neighbors; flattened map has ten | First33 death forces a specific65-CH/48-member role; later65 death isolates48 | All measured AC endings occur with 98 alive and substantial residual energy |
| Clustering-energy objective versus duration metric | AC39 saves4.21% initially and 8.55% in the common late window, yet lasts28 fewer rounds | Saving total energy does not ensure saving necessary relays | Better energy clustering coexists with lower reported duration |
| AC probability dilution and differing trail memory | Exact mixture formula;25.6% initial signal retention;181 versus 404 occurrences of useful65/77 pair | Chaotic exploration weakens local pair reinforcement; high rho shortens memory | Critical relay sometimes uses a much more expensive parent |
| Sample failure ends a still-feasible run | Exact ACO39 final-state reconstruction succeeds after 400 failed attempts | Narrow feasible CH roles are missed; Simulator ends immediately | Reported lifespan includes solver reliability as well as network endurance |
| Reinforcement and schedule scaling changed in implementation | Q/path0.0184 becomes Q/energy 5944.8; cap350->3000 relocates beta transition | Clipping erases graded reinforcement; raw-index schedule delays adaptation then switches sharply | Adaptive mechanisms have materially different numerical behavior from earlier repositoryAC code |

The last row proves changed mechanics, not the size of their individual contribution to lifetime. No full-factorial ablation established those causal effect sizes. The evidence does not support blaming missingz, NumPy rounding, state leakage, or a simulator/fitness energy-law mismatch.

PSO's cache-key bug is independently confirmed but does not explain the ACO/AC-ACO ordering.

## 9. Minimal correction plan

Order before tuning:

1. **Correctness of experiment interpretation:** Keep the current 3D distances and shared acoustic model. Record stop_reason, completed_rounds, first-node-death, final alive count and residual energy. Distinguish search exhaustion from physical disconnection; retain model cost versus available-energy accounting explicitly.
2. **Correctness of feasibility handling:** Rebuild a previous valid CH configuration on fresh Nodes/current live state before terminating after a failed ant batch. Apply the same narrow feasibility safeguards to both methods: where the existing radius/monotonic rules force a sole remaining neighbor to be a CH, preserve that CH role and the dependent member role while maintaining the CH count. This changes candidate construction within the existing routing problem, not 3D support or routing physics.
3. **Fairness and diagnostic accounting:** Fix PSO's order-sensitive cache key. Make routing-failure counters count actual attempts. Compare the same number of evaluated feasible solutions or report attempted and feasible budgets separately. Record algorithm seed, fixed map fingerprint, revision and settings in result metadata; avoid overwriting repeats. If comparing PSO under identical CH constraints, align its five-percent target explicitly before making that comparison.
4. **Numerical scaling:** Define the probability-chaos coefficient as an explicit bounded mixture if that is its intended meaning. Rescale/normalize pheromone deposits so objective differences survive clipping. Separate adaptation horizon from T_max and express schedule slope in consistent units. Verify each isolated change before combining them.
5. **Only then tune or change the research objective:** Retune on multiple fixed deployments/seeds after the mechanics above are defined. If the claim is about clustering, compare matched-round energy and load/drain metrics. If the claim is about lifetime, explicitly add actual per-node residual-normalized drain/connectivity information to the objective; this is an objective change, not a cosmetic refactor or automatic consequence of 3D.

No implementation changes were made.

Unresolved questions: exact native 3D tied seeds are unavailable; the remembered≈500-round AC advantage was not tied to a reproducible seed; no equivalent historical 2D benchmark exists in this checkout; the intended one/two-aggregated-packet interpretation is unspecified; individual lifetime effects of the chaos normalization, reinforcement scale and schedule changes require isolated full-run ablations. The controlledz=0 run is capped, so it cannot establish uncapped 2D lifetime superiority.
