# D-ACO performance evidence

These are historical controlled comparisons, grouped by the objective, map,
seeds and horizon actually tested. Old default decisions are not current settings.
Current production uses powered depletion divided by structural grid density,
geometric calibration references, live pheromone and a single ant batch per round.
Parabolic grid decay is now the default by user choice. The first density-only
comparison below did not establish that parabolic decay improves every map.
No removed experiment driver is needed by the maintained algorithms or tests.
Full historical drivers and datasets remain retrievable from Git history.


---

Historical source: `plans/phase7-daco-grid/README.md`. Its implementation and defaults may differ from current production.

# Full D-ACO grid-distance experiment

Historical baseline objective: production has since moved to phase-9 powered
load/density fitness with always-live pheromone. This report retains the original
measurements. Its runner imports frozen legacy D-ACO, not current production.

Twelve full trajectories on the current 100-node map, radius 200 m, paired seeds 15/16/17. Each runs until no feasible tree, all nodes die, or the 3000-round horizon. Only grid attenuation changes; 40 ants, one batch, up to ten feasibility attempts per ant, routing, pheromone, and energy/load-CV fitness remain fixed.

The original overlap matrix F has unit weights for fully reachable cells. Linear multiplies F by `max(1 - d/(R + r_cell), 0)`; quadratic uses its square. Parabolic instead uses `max(1 - (d/(R + r_cell))^2, 0)`: gentle nearby, steeper farther away. `d` is sensor-to-cell-center distance and `r_cell` is the cell half-diagonal. The extended reach preserves partially reachable cells. This factor is applied consistently to grid density, candidate density, and coverage loss. No sensor-neighbor density is used.

| Seed | Grid | First-node death | Completed service | CPU seconds |
| --- | --- | ---: | ---: | ---: |
| 15 | none | 1676 | 2202 | 468.9 |
| 15 | linear | 1682 | 2206 | 499.3 |
| 15 | quadratic | 1699 | 2204 | 582.0 |
| 15 | parabolic | 1651 | 2195 | 555.5 |
| 16 | none | 1643 | 2186 | 474.6 |
| 16 | linear | 1677 | 2194 | 494.5 |
| 16 | quadratic | 1701 | 2194 | 580.7 |
| 16 | parabolic | 1656 | 2189 | 553.4 |
| 17 | none | 1656 | 2184 | 461.3 |
| 17 | linear | 1675 | 2199 | 497.5 |
| 17 | quadratic | 1688 | 2195 | 575.1 |
| 17 | parabolic | 1646 | 2164 | 541.5 |

Energy comparisons use the same first 2164 completed rounds for every run.

| Grid | Mean FND | Mean service | Equal-round energy | Energy change | CPU per completed round |
| --- | ---: | ---: | ---: | ---: | ---: |
| none | 1658.33 | 2190.67 | 34.186124 | +0.000% | 0.2138s |
| linear | 1678.00 | 2199.67 | 34.277189 | +0.266% | 0.2260s |
| quadratic | 1696.00 | 2197.67 | 34.515567 | +0.964% | 0.2636s |
| parabolic | 1651.00 | 2182.67 | 34.199126 | +0.038% | 0.2520s |

Full service means the search found a tree for every surviving sensor. Failure to find a tree is not equivalent to all sensors dying; HND/LND can be censored. Energy over equal rounds avoids rewarding an algorithm simply for stopping earlier. CPU times include the terminal failed search; concurrent runs make wall-time comparisons unsuitable.

CPU measurements are indicative: concurrency increased during the later trials, and hardware load/frequency were not controlled. Do not treat their ratios as precise kernel overhead.

Three seeds on one map are a paired comparison, not proof of improvement across deployments. No density-aware load fitness is enabled in these runs.

## Energy while all sensors remain alive: first 1642 rounds

| Grid | Mean energy | Change from original | Paired changes by seed |
| --- | ---: | ---: | --- |
| none | 25.716867 | +0.000% | +0.000%, +0.000%, +0.000% |
| linear | 25.814059 | +0.378% | +0.419%, +0.398%, +0.317% |
| quadratic | 26.019309 | +1.176% | +1.483%, +1.091%, +0.955% |
| parabolic | 25.747244 | +0.118% | +0.325%, +0.089%, -0.060% |

| Grid | Mean load CV | Mean peak relative depletion |
| --- | ---: | ---: |
| none | 0.778855 | 0.003458 |
| linear | 0.782677 | 0.002570 |
| quadratic | 0.785995 | 0.002387 |
| parabolic | 0.780954 | 0.003506 |

## Decision

Keep the original grid (`density_decay="none"`) as the default. Linear improves mean service by 9 rounds (paired changes +4/+8/+15), but raises all-alive energy by 0.378%. It is the best service tradeoff of these variants. The fast-drop quadratic curve delays first-node death most, at a 1.176% energy cost. The gentle-near parabolic curve loses 8 mean service rounds and uses 0.118% more all-alive energy.

All three curves are available as explicit production options, including `density_decay="parabolic"`. The optional parabolic implementation was added after the experiments completed; a regression test verifies its grid weights, density, and coverage-loss scores exactly match the tested adapter. Recorded source hashes describe the code used during the runs, not this later addition.

Density-aware load fitness remains unchanged because the proposed gentle-near curve did not improve the full comparison. Any later fitness experiment should use the baseline weighted grid density before CH coverage loss, rather than the order-dependent remaining-density score.

Mean peak relative depletion is sensitive to a nearly exhausted sensor just before first-node death; its reduction alone does not quantify whole-network balance. Absolute load CV slightly increases for all weighted variants.

---

Historical source: `plans/phase8-daco-tuned/RESULTS.md`. Its implementation and defaults may differ from current production.

# Full D-ACO: sibling tuning and density-load fitness

Historical max/CV objective, superseded in production by phase-9 powered load/density.

Fifteen full runs on the current 100-sensor map (radius 200 m), paired seeds 15/16/17. Only D-ACO is simulated. Forty ants in one batch, until no feasible complete tree, all nodes die, or the 3000-round horizon. Every successful tree is checked to serve every surviving sensor.

The sibling tuning is a single-batch adaptation. Its original four iterations of 20 ants are not reinstated. Absolute energy/CV fitness, live deposits, elite units, evaporation order, coverage scaling, and numeric controls are transferred together. Shared routing, energy model, and map come from review_uwsn. No files are changed in uwsn.

Energy uses the same first 1589 rounds with every sensor alive. CPU is recorded but concurrency and hardware frequency were not controlled.

| Configuration | Mean first-node death | Mean service | All-alive energy change | Mean clustering attempts |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1658.3 | 2190.7 | +0.000% | 185662 |
| tuned | 1609.3 | 2191.7 | +2.604% | 143447 |
| risk_control | 2309.3 | 2380.3 | +3.304% | 117305 |
| density_005 | 2303.3 | 2385.7 | +2.380% | 120224 |
| density_010 | 2333.7 | 2372.3 | +4.791% | 108249 |

## Selection

The tuning comparison retains `baseline`. The transferred tuning increases energy by 2.604% and has earlier first-node death in all three seeds. It is not promoted. Grid attenuation variants remain available and unchanged.

The energy-preserving promotion rule selects `baseline`. Density fitness remains explicit opt-in when no variant meets that rule. Its lifetime/energy tradeoff is reported rather than described as an energy improvement.

## Fitness calculation

Use structural grid density `D_i = F_i dot density` before candidate CH coverage loss. Normalize D_i by the median positive live-sensor density. With evaluated consumption e_i and pre-round residual energy r_i, define:

`P = max_i [(e_i/r_i) * (1 + kappa/(1 + D_i/median(D_positive)))] / (E_total/sum(r_i))`

Add `lambda * P` to existing energy/CV fitness. All live sensors, including members and relays, are included. `risk_control` uses lambda=0.10, kappa=0; `density_005` and `density_010` use kappa=1 and lambda=0.05/0.10. The same score guides selection and pheromone reinforcement.

The scarcity multiplier changes both spatial weighting and overall penalty magnitude. The control removes that multiplier; it does not match the mean penalty magnitude. These results therefore do not isolate scarcity geometry from penalty strength. The candidate energy normalization in P also means a more expensive tree can reduce its relative concentration score; the separate energy term continues to penalize that cost.

## Paired changes versus selected base

| Configuration | First-node-death changes | Service changes | Energy changes |
| --- | --- | --- | --- |
| baseline | [0, 0, 0] | [0, 0, 0] | +0.000%, +0.000%, +0.000% |
| tuned | [-86, -28, -33] | [-21, 26, -2] | +2.748%, +2.670%, +2.393% |
| risk_control | [634, 663, 656] | [168, 207, 194] | +3.485%, +3.270%, +3.157% |
| density_005 | [630, 647, 658] | [193, 178, 214] | +2.387%, +2.408%, +2.346% |
| density_010 | [660, 692, 674] | [158, 198, 189] | +5.128%, +4.585%, +4.661% |

To enable the low-weight density option, set `DACOParameters().density_load_weight = 0.05` on the parameter instance passed to DACO. `density_load_kappa=1` is already the default. Set weight zero to retain prior fitness. Do not substitute remaining CH-coverage density.

First-node death and completed service are different metrics. HND/LND can remain censored when complete routing fails with most sensors alive. Three seeds on one map establish a paired comparison here, not a general deployment guarantee.

Raw records, parameters, deaths, residual energy, counters, and source/map hashes are in `full/`. The fresh baseline matches all three historical phase-7 trajectories exactly.

---

Historical source: `plans/phase9-daco-power/RESULTS.md`. Its implementation and defaults may differ from current production.

# Full D-ACO: powered load/density with live pheromone

Fifteen new full trials: three paired seeds 15/16/17 for five configurations. Six completed historical full trajectories supply old baseline and max-penalty references. All use the current 100-sensor map and 3000-round horizon or normal termination. Only D-ACO is simulated; all physical rounds use one batch of 40 ants.

`P = mean((consumption/residual)^p / max(structural_grid_density, epsilon))`

`F = total_energy + weight * E_ref * P/P_ref`

Ant and elite use the same cached F and frozen per-round E_ref. Pheromone is always live. A throwaway initial batch estimates E_ref and P_ref; it consumes computation and RNG, but no simulated energy, deposits, or physical round. Reference updates after the round are geometric: previous^0.8 * observed^0.2. Evaporation occurs once before physical ants; the elite bonus follows their live deposits.

Energy comparisons use the same first 1617 rounds with all sensors alive. Historical references did not have the new calibration batch or live policy. The energy_live control separates that policy change from adding powered load/density.

| Configuration | Mean FND | Mean service | All-alive energy change | Mean attempts, including calibration |
| --- | ---: | ---: | ---: | ---: |
| old_baseline | 1658.3 | 2190.7 | +0.000% | 185662 |
| old_max_005 | 2303.3 | 2385.7 | +2.411% | 120224 |
| energy_live | 1626.0 | 2160.7 | +0.191% | 181169 |
| linear_load | 1659.7 | 2189.7 | +0.272% | 179539 |
| power_010 | 1784.3 | 2263.7 | +0.466% | 181778 |
| power_025 | 1896.7 | 2318.0 | +0.601% | 178841 |
| power_100 | 2081.3 | 2366.7 | +1.834% | 158323 |

CPU includes calibration and the terminal failed search, but hardware frequency and concurrent scheduling are uncontrolled. Attempt counts are a more stable measure of work. Full-survivor service failure does not mean all sensors died; HND/LND may be censored. Three seeds on one map are not deployment-wide validation.

Q stays fixed when changing the objective multiplier. A larger multiplier also reduces inverse-fitness deposit magnitudes; these trials measure the complete policy, not an objective-weight change with total reinforcement mass held constant.

The old CV/max objectives and mode switches are removed from production, not deleted from historical evidence. Their code lives only in archive; its original hashes and first-ten-round replay match the six references. All grid decay options remain. AC-ACO and the sibling uwsn source are unchanged in this phase.

## Selected production default

Use load_power=2, load_density_weight=0.25, reference_memory=0.8. This is a deliberate energy/lifetime compromise: mean first-node death 1896.7 and mean service 2318.0, versus 1658.3 and 2190.7 for the old baseline. Energy rises 0.601% over equal all-alive rounds. Paired service gains are +101/+135/+146, and paired first-death gains +209/+267/+239.

Weight 0.10 gives 2263.7 mean service rounds for +0.466% energy; moving to 0.25 adds 54.3 rounds at only 0.135 percentage points more energy. Moving from 0.25 to 1.0 adds a further 48.7 service rounds but raises energy by another 1.232 percentage points relative to baseline. Weight 1.0 remains available.

The old max-penalty reference still gives later first-node death and slightly more service than the new weight-1.0 case, at a larger energy cost. The new policy is not uniformly superior to max. The clean p=1 versus p=2 comparison at weight 0.10 shows the exponent improves lifetime within the new framework.

The default was promoted after all runs finished. Raw source hashes describe the tested prototype default; its explicit power_025 parameter set matches the promoted default. The experiment base is now explicitly frozen at 0.10 to prevent labels changing when production defaults change.

---

Historical source: `plans/phase10-daco-vs-pheromone/RESULTS.md`. Its implementation and defaults may differ from current production.

# Current D-ACO versus pheromone-only SimpleACO

Six fresh full trajectories on the current map; paired seeds 24, 25, 26. Both use 40 ants, at most 10 feasibility attempts per ant, one batch per round, 20% cluster heads, and the same multi-hop routing and physical energy evaluator.

Map: 100 sensors, 500 × 500 × 500 m, radius 200 m, initial energy 0.6 J/node, sink (250, 250, 0). Map SHA-256: `d9e086fde395ff10a4348122727bc2af6972dffa25d5f92afa37ed0d56ca4b05`.

D-ACO uses the current defaults: quadratic relative depletion divided by structural grid density, weight 0.25, geometric reference memory 0.8, live node pheromone, and 40 initial throwaway calibration ants. SimpleACO explicitly uses beta=gamma=0: its cluster-head sampling weights are pheromone^alpha. Its candidate selection and pheromone reinforcement still use evaluated physical energy. Routing also retains its ordinary distance and residual-energy inputs.

All other algorithm parameters retain their own current defaults. This compares the two implementations; it does not isolate a single heuristic or fitness change.

| Metric (mean of 3 seeds) | D-ACO | SimpleACO, pheromone only | D-ACO difference |
|---|---:|---:|---:|
| First node death (round) | 2675.000 | 2636.000 | +1.48% |
| Completed service rounds | 2747.333 | 2936.000 | -6.43% |
| Energy, first 2611 rounds (J; all nodes alive) | 43.648 | 42.466 | +2.78% |
| Energy, first 2730 rounds (J; includes deaths) | 45.759 | 44.370 | +3.13% |
| Process CPU time (s) | 307.755 | 290.594 | +5.91% |
| Process CPU seconds / completed round | 0.112 | 0.099 | +13.18% |
| Clustering attempts / completed round | 40.160 | 41.974 | -4.32% |
| Routing attempts / completed round | 40.160 | 41.974 | -4.32% |

| Seed | D-ACO FND | SimpleACO FND | D-ACO service | SimpleACO service |
|---|---:|---:|---:|---:|
| 24 | 2692 | 2657 | 2730 | 2938 |
| 25 | 2675 | 2639 | 2750 | 2938 |
| 26 | 2658 | 2612 | 2762 | 2932 |

The configured horizon is 3000 rounds. Horizon runs give only a lower bound on service lifetime. A stop for no feasible complete routing tree is distinct from every sensor dying. FND/HND/LND remain censored when absent in raw trajectories.

Runtime includes constructor work and calibration. Three seed processes ran concurrently, so CPU measurements are indicative; attempt counts are the more robust search-cost comparison. Seeds share starting randomness, but different algorithms consume the RNG differently. Three seeds on one map do not establish performance across deployments.

Checks: every selected tree covered exactly the live nodes, all costs were finite and nonnegative with positive total energy, and source/map hashes stayed unchanged through each run. Raw results contain parameters, trajectories, death rounds, attempts, residual energy, and provenance. Production settings were not changed.

Run: `python -B plans/phase10-daco-vs-pheromone/full_run.py SEED` (24, 25, or 26), then `python -B plans/phase10-daco-vs-pheromone/report.py`.

## Interpretation

On this map, pheromone-only SimpleACO has lower energy cost and longer service in all three paired seeds. D-ACO postpones first death in all three seeds, but the mean improvement is only 39 rounds (+1.48%), while service is 188.67 rounds shorter (-6.43%) and all-alive energy is 2.78% higher. D-ACO uses fewer feasibility attempts per round, yet more CPU per round (+13.18%); its additional fitness and grid computations do not pay off in these outcomes. This is a comparison of the current complete policies, so it does not identify which individual D-ACO component causes the difference. No default was changed.

---

Historical source: `plans/phase11-daco-concentration/RESULTS.md`. Its implementation and defaults may differ from current production.

# Stronger D-ACO pheromone versus lighter heuristics

Twelve new full variant runs, three instrumented baseline replays, and three previously completed pheromone-only SimpleACO controls. Paired seeds: 24, 25, 26. Every source/map hash matches the phase-10 epoch. Each baseline replay reproduces the complete previous trajectory and final residual energies exactly.

Current D-ACO fitness, load power 2, load/density weight 0.25, reference memory 0.8, 40 calibration ants, evaporation, pheromone bounds [1,8], and all other controls remain fixed. Both heuristic exponents are scaled together. Q variants retain beta=0.9, gamma=0.4; heuristic variants retain Q=5. Fitness reference values continue to adapt normally to the sampled candidates. No production defaults changed.

Each round uses one batch of 40 ants, max 10 feasibility attempts per ant, 20% cluster heads, and the existing shared routing/physical energy model. The full horizon is 3000 rounds; runs stop normally if no complete tree is found.

Energy uses the same first **2611 rounds**, before any node dies in any trial. Lifetime numbers are completed service, distinct from all sensors dying.

| Variant | Q | beta / gamma | Mean first death | Mean service | Energy (J) | Energy vs baseline | Service vs baseline |
|---|---:|---|---:|---:|---:|---:|---:|
| Current D-ACO | 5 | 0.9 / 0.4 | 2675.00 | 2747.33 | 43.6483 | +0.00% | +0.00% |
| Deposits ×2 | 10 | 0.9 / 0.4 | 2674.00 | 2790.67 | 43.4428 | -0.47% | +1.58% |
| Deposits ×4 | 20 | 0.9 / 0.4 | 2742.67 | 2830.33 | 43.4092 | -0.55% | +3.02% |
| Heuristics ×0.5 | 5 | 0.45 / 0.2 | 2734.33 | 2815.67 | 43.2557 | -0.90% | +2.49% |
| Heuristics ×0.25 | 5 | 0.225 / 0.1 | 2782.67 | 2938.00 | 43.1655 | -1.11% | +6.94% |
| SimpleACO, pheromone only | 0.07 | 0 / 0 | 2636.00 | 2936.00 | 42.4661 | -2.71% | +6.87% |

## Paired full results

| Variant | Seed | First death | Service | Terminal alive nodes | Stop |
|---|---:|---:|---:|---:|---|
| Current D-ACO | 24 | 2692 | 2730 | 97 | no_feasible_tree |
| Current D-ACO | 25 | 2675 | 2750 | 97 | no_feasible_tree |
| Current D-ACO | 26 | 2658 | 2762 | 97 | no_feasible_tree |
| Deposits ×2 | 24 | 2667 | 2794 | 97 | no_feasible_tree |
| Deposits ×2 | 25 | 2672 | 2787 | 97 | no_feasible_tree |
| Deposits ×2 | 26 | 2683 | 2791 | 97 | no_feasible_tree |
| Deposits ×4 | 24 | 2756 | 2841 | 97 | no_feasible_tree |
| Deposits ×4 | 25 | 2745 | 2820 | 97 | no_feasible_tree |
| Deposits ×4 | 26 | 2727 | 2830 | 97 | no_feasible_tree |
| Heuristics ×0.5 | 24 | 2728 | 2832 | 96 | no_feasible_tree |
| Heuristics ×0.5 | 25 | 2742 | 2798 | 97 | no_feasible_tree |
| Heuristics ×0.5 | 26 | 2733 | 2817 | 96 | no_feasible_tree |
| Heuristics ×0.25 | 24 | 2789 | 2951 | 92 | no_feasible_tree |
| Heuristics ×0.25 | 25 | 2774 | 2925 | 92 | no_feasible_tree |
| Heuristics ×0.25 | 26 | 2785 | 2938 | 92 | no_feasible_tree |
| SimpleACO, pheromone only | 24 | 2657 | 2938 | 91 | no_feasible_tree |
| SimpleACO, pheromone only | 25 | 2639 | 2938 | 90 | no_feasible_tree |
| SimpleACO, pheromone only | 26 | 2612 | 2932 | 91 | no_feasible_tree |

## Pheromone saturation and search cost

Diagnostics below use the same first 2611 all-alive rounds. Cap fraction is the fraction of live nodes at tau_max after the elite deposit. Clipped updates count individual node deposits that exceeded the bound; lost mass is the fraction of requested deposit removed by clipping. These describe actual updates, not just the nominal Q multiplier.

| D-ACO variant | Mean nodes at cap | Clipped updates | Lost deposit mass | Mean tau range | CPU s / round | Attempts / round |
|---|---:|---:|---:|---:|---:|---:|
| Current D-ACO | 2.26% | 0.80% | 1.08% | 5.068 | 0.3299 | 40.160 |
| Deposits ×2 | 16.93% | 7.20% | 8.27% | 6.917 | 0.3277 | 40.158 |
| Deposits ×4 | 54.66% | 29.57% | 30.67% | 6.754 | 0.3245 | 40.155 |
| Heuristics ×0.5 | 1.05% | 0.29% | 0.41% | 4.546 | 0.2489 | 40.156 |
| Heuristics ×0.25 | 0.55% | 0.13% | 0.19% | 4.295 | 0.2454 | 41.259 |

Raw trajectories also record within-round log-score component ranges. Those ranges pool different selection steps and should not be interpreted as an exact probability concentration or a causal dominance measure.

CPU includes constructor/calibration and diagnostic overhead. Concurrent processes make timing indicative; baseline and D-ACO variants share instrumentation, whereas the reused SimpleACO timings do not. The deposit/control wave had up to nine concurrent tasks; the heuristic wave mostly had six. CPU-time differences between these waves cannot be attributed to the parameter changes. Attempt counts are a more robust search-budget measure. Three seeds on one map do not establish general deployment performance.

Checks: every selected tree covered exactly the live nodes; all physical costs were finite, nonnegative, and positive in total; source/map hashes remained unchanged through each run; each variant changes only its declared controls; the three complete baseline replays match the previously saved outcomes.


## Interpretation

Quartering the heuristic exponents (beta=0.225, gamma=0.1, Q=5) is the best tested D-ACO variant on mean first death, service, and equal-round energy. Against current D-ACO, it delays first death by 107.67 rounds (+4.02%), adds 190.67 service rounds (+6.94%), and reduces all-alive energy by 1.11%. Each paired seed improves these three outcomes against the baseline.

Against pheromone-only SimpleACO, quarter weights give essentially the same service: 2938 versus 2936 mean rounds. The paired service differences are +13, -13, and +6 rounds, so this is not persuasive evidence of better service than SimpleACO. First death is later by 146.67 rounds (+5.56%), at 1.65% more all-alive energy.

Stronger deposits also help service and energy, but less: Q=10 adds 1.58% service with 0.47% lower energy; Q=20 adds 3.02% service with 0.55% lower energy. With Q=20, an average 54.66% of live nodes are at the cap after a round, and 30.67% of requested deposit mass is clipped over the common all-alive interval. It still improves outcomes, so saturation does not make the larger Q ineffective; it limits how much extra deposit is retained.

The tested results favor lighter heuristics over increasing Q alone. They support this parameter direction for this map, without establishing a universal optimum or proving a local-search mechanism. Production defaults remain unchanged: beta=0.9, gamma=0.4, Q=5.

---

Historical source: `plans/phase12-daco-higher-cap/RESULTS.md`. Its implementation and defaults may differ from current production.

# Higher D-ACO pheromone bounds and deposits

Nine fresh full trials: deposits ×4 (Q=20) with tau_max=32, deposits ×6 (Q=30) with tau_max=8, and deposits ×6 with tau_max=32. Three paired seeds per case (24,25,26), normal 3000-round horizon. Previously completed current D-ACO, ×4/cap-8, quarter-heuristic, and pheromone-only SimpleACO controls are reused only after verifying exact source/map epoch matches.

New variants retain beta=0.9, gamma=0.4, alpha=1, tau_min=tau0=1, the existing evaporation schedule, fitness formula and parameters, geometric normalization, 40 calibration ants, and live per-ant pheromone. No production defaults changed. Each physical round has one batch of 40 ants and at most 10 feasibility attempts per ant, with identical routing and physics.

The high cap is 32 versus the current 8. It is held fixed for ×4 and ×6 so that their difference isolates deposit strength; ×6/cap-8 provides a matching control for the ceiling change.

Energy below uses the same first **2611 all-alive rounds** across every case. Completed service stops when no complete route is found or the horizon is reached; this is distinct from all nodes dying. Horizon-censored results are flagged in the per-seed table and only give lower bounds on lifetime.

| Variant | Q | Upper bound | beta / gamma | Mean first death | Mean completed service | Energy (J) | Energy vs baseline |
|---|---:|---:|---|---:|---:|---:|---:|
| Current D-ACO | 5 | 8 | 0.9 / 0.4 | 2675.00 | 2747.33 | 43.6483 | +0.00% |
| Deposits ×4, cap 8 | 20 | 8 | 0.9 / 0.4 | 2742.67 | 2830.33 | 43.4092 | -0.55% |
| Deposits ×4, cap 32 | 20 | 32 | 0.9 / 0.4 | 2638.67 | 2702.33 | 43.7611 | +0.26% |
| Deposits ×6, cap 8 | 30 | 8 | 0.9 / 0.4 | 2761.00 | 2849.00 | 43.4038 | -0.56% |
| Deposits ×6, cap 32 | 30 | 32 | 0.9 / 0.4 | 2644.33 | 2733.67 | 43.6668 | +0.04% |
| Quarter heuristics, cap 8 | 5 | 8 | 0.225 / 0.1 | 2782.67 | 2938.00 | 43.1655 | -1.11% |
| SimpleACO, pheromone only | 0.07 | 10 | 0 / 0 | 2636.00 | 2936.00 | 42.4661 | -2.71% |

## Controlled comparisons

| Comparison | Completed service difference | Equal-round energy difference |
|---|---:|---:|
| Deposits ×4, cap 32 vs Deposits ×4, cap 8 | -4.52% | +0.81% |
| Deposits ×6, cap 32 vs Deposits ×6, cap 8 | -4.05% | +0.61% |
| Deposits ×6, cap 32 vs Deposits ×4, cap 32 | +1.16% | -0.22% |

## Saturation

Measured over the common first 2611 all-alive rounds. Cap fraction counts live nodes at the upper bound after the round. Clipped updates count individual node deposits; lost mass is the fraction of requested deposit discarded by the cap.

| Variant | Mean nodes at cap | Clipped updates | Lost deposit mass | Mean maximum tau | Mean tau range |
|---|---:|---:|---:|---:|---:|
| Current D-ACO | 2.26% | 0.80% | 1.08% | 6.125 | 5.068 |
| Deposits ×4, cap 8 | 54.66% | 29.57% | 30.67% | 8.000 | 6.754 |
| Deposits ×4, cap 32 | 2.50% | 0.89% | 1.21% | 26.555 | 25.528 |
| Deposits ×6, cap 8 | 76.31% | 48.32% | 47.93% | 8.000 | 5.887 |
| Deposits ×6, cap 32 | 8.59% | 3.38% | 4.14% | 31.086 | 30.026 |
| Quarter heuristics, cap 8 | 0.55% | 0.13% | 0.19% | 5.416 | 4.295 |

## Per-seed trajectories

| Variant | Seed | First death | Completed service | Alive at stop | Termination |
|---|---:|---:|---:|---:|---|
| Current D-ACO | 24 | 2692 | 2730 | 97 | no_feasible_tree |
| Current D-ACO | 25 | 2675 | 2750 | 97 | no_feasible_tree |
| Current D-ACO | 26 | 2658 | 2762 | 97 | no_feasible_tree |
| Deposits ×4, cap 8 | 24 | 2756 | 2841 | 97 | no_feasible_tree |
| Deposits ×4, cap 8 | 25 | 2745 | 2820 | 97 | no_feasible_tree |
| Deposits ×4, cap 8 | 26 | 2727 | 2830 | 97 | no_feasible_tree |
| Deposits ×4, cap 32 | 24 | 2644 | 2707 | 97 | no_feasible_tree |
| Deposits ×4, cap 32 | 25 | 2633 | 2691 | 97 | no_feasible_tree |
| Deposits ×4, cap 32 | 26 | 2639 | 2709 | 97 | no_feasible_tree |
| Deposits ×6, cap 8 | 24 | 2766 | 2840 | 97 | no_feasible_tree |
| Deposits ×6, cap 8 | 25 | 2780 | 2866 | 97 | no_feasible_tree |
| Deposits ×6, cap 8 | 26 | 2737 | 2841 | 97 | no_feasible_tree |
| Deposits ×6, cap 32 | 24 | 2650 | 2734 | 97 | no_feasible_tree |
| Deposits ×6, cap 32 | 25 | 2647 | 2748 | 97 | no_feasible_tree |
| Deposits ×6, cap 32 | 26 | 2636 | 2719 | 97 | no_feasible_tree |
| Quarter heuristics, cap 8 | 24 | 2789 | 2951 | 92 | no_feasible_tree |
| Quarter heuristics, cap 8 | 25 | 2774 | 2925 | 92 | no_feasible_tree |
| Quarter heuristics, cap 8 | 26 | 2785 | 2938 | 92 | no_feasible_tree |
| SimpleACO, pheromone only | 24 | 2657 | 2938 | 91 | no_feasible_tree |
| SimpleACO, pheromone only | 25 | 2639 | 2938 | 90 | no_feasible_tree |
| SimpleACO, pheromone only | 26 | 2612 | 2932 | 91 | no_feasible_tree |

All selected trees covered exactly the live nodes, every physical cost was finite/nonnegative with positive total energy, and source/map hashes remained unchanged through each run. Diagnostic instrumentation is identical to the phase-11 observer, whose three complete baseline replays reproduced the original results exactly. The new driver and underlying runner hashes are recorded in every result.

Nine concurrent trial processes ran in this phase. Stored CPU measurements include diagnostic overhead and are not a controlled speed comparison against the earlier waves or uninstrumented SimpleACO. Three seeds on one map support conclusions for this tested deployment, not a universal optimum.


## Interpretation

Raising the ceiling from 8 to 32 worsens first death, service, and equal-round energy for every paired seed at both Q=20 and Q=30. At Q=20, the higher cap loses 128 service rounds (-4.52%) and uses 0.81% more energy. At Q=30, it loses 115.33 service rounds (-4.05%) and uses 0.61% more energy.

The higher ceiling removes most clipping: for Q=20, discarded deposit mass falls from 30.67% to 1.21%; for Q=30, it falls from 47.93% to 4.14%. Therefore clipping was not simply preventing a beneficial stronger-deposit policy. Less clipping and a wider pheromone range do not imply better search in this configuration. These outcomes support keeping the tested cap at 8; they do not identify the detailed failure mechanism.

Q=30/cap-8 improves mean service by 18.67 rounds (+0.66%) over Q=20/cap-8, while energy is effectively unchanged (-0.012%). The paired service differences are -1, +46, and +11 rounds, so this small mean gain is not a consistent improvement in every seed. Relative to current D-ACO, Q=30/cap-8 adds 3.70% service and uses 0.56% less all-alive energy.

Quarter heuristics remain the best tested D-ACO variant on the three mean outcomes: first death 2782.67, service 2938, and energy 43.1655 J. In comparison, Q=30/cap-8 gives 2761, 2849, and 43.4038 J. Production defaults remain unchanged; the cap-32 variants are not adopted.