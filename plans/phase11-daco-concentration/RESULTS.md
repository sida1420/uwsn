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

Reproduce: `python -B plans/phase11-daco-concentration/batch.py SEED GROUP` (seeds 24/25/26, groups a/b), `python -B plans/phase11-daco-concentration/replay_baseline.py SEED`, then `python -B plans/phase11-daco-concentration/report.py`.

## Interpretation

Quartering the heuristic exponents (beta=0.225, gamma=0.1, Q=5) is the best tested D-ACO variant on mean first death, service, and equal-round energy. Against current D-ACO, it delays first death by 107.67 rounds (+4.02%), adds 190.67 service rounds (+6.94%), and reduces all-alive energy by 1.11%. Each paired seed improves these three outcomes against the baseline.

Against pheromone-only SimpleACO, quarter weights give essentially the same service: 2938 versus 2936 mean rounds. The paired service differences are +13, -13, and +6 rounds, so this is not persuasive evidence of better service than SimpleACO. First death is later by 146.67 rounds (+5.56%), at 1.65% more all-alive energy.

Stronger deposits also help service and energy, but less: Q=10 adds 1.58% service with 0.47% lower energy; Q=20 adds 3.02% service with 0.55% lower energy. With Q=20, an average 54.66% of live nodes are at the cap after a round, and 30.67% of requested deposit mass is clipped over the common all-alive interval. It still improves outcomes, so saturation does not make the larger Q ineffective; it limits how much extra deposit is retained.

The tested results favor lighter heuristics over increasing Q alone. They support this parameter direction for this map, without establishing a universal optimum or proving a local-search mechanism. Production defaults remain unchanged: beta=0.9, gamma=0.4, Q=5.
