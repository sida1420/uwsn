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
