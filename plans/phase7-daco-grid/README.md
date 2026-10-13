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
