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
