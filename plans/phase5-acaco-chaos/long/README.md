# Longer chaos validation

Historical scope: these runs used frozen per-round pheromone. The sampler now exposes earlier ants' deposits immediately; [the live balance study](../../phase5-acaco-balance/README.md) compares that change at matched states. These archived lifetime results are not measurements of the new live sampler.

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

Run `python -B plans/phase5-acaco-chaos/long_run.py` to run/reuse all pairs. `run_pair.py 7` and `run_pair.py 8` allow independent pairs to run concurrently; completed files are reused. Then run `math_probe.py` and `long_report.py`. Long-run source hashes must match the preceding amplitude study.

See [the mathematical analysis](MATH_ANALYSIS.md) for the exact mixing identity, coverage mechanism and limitations.
