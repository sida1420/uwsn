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

Reproduce: `python -B plans/phase12-daco-higher-cap/full_run.py NAME SEED` (names deposit_4x_cap32, deposit_6x_cap8, deposit_6x_cap32; seeds 24/25/26), then `python -B plans/phase12-daco-higher-cap/report.py`.

## Interpretation

Raising the ceiling from 8 to 32 worsens first death, service, and equal-round energy for every paired seed at both Q=20 and Q=30. At Q=20, the higher cap loses 128 service rounds (-4.52%) and uses 0.81% more energy. At Q=30, it loses 115.33 service rounds (-4.05%) and uses 0.61% more energy.

The higher ceiling removes most clipping: for Q=20, discarded deposit mass falls from 30.67% to 1.21%; for Q=30, it falls from 47.93% to 4.14%. Therefore clipping was not simply preventing a beneficial stronger-deposit policy. Less clipping and a wider pheromone range do not imply better search in this configuration. These outcomes support keeping the tested cap at 8; they do not identify the detailed failure mechanism.

Q=30/cap-8 improves mean service by 18.67 rounds (+0.66%) over Q=20/cap-8, while energy is effectively unchanged (-0.012%). The paired service differences are -1, +46, and +11 rounds, so this small mean gain is not a consistent improvement in every seed. Relative to current D-ACO, Q=30/cap-8 adds 3.70% service and uses 0.56% less all-alive energy.

Quarter heuristics remain the best tested D-ACO variant on the three mean outcomes: first death 2782.67, service 2938, and energy 43.1655 J. In comparison, Q=30/cap-8 gives 2761, 2849, and 43.4038 J. Production defaults remain unchanged; the cap-32 variants are not adopted.
