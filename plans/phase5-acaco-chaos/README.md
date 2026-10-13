# Chaos after pheromone calibration - 2026-10-11

## Question and controlled design

Does reducing chaos behave differently after replacing Q=100, bounds [.1,10] and rho_max=.9 with Q=.01, bounds [.01,20] and rho_max=.6?

Both chaos_min and chaos_max are multiplied by 0, .25, .5, 1 or 2. The logistic r=3.61 and seed=.37 are fixed. Q, pheromone bounds, heuristic exponents, distance bias, CH proportion, routing, physics and search effort are fixed within each scale. Zero is an experimental ablation, not a proposed default.

Screening: two pheromone scales, five amplitudes, plus two calibrated mechanism ablations; 20 searches at unchanged physical state per seed (0/1/2), retaining optimizer memory. Validation: all five calibrated amplitudes, independent 150-round physical trajectories on fresh seeds 6/7/8, 40 ants per round. These seeds were unused in the previous calibration. All strengths were declared before validation; no selection-driven holdout retuning.

Schedule horizon stays 3000. Configuration order rotates by validation seed. CPU includes tree-signature instrumentation; post-search diagnostics are outside the measured search. Timings are indicative, not precise speed claims.

## Interaction with the old pheromone scale

| Chaos factor | Old scale mean energy, 20 searches (J) | Change vs old x1 | New scale mean energy (J) | Change vs new x1 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0.405826382 | +17.333% | 0.362587068 | +5.801% |
| 0.25 | 0.355105396 | +2.668% | 0.350036932 | +2.139% |
| 0.5 | 0.353283891 | +2.142% | 0.347601953 | +1.428% |
| 1 | 0.345876365 | +0.000% | 0.342707606 | +0.000% |
| 2 | 0.341238775 | -1.341% | 0.340234344 | -0.722% |

These are matched current-code controls, not an attempted reproduction of undocumented historical chaos results. The previous audits used different states/budgets; their numerical percentages cannot be compared directly.

## Independent 150-round trajectories

| Chaos factor | Strength bounds | Mean energy (J) | Change vs x1 | Mean minimum residual (J/node) | Mean clustering outliers | Mean CPU (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | [0, 0] | 2.611398390 | +4.512% | 0.542221 | 15.937 | 16.734 |
| 0.25 | [0.0125, 0.075] | 2.542109721 | +1.739% | 0.546534 | 7.395 | 13.266 |
| 0.5 | [0.025, 0.15] | 2.516974183 | +0.733% | 0.545481 | 5.987 | 13.984 |
| 1 | [0.05, 0.3] | 2.498649410 | +0.000% | 0.545228 | 5.063 | 13.458 |
| 2 | [0.1, 0.6] | 2.487085613 | -0.463% | 0.545461 | 4.572 | 14.714 |

| Seed | Off vs x1 | Quarter vs x1 | Half vs x1 | Double vs x1 |
| --- | ---: | ---: | ---: | ---: |
| 6 | +4.979% | +1.776% | +1.148% | -0.546% |
| 7 | +4.096% | +1.539% | +0.599% | -0.675% |
| 8 | +4.463% | +1.904% | +0.454% | -0.168% |

## Which mechanism matters?

| Calibrated fixed-state control | Mean energy (J) | Change vs full chaos | Mean clustering outliers | Diagnostic transition entropy |
| --- | ---: | ---: | ---: | ---: |
| calibrated_x1 | 0.342707606 | +0.000% | 4.984 | 0.977205 |
| calibrated_without_transition | 0.365259695 | +6.581% | 14.578 | 0.702622 |
| calibrated_without_pheromone | 0.343005298 | +0.087% | 5.071 | 0.973631 |
| calibrated_x0 | 0.362587068 | +5.801% | 15.752 | 0.646287 |

Chaos is used twice: additive mixing of transition probabilities and additive disturbance of pheromone updates. Experiment-local overrides disable each mechanism independently while preserving the logistic recurrence and all production code. These mechanism ablations are screening probes only, not validated lifetime interventions.

For transition probabilities, c = strength * chaos[source], and `p_new = (p + c)/(1+n*c) = (1-lambda)*p + lambda/n`, where `lambda = n*c/(1+n*c)`. Lower strength makes the sampler more concentrated on pheromone/local heuristics; higher strength spreads CH choices. On this map that changes clustering coverage and the costs faced by the shared router.

Clustering outliers are sensors beyond every selected CH radius; they still participate in multi-hop routing. They are not omitted or unserved sensors. Entropy is normalized by log(candidate count), averaged over hypothetical first transitions from the first ten live sources. Mixture share is a diagnostic average over live sources and 99..81 candidate counts; it is not an empirical average over the ants' sampled source frequencies.

## Verification, limits and decision

Completed 118,800 feasible full-tree evaluations. Actual calls and unique trees are recorded separately; unique trees do not replace the equal 40-evaluation search budget.
All measured rounds served every live sensor; no deaths were observed. Every selected tree is independently reevaluated. Tests verify instrumented control trajectories equal plain production trajectories and disabling both mechanisms equals zero-amplitude chaos. All 24 repository tests pass.

| Factor | Mean pheromone floor occupancy | Mean ceiling occupancy | Maximum relative one-round depletion |
| --- | ---: | ---: | ---: |
| 0 | 95.260% | 0.000% | 0.003415364 |
| 0.25 | 0.000% | 0.000% | 0.002224144 |
| 0.5 | 0.000% | 0.000% | 0.002179895 |
| 1 | 0.000% | 0.000% | 0.002492045 |
| 2 | 0.000% | 0.000% | 0.002246776 |

The doubled maximum disturbance remains within the reference late-round pheromone envelope: at route cost .015 J, minimum evaporation .1 and max chaos .6, the all-ant-plus-elite equilibrium bound is `((2-.1)*(.01/.015)+.6*(3.61/4))/.1 = 18.081667 < 20`. This reference cost is not a universal lower bound.

Retain production chaos bounds [.05,.30] for now. Higher amplitude is an opt-in candidate based on early energy, not a certified lifetime improvement. No source-code default is changed by this early study. Lifetime/FND outcomes and behavior around raw-beta transition at round 1500 are examined in the [longer follow-up](long/README.md), with a [mathematical analysis](long/MATH_ANALYSIS.md). Different topologies remain untested. No statistical-significance or global-optimality claim is supported by three seeds on one topology.

## Artifacts and reproduction

- `experiment.py`: explicit paired controls, mechanism interventions and instrumentation.
- `results.json`: all configurations, per-round/per-seed raw metrics, map/source/script fingerprints.
- `summarize.py`: regenerates this report.
- `higher-chaos-candidate.json`: full x2 configuration for opt-in follow-up.

From the repository root run `python -B plans/phase5-acaco-chaos/experiment.py`, then `python -B plans/phase5-acaco-chaos/summarize.py`. Matching saved runs are reused; move the results artifact for a fresh run.

Starting git SHA: `da40055a9f34a7c8ecf31f7a23736bb338098c1d`. Map SHA-256: `ebe729265598746b30af09715e239a9891b2ac95ac66656096dc712e6c34fdcc`.
