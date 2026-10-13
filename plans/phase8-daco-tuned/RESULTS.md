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
