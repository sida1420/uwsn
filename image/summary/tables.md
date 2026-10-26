### Lifetime, clustered N = 100 (extended run, T_max = 10000)

| Algorithm | Seeds | FND | HND | LND | Alive at end | Disconnected at end |
|---|---|---|---|---|---|---|
| D-ACO | 3.0 | 3,039 ± 302 | 4,662 ± 359 (2/3) | n.r. | 43.7 ± 16.4 | 43.3 ± 17.0 |
| AC-ACO | 1.0 | 2,269 | 4,301 | n.r. | 37.0 | 36.0 |
| SimpleACO | 3.0 | 2,043 ± 118 | 4,505 ± 256 (2/3) | n.r. | 48.3 ± 13.0 | 48.0 ± 13.5 |
| NodeACO | 2.0 | 2,060 ± 153 | 4,357 (1/2) | n.r. | 43.0 ± 11.3 | 42.5 ± 12.0 |
| PSO | 3.0 | 2,906 ± 358 | 4,558 (1/3) | n.r. | 47.3 ± 13.9 | 47.0 ± 14.4 |

### Strict repository rule, clustered N = 100 (T_max = 3500)

| Algorithm | FND | HND | LND | Completed rounds |
|---|---|---|---|---|
| D-ACO | 3,039 ± 302 | n.r. | n.r. | 3,264 ± 409 |
| AC-ACO | 2,269 | n.r. | n.r. | 3,500 |
| SimpleACO | 2,043 ± 118 | n.r. | n.r. | 3,222 ± 425 |
| NodeACO | 2,060 ± 153 | n.r. | n.r. | 3,046 ± 641 |
| PSO | 2,906 ± 358 | n.r. | n.r. | 3,269 ± 400 |

### Energy, clustered N = 100

| Algorithm | Cum. E @1000 (J) | Cum. E @2000 (J) | Cum. E @3500 (J) | Cum. E @FND (J) | Rounds/J to FND | Total consumed (J) | CV per-sensor E |
|---|---|---|---|---|---|---|---|
| D-ACO | 13.096 ± 0.599 | 26.279 ± 0.896 | 45.982 ± 0.712 | 40.095 ± 3.264 | 75.7 ± 1.7 | 53.69 ± 3.52 | 0.167 ± 0.063 |
| AC-ACO | 14.836 | 29.840 | 51.214 | 33.871 | 67.0 | 56.87 | 0.088 |
| SimpleACO | 14.354 ± 0.629 | 28.631 ± 1.247 | 48.688 ± 1.802 | 29.201 ± 0.402 | 69.9 ± 3.1 | 53.67 ± 3.34 | 0.151 ± 0.048 |
| NodeACO | 14.708 ± 0.522 | 29.363 ± 0.571 | 50.145 ± 0.462 | 30.246 ± 1.673 | 68.1 ± 1.3 | 55.65 ± 2.76 | 0.119 ± 0.068 |
| PSO | 13.092 ± 0.513 | 26.586 ± 0.998 | 46.443 ± 1.172 | 38.977 ± 4.718 | 74.6 ± 2.6 | 53.45 ± 2.55 | 0.161 ± 0.043 |

### FND / HND / LND vs. number of nodes (clustered)

| N | Algorithm | Seeds | FND | HND | LND | Strict completed rounds |
|---|---|---|---|---|---|---|
| 50 | D-ACO | 1.0 | 1,110 | 3,893 | n.r. | 1,110 |
| 100 | D-ACO | 3.0 | 3,039 ± 302 | 4,662 ± 359 (2/3) | n.r. | 3,264 ± 409 |
| 100 | AC-ACO | 1.0 | 2,269 | 4,301 | n.r. | 3,500 |
| 100 | SimpleACO | 3.0 | 2,043 ± 118 | 4,505 ± 256 (2/3) | n.r. | 3,222 ± 425 |
| 100 | NodeACO | 2.0 | 2,060 ± 153 | 4,357 (1/2) | n.r. | 3,046 ± 641 |
| 100 | PSO | 3.0 | 2,906 ± 358 | 4,558 (1/3) | n.r. | 3,269 ± 400 |

### Energy vs. number of nodes (clustered)

| N | Algorithm | Cum. E @1000 (J) | Cum. E @FND (J) | Rounds/J to FND | CV per-sensor E | Balance error (J) |
|---|---|---|---|---|---|---|
| 50 | D-ACO | 7.267 | 8.064 | 137.6 | 0.233 | -0.0 |
| 100 | D-ACO | 13.096 ± 0.599 | 40.095 ± 3.264 | 75.7 ± 1.7 | 0.167 ± 0.063 | -0.0 ± 0.0 |
| 100 | AC-ACO | 14.836 | 33.871 | 67.0 | 0.088 | 0.0 |
| 100 | SimpleACO | 14.354 ± 0.629 | 29.201 ± 0.402 | 69.9 ± 3.1 | 0.151 ± 0.048 | 0.0 ± 0.0 |
| 100 | NodeACO | 14.708 ± 0.522 | 30.246 ± 1.673 | 68.1 ± 1.3 | 0.119 ± 0.068 | 0.0 ± 0.0 |
| 100 | PSO | 13.092 ± 0.513 | 38.977 ± 4.718 | 74.6 ± 2.6 | 0.161 ± 0.043 | 0.0 ± 0.0 |

### Runtime

| Deployment | N | Algorithm | Runs | Wall time (s) | Time/round (s) | Mean CHs (rounds 1-1000) |
|---|---|---|---|---|---|---|
| clustered | 50 | D-ACO | 1.0 | 45 | 0.0045 | 10.0 |
| clustered | 100 | D-ACO | 3.0 | 351 ± 24 | 0.0510 ± 0.0146 | 20.0 ± 0.0 |
| clustered | 100 | AC-ACO | 1.0 | 584 | 0.0584 | 20.0 |
| clustered | 100 | SimpleACO | 3.0 | 354 ± 27 | 0.0528 ± 0.0231 | 20.0 ± 0.0 |
| clustered | 100 | NodeACO | 2.0 | 400 ± 82 | 0.0656 ± 0.0444 | 20.0 ± 0.0 |
| clustered | 100 | PSO | 3.0 | 343 ± 33 | 0.0469 ± 0.0110 | 20.0 ± 0.0 |

### Paired Wilcoxon signed-rank tests, D-ACO vs. each algorithm (all maps pooled)

| Compared with | Metric | Paired maps | D-ACO better | Median D-ACO | Median other | p (two-sided) |
|---|---|---|---|---|---|---|
| AC-ACO | FND | 1 | 1/1 | 3,375.000 | 2,269.000 | 1 |
| AC-ACO | HND | 1 | 1/1 | 4,409.000 | 4,301.000 | 1 |
| AC-ACO | cumulative_energy_r1000 | 1 | 1/1 | 12.465 | 14.836 | 1 |
| AC-ACO | rounds_per_joule_to_FND | 1 | 1/1 | 76.998 | 66.989 | 1 |
| AC-ACO | sensor_energy_cv | 1 | 0/1 | 0.098 | 0.088 | 1 |
| NodeACO | FND | 2 | 2/2 | 3,083.000 | 2,059.500 | 0.371 |
| NodeACO | HND | 1 | 1/1 | 4,409.000 | 4,357.000 | 1 |
| NodeACO | cumulative_energy_r1000 | 2 | 2/2 | 13.061 | 14.708 | 0.371 |
| NodeACO | rounds_per_joule_to_FND | 2 | 2/2 | 75.412 | 68.055 | 0.371 |
| NodeACO | sensor_energy_cv | 2 | 0/2 | 0.138 | 0.119 | 0.371 |
| PSO | FND | 3 | 2/3 | 2,951.000 | 2,804.000 | 0.423 |
| PSO | HND | 1 | 0/1 | 4,409.000 | 4,558.000 | 1 |
| PSO | cumulative_energy_r1000 | 3 | 1/3 | 13.167 | 13.137 | 1.21 |
| PSO | rounds_per_joule_to_FND | 3 | 3/3 | 76.355 | 75.775 | 0.181 |
| PSO | sensor_energy_cv | 3 | 2/3 | 0.178 | 0.177 | 1.21 |
| SimpleACO | FND | 3 | 3/3 | 2,951.000 | 2,016.000 | 0.181 |
| SimpleACO | HND | 2 | 2/2 | 4,662.500 | 4,505.000 | 0.371 |
| SimpleACO | cumulative_energy_r1000 | 3 | 3/3 | 13.167 | 14.261 | 0.181 |
| SimpleACO | rounds_per_joule_to_FND | 3 | 3/3 | 76.355 | 69.538 | 0.181 |
| SimpleACO | sensor_energy_cv | 3 | 0/3 | 0.178 | 0.168 | 0.181 |
