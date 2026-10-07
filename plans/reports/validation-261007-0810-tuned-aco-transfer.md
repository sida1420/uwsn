# Validation: tuned ACO vs old and updated AC-ACO

Seeds 0–4; original map; shared model; T_max=3000; 15 complete cases.

## First 100 completed rounds: matched service, all 100 nodes alive

| Seed | Tuned ACO J | Old AC-ACO J | New AC-ACO J | Lowest energy |
|---|---|---|---|---|
| 0 | 1.799589 | 1.669953 | 1.670455 | old |
| 1 | 1.807865 | 1.680235 | 1.674896 | new |
| 2 | 1.794040 | 1.677283 | 1.670038 | new |
| 3 | 1.781205 | 1.676027 | 1.670693 | new |
| 4 | 1.779087 | 1.673921 | 1.663170 | new |

| Algorithm | 100-round J: mean ± sample SD | Mean completed rounds | Mean final residual J |
|---|---|---|---|
| tuned | 1.792357 ± 0.012207 | 2279.2 | 19.741955 |
| old | 1.675484 ± 0.003845 | 2179.4 | 24.857014 |
| new | 1.669851 ± 0.004219 | 2184.0 | 24.884677 |

Updated AC-ACO uses 6.83% less matched-horizon energy than tuned ACO and 0.34% less than old AC-ACO. It beats old AC-ACO on energy in four of five seeds. The incremental gain is small; five seeds on one map do not establish general superiority. Tuned ACO sustains routing longer. The ACO pre-tuning control and isolated ablations in the companion audit also contradict a blanket claim that the latest ACO tuning reduces energy.

## Rejected total-mass chaos trial (not the final implementation)

Changing `(p+c)/(1+n*c)` to `(p+c/n)/(1+c)` sharply weakened exploration. Three completed seeds showed shorter service than tuned ACO; remaining trial seeds were stopped to free CPU. No result is imputed. The final patch preserves the original rule.

| Seed | Trial service rounds | Final AC-ACO service rounds | Tuned ACO service rounds | Trial 100-round J |
|---|---|---|---|---|
| 0 | 1831 | 2195 | 2210 | 1.692536 |
| 1 | 1740 | 2186 | 2327 | 1.708160 |
| 2 | 1629 | 2182 | 2335 | 1.689666 |

## Lifetime and energy at stopping

Completed rounds are service lifetime; first death uses a one-based completed-round count. Energy totals at unequal lifetimes are not an efficiency ranking. T_max means censored lifetime; no_feasible_route is failed full-network routing search within the algorithm's budget, not proof that the physical graph is disconnected.

| Seed | Algorithm | Rounds | First death | Alive at stop | Modeled J | Depleted J | Residual J | Stop |
|---|---|---|---|---|---|---|---|---|
| 0 | tuned | 2210 | 1420 | 99 | 38.920228 | 38.920064 | 21.079936 | no_feasible_route |
| 0 | old | 2173 | 1503 | 98 | 35.015842 | 35.015747 | 24.984253 | no_feasible_route |
| 0 | new | 2195 | 1487 | 98 | 35.358899 | 35.358423 | 24.641577 | no_feasible_route |
| 1 | tuned | 2327 | 1587 | 98 | 41.003644 | 41.003026 | 18.996974 | no_feasible_route |
| 1 | old | 2187 | 1508 | 98 | 35.250071 | 35.249697 | 24.750303 | no_feasible_route |
| 1 | new | 2186 | 1469 | 98 | 35.131265 | 35.130922 | 24.869078 | no_feasible_route |
| 2 | tuned | 2335 | 1484 | 95 | 41.251031 | 41.250218 | 18.749782 | no_feasible_route |
| 2 | old | 2173 | 1471 | 98 | 35.083911 | 35.083588 | 24.916412 | no_feasible_route |
| 2 | new | 2182 | 1511 | 98 | 35.090224 | 35.089677 | 24.910323 | no_feasible_route |
| 3 | tuned | 2240 | 1360 | 98 | 39.774957 | 39.774611 | 20.225389 | no_feasible_route |
| 3 | old | 2185 | 1523 | 98 | 35.195246 | 35.194893 | 24.805107 | no_feasible_route |
| 3 | new | 2182 | 1517 | 98 | 35.026680 | 35.026319 | 24.973681 | no_feasible_route |
| 4 | tuned | 2284 | 1445 | 98 | 40.342439 | 40.342306 | 19.657694 | no_feasible_route |
| 4 | old | 2179 | 1488 | 98 | 35.171251 | 35.171003 | 24.828997 | no_feasible_route |
| 4 | new | 2175 | 1502 | 98 | 34.971900 | 34.971276 | 25.028724 | no_feasible_route |

## Structure and accounting: five-seed means over first 100 rounds

| Metric (distances m, energy J/round) | tuned | old | new |
|---|---|---|---|
| ch_count | 20.000000 | 20.000000 | 20.000000 |
| node_ch_distance | 120.591268 | 106.270903 | 105.856045 |
| ch_bs_distance | 278.218398 | 297.074520 | 296.876769 |
| ch_parent_distance | 128.402121 | 143.341458 | 143.229326 |
| cluster_size_std | 2.832570 | 2.452393 | 2.418253 |
| unclustered_nodes | 8.758000 | 3.404000 | 3.558000 |
| tx_energy | 0.016459 | 0.015272 | 0.015219 |
| rx_energy | 0.001351 | 0.001370 | 0.001366 |
| aggregation_energy | 0.000113 | 0.000113 | 0.000113 |

Direct non-CH members per CH after routing; distribution is member-count:frequency.

| Algorithm | Cluster-size distribution |
|---|---|
| tuned | {"0":1388,"1":1379,"2":1416,"3":1484,"4":1147,"5":885,"6":770,"7":510,"8":347,"9":248,"10":181,"11":108,"12":72,"13":42,"14":16,"15":2,"16":4,"21":1} |
| old | {"0":531,"1":1282,"2":1498,"3":1811,"4":1398,"5":1171,"6":860,"7":600,"8":390,"9":192,"10":122,"11":74,"12":42,"13":18,"14":7,"15":2,"16":2} |
| new | {"0":516,"1":1237,"2":1514,"3":1824,"4":1496,"5":1189,"6":771,"7":614,"8":392,"9":210,"10":114,"11":62,"12":25,"13":27,"14":5,"15":3,"17":1} |

## Alive nodes by round

Stopped simulations are NA, not padded with zero deaths. Active-run means can be survivor-biased.

| Completed rounds | tuned | old | new |
|---|---|---|---|
| 1 | 100.00 (5/5 active) | 100.00 (5/5 active) | 100.00 (5/5 active) |
| 100 | 100.00 (5/5 active) | 100.00 (5/5 active) | 100.00 (5/5 active) |
| 500 | 100.00 (5/5 active) | 100.00 (5/5 active) | 100.00 (5/5 active) |
| 1000 | 100.00 (5/5 active) | 100.00 (5/5 active) | 100.00 (5/5 active) |
| 1500 | 99.20 (5/5 active) | 99.60 (5/5 active) | 99.60 (5/5 active) |
| 2000 | 99.00 (5/5 active) | 99.00 (5/5 active) | 99.00 (5/5 active) |
| 2500 | NA (0/5 active) | NA (0/5 active) | NA (0/5 active) |
| 3000 | NA (0/5 active) | NA (0/5 active) | NA (0/5 active) |

## Objective / within-round convergence

Fitness is total raw tree energy in joules. Mean best-so-far candidate cost over first 100 rounds; 40 candidates per round for all cases. There is no inner optimizer iteration or early-convergence rule.

| Feasible ants evaluated | tuned | old | new |
|---|---|---|---|
| 1 | 0.021780 | 0.019237 | 0.019247 |
| 10 | 0.018724 | 0.017307 | 0.017312 |
| 20 | 0.018279 | 0.016993 | 0.016985 |
| 40 | 0.017924 | 0.016755 | 0.016699 |

## Mechanisms exercised in real lifetime trajectories

| Algorithm | Adaptive beta range | Adaptive rho range | Chaos strength range | Rounds with logistic state change |
|---|---|---|---|---|
| old | 1.000..5.000 | 0.317..0.900 | 0.050000..0.108873 | 10897/10897 |
| new | 1.000..5.000 | 0.315..0.900 | 0.050000..0.108966 | 10920/10920 |

Both probability chaos and pheromone chaos execute with positive strength; targeted tests verify each changes its respective values. Full traces include round-level controls and logistic-change flags.

## Reproduction and files

```powershell
C:\Users\LOQ\miniconda3\python.exe -B plans/reports/aco-transfer-261007-0810/compare.py
C:\Users\LOQ\miniconda3\python.exe -B plans/reports/aco-transfer-261007-0810/summarize.py
```

`results/lifetime/{tuned,old}-*.json.gz` and `results/final/new-*.json.gz`: compressed per-round energy/residual/alive/cluster/candidate/convergence/control data. `summary.csv`: per-seed endpoints; `comparison.png`: four-panel figure; `baseline/*.py`: exact pre-edit AC-ACO source. `results/audit/*.json.gz`: ablations.

[Audit and full mapping](audit-261007-0810-tuned-aco-transfer.md) · [Comparison figure](aco-transfer-261007-0810/comparison.png) · [Endpoint CSV](aco-transfer-261007-0810/summary.csv) · [Source/version manifest](aco-transfer-261007-0810/manifest.json)
