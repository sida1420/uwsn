# Full D-ACO: powered load/density with live pheromone

Fifteen new full trials: three paired seeds 15/16/17 for five configurations. Six completed historical full trajectories supply old baseline and max-penalty references. All use the current 100-sensor map and 3000-round horizon or normal termination. Only D-ACO is simulated; all physical rounds use one batch of 40 ants.

`P = mean((consumption/residual)^p / max(structural_grid_density, epsilon))`

`F = total_energy + weight * E_ref * P/P_ref`

Ant and elite use the same cached F and frozen per-round E_ref. Pheromone is always live. A throwaway initial batch estimates E_ref and P_ref; it consumes computation and RNG, but no simulated energy, deposits, or physical round. Reference updates after the round are geometric: previous^0.8 * observed^0.2. Evaporation occurs once before physical ants; the elite bonus follows their live deposits.

Energy comparisons use the same first 1617 rounds with all sensors alive. Historical references did not have the new calibration batch or live policy. The energy_live control separates that policy change from adding powered load/density.

| Configuration | Mean FND | Mean service | All-alive energy change | Mean attempts, including calibration |
| --- | ---: | ---: | ---: | ---: |
| old_baseline | 1658.3 | 2190.7 | +0.000% | 185662 |
| old_max_005 | 2303.3 | 2385.7 | +2.411% | 120224 |
| energy_live | 1626.0 | 2160.7 | +0.191% | 181169 |
| linear_load | 1659.7 | 2189.7 | +0.272% | 179539 |
| power_010 | 1784.3 | 2263.7 | +0.466% | 181778 |
| power_025 | 1896.7 | 2318.0 | +0.601% | 178841 |
| power_100 | 2081.3 | 2366.7 | +1.834% | 158323 |

CPU includes calibration and the terminal failed search, but hardware frequency and concurrent scheduling are uncontrolled. Attempt counts are a more stable measure of work. Full-survivor service failure does not mean all sensors died; HND/LND may be censored. Three seeds on one map are not deployment-wide validation.

Q stays fixed when changing the objective multiplier. A larger multiplier also reduces inverse-fitness deposit magnitudes; these trials measure the complete policy, not an objective-weight change with total reinforcement mass held constant.

The old CV/max objectives and mode switches are removed from production, not deleted from historical evidence. Their code lives only in archive; its original hashes and first-ten-round replay match the six references. All grid decay options remain. AC-ACO and the sibling uwsn source are unchanged in this phase.

## Selected production default

Use load_power=2, load_density_weight=0.25, reference_memory=0.8. This is a deliberate energy/lifetime compromise: mean first-node death 1896.7 and mean service 2318.0, versus 1658.3 and 2190.7 for the old baseline. Energy rises 0.601% over equal all-alive rounds. Paired service gains are +101/+135/+146, and paired first-death gains +209/+267/+239.

Weight 0.10 gives 2263.7 mean service rounds for +0.466% energy; moving to 0.25 adds 54.3 rounds at only 0.135 percentage points more energy. Moving from 0.25 to 1.0 adds a further 48.7 service rounds but raises energy by another 1.232 percentage points relative to baseline. Weight 1.0 remains available.

The old max-penalty reference still gives later first-node death and slightly more service than the new weight-1.0 case, at a larger energy cost. The new policy is not uniformly superior to max. The clean p=1 versus p=2 comparison at weight 0.10 shows the exponent improves lifetime within the new framework.

The default was promoted after all runs finished. Raw source hashes describe the tested prototype default; its explicit power_025 parameter set matches the promoted default. The experiment base is now explicitly frozen at 0.10 to prevent labels changing when production defaults change.
