# Frozen reference: best-set balance and inner iterations

These are historical frozen-sampler controls. See [the live-sampler report](README.md) for the current implementation. Checkpoint states are independently deep-copied; the initial order-confounded screens were excluded and archived under `invalid-screen-state-alias/`.

## What current D-ACO does

The current D-ACO wrapper runs one ant batch per physical round, not a nested optimizer loop. It scores candidates by `.9 * energy / mean_energy + .1 * load_CV / mean_CV`, and gives the best set an additional pheromone multiplier `theta=.1`. Its pheromone belongs to CH nodes; AC-ACO pheromone belongs to CH-order transitions. AC-ACO currently selects by total energy and uses an elite multiplier of 1.

D-ACO deposits `Q/fitness`, whereas AC-ACO deposits `Q/physical_energy`. Copying the former denominator would change the calibrated scale drastically. This study tests the elite multiplier and candidate selection separately while retaining inverse-physical-energy deposits.

## Controlled design

Frozen screening uses RNG seeds 0/1/2 and 12 consecutive optimizer searches at each unchanged physical state. The states are the calibrated current-chaos seed-6 checkpoint after 600 rounds, and the exact state after node 33 dies at round 1510. The latter is recreated by replaying nine saved-state rounds and checking every cost against the prior trajectory. Each configuration starts from identical physical and optimizer state. Memory evolves during the 12 searches; energy is not deducted.

Independent validation uses fresh seeds 9/10/11 and 300 physical rounds per configuration. All seven configurations were declared before validation. The schedule horizon stays 3000. Configuration order rotates by seed. This is an early-trajectory comparison, not a lifetime/FND validation.

One iteration uses 40 ants. Split-2 and split-4 use 20x2 and 10x4 ants, respectively. Expanded-budget controls compare 80x1 versus 40x2, and 160x1 versus 40x4. Every ant retains the same ten-attempt limit. Actual feasible candidates and attempts are counted.

## Frozen screening

### Checkpoint 600

| Configuration | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Feasible candidates | Elite share of new mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | +0.000% | 1.00x | +0.000% | +0.000% | 40.00 | 69.59% |
| elite_off | +0.640% | 1.01x | -1.698% | -6.687% | 40.00 | 0.00% |
| elite_01 | +0.122% | 1.04x | -2.782% | -7.557% | 40.00 | 18.55% |
| elite_05 | +0.216% | 0.83x | -0.256% | -6.500% | 40.00 | 53.24% |
| fitness_cv | +0.419% | 0.86x | -3.692% | -7.951% | 40.00 | 69.45% |
| combined | +0.276% | 0.98x | -3.528% | -10.661% | 40.00 | 18.55% |
| split_2 | +0.464% | 1.06x | -1.263% | -7.460% | 40.00 | 69.32% |
| split_4 | +0.222% | 0.96x | +0.175% | -6.608% | 40.00 | 69.30% |
| batch_80 | -1.406% | 1.66x | -2.744% | -15.375% | 80.00 | 69.88% |
| inner_80 | -1.724% | 1.53x | -1.885% | -10.447% | 80.00 | 69.80% |
| batch_160 | -3.150% | 2.62x | -0.340% | -8.866% | 160.00 | 70.26% |
| inner_160 | -1.843% | 3.27x | -0.312% | -8.647% | 160.00 | 69.84% |
### Checkpoint 1510

| Configuration | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Feasible candidates | Elite share of new mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | +0.000% | 1.00x | +0.000% | +0.000% | 29.92 | 70.40% |
| elite_off | -0.137% | 1.31x | -1.717% | -3.678% | 30.47 | 0.00% |
| elite_01 | -0.195% | 1.28x | -0.804% | -5.990% | 31.36 | 18.51% |
| elite_05 | +0.175% | 1.45x | +1.954% | +3.171% | 30.22 | 53.97% |
| fitness_cv | +0.589% | 1.23x | -1.833% | -1.376% | 29.92 | 70.26% |
| combined | -0.232% | 1.13x | -1.934% | -3.944% | 30.78 | 18.80% |
| split_2 | -0.107% | 1.08x | -0.873% | -1.888% | 30.69 | 69.58% |
| split_4 | +0.044% | 1.14x | -2.152% | -0.988% | 31.28 | 69.11% |
| batch_80 | -1.464% | 2.05x | -2.082% | -7.015% | 61.44 | 70.14% |
| inner_80 | -1.297% | 1.36x | +0.905% | -0.643% | 62.31 | 69.70% |
| batch_160 | -2.958% | 3.68x | -0.572% | -3.837% | 122.14 | 70.60% |
| inner_160 | -3.141% | 3.55x | -1.963% | -5.427% | 121.56 | 70.47% |

## Fresh 300-round trajectories

| Configuration | Mean total energy (J) | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Node 33 final residual (J) | Node 65 final residual (J) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.919402522 | +0.000% | 1.00x | +0.000% | +0.000% | 0.494591 | 0.547585 |
| elite_01 | 4.913835830 | -0.113% | 1.33x | -0.009% | -0.028% | 0.496020 | 0.546825 |
| fitness_cv | 4.920330882 | +0.019% | 1.45x | -0.968% | -2.280% | 0.496156 | 0.548654 |
| combined | 4.929400695 | +0.203% | 1.51x | -1.688% | -2.875% | 0.496784 | 0.547814 |
| split_2 | 4.915485487 | -0.080% | 1.39x | -0.239% | -0.840% | 0.495438 | 0.548536 |
| batch_80 | 4.851383598 | -1.383% | 2.60x | +0.194% | -0.963% | 0.497021 | 0.549126 |
| inner_80 | 4.847483469 | -1.462% | 2.44x | -0.245% | -2.247% | 0.497651 | 0.548657 |

## Equal-budget effect of inner feedback

| Context | Inner / one-batch control | Energy change | CPU ratio |
| --- | --- | ---: | ---: |
| frozen 600 | split_2 / baseline | +0.464% | 1.06x |
| frozen 600 | split_4 / baseline | +0.222% | 0.96x |
| frozen 600 | inner_80 / batch_80 | -0.323% | 0.92x |
| frozen 600 | inner_160 / batch_160 | +1.350% | 1.25x |
| frozen 1510 | split_2 / baseline | -0.107% | 1.08x |
| frozen 1510 | split_4 / baseline | +0.044% | 1.14x |
| frozen 1510 | inner_80 / batch_80 | +0.169% | 0.66x |
| frozen 1510 | inner_160 / batch_160 | -0.189% | 0.97x |
| 300-round trajectories | split_2 / baseline | -0.080% | 1.39x |
| 300-round trajectories | inner_80 / batch_80 | -0.080% | 0.94x |

## Interpreting balance

Load CV is the standard deviation of absolute per-node round energy divided by its mean, matching D-ACO. It is different from residual-aware depletion. Peak relative depletion is `max_i(cost_i / residual_i)` and is measured independently. A lower CV can still burden a nearly exhausted critical node; total energy can rise when choosing a more uniform load. No FND or full-service gain is established by 300 rounds.

Elite mass shares refer to newly added ant and elite reinforcement after accounting for their remaining evaporation. They exclude existing pheromone and chaos, and are theoretical surviving additions before any clipping. CPU uses process time from the same instrumented runner, which calculates candidate load CV even for energy-only controls. Absolute timings are not bare-production benchmarks; ratios are indicative.

## Mathematical normalization of inner updates

For outer-round evaporation `rho` and `m` batches, use `rho_inner = 1-(1-rho)^(1/m)`. With `a=1-rho_inner`, the effective decay is `a^m=1-rho`. Use pheromone disturbance `c_inner=c*rho_inner/rho`, giving `sum(a^i*c_inner)=c`. Transition mixing retains the original outer strength, and the logistic state advances once after the final batch. Beta, evaporation progress and physical energy advance once per physical round.

For batch `b=0..m-1`, per-ant deposits divide by the total ant budget `B`, and are multiplied by `(1-rho)/a^(m-b)`. Their final survival therefore matches the single-update control. The best-so-far elite deposit per batch uses `theta / sum(a^i)`. For identical candidate costs and paths this preserves total elite reinforcement. Clipping or changing candidate quality can break exact mass equivalence, and are part of the measured optimizer behavior. This normalization isolates feedback within the round instead of simply increasing evaporation, logistic steps or deposit strength.

For a single batch with `K` CHs and `B` ants, surviving ant mass is `A=(1-rho)*(K-1)*Q/B*sum(1/E_ant)`, while elite mass is `G=(K_best-1)*theta*Q/E_best`. The elite share is `G/(A+G)`. For equal costs, all ants feasible and equal CH counts, it simplifies to `theta/(1-rho+theta)`. At rho=.6, theta=1 yields 71.43%, while theta=.1 yields 20%. A cheaper best candidate or fewer feasible ants increases its share. Thus a full-strength best-set deposit can outweigh all ordinary ants together.

## Verification and reproduction

All 37 tests passed. Experimental live configurations match production consumption, pheromone, chaos and RNG state when instantiated with corresponding weights. Tests also verify one physical/logistic step despite multiple inner batches, identical-candidate reinforcement across split budgets, and the normalized D-ACO fitness tradeoff. Every selected tree is independently reevaluated and serves every live node; source/map/script fingerprints and instantiated parameters are saved.

Run `python -B plans/phase5-acaco-balance/balance_study.py screen SEED FRESH_RESULTS_DIRECTORY` for seeds 0/1/2; run with `validation SEED FRESH_RESULTS_DIRECTORY` for seeds 9/10/11. Use a fresh directory after code changes to preserve old provenance. Then run `summarize_balance.py`. Inner iterations remain experiment-local; production exposes separate elite and fitness weights.
