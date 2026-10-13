# Live AC-ACO: elite balance, load fitness and inner iterations

Historical scope: these measurements use `energy_cost_exponent=1`. Production now defaults to 0.1; the results below do not measure that change.

The production sampler now reads live pheromone rows: each later ant sees deposits from earlier feasible ants. The frozen per-round pheromone snapshot was removed. Residual-energy state still stays fixed during search because only the selected tree consumes physical energy.

## Completed full lifetime follow-up

Fresh paired seeds 15/16/17 tested production weights 1 and 0.1 with one batch of 40 ants. Mean FND was 1504.667 versus 1505.000 rounds; mean service was 2193.667 versus 2191.667 rounds (-0.091%). Weight 0.1 lost two service rounds in every pair and used 0.199% more energy through round 1400. All runs stopped when node 65 died and isolated node 48, with 98 survivors. The lower weight balances reinforcement but does not improve lifetime on these seeds. See [full results and terminal topology](full/README.md).


Separate `elite_weight` and `load_weight` parameters implement the two D-ACO-inspired interventions. The following tests isolate each intervention and also test their combination. The resulting production defaults are elite weight 0.1, load weight 0, and one batch of 40 ants. The study controls explicitly retain elite weight 1; `live_elite_01` tests elite weight 0.1 with the historical energy-cost exponent.

## Decision

Reduce the best-set multiplier to 0.1 to balance reinforcement, matching D-ACO. Its measured elite share falls from 73.59% to 21.81% in fresh validation. Mean early energy rises 0.180%, while matched checkpoint energy falls 0.404% at round 600 and 0.279% at round 1510. This is a deliberate reinforcement-balance choice, not a demonstrated lifetime optimization.

Keep load fitness opt-in: `ACACOParameters(load_weight=0.1)` combines it with the new elite default. Tested alone against theta=1, it reduces load CV by 2.234% and mean peak relative depletion by 4.916%, with a 0.348% energy cost in fresh validation. Both combined give a 0.358% energy cost, 1.877% lower CV and 3.568% lower mean peak relative depletion. The critical-node residuals and per-seed outcomes are mixed; these measurements do not establish longer service.

Keep one batch of 40 ants. Two batches of 20 use 0.157% more energy than one batch of 40 in fresh validation. Two batches of 40 versus one batch of 80 differ by only -0.003% energy. Increasing to 80 ants saves about 1.33% energy but uses roughly twice the CPU. There is no compelling energy benefit from extra inner iterations at equal ant budget.

## D-ACO comparison and design

The D-ACO implementation in this checkout runs one ant batch per simulator round. It uses elite multiplier theta=.1 and candidate fitness `.9*E/mean(E)+.1*CV/mean(CV)`. CV is the standard deviation of absolute per-node round costs divided by their mean. AC-ACO uses ordered-CH transition pheromone rather than D-ACO node pheromone. This study retains AC-ACO deposits `Q/physical_energy`; copying D-ACO's `Q/fitness` would alter the calibrated deposit scale.

Each checkpoint screen uses three seeds and 12 optimizer searches at a fixed physical state: after round 600 and immediately after node 33 dies at round 1510 in the earlier frozen trajectory. The late state is replayed from its saved checkpoint and checked against archived costs. Every configuration starts from an independent deep copy of physical and optimizer state. The original screens had shared-state aliasing, were excluded, and remain in `invalid-screen-state-alias/` for audit.

Fresh validation uses seeds 12/13/14 and 150 physical rounds per configuration. All eight configurations share the calibrated bounds and current chaos amplitudes. The schedule horizon remains 3000. This is an early-trajectory comparison, not a lifetime/FND validation. The earlier frozen study has three separate 300-round trajectories per configuration in [FROZEN_REFERENCE.md](FROZEN_REFERENCE.md).

| Configuration | Elite weight | Load weight | Batches x ants |
| --- | ---: | ---: | --- |
| baseline | 1.0 | 0.0 | 1 x 40 |
| live_baseline | 1.0 | 0.0 | 1 x 40 |
| live_elite_01 | 0.1 | 0.0 | 1 x 40 |
| live_fitness_cv | 1.0 | 0.1 | 1 x 40 |
| live_combined | 0.1 | 0.1 | 1 x 40 |
| live_split_2 | 1.0 | 0.0 | 2 x 20 |
| live_batch_80 | 1.0 | 0.0 | 1 x 80 |
| live_inner_80 | 1.0 | 0.0 | 2 x 40 |

`baseline` alone retains the old frozen sampler as a control. All `live_` configurations use live pheromone. Percentages below use `live_baseline` as the reference unless stated otherwise.

## Checkpoint 600

| Configuration | Mean total energy (J) | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Elite share of new mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.188469881 | -0.393% | 1.18x | -0.515% | +4.995% | 69.59% |
| live_baseline | 0.189212562 | +0.000% | 1.00x | +0.000% | +0.000% | 69.50% |
| live_elite_01 | 0.188447265 | -0.404% | 1.00x | -2.648% | -6.676% | 18.60% |
| live_fitness_cv | 0.190061980 | +0.449% | 1.04x | -3.609% | -2.493% | 69.38% |
| live_combined | 0.188893941 | -0.168% | 1.29x | -4.486% | -5.615% | 18.56% |
| live_split_2 | 0.189266378 | +0.028% | 1.11x | -3.720% | -7.123% | 69.33% |
| live_batch_80 | 0.186613041 | -1.374% | 2.09x | -2.938% | -8.426% | 69.75% |
| live_inner_80 | 0.186165812 | -1.610% | 2.08x | -2.143% | -8.463% | 69.69% |
## Checkpoint 1510

| Configuration | Mean total energy (J) | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Elite share of new mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.196442275 | -0.013% | 0.95x | +1.270% | +0.234% | 70.40% |
| live_baseline | 0.196468000 | +0.000% | 1.00x | +0.000% | +0.000% | 69.16% |
| live_elite_01 | 0.195920442 | -0.279% | 1.07x | -0.335% | -6.253% | 19.19% |
| live_fitness_cv | 0.196781538 | +0.160% | 1.20x | -1.248% | -4.263% | 69.81% |
| live_combined | 0.197309660 | +0.428% | 1.26x | -0.464% | -7.847% | 19.13% |
| live_split_2 | 0.196857878 | +0.198% | 1.15x | -1.313% | -4.296% | 69.59% |
| live_batch_80 | 0.193029569 | -1.750% | 2.06x | +2.000% | +0.565% | 70.49% |
| live_inner_80 | 0.192966295 | -1.782% | 1.89x | +1.046% | -3.781% | 70.15% |
## Fresh 150-round trajectories

| Configuration | Mean total energy (J) | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Elite share of new mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 2.498965943 | +0.115% | 0.87x | -0.580% | -1.904% | 73.56% |
| live_baseline | 2.496105783 | +0.000% | 1.00x | +0.000% | +0.000% | 73.59% |
| live_elite_01 | 2.500593792 | +0.180% | 1.21x | -0.208% | -1.103% | 21.81% |
| live_fitness_cv | 2.504795155 | +0.348% | 1.18x | -2.234% | -4.916% | 73.54% |
| live_combined | 2.505041315 | +0.358% | 1.22x | -1.877% | -3.568% | 21.76% |
| live_split_2 | 2.500012569 | +0.157% | 1.29x | -0.506% | -2.012% | 73.44% |
| live_batch_80 | 2.462986179 | -1.327% | 2.17x | -0.618% | -3.193% | 73.88% |
| live_inner_80 | 2.462913031 | -1.330% | 1.82x | -0.047% | -3.094% | 73.77% |

## Equal-budget inner feedback and snapshot removal

| Context | Comparison | Energy change | CPU ratio |
| --- | --- | ---: | ---: |
| 600 | live_baseline / baseline | +0.394% | 0.85x |
| 600 | live_split_2 / live_baseline | +0.028% | 1.11x |
| 600 | live_inner_80 / live_batch_80 | -0.240% | 1.00x |
| 600 | live_batch_80 / live_baseline | -1.374% | 2.09x |
| 1510 | live_baseline / baseline | +0.013% | 1.06x |
| 1510 | live_split_2 / live_baseline | +0.198% | 1.15x |
| 1510 | live_inner_80 / live_batch_80 | -0.033% | 0.92x |
| 1510 | live_batch_80 / live_baseline | -1.750% | 2.06x |
| 150 physical rounds | live_baseline / baseline | -0.114% | 1.15x |
| 150 physical rounds | live_split_2 / live_baseline | +0.157% | 1.29x |
| 150 physical rounds | live_inner_80 / live_batch_80 | -0.003% | 0.84x |
| 150 physical rounds | live_batch_80 / live_baseline | -1.327% | 2.17x |

## Per-seed validation and critical nodes

| Configuration | Seed | Energy change | Mean peak relative depletion change | Node 33 residual (J) | Node 65 residual (J) |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 12 | -0.128% | -4.585% | 0.546527 | 0.577477 |
| baseline | 13 | +0.418% | +0.650% | 0.548428 | 0.577512 |
| baseline | 14 | +0.055% | -1.670% | 0.548844 | 0.577966 |
| live_baseline | 12 | +0.000% | +0.000% | 0.547318 | 0.579029 |
| live_baseline | 13 | +0.000% | +0.000% | 0.548528 | 0.576734 |
| live_baseline | 14 | +0.000% | +0.000% | 0.547004 | 0.577358 |
| live_elite_01 | 12 | +0.169% | -3.974% | 0.548631 | 0.579810 |
| live_elite_01 | 13 | +0.033% | +3.445% | 0.550058 | 0.578452 |
| live_elite_01 | 14 | +0.337% | -2.596% | 0.547580 | 0.577117 |
| live_fitness_cv | 12 | +0.280% | -7.181% | 0.548635 | 0.577631 |
| live_fitness_cv | 13 | +0.675% | -2.127% | 0.546122 | 0.578912 |
| live_fitness_cv | 14 | +0.091% | -5.324% | 0.546794 | 0.576687 |
| live_combined | 12 | +0.524% | -5.967% | 0.546755 | 0.577922 |
| live_combined | 13 | +0.560% | +0.996% | 0.546581 | 0.580180 |
| live_combined | 14 | -0.009% | -5.552% | 0.549478 | 0.579679 |
| live_split_2 | 12 | +0.106% | -4.072% | 0.546425 | 0.577811 |
| live_split_2 | 13 | +0.230% | +1.160% | 0.547486 | 0.579087 |
| live_split_2 | 14 | +0.134% | -2.997% | 0.547991 | 0.578838 |
| live_batch_80 | 12 | -1.662% | -4.078% | 0.547901 | 0.578695 |
| live_batch_80 | 13 | -1.230% | -1.967% | 0.549024 | 0.580055 |
| live_batch_80 | 14 | -1.089% | -3.483% | 0.547734 | 0.576922 |
| live_inner_80 | 12 | -1.460% | -5.102% | 0.547706 | 0.578718 |
| live_inner_80 | 13 | -0.908% | +0.079% | 0.543742 | 0.577462 |
| live_inner_80 | 14 | -1.620% | -4.131% | 0.547522 | 0.579605 |

## Why best-set influence is large

For one batch, let B be the ant budget and K the CH count. Ant deposits happen before evaporation, while the elite deposit happens after it. For equal candidate costs E, equal K and all ants feasible, surviving ant reinforcement is `(1-rho)*(K-1)*Q/E` and elite reinforcement is `theta*(K-1)*Q/E`. The elite share of new reinforcement is therefore `theta/(1-rho+theta)`. At rho=.6, theta=1 gives 71.43%; theta=.1 gives 20%. A cheaper elite or fewer feasible ants increases its share. This quantifies why the old best-set bonus can outweigh all ordinary ants together. It does not imply that reducing it always improves routing. Tables measure surviving additions before clipping, excluding old pheromone and chaos.

For the load-fitness comparison, a higher-energy candidate wins over a lower-energy candidate only if `w*(CV_low-CV_high)/mean(CV) > (1-w)*(E_high-E_low)/mean(E)`. At w=.1, a CV advantage must offset nine times the normalized energy disadvantage. This permits an energy/load tradeoff but does not account for residual energy or critical-node topology. Peak relative depletion, `max_i(cost_i/residual_i)`, is measured separately; a lower absolute CV can still exhaust a vulnerable node sooner.

## How multiple batches are controlled

For m batches use `rho_inner=1-(1-rho)^(1/m)` and `a=1-rho_inner`, so `a^m=1-rho`. Disturbance is `c_inner=c*rho_inner/rho`, so its final geometric sum remains c. For batch b (zero-based), divide ant deposits by the total budget B and multiply by `(1-rho)/a^(m-b)`. Each batch deposits its best-so-far elite with multiplier `theta/sum(a^i, i=0..m-1)`. Identical candidates thus produce equal final reinforcement across batch counts before clipping. One physical round advances beta/rho schedules and logistic chaos exactly once; energy is deducted once. This separates inner feedback from simply using more ants or applying extra evaporation.

Live ants already receive within-round feedback, so extra batches add intermediate evaporation, disturbance and elite reinforcement. Their benefit must be assessed against an equal total ant budget. The 80-ant batch versus two 40-ant batches comparison provides that control.

## Verification and practical limits

All 37 tests pass. Checks cover live deposits changing later probabilities, production/experimental equivalence, independent checkpoint restoration, valid parameter ranges, one physical/logistic step, and equal reinforcement for forced identical candidates. Every selected tree is independently reevaluated, serves every live node, and leaves residual energy unchanged during search. All pheromone entries remain finite and within calibrated bounds.

CPU is process time from the instrumented runner, which calculates CV for every candidate. Absolute time and ratios are indicative: these are short concurrent jobs, not a dedicated production benchmark. Three seeds and early trajectories cannot establish FND or full-service gains. Checkpoint states are from the old frozen trajectory, so they test the new sampler at matched states rather than predict its eventual late trajectory.

Reproduce with `python -B plans/phase5-acaco-balance/balance_study.py live_screen SEED FRESH_RESULTS_DIRECTORY` for seeds 0/1/2 and `live_validation SEED FRESH_RESULTS_DIRECTORY` for seeds 12/13/14. Use a fresh directory after source/script changes; the runner refuses to overwrite metadata with different provenance. `summarize_live.py` reads the archived study results in this folder. Raw records retain effective experimental configuration, parameters, routing counts, source/map/script hashes and per-round metrics.
