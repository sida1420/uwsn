# Tuned ACO foundation for AC-ACO

Baseline: branch `fix-ac-aco-long-time`, HEAD `8930cb2`.

## Checklist

- [x] Inspect ACO, AC-ACO, history, shared routing/energy and seed propagation.
- [x] Preserve old AC-ACO and measure seeded controls and ACO ablations.
- [x] Record component/parameter mapping and accounting limitations.
- [x] Map hop-energy exponent, deposit scale, distinct starts, within-round learning.
- [x] Retain adaptive beta/rho, logistic map, cost-dependent chaos and disturbance.
- [x] Bound deposits; test and reject candidate-normalized chaos, retain original rule.
- [x] Add explicit ACO seed and experiment seed input; preserve legacy callers.
- [x] Test probabilities, accounting, routes, failure handling and reproducibility.
- [x] Compare identical seeds/topology/model at fixed horizon and full lifetime.
- [x] Independent code review, finalize report and artifact paths.

## Decisions before implementation

ACO weight is `tau^alpha * (residual/distance)^gamma * E_m^-beta`.
AC-ACO weight is `tau^pheromone_exponent * (residual/distance)^beta(t) * E_m^-energy_cost_exponent`.
Thus ACO beta 0.5 maps to static energy_cost_exponent, NOT adaptive beta.
Keep beta schedule 1..5, rho schedule 0.9..0.1 and logistic controls.
Map Q 0.07 (shared objective in joules), keep 40 ants/10 retries/20% CHs.
Sync per-ant deposits into the NumPy snapshot. Use distinct starts like ACO.
Initial hypothesis: normalize additive probability chaos by number of available
nodes. Rejected after three paired lifetime trials shortened service in every
seed; preserve original `(p+c)/(1+n*c)` exploration in the final patch.
Enforce AC-ACO bounds on deposits, but preserve ACO baseline numerical behavior.
No modifications to evaluator, router, PSO, packet counts or experiment metrics.
Add benchmark-only diagnostics rather than modifying Simulator history columns.

## Validation design

Predeclared seeds 0,1,2,3,4; original map and all HyperParameters unchanged.
Compare first 100 completed rounds (all nodes alive), then run to the existing
T_max=3000/route failure/all-dead stopping conditions. Total energy over unequal
lifetimes is not an energy-efficiency ranking. Record fixed-horizon efficiency
and separate lifetime, first death, residual and stop reason.
Verify every tree covers exactly the live IDs, parent consistency, radius,
cycles/duplicates, and independently recompute per-node packet costs.
Retain per-round structural metrics, convergence and schedule/chaos evidence.
Use parameter ablations across the same five seeds, not best-seed tuning.

Final variant measured separately in `results/final`; rejected normalization
trial source retained in `trial-total-mass` and results labeled `normalized`.
The incomplete two additional trial seeds were stopped to free CPU; no final
variant result is substituted from that experiment. Final source fixed for all
five new cases. Other algorithms and experiment conditions remain unchanged.

## Risks and questions

CH packet count is currently two even for empty clusters; relay data aggregated
at CHs; no control/CH-selection cost. Shared limitations, not silently changed.
Global lifetime optimum is not the objective. One topology cannot establish
general superiority. Paper equations are reference mechanisms, not an exact
reproduction of the original terrestrial experiments.
