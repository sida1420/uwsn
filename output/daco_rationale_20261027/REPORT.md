# DACO rationale: exploratory experiments

Production algorithm sources were frozen and not edited.

## Scope

72 runs: 6 variants × 3 distributions × 2 maps × 2 search seeds. 36 nodes, 300 m cube, radius 190 m, initial energy 0.02 J, horizon 240; 40 ants, 40 calibration ants, at most 10 construction attempts per ant. Initial energy is reduced from ordinary 0.6 J deployments to accelerate depletion. This is a small mechanism pilot, not a production-scale lifetime benchmark or a tuned final comparison.

## Existing tests and direct checks

The existing 13 DACO tests passed before this campaign. The experiment verifies the native/full wrapper on three rounds, weighted-overlap score identities, a one-sensor plateau example, routing-tree inclusion/range, and battery conservation in every simulated round.

## Completed modeled rounds

| Distribution | Variant | Mean rounds | FND observed | Horizon | Search failure | Mean CPU s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| uniform | full | 131.2 | 4/4 | 0 | 4 | 6.12 |
| uniform | energy_only | 147.5 | 4/4 | 0 | 4 | 5.90 |
| uniform | no_inverse_density | 135.0 | 4/4 | 0 | 4 | 5.63 |
| uniform | no_sampling_density | 134.5 | 4/4 | 0 | 4 | 6.33 |
| uniform | flat_kernel | 133.2 | 4/4 | 0 | 4 | 6.00 |
| uniform | edge_memory | 122.8 | 4/4 | 0 | 4 | 5.78 |
| normal | full | 240.0 | 4/4 | 4 | 0 | 8.27 |
| normal | energy_only | 240.0 | 4/4 | 4 | 0 | 7.75 |
| normal | no_inverse_density | 240.0 | 4/4 | 4 | 0 | 8.09 |
| normal | no_sampling_density | 240.0 | 4/4 | 4 | 0 | 8.28 |
| normal | flat_kernel | 240.0 | 4/4 | 4 | 0 | 8.27 |
| normal | edge_memory | 240.0 | 4/4 | 4 | 0 | 7.65 |
| clustered | full | 174.5 | 4/4 | 0 | 4 | 7.34 |
| clustered | energy_only | 204.8 | 4/4 | 0 | 4 | 7.09 |
| clustered | no_inverse_density | 180.5 | 4/4 | 0 | 4 | 7.09 |
| clustered | no_sampling_density | 178.8 | 4/4 | 0 | 4 | 7.42 |
| clustered | flat_kernel | 175.0 | 4/4 | 0 | 4 | 7.91 |
| clustered | edge_memory | 166.5 | 4/4 | 0 | 4 | 7.37 |

## Paired map-level differences

Search-seed differences are averaged inside each of the six map/distribution cells before counting wins. No independence across nodes or repeated runs is assumed, and no significance claim is made.

| Comparator | Full minus comparator rounds | Map cells longer / shorter / tied |
| --- | ---: | --- |
| energy_only | -15.50 | 1 / 3 / 2 |
| no_inverse_density | -3.25 | 1 / 3 / 2 |
| no_sampling_density | -2.50 | 0 / 4 / 2 |
| flat_kernel | -0.83 | 2 / 2 / 2 |
| edge_memory | +5.50 | 4 / 0 / 2 |

## Variant definitions

- full: native DACO; wrapper parity checked.
- energy_only: λ=0; candidate construction, calibration allowance, and feedback schedule retained. Online scores change subsequent samples.
- no_inverse_density: density denominator set to one in scoring only; weighted fractional depletion remains, and density-guided construction remains.
- no_sampling_density: density exponent γ=0 in construction only; density still enters scoring.
- flat_kernel: remove the extra proximity decay in the grid; affects both construction and scoring. The underlying overlap approximation can still decrease near its boundary.
- edge_memory: replace node pheromone with directed transition pheromone while retaining DACO's density, energy score, bounds, and schedule. Deposits reinforce k−1 transitions instead of k nodes; representation credit assignment is inherently different. This is not native SimpleACO/ACACO.

All variants use the same ant/attempt budget; feasible evaluation counts and CPU can differ. Calibration, retries, and the first round's cost are included. Matched seeds do not force identical samples after feedback diverges. The routing decoder retains its current order sensitivity.

## Spatial allocation diagnostic

Synthetic two-region case: 30 compact nodes and 10 more dispersed nodes; select 8 heads in each of 400 seeded trials. Pheromone and energy preferences are held equal. All modes start from the same random node per seed. The short-transition mode uses an inverse-distance construction preference, not a complete published protocol.

| Construction | Mean dense heads | Mean sparse heads | Mean CH pair distance |
| --- | ---: | ---: | ---: |
| uniform | 5.978 | 2.022 | 82.198 |
| density | 6.600 | 1.400 | 65.499 |
| density_no_loss | 6.630 | 1.370 | 63.923 |
| short_transition | 7.200 | 0.800 | 36.501 |

Raw numerical checks, singleton cells, fixed candidate ranking, and density-versus-node-removal diagnostics are in `mechanism_diagnostics.json`, `singleton_cells.csv`, `candidate_pool.json`, and `criticality.csv`.

## Interpretation limits

- Completed rounds use the existing energy-clamping model; nominal terminal costs may exceed residual energy. Actual battery spending is logged separately.
- Failed bounded search is distinct from physical disconnection. Initial graph reachability is recorded.
- FND means the first observed energy-clamping death; it is never substituted with run termination. Unobserved FND/LND remain null.
- The common energy window is 20 rounds. Compare only pairs where both complete it with all original sensors alive; see paired_summary.json for coverage.
- State-space/score identities do not establish lifetime optimality. A dense gateway counterexample and graph criticality diagnostics test the limits of the sparse-node hypothesis.
- CPU/wall timings come from two concurrent workers on this machine; report them as exploratory, not definitive runtime benchmarks.
- No parameters were tuned to the final comparison results; one uniform 30-round pilot checked run cost before the configuration was frozen.

Reproduce with the frozen `source_snapshot/daco_rationale.py` and `source_snapshot/src/`. The controller configuration, source hashes, maps, individual histories, and all variants are preserved.
