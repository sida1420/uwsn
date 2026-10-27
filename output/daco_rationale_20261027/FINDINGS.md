# What the DACO rationale experiments actually support

Exploratory pilot, 27 October 2026. See REPORT.md for the frozen configuration and variant definitions; all 72 paired runs completed. Per-source hashes verified. Production code and existing campaign files were not edited.

## Measured online effects

Positive values below mean full DACO exceeds the comparator. Search-seed differences are first averaged within each of six map/distribution cells. Only two generating seeds per distribution were used; uniform and clustered maps with the same seed share underlying coordinate draws, so the six cells are not fully independent. these descriptive averages do not establish statistical significance or universal superiority.

| Comparator | Change in FND (rounds) | Change in completed rounds | Change in energy at 20 all-alive rounds | Map cells: longer / shorter / tied |
| --- | ---: | ---: | ---: | --- |
| energy_only | +55.25 | -15.50 | +2.99% | 1 / 3 / 2 |
| no_inverse_density | +2.08 | -3.25 | +0.93% | 1 / 3 / 2 |
| no_sampling_density | +0.25 | -2.50 | +0.04% | 0 / 4 / 2 |
| flat_kernel | +0.33 | -0.83 | -0.08% | 2 / 2 / 2 |
| edge_memory | +2.33 | +5.50 | -6.55% | 4 / 0 / 2 |

FND was observed in 72/72 runs. Terminations: {'search_failure': 48, 'all_dead': 0, 'horizon': 24}. No run termination is substituted for an unobserved death event. The simulations use reduced initial energy (0.02 J), 36 nodes, and a 240-round horizon. First-node survival and completed collection duration are separate outcomes; use both when judging the criterion.

## Your four mechanisms

### 1. Proximity preference can concentrate successive choices

In the synthetic 30-node dense region plus 10-node sparse region, 400 paired construction trials selected eight CHs. Uniform selection allocated 5.978 heads to the dense region; the inverse-distance transition rule allocated 7.200; density with overlap reduction allocated 6.600. This supports the local concentration concern in the designed geometry. It is not a full native SimpleACO/ACACO benchmark: the diagnostic holds other preferences equal.

### 2. Density allocates more heads to the dense region, but the overlap reduction was modest here

Without subtracting selected-head support the dense allocation was 6.630; with subtraction it was 6.600. The exact diminishing-overlap identity passed across four decay choices and two live-node sets (maximum numerical error 2.72e-15). The property is verified; a large practical benefit from this subtraction alone is not established by this one construction geometry.

### 3. Proximity weighting resolves the plateau; its end-to-end benefit is a separate result

The one-sensor example has 2 fully covered cells. Their flat weights have 1 distinct value, versus 2 with parabolic decay. This confirms localization in the intended minimal example. The flat_kernel online ablation also changes the density used by the score, so it measures the complete proximity-kernel effect, not sampling alone.

### 4. Depletion scoring changes load allocation; density is not equivalent to irreplaceability

In a fixed pool of 600 feasible trees from 600 attempts, with heterogeneous residual energies, the weighted score selected a tree with +2.64% total energy and -52.36% maximum fractional drain relative to the energy-minimum tree. The weighted and unweighted fractional-depletion criteria selected the same tree in this example. Thus it demonstrates a depletion-versus-energy trade-off, but does not independently support inverse-density weighting.

Across the six random maps, only 1 of 216 node-removal cases disconnected another sensor from the sink. That is too little bottleneck variation to validate density as a criticality proxy. The constructed counterexample makes the limitation explicit: a gateway has degree 11 and density 2.656, yet removing it disconnects 13 other sensors; a leaf has density 0.356, and removing it disconnects no other sensor. The hypothesis needs targeted bottleneck maps and alternative-relay measurements before it becomes a general claim.

## What to write now

Use the analytical claims about overlap, representation, and plateau removal as mechanism properties. Report online gains and losses by endpoint and deployment regime, not as a single lifetime improvement. Describe sparse-node importance as a motivation/proxy whose applicability remains to be tested; the current random-map criticality diagnostic does not establish it.

## Important controls

- Edge_memory retains DACO's heuristic and score and changes pheromone credit assignment. It is not native edge ACO, and the routing decoder remains order-sensitive.
- Equal ant/attempt limits do not ensure equal successful evaluations. Individual logs include retries, calibration, CPU, and wall time.
- Battery conservation was checked using clamped spending, distinct from nominal requested costs. Terminal-round delivery is not physically validated.
- The energy comparison uses the common first 20 rounds with all initial nodes alive in both members of a pair.
- Variants use fixed existing parameters without retuning; results estimate these settings, not the best possible version of every ablation.
- The 240-round horizon also sets the evaporation schedule's timescale. This pilot therefore cannot be treated as a simple time-rescaled version of a 3500-round production run.

## Outputs

- mechanism_panels.png: spatial allocation, fixed-pool ranking, singleton weights, and counterexample.
- endpoints.png: FND and completed-round means by distribution and variant.
- paired_metrics.json: map-level paired effects and computational ratios.
- jobs/: every run's history, endpoint, parameters, and search counters.
- source_snapshot/: exact runner and sources used.

## Runtime check

Full node-memory DACO used 0.03980 CPU seconds per completed round, versus 0.03929 for the edge-memory control (+1.28%). This small pilot does not establish a total runtime advantage for node memory. The edge control uses vectorized matrix updates while native node evaporation uses Python lists; theoretical pheromone storage savings are not equivalent to a measured overall speedup.

## Follow-up: exact termination replay

After seeing the FND/completed-round trade-off, two uniform-map-37/search-seed-101 cases were replayed with the frozen source. Every round's nominal cost matched the original run. This follow-up was selected after the pilot results, and is diagnostic rather than an additional independent replicate.

- full: 181 completed rounds; 6 sensors alive and 6 physically sink-reachable at search termination.
- energy_only: 209 completed rounds; 6 sensors alive and 6 physically sink-reachable at search termination.

Both runs terminated despite the remaining communication graph being connected. This does not establish feasibility under the fixed CH count and greedy decoder, but it rules out physical graph disconnection as the reason for these two stops. Their completed-round difference cannot be attributed solely to preserving physical connectivity.
