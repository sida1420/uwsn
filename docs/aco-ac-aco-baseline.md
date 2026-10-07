# Tuned ACO baseline for AC-ACO

This note records the focused ACO-to-AC-ACO transfer on `fix-ac-aco-long-time`.
It describes the current implementation and how to reproduce a controlled
comparison; it does not claim that AC-ACO is superior.

## Model and scope

Both algorithms construct CH paths, turn them into a tree with the same
multi-hop router, and score it with the same `Evaluator`. The objective is raw
current-round energy. Neither has a cluster-balance term or an explicit
CH-to-base distance term in CH selection. Distances are the shared 3D network
matrices. The shared energy model and its limitations are unchanged: CHs emit
two packets, and aggregation uses a fixed output-size assumption even for
forwarded traffic.

The 100-round five-seed audit qualifies the original premise: tuned ACO used
`1.792357 J` mean energy, while old AC-ACO used `1.675484 J`. These are
compatibility mappings, not a guarantee that the tuned ACO controls lower
energy or improve lifetime.

## Parameter roles

| Control | Tuned ACO | AC-ACO after transfer | Mapping |
|---|---:|---:|---|
| ants / attempts | 40 / 10 | 40 / 10 | Same static search budget |
| CH proportion | 0.20 | 0.20 | Same static target |
| pheromone exponent | `alpha=1` | `pheromone_exponent=1` | Same role |
| inverse hop-energy exponent | `beta=.5` | `energy_cost_exponent=.5` | Safe role-based transfer |
| residual/distance exponent | `gamma=1` | adaptive `beta: 1..5` | Keep adaptation; 1 is its lower/reference value |
| evaporation | `rho=.1` | adaptive `.9 -> .1` | Keep AC schedule; `.1` is its late bound |
| deposit scale | `Q=.07` | `Q=.07` | Same joule-based objective |
| initial/bounds | `tau0=1`, `.1..10` | `tau0=1`, `.1..10` | Same limits |

The labels `beta` and `gamma` are swapped between implementations. Tuned ACO
uses `tau^alpha * (residual/distance)^gamma * E_m^-beta`; AC-ACO uses
`tau^pheromone_exponent * (residual/distance)^beta(t) *
E_m^-energy_cost_exponent`. Copying names instead of mathematical roles would
break AC-ACO's adaptive heuristic schedule.

## Preserved AC-ACO mechanisms

- `beta(t)` remains a sigmoid from 1 to 5 with slope 5.
- `rho(t)` remains a linear decay from .9 to .1 over `T_max`.
- Logistic chaos remains seeded at `.37`, with `r=3.61` and strength `.05` to `.30`.
- The transition probabilities retain the original chaotic rule:
  `(p + c) / (1 + n*c)`, where `c = strength * chaos[source]`.
  Uniform exploration depends on candidate count. A total-mass normalization
  trial weakened exploration and shortened service in three paired seeds,
  so it was rejected from the final transfer.
- The per-round chaos disturbance and adaptive pheromone update remain active.

## Transferred tuned-core behavior

| Change | AC-ACO treatment | Reason |
|---|---|---|
| Distinct ant starts | Mapped | Stops duplicate initial ants; each retry retains its ant's start. |
| Immediate successful-ant deposit | Mapped | The NumPy pheromone array is synchronized immediately, so later ants see it. |
| Clamp each deposit | Mapped with modification | Enforces `.1..10` without removing adaptive evaporation or chaos. |
| `Q=.07`, inverse hop-energy exponent `.5` | Mapped | Same mathematical roles and score units. |
| Fixed `rho=.1` | Not mapped | Would disable AC-ACO's adaptive evaporation. |
| Static residual/distance exponent `1` | Not mapped directly | AC-ACO retains its 1..5 adaptive schedule. |
| No chaos | Not mapped | Chaos is a defining AC-ACO mechanism. |

AC-ACO also retains its stronger guards: positive-residual candidate filtering,
finite positive candidate-cost validation, deterministic best-candidate ties,
and a post-round update even when all candidate constructions fail.

## Reproducible comparison

Use fresh algorithm instances for every seed because pheromone, round state and
chaos persist between rounds. `SimpleACO` and `ACACO` accept `seed`; an
explicit seed creates a private RNG, while `None` continues to honor callers
that seed global `random`.

`src/run.py --seed 0` supplies a reproducible default, but its `ALGORITHMS`
list remains `NodeACO` and `PSO`. It is not the ACO/AC-ACO comparison runner.
Run the focused three-variant harness from the repository root:

```powershell
C:\Users\LOQ\miniconda3\python.exe -B plans\reports\aco-transfer-261007-0810\compare.py --variants tuned old new --seeds 0 1 2 3 4 --rounds 100 --tag quick-100
```

`tuned` is current tuned ACO, `old` loads the preserved pre-transfer AC-ACO,
and `new` is updated AC-ACO. It fixes map, topology, energy model, stopping
conditions and each seed across variants, and records objective convergence,
cluster/route metrics, alive nodes, residual energy and whether chaos changes.

## Evidence and result

The full audit, parameter map and controlled ablations are in the
[transfer audit](../plans/reports/audit-261007-0810-tuned-aco-transfer.md).
The completed 15-case multi-seed comparison is recorded in the
[validation report](../plans/reports/validation-261007-0810-tuned-aco-transfer.md).
Updated AC-ACO averages 1.669851 J over the matched first 100 rounds,
6.83% below tuned ACO and 0.34% below old AC-ACO. Mean routing service is
2184.0 rounds versus tuned ACO's 2279.2 and old AC-ACO's 2179.4. The small
increment over old AC-ACO does not establish general superiority on other maps.
Do not infer a lifetime advantage from the early fixed-horizon figures above;
inspect both modeled energy and clamped residual depletion, first death,
completed rounds and route feasibility.
