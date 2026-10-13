# AC-ACO pheromone calibration — 2026-10-11

This is a bounded calibration requested by the user, not execution of every
stage in the supplied Downloads/plan.md. That document's reports describing
46/51 tests and later audits are absent from this checkout; they are historical
context, not reproduced evidence. The initial checkout had 17 passing tests.

## Sources and interpretation

- [Zhou, Chen and Cao (2025), Table 2 and equations 11–20](https://cdn.techscience.cn/files/cmc/2025/TSP_CMC-84-3/TSP_CMC_65561/TSP_CMC_65561.pdf):
  reference alpha=1, beta=3, rho=.2, initial pheromone=1, chaos coefficient=.1,
  logistic r=3.58. Its radio network differs from this acoustic 3D model. Its
  gamma is a chaos coefficient, not this implementation's acoustic exponent.
- [Stützle et al., Parameter Adaptation in Ant Colony Optimization](https://lopez-ibanez.eu/doc/StuLopPelMau2010adaptiveACO.pdf):
  deposit is proportional to inverse solution cost; pheromone bounds and
  evaporation interact, and suitable parameter settings depend on the variant
  and computational budget. It does not supply universal UWSN bounds.
- [Logistic-map periodic-window study](https://pubmed.ncbi.nlm.nih.gov/39820460/):
  the accepted interval for r is not uniformly chaotic. Retaining r=3.61 is a
  controlled choice, not a claim that every accepted r is suitable.

The numeric search limits below are an adaptation derived from our actual
equation, not parameter intervals prescribed by these papers.

## Full-update scale

Ant deposits occur before evaporation; the elite deposit occurs after it.
Let D=Q/E_ref. If all 40 ants and the elite repeatedly reinforce the same
edge at E_ref, and disturbance is c, the unclamped recurrence is

```
tau_next = (1-rho) * (tau + D) + c + D
tau_equilibrium = ((2-rho)*D + c) / rho
```

For logistic r=3.61, every iterated value is at most r/4=.9025, so
c <= chaos_max*r/4=.27075. At minimum evaporation .1 and reference route
cost .015 J, Q=.01 gives an equilibrium envelope of 15.3741667. A ceiling
of 20 leaves headroom. Q=.003 gives 6.5075, motivating a ceiling of 8.
Ceilings 2 and 5 are also measured as controls but cannot accommodate these
reference worst cases at late evaporation. The original ceiling 10 coupled
with Q=100 is orders of magnitude below its deposit scale.

**.015 J is a reference scenario, not a proven lower bound on route costs.**
Small deployments or different physics can still reach the ceiling; clamping
remains necessary. The stress test verifies the recurrence, not lifetime.

The logistic invariant interval for this r has lower endpoint
r*(r/4)*(1-r/4)=.3176574375. With minimum chaos .05 and maximum evaporation
.6, the minimum-disturbance background equilibrium is about .02647. A floor
of .01 lies below it; .1 can flatten naturally distinct low pheromone levels.
Floors .001/.01/.05 and initial levels 1/2 are screened explicitly. This
argument is conditional on the specified r and chaos/evaporation bounds.

## Reproduction and experimental limits

Run `python -B plans/phase5-acaco-tuning/calibrate.py` from the repository root.
The bundled Python runtime was used because `python` is absent from PATH.
`results.json` contains full explicit configurations, seeds, map SHA, git SHA,
source fingerprints, per-round costs, CPU timings, feasible evaluation counts,
floor/ceiling occupancy and depletion diagnostics. Existing matching results
are reused; delete or move that artifact for a fresh run.

Screening: 20 searches at fixed physical state, optimizer memory retained,
seeds 0/1/2, 40 ants per search, maximum 10 attempts per ant. Validation:
independent 150-round energy-depleting trajectories, seeds 3/4/5. Schedule
horizon remains 3000. No mutation of shared routing, physics, simulator,
topology or other algorithms. Every successful round independently checks
tree energy and exact live-node service. Diagnostic probability calculations
consume no RNG and do not advance persistent iteration or chaos state.

The initial pilot selected two finalists from small ceilings before the
late-equilibrium guard was added. Their validation results are retained as
exploratory controls. The extended run includes wider ceilings and reranks
using the equilibrium guard. Its final contenders are reported separately.

CPU measurements include evaluation counting instrumentation, exclude the
after-search diagnostics, and were collected sequentially. They are practical
checks, not a precise performance benchmark. The validation seeds were not
used for screening, but all experiments use one existing topology. This is
not independent topology validation, a global optimum, or evidence about
FND, HND/LND, post-death service, or late-round energy performance.

<!-- RESULTS -->

## Completed results

| Validation configuration | Mean 150-round energy (J) | Change vs historical | Mean CPU (s) | Floor occupancy | Ceiling occupancy |
| --- | ---: | ---: | ---: | ---: | ---: |
| historical | 2.510832058 | +0.000% | 29.620 | 81.479% | 7.044% |
| moderate_heuristic | 2.489096505 | -0.866% | 53.875 | 0.000% | 0.000% |
| q0.01_max2.0_rho0.6 | 2.500538060 | -0.410% | 29.828 | 0.000% | 0.000% |
| moderate_heuristic_wide | 2.489096505 | -0.866% | 30.661 | 0.000% | 0.000% |
| q0.01_max20.0_rho0.6 | 2.500538060 | -0.410% | 22.562 | 0.000% | 0.000% |

| Seed | Historical energy (J) | New defaults (J) | Change |
| --- | ---: | ---: | ---: |
| 3 | 2.512037836 | 2.501974943 | -0.401% |
| 4 | 2.505098702 | 2.497558622 | -0.301% |
| 5 | 2.515359637 | 2.502080614 | -0.528% |

Screened 22 configurations; completed 142,800 feasible evaluations including exploratory controls and validation.
All measured rounds served all 100 live sensors, with no observed deaths or routing failures.

Applied defaults: `Q=.01`, `tau_min=.01`, `tau0=1`, `tau_max=20`, `rho_min=.1`, `rho_max=.6`. Other parameters retain their explicitly inventoried values.
The lower acoustic exponent remains experimental: it saved slightly more early energy, but late-round behavior and lifetime are unvalidated. Repeated timings varied markedly even for identical trajectories, so the initial apparent CPU regression is not reliable. Beta_max=3 was exploratory only; these 150-round trials cannot assess the raw schedule near round 1500.

Maximum observed single-round relative depletion: historical 0.001923080, selected 0.002120219 (+10.25%). This is a remaining lifetime risk, not proof of earlier death. The change is adopted for numerical scale and preserved early feasibility, not a claimed lifetime improvement.

Floors .001/.01/.05 gave the same screening energies in their matched controls; .01 is chosen from the background-disturbance scale, not a measured optimum. Wide and small ceilings also yield identical early trajectories when neither clips; the wider value is chosen for late recurrence headroom.

Validation seed results do not certify generalization across topologies. No 600-round or full-lifetime experiment was performed.

Verification: 21 unit tests pass, including historical elite-clamp regression, inverse-cost discrimination, sustained late reinforcement, finite normalized probabilities and exact full service across coupled scales.

Map SHA-256: `ebe729265598746b30af09715e239a9891b2ac95ac66656096dc712e6c34fdcc`. Starting git SHA: `da40055a9f34a7c8ecf31f7a23736bb338098c1d`.
