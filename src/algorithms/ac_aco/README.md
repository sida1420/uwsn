# AC-ACO for the UWSN simulator

This package adapts the CH-selection parts of Zhou, Chen, and Cao (2025),
DOI [10.32604/cmc.2025.065561](https://doi.org/10.32604/cmc.2025.065561), to
this repository's 3D underwater acoustic simulator. `IT4906_WSN_final.pptx`
is presentation material only; the paper supplies the equations.

It does not reproduce the paper's 2D radio experiments or Figures 3–6. The
search scores feasible routes by this repository's `Evaluator`, and the
simulator deducts energy only for the selected route once per network round.

## Operation

`T_max=3500` controls network rounds. Each nonempty round creates exactly
`num_ants` candidates (10 by default), selects its best feasible candidate,
and updates pheromone once. There is no inner optimizer iteration loop.
A candidate selects
`max(1, round(ch_proportion * live_nodes))` unique CHs, then uses:

```text
build_clusters(CHs) -> multi_hop_routing(...) -> Evaluator.energy_consumption(...)
```

All sensor-to-sensor and sensor-to-base edges remain within `network.radius`.
The shared router constructs a cycle-free tree from the base and promotes a
non-CH sensor to relay only when it lies on a routed path. A connected 3D deployment
can therefore route CHs that are outside direct base range.

## AC-ACO parameters

| Parameter | Default | Role |
|---|---:|---|
| `num_ants`, `num_iterations` | 10, 5 | Ants per round; legacy inner-iteration count (unused) |
| `ch_proportion` | 0.10 | Target CH proportion |
| `pheromone_exponent` | 1 | Pheromone exponent |
| `energy_cost_exponent` | 0.1 | Inverse acoustic-hop-cost exponent |
| `beta_min`, `beta_max`, `beta_slope` | 1, 5, 5 | Eq. (14) heuristic schedule |
| `rho_min`, `rho_max` | 0.1, 0.9 | Eq. (13) evaporation schedule |
| `chaos_min`, `chaos_max`, `chaos_r` | .05, .3, 3.61 | Logistic chaos controls |
| `Q`, `tau0` | 100, 1 | Eq. (10) deposit and initial pheromone |
| `hopping_factor` | .4 | Shared-router energy/distance tradeoff |

For transition `i -> j`, the implementation uses Eq. (18)/(20):

```text
eta = residual_energy[j] / distance(i, j)
P(i, j) proportional to tau(i, j)^pheromone_exponent
                       * eta^beta(t)
                       * (1 / E_m(i, j))^energy_cost_exponent
```

The first CH is selected uniformly because the source does not specify a start
distribution. Chaos is generated deterministically from `chaos_seed`, added to
weights, and normalized. Eq. (15) uses the previous iteration's best consumed
route energy and the min/max feasible costs observed in prior iterations;
the first iteration and degenerate bounds use `chaos_min`. These are explicit
UWSN adaptations where the paper leaves the window or edge mapping undefined.

Pheromone is updated once per network round. The round-best ordered
CH path receives `Q / max(solution.cost, 1e-12)`, using the total routing
energy returned by the shared evaluator. Relay and outlier edges do
not receive a deposit because ants did not choose them.

## Use

```python
from algorithms.ac_aco import ACACOClustering, ACACOParameters

algorithm = ACACOClustering(network, hparameters, ACACOParameters(random_seed=42))
root = algorithm.plan_round(live_nodes, residual_e)
```

`last_solution` is the selected `ClusterSolution` or `None`; it exposes the
ordered `cluster_heads`, `root`, acoustic `cost`, `path_length`, and target CH
count. `select_cluster_heads()` remains available for demos and returns the
selected IDs.

## Issue #16: iteration equals round

The current call graph is `Simulator.run()`'s `for t in range(T_max)` loop
calling `algorithm.plan_round(...)` exactly once, which calls
`optimizer.optimize(...)` exactly once. Neither call site retries, and
`plan_round()` does not call `select_cluster_heads()`. No round index is passed
through this interface, so the optimizer maintains a one-based call counter:
iteration 1 corresponds to simulator round 0. Standalone calls to `optimize()`
or `select_cluster_heads()` also advance this state; use a fresh algorithm
instance for an independent simulation run.

Beta, rho, and chaos strength are calculated once per round with the existing
equations. The previous round's best energy and the min/max feasible candidate
energies persist across calls without retaining old routing trees. All defaults
remain unchanged, including the legacy `num_iterations=5`, which no longer
controls search or schedules. The optimizer retains `hparameters.T_max` as
the schedule horizon because the simulator uses that value as its round limit
(3500 by default). Eq. (13)/(14) are unchanged: rho reaches its lower bound
at iteration `T_max`, and beta's sigmoid is centered at `T_max / 2`.
Alpha and the inverse-hop-energy exponent remain fixed.

The shared clustering/routing contract supplies the tree; AC-ACO no longer
duplicates its coverage, parent, cycle, or range validation. A missing root or
nonpositive/nonfinite evaluated energy still rejects a candidate. If every ant
fails, the optimizer performs its single evaporation/chaos update and returns
`None`, without retries or reusing a previous round's route. `path_length` is
retained as a public solution field, but does not influence reinforcement.

The compact `[AC-ACO DEBUG]` line prints on iteration 1, every 100 iterations,
and failed rounds. It includes the adaptive values, ant/CH counts, feasible
candidate count, best energy, and post-update pheromone statistics over live
directed edges (the diagonal for a single remaining node). In this line,
`alpha` means `pheromone_exponent` and `gamma` means `energy_cost_exponent`;
their labels should not be confused with SimpleACO's different exponent mapping.

## Comparison with the current SimpleACO

- The old optimizer ran 50 candidates and five pheromone/chaos updates per
  network round. Beta/rho restarted and traversed their five-iteration schedule
  before residual energy changed, allowing repeated reinforcement on the same
  energy state. More candidates alone do not imply worse per-round energy;
  the extra updates affect future selection and runtime.
- Ranking routes by total energy while depositing by CH path length rewarded
  a different objective. CH ordering is a sampling path, not the actual relay
  tree; short paths can still incur expensive relay/member communication.
- Chaos adds the same `c = strength * chaos[source]` to each normalized
  transition probability. With `n` available choices, the result is
  `(p_j + c) / (1 + n*c)`, a mixture with the uniform distribution that can
  substantially flatten preferences. The equation is unchanged.
- AC-ACO uses `tau^alpha * (residual/distance)^beta(t) * E_m^-gamma`.
  SimpleACO uses `tau^alpha * (residual/distance)^gamma * E_m^-beta`.
  Their current exponent defaults and CH proportions differ; comparing labels
  alone misses the strong residual-energy/distance bias in AC-ACO.
- SimpleACO samples distinct starting nodes and permits up to 20 clustering
  attempts per ant (20 ants by default, at most 400 constructions). AC-ACO
  samples starts with replacement and now constructs exactly 10 candidates,
  with no retries. These existing search-budget and diversity differences can
  affect feasibility and lifetime.
- Both retain pheromone across rounds and clamp it to existing bounds.
  Energy-based `Q/cost` can hit `tau_max`; the debug statistics expose this
  concentration. Both select minimum current-round energy, which does not
  directly optimize lifetime or prevent individual relay depletion.

These are implementation findings, not evidence that AC-ACO beats SimpleACO.
No hyperparameter or benchmark rule was tuned for this change.
