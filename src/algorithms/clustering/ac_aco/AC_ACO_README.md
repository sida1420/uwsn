# AC-ACO for the UWSN simulator

Adapts the cluster-head (CH) selection of Zhou, Chen and Cao (2025),
DOI [10.32604/cmc.2025.065561](https://doi.org/10.32604/cmc.2025.065561),
to this repository's 3D underwater acoustic simulator. The paper supplies the
equations; it does **not** reproduce the paper's 2D radio experiments. Routes
are scored by this repository's `Evaluator`.

## Files

| File | Contents |
|---|---|
| `algorithms/clustering/ac_aco/ac_aco.py` | Schedules (Eq. 13-15), logistic chaos, and `ACACOClustering` (pheromone, chaos state, ant walk) |
| `algorithms/clustering/ac_aco/parameters.py` | Validated `ACACOParameters` |
| `algorithms/ac_aco.py` | `ACACO(Algorithm)`: per-round ant loop, routing, best-tree selection, failure counters |

## Round lifecycle

`Simulator.run` calls `ACACO.plan_round(live_sensors, residual_e)` once per
network round (`T_max` rounds at most). There is no inner iteration loop.

1. `pre_round` increments a one-based round counter (iteration 1 = simulator
   round 0), drops nodes with no energy, and computes `target =
   min(live, max(1, round(ch_proportion * live)))`, `rho`, `beta` and the chaos
   strength. Returns a `RoundState`, or `None` if nothing is alive.
2. Sample distinct start nodes, up to `min(num_ants, live_count)`. For each
   start, up to `max_clustering_attempts` tries, keeping that same start:
   `create_clusters` walks an ordered CH path and calls `build_clusters`;
   `dropping_member_multi_hop_routing` builds the tree; the tree is scored by
   `Evaluator.energy_consumption`. The first feasible attempt (root exists,
   cost finite and > 0) is kept as that ant's candidate.
3. The candidate with the lowest `(cost, CH path)` wins.
4. `post_round` runs exactly once, even if every ant failed: it updates the
   cost window, updates pheromone, and prints the debug line.
5. `plan_round` returns `(root, consumption)` of the winner, or `(None, {})`
   if no ant produced a feasible tree.

The counters `total_/failed_clustering_attempts` and
`total_/failed_routing_attempts` from `Algorithm` are maintained.

## Parameters (defaults from `ACACOParameters`)

| Parameter | Default | Role |
|---|---:|---|
| `num_ants` | 40 | Candidates constructed per round |
| `max_clustering_attempts` | 10 | Retries per ant until routing is feasible |
| `ch_proportion` | 0.20 | Target fraction of live nodes that become CHs |
| `pheromone_exponent` | 1.0 | Exponent on tau (labelled `alpha` in the debug line) |
| `energy_cost_exponent` | 0.5 | Tuned ACO exponent on the inverse hop cost (`gamma` in the debug line) |
| `beta_min`, `beta_max`, `beta_slope` | 1, 5, 5 | Eq. (14) heuristic-weight schedule |
| `rho_min`, `rho_max` | 0.10, 0.90 | Eq. (13) evaporation schedule |
| `chaos_min`, `chaos_max` | 0.05, 0.30 | Range of the chaos strength (Eq. 15) |
| `chaos_r`, `chaos_seed` | 3.61, 0.37 | Logistic map parameter and seed |
| `Q`, `tau0` | 0.07, 1 | Tuned ACO deposit constant and initial pheromone |
| `tau_min`, `tau_max` | 0.10, 10 | Pheromone bounds |
| `hopping_factor` | 0.40 | Energy/distance trade-off in the shared router |

Parameters are validated in `__post_init__` (bounds, `chaos_r` in (3.57, 4), etc.).

## Ant walk

Ant starts are sampled uniformly without replacement from live nodes. Each next CH `j`, from
the previous CH `i`, is sampled from the remaining live nodes with weight

```text
tau(i, j)^pheromone_exponent
  * (residual_energy[j] / distance(i, j))^beta(t)
  * (1 / E_m(distance(i, j)))^energy_cost_exponent
```

computed in log space for numerical stability. The normalized probabilities
then receive the original chaotic disturbance `p_j + strength * chaos[i]` and
are renormalized: `(p_j + c) / (1 + n*c)` for `n` candidates and
`c = strength * chaos[i]`. Its uniform-exploration mass depends on candidate
count. A `(p_j+c/n)/(1+c)` trial weakened exploration and shortened routing
service in three paired seeds; it was rejected from the final transfer.

## Performance-critical data

`ACACOClustering.__init__` converts the immutable network distance matrix to
NumPy arrays and computes `E_m(distance)` plus its logarithm once for every
edge. During each ant walk, `_transition_probabilities` indexes those cached
arrays for the currently available targets and evaluates the log weights in a
vectorized NumPy operation. This preserves the selection formula while
removing repeated scalar `E_m` calculations from the hot path. Each per-ant
deposit also updates the pheromone array immediately, so later ants learn from
successful candidates within the same round, as in tuned ACO.

The optimization requires `numpy` (declared in the repository-root
`requirements.txt`). It does not vectorize clustering or multi-hop routing;
their work still scales with the number of ants and routing attempts.

## Schedules

- `rho(t) = rho_max - min(t / T_max, 1) * (rho_max - rho_min)` (Eq. 13)
- `beta(t) = beta_min + (beta_max - beta_min) * sigmoid(slope * (t - T_max/2))` (Eq. 14)
- Chaos strength (Eq. 15) is a linear map of the *previous round's* best
  energy inside the `[lower, upper]` window of feasible candidate costs seen
  so far. It is `chaos_min` on the first round, after a failed round, or while
  the window is degenerate. This window is a UWSN adaptation, since the
  paper leaves it undefined.

`T_max` comes from `HyperParameters`, so the schedule horizon matches the
simulator's round limit.

## Pheromone update (once per round)

For every ordered pair `(i, j)` of live nodes:

```text
tau(i, j) <- clamp( (1 - rho) * tau(i, j)
                    + [Q / cost  if (i, j) is a consecutive pair in the
                       winning CH path, else 0]
                    + strength * chaos[i],
                    tau_min, tau_max )
```

`cost` is the total energy of the winning routing tree. Each successful ant
also deposits `Q / (cost * num_ants)` immediately after its route is scored.
Each deposit is clamped to the pheromone bounds; the evaporation/chaos update
is clamped separately before the winning-path deposit. Then `chaos[i]`
advances by one logistic step for each live `i`. If every ant
failed, there is no per-ant deposit, but evaporation and chaos still apply.
Relay and outlier edges are never reinforced, because ants only choose the CH
path.

## Usage

```python
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters

algorithm = ACACO(network, hparameters, ACACOParameters(), seed=42)
root, consumption = algorithm.plan_round(live_sensors, residual_e)
```

Explicit `seed` creates a private RNG; the same seed and map reproduce a run.
With `seed=None`, draws use global `random`, preserving `random.seed` callers.
`SimpleACO` now accepts the same explicit seed API. `run.py --seed 0` supplies
one seed consistently; its algorithm list remains unchanged. For a focused
five-seed ACO/AC-ACO experiment, use the comparison script linked below.
Use a fresh instance per simulation run: the round counter, pheromone and
chaos state persist across `plan_round` calls.

## Debug output

`[AC-ACO DEBUG]` is printed on round 1, every 100th round, and any failed
round. It shows `alpha`, `beta`, `gamma`, `rho`, chaos strength, ants, CH
count, number of feasible candidates, best energy, and pheromone min / max /
mean over live directed edges (taken after the update).

## Differences from SimpleACO

- AC-ACO: `tau^alpha * (residual/distance)^beta(t) * E_m^-gamma`.
  SimpleACO: `tau^alpha * (residual/distance)^gamma * E_m^-beta`. The exponent
  names are swapped between the two, so do not compare labels alone.
- AC-ACO adds a chaos term, decaying `rho`, and growing `beta`. Both now use
  distinct starts, the tuned inverse-energy exponent .5 and Q=.07.
- Both keep pheromone across rounds, clamp it, deposit `Q / cost` on the
  round-best CH path, and select the minimum current-round energy, which does
  not directly optimize lifetime.

These are implementation differences, not evidence that either algorithm
performs better.

Audit, parameter-role mapping and controlled ablations are in
[the transfer report](../../../../plans/reports/audit-261007-0810-tuned-aco-transfer.md).
[The comparison harness](../../../../plans/reports/aco-transfer-261007-0810/compare.py)
preserves the old AC-ACO source and uses identical seeds, topology and model.
