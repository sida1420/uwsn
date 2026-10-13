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
2. For each of `num_ants` ants, up to `max_clustering_attempts` tries:
   `create_clusters` walks an ordered CH path and calls `build_clusters`;
   `dropping_member_multi_hop_routing` builds the tree; the tree is scored by
   `Evaluator.energy_consumption`. The first feasible attempt (root exists,
   cost finite and > 0) is kept as that ant's candidate.
3. With `load_weight=0`, the lowest `(cost, CH path)` wins. Positive weights
   use normalized energy and absolute load CV, following D-ACO's selection score.
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
| `energy_cost_exponent` | 0.1 | Exponent on the inverse hop cost (`gamma` in the debug line) |
| `beta_min`, `beta_max`, `beta_slope` | 1, 5, 5 | Eq. (14) heuristic-weight schedule |
| `rho_min`, `rho_max` | 0.10, 0.60 | Eq. (13) evaporation schedule |
| `chaos_min`, `chaos_max` | 0.05, 0.30 | Range of the chaos strength (Eq. 15) |
| `chaos_r`, `chaos_seed` | 3.61, 0.37 | Logistic map parameter and seed |
| `Q`, `tau0` | 0.01, 1 | Deposit constant and initial pheromone |
| `elite_weight` | 0.1 | Extra best-set deposit multiplier (D-ACO's theta); tunable in [0,1] |
| `load_weight` | 0.0 | Load-CV share in normalized energy/load selection; tunable in [0,1] |
| `tau_min`, `tau_max` | 0.01, 20 | Calibrated pheromone bounds |
| `hopping_factor` | 0.40 | Energy/distance trade-off in the shared router |

Parameters are validated in `__post_init__` (bounds, `chaos_r` in (3.57, 4), etc.).

The deposit constant, pheromone floor/ceiling and evaporation maximum were
calibrated together on the existing map. The old values (`Q=100`, floor `.1`,
ceiling `10`, maximum evaporation `.9`) remain an explicit historical control
in `plans/phase5-acaco-tuning/calibrate.py`. The new ceiling accounts for both
ant and elite deposits plus additive chaos at late-round evaporation. These
are practical defaults for this cost scale, not universally optimal values.
See [calibration derivation and results](../../../../plans/phase5-acaco-tuning/README.md).
Valid bounds require `0 < tau_min < tau_max` and `tau_min <= tau0 <= tau_max`.

## Ant walk

The first CH is chosen uniformly from the live nodes. Each next CH `j`, from
the previous CH `i`, is sampled from the remaining live nodes with weight

```text
tau(i, j)^pheromone_exponent
  * (residual_energy[j] / distance(i, j))^beta(t)
  * (1 / E_m(distance(i, j)))^energy_cost_exponent
```

computed in log space for numerical stability. The normalized probabilities
then receive the chaotic disturbance `p_j + strength * chaos[i]` and are
renormalized, which mixes the distribution towards uniform:
`(p_j + c) / (1 + n*c)` for `n` candidates.

## Performance-critical data

`ACACOClustering.__init__` converts the immutable network distance matrix to
NumPy arrays and computes `E_m(distance)` plus its logarithm once for every
edge. During each ant walk, `_transition_probabilities` indexes those cached
arrays for the currently available targets and evaluates the log weights in a
vectorized NumPy operation. This preserves the selection formula while
removing repeated scalar `E_m` calculations from the hot path.

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

Each feasible ant first adds `Q / (cost * num_ants)` on consecutive pairs of
its ordered CH path. Selection probabilities read the live pheromone row,
so these deposits influence later ants in the same round and future rounds.
Physical residual energy stays fixed while candidates are searched. Then, for every
distinct ordered pair `(i, j)` of live nodes:

```text
tau(i, j) <- clamp( (1 - rho) * tau(i, j)
                    + strength * chaos[i],
                    tau_min, tau_max )
```

The elite then adds `elite_weight * Q / best_cost` on its CH path, clamped to `tau_max`.
`best_cost` is the total energy of the winning routing tree. This ordering
matters: ant deposits evaporate; the elite deposit does not. Then
`chaos[i]` has advanced by one logistic step for each live `i`. If every ant
failed, there is no per-ant deposit, but evaporation and chaos still apply.
Relay and outlier edges are never reinforced, because ants only choose the CH
path.

With positive `load_weight=w`, candidate fitness is
`(1-w)*energy/mean_energy + w*load_cv/mean_load_cv`, where load CV is the
standard deviation of per-node round costs divided by their mean. If all CVs
are zero, the normalized CV contribution is constant. Deposits still use
physical energy, preserving the calibrated pheromone scale. Absolute load CV
does not account for uneven residual energy; it is not a lifetime guarantee.
The balance and inner-iteration study is in
`plans/phase5-acaco-balance/README.md`.
The default elite weight is 0.1 to reduce best-set dominance. Load fitness
remains opt-in with `ACACOParameters(load_weight=0.1)`; the study found a
small energy cost for lower load variation, without establishing a lifetime gain.

## Usage

```python
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters

algorithm = ACACO(network, hparameters, ACACOParameters(), seed=42)
root, consumption = algorithm.plan_round(live_sensors, residual_e)
```

`seed` (default `None`) seeds the ant RNG; the same seed and map reproduce a run. Use a fresh instance per simulation run: the round counter, pheromone and
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
- AC-ACO adds a chaos term, decaying `rho`, growing `beta`, and samples start
  nodes with replacement. SimpleACO uses fixed parameters and distinct starts.
- Both keep pheromone across rounds and clamp it. AC-ACO scales its
  round-best CH-path deposit by `elite_weight`; SimpleACO uses `Q / cost`.
  AC-ACO selects minimum current-round energy by default, with optional load
  fitness. Neither objective directly optimizes lifetime.

These are implementation differences, not evidence that either algorithm
performs better.
