# AC-ACO for the UWSN simulator

This package adapts the CH-selection parts of Zhou, Chen, and Cao (2025),
DOI [10.32604/cmc.2025.065561](https://doi.org/10.32604/cmc.2025.065561), to
this repository's 3D underwater acoustic simulator. `IT4906_WSN_final.pptx`
is presentation material only; the paper supplies the equations.

It does not reproduce the paper's 2D radio experiments or Figures 3–6. The
search scores feasible routes by this repository's `Evaluator`, and the
simulator deducts energy only for the selected route once per network round.

## Operation

`T_max=3500` controls network rounds. Each round creates at most 10 ants × 5
optimizer iterations. A candidate selects
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
| `num_ants`, `num_iterations` | 10, 5 | Candidate budget per round |
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

Pheromone is updated once per optimizer iteration. The iteration-best ordered
CH path receives `Q / L_k`, where `L_k` is the sum of its selected CH-to-CH
edge lengths (or a small positive guard for one CH). Relay and outlier edges do
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
