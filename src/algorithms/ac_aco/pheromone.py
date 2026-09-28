from algorithms.ac_aco.adaptive import logistic_step


def initial_chaos(count, seed, r):
    values = []
    value = seed
    for _ in range(count):
        value = logistic_step(value, r)
        values.append(value)
    return values


def update_pheromone(pheromone, chaos, live_nodes, parameters, rho, strength, path):
    """Bound the complete Eq. (12), using Q/energy on the round-best path."""
    if path is None or path.cost <= 0:
        deposit = 0.0
        reinforced_edges = set()
    else:
        deposit = parameters.Q / max(path.cost, 1e-12)
        reinforced_edges = set(zip(path.cluster_heads, path.cluster_heads[1:]))

    for source in live_nodes:
        disturbance = strength * chaos[source]
        for target in live_nodes:
            if source == target:
                continue
            pheromone[source][target] = _bounded(
                (1.0 - rho) * pheromone[source][target]
                + (deposit if (source, target) in reinforced_edges else 0.0)
                + disturbance,
                parameters,
            )
        chaos[source] = logistic_step(chaos[source], parameters.chaos_r)


def _bounded(value, parameters):
    return min(max(value, parameters.tau_min), parameters.tau_max)
