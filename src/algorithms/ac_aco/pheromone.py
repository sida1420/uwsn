from algorithms.ac_aco.adaptive import logistic_step


def initial_chaos(count, seed, r):
    values = []
    value = seed
    for _ in range(count):
        value = logistic_step(value, r)
        values.append(value)
    return values


def update_pheromone(pheromone, chaos, live_nodes, parameters, rho, strength, path):
    """Apply Eq. (12) once, then deposit Q/Lk on the iteration-best path."""
    for source in live_nodes:
        disturbance = strength * chaos[source]
        for target in live_nodes:
            if source == target:
                continue
            pheromone[source][target] = _bounded(
                (1.0 - rho) * pheromone[source][target] + disturbance,
                parameters,
            )
        chaos[source] = logistic_step(chaos[source], parameters.chaos_r)

    if path is None or path.path_length <= 0:
        return
    deposit = parameters.Q / path.path_length
    for source, target in zip(path.cluster_heads, path.cluster_heads[1:]):
        pheromone[source][target] = _bounded(
            pheromone[source][target] + deposit, parameters
        )


def _bounded(value, parameters):
    return min(max(value, parameters.tau_min), parameters.tau_max)
