from algorithms.ac_aco.adaptive import (
    chaos_weight,
    evaporation_rate,
    logistic_step,
)


def initial_chaos(count, seed, r):
    values = []
    value = seed
    for _ in range(count):
        value = logistic_step(value, r)
        values.append(value)
    return values


def update_pheromone(
    start_pheromone,
    pheromone,
    chaos,
    solutions,
    live_nodes,
    residual_e,
    network,
    parameters,
    progress,
):
    """Apply evaporation, logistic disturbance, then all-ant edge deposits."""
    rho = evaporation_rate(progress, parameters.rho_min, parameters.rho_max)
    energy_ratio = sum(max(0.0, value) for value in residual_e) / max(
        network.N * network.init_energy, 1e-12
    )
    disturbance = chaos_weight(
        energy_ratio, parameters.chaos_min, parameters.chaos_max
    )

    for node_id in live_nodes:
        chaos[node_id] = logistic_step(chaos[node_id], parameters.chaos_r)
        start_pheromone[node_id] = _bounded(
            (1.0 - rho) * start_pheromone[node_id]
            + disturbance * chaos[node_id],
            parameters,
        )
        for next_id in live_nodes:
            pheromone[node_id][next_id] = _bounded(
                (1.0 - rho) * pheromone[node_id][next_id]
                + disturbance * chaos[node_id],
                parameters,
            )

    for solution in solutions:
        deposit = parameters.deposit_strength / (1.0 + solution.cost)
        path = solution.aco_heads
        start_pheromone[path[0]] = _bounded(
            start_pheromone[path[0]] + deposit, parameters
        )
        for source, target in zip(path, path[1:]):
            pheromone[source][target] = _bounded(
                pheromone[source][target] + deposit, parameters
            )


def _bounded(value, parameters):
    return min(max(value, parameters.tau_min), parameters.tau_max)

