from math import sqrt

from algorithms.ac_aco.cluster_tree import build_cluster_tree


def phase1_cost(
    network,
    evaluator,
    parameters,
    heads,
    assignments,
    live_nodes,
    residual_e_by_id,
    target_head_count,
    network_diagonal,
):
    """Normalized energy-distance-load objective; lower is better."""
    root = build_cluster_tree(heads, assignments)
    _, round_energy = evaluator.energy_consumption(
        root, network.dist_matrix, network.base_dists
    )
    max_node_cost = (
        evaluator.E_tx(network_diagonal) + evaluator.E_rx() + evaluator.E_da()
    )
    transmission_cost = round_energy / max(len(live_nodes) * max_node_cost, 1e-12)
    energy_ratios = [
        min(1.0, max(0.0, residual_e) / max(network.init_energy, 1e-12))
        for residual_e in (residual_e_by_id[ch] for ch in heads)
    ]
    selected_energy_cost = 1.0 - (
        sum(energy_ratios) / len(energy_ratios) + min(energy_ratios)
    ) / 2.0
    energy_cost = (transmission_cost + selected_energy_cost) / 2.0

    member_distances = [
        network.dist_matrix[node_id][ch_id]
        for node_id, ch_id in assignments.items()
        if node_id != ch_id
    ]
    member_distance_cost = (
        sum(member_distances)
        / len(member_distances)
        / max(network.radius, 1e-12)
        if member_distances
        else 0.0
    )
    sink_distance_cost = (
        sum(network.base_dists[ch] for ch in heads)
        / len(heads)
        / network_diagonal
    )
    distance_cost = (member_distance_cost + sink_distance_cost) / 2.0

    loads = [sum(ch == head for ch in assignments.values()) for head in heads]
    mean_load = len(live_nodes) / len(heads)
    load_cv = (
        sqrt(sum((load - mean_load) ** 2 for load in loads) / len(loads))
        / mean_load
    )
    load_cost = load_cv / (1.0 + load_cv)
    extra_head_cost = max(0, len(heads) - target_head_count) / len(live_nodes)

    weight_sum = (
        parameters.energy_weight
        + parameters.distance_weight
        + parameters.load_balance_weight
        + parameters.extra_head_weight
    )
    return (
        parameters.energy_weight * energy_cost
        + parameters.distance_weight * distance_cost
        + parameters.load_balance_weight * load_cost
        + parameters.extra_head_weight * extra_head_cost
    ) / weight_sum
