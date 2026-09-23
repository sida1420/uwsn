"""Shared cluster construction plus direct and multi-hop CH routing."""
from node import Node


def build_clusters(CHs, live_nodes, dist_matrix, radius):
    """
    Assign each live, non-CH node to its nearest CH, within `radius`.

    Returns {CH_id: Node}, each CH Node populated with its member
    sensors as children, or None if some node can't reach any CH.
    """
    CH_set = set(CHs)
    CH_nodes = {ch_id: Node(ch_id, isCH=True) for ch_id in CHs}

    for i in live_nodes:
        if i in CH_set:
            continue

        nearest_ch = min(CHs, key=lambda ch: dist_matrix[i][ch])
        nearest_dist = dist_matrix[i][nearest_ch]
        if nearest_dist > radius:
            return None

        member = Node(i)
        member.set_previous(CH_nodes[nearest_ch])
        CH_nodes[nearest_ch].add_next(member)

    return CH_nodes


def direct_routing(CHs, live_nodes, dist_matrix, base_dists, radius):
    """
    Build the full routing tree for one round: base station -> CHs ->
    member sensors. Returns the base-station root Node (id=-1), or None
    if the clustering is infeasible (some node/CH out of range).
    """
    if not CHs:
        return None

    CH_nodes = build_clusters(CHs, live_nodes, dist_matrix, radius)
    if CH_nodes is None:
        return None

    base = Node(-1)
    for ch_id, ch_node in CH_nodes.items():
        if base_dists[ch_id] > radius:
            return None
        ch_node.set_previous(base)
        base.add_next(ch_node)

    return base


def multi_hop_routing(
    CHs,
    live_nodes,
    dist_matrix,
    base_dists,
    residual_e,
    radius,
    hopping_factor=0.4,
):
    """
    Build a clustered, multi-hop routing tree in a 3D deployment.

    Ordinary sensors are assigned to their nearest cluster head. A cluster
    head that cannot reach the base directly relays through another cluster
    head that is both within communication range and strictly closer to the
    base. The strict distance reduction guarantees that relay links cannot
    form a cycle.

    ``dist_matrix`` and ``base_dists`` are computed from all three Point
    coordinates by NetworkInstance, so range checks and relay costs here are
    true 3D distances.
    """
    if not CHs:
        return None

    CH_nodes = build_clusters(CHs, live_nodes, dist_matrix, radius)
    if CH_nodes is None:
        return None

    base = Node(-1)
    for ch_id, ch_node in CH_nodes.items():
        distance_to_base = base_dists[ch_id]
        if distance_to_base <= radius:
            ch_node.set_previous(base)
            base.add_next(ch_node)
            continue

        candidates = [
            candidate_id
            for candidate_id in CHs
            if candidate_id != ch_id
            and dist_matrix[ch_id][candidate_id] <= radius
            and base_dists[candidate_id] < distance_to_base
            and residual_e[candidate_id] > 0
        ]
        if not candidates:
            return None

        total_candidate_energy = sum(residual_e[candidate_id] for candidate_id in candidates)

        def relay_cost(candidate_id):
            energy_cost = total_candidate_energy / max(residual_e[candidate_id], 1e-12)
            distance_cost = (
                dist_matrix[ch_id][candidate_id] ** 2
                + base_dists[candidate_id] ** 2
            ) / max(distance_to_base**2, 1e-12)
            return hopping_factor * energy_cost + (1 - hopping_factor) * distance_cost

        parent_id = min(candidates, key=relay_cost)
        parent = CH_nodes[parent_id]
        ch_node.set_previous(parent)
        parent.add_next(ch_node)

    return base
