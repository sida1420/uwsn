
""" plus direct and multi-hop CH routing."""
from node import Node

# def direct_routing(CHs, live_sensors, dist_matrix, base_dists, radius):
#     """
#     Build the full routing tree for one round: base station -> CHs ->
#     member sensors. Returns the base-station root Node (id=-1), or None
#     if the clustering is infeasible (some node/CH out of range).
#     """
#     if not CHs:
#         return None

#     CH_nodes, _, _ = build_clusters(CHs, live_sensors, dist_matrix, radius)
#     if CH_nodes is None:
#         return None

#     base = Node(-1)
#     for ch_id, ch_node in CH_nodes.items():
#         if base_dists[ch_id] > radius:
#             return None
#         ch_node.set_previous(base)
#         base.add_next(ch_node)

#     return base



def multi_hop_routing(
    CH_nodes,
    nodes,
    live_sensors,
    outliers,
    dist_matrix,
    base_dists,
    residual_e,
    radius,
    hopping_factor=0.4,
):
    """
    Build a clustered, multi-hop routing tree in a 3D deployment.

    Ordinary sensors are assigned to their nearest cluster head by
    build_clusters before this runs. A cluster head -- or an outlier
    sensor that build_clusters couldn't assign to any cluster -- that
    cannot reach the base directly relays through the nearest available
    node, of *any* kind (cluster head, ordinary sensor, or another
    outlier), that is both within communication range and strictly
    closer to the base. The strict distance reduction guarantees that
    relay links cannot form a cycle.

    Outliers take part in routing the same way a cluster head does,
    instead of causing the round to be marked infeasible.

    dist_matrix and base_dists are computed from all three Point
    coordinates by NetworkInstance, so range checks and relay costs
    here are true 3D distances.
    """
    base = Node(-1)

    outlier_nodes = {outlier_id: Node(outlier_id) for outlier_id in outliers}
    # every node that could plausibly serve as a relay hop, including the
    # freshly-created outlier nodes -- built locally so the caller doesn't
    # have to know about outliers in advance
    nodes = {**nodes, **outlier_nodes}

    for id, node in (CH_nodes | outlier_nodes).items():
        distance_to_base = base_dists[id]
        if distance_to_base <= radius:
            node.set_previous(base)
            base.add_next(node)
            continue

        candidates = []
        for candidate_id in live_sensors:
            
            if candidate_id == id:
                continue
            if dist_matrix[id][candidate_id] > radius:
                continue
                
            if base_dists[candidate_id] > distance_to_base:
                continue
            if residual_e[candidate_id] <= 0:
                continue
            if not nodes[candidate_id].isCH and nodes[candidate_id].prev is not None and nodes[candidate_id].prev.isCH and distance_to_base<=base_dists[nodes[candidate_id].prev.id]:
                continue

            candidates.append(candidate_id)
        if not candidates:
            return None

        total_candidate_energy = sum(residual_e[candidate_id] for candidate_id in candidates)

        def relay_cost(candidate_id):
            energy_cost = total_candidate_energy / max(residual_e[candidate_id], 1e-12)
            distance_cost = (
                dist_matrix[id][candidate_id] ** 2
                + base_dists[candidate_id] ** 2
            ) / max(distance_to_base**2, 1e-12)
            return hopping_factor * energy_cost + (1 - hopping_factor) * distance_cost

        parent_id = min(candidates, key=relay_cost)
        parent = nodes[parent_id]
        parent.isRelay = True
        node.set_previous(parent)
        parent.add_next(node)

    return base