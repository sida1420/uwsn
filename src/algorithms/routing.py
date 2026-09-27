
"""Shared direct and multi-hop routing helpers."""
import heapq

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
    cannot reach the base directly relays through a bounded-hop path of
    available live nodes. The path search starts at the base, so every
    created edge points toward an already rooted node and cannot form a
    cycle.

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

    connected = set()

    def detach(node):
        if node.prev is not None:
            node.prev.nxts.remove(node)

    def paths_from_base():
        """Return a lowest-cost rooted predecessor for every reachable sensor."""
        total_energy = sum(max(residual_e[node_id], 0.0) for node_id in live_sensors)
        costs, parents, queue = {}, {}, []
        for node_id in live_sensors:
            if base_dists[node_id] <= radius:
                cost = (1 - hopping_factor) * base_dists[node_id] / max(radius, 1e-12)
                costs[node_id], parents[node_id] = cost, -1
                heapq.heappush(queue, (cost, node_id))
        while queue:
            cost, node_id = heapq.heappop(queue)
            if cost != costs[node_id]:
                continue
            for neighbor_id in live_sensors:
                if neighbor_id == node_id or dist_matrix[node_id][neighbor_id] > radius:
                    continue
                edge_cost = (
                    hopping_factor * total_energy / max(residual_e[neighbor_id], 1e-12)
                    + (1 - hopping_factor) * dist_matrix[node_id][neighbor_id] / max(radius, 1e-12)
                )
                candidate_cost = cost + edge_cost
                if candidate_cost < costs.get(neighbor_id, float("inf")):
                    costs[neighbor_id], parents[neighbor_id] = candidate_cost, node_id
                    heapq.heappush(queue, (candidate_cost, neighbor_id))
        return parents

    parents = paths_from_base()
    for node_id in CH_nodes | outlier_nodes:
        if node_id not in parents:
            return None
        path = []
        current = node_id
        while current != -1:
            path.append(current)
            current = parents[current]
        for child_id in reversed(path):
            parent_id = parents[child_id]
            if child_id in connected:
                continue
            child = nodes[child_id]
            detach(child)
            parent = base if parent_id == -1 else nodes[parent_id]
            if parent_id != -1 and not parent.isCH:
                parent.isRelay = True
            child.set_previous(parent)
            parent.add_next(child)
            connected.add(child_id)

    return base
