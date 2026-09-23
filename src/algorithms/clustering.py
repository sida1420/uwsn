"""
Direct (single-hop) clustering: every ordinary sensor is assigned to
its nearest cluster head (CH), and every CH talks straight to the base
station -- no CH-to-CH relaying. This is the routing scheme used by
SimpleACOClustering, but it's kept standalone so future algorithms that
only differ in *how they pick the CH set* can reuse it too.
"""
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
