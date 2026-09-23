"""Shared cluster construction"""
from node import Node


def build_clusters(CHs, live_sensors, dist_matrix, radius):
    """
    Assign each live, non-CH node to its nearest CH, within `radius`.

    Returns {CH_id: Node}, each CH Node populated with its member
    sensors as children, or None if some node can't reach any CH.
    """
    CH_set = set(CHs)
    CH_nodes = {ch_id: Node(ch_id, isCH=True) for ch_id in CHs}

    outliers = []

    nodes={ch_id: ch_node for ch_id, ch_node in CH_nodes.items()}

    for i in live_sensors:
        if i in CH_set:
            continue

        nearest_ch = min(CHs, key=lambda ch: dist_matrix[i][ch])
        nearest_dist = dist_matrix[i][nearest_ch]
        if nearest_dist > radius:
            # print(f"Node {i} cannot reach any CH within radius {radius} (nearest CH {nearest_ch} at distance {nearest_dist})")
            # print(f"Distance matrix row for node to all the cluster head {i}: { [dist_matrix[i][ch] for ch in CHs] }")
            #Outlier node, cannot reach any CH within radius
            outliers.append(i)
            continue

        member = Node(i)
        member.set_previous(CH_nodes[nearest_ch])
        nodes[i] = member
        CH_nodes[nearest_ch].add_next(member)

    return CH_nodes, nodes, outliers

