from node import Node


def build_cluster_tree(cluster_heads, assignments):
    """Build the phase-1 compatibility tree: sink -> CH -> members."""
    root = Node(-1)
    ch_nodes = {idx: Node(idx, isCH=True) for idx in cluster_heads}

    for ch_node in ch_nodes.values():
        ch_node.set_previous(root)
        root.add_next(ch_node)

    for sensor_id, ch_id in assignments.items():
        if sensor_id == ch_id:
            continue
        member = Node(sensor_id)
        member.set_previous(ch_nodes[ch_id])
        ch_nodes[ch_id].add_next(member)

    return root

