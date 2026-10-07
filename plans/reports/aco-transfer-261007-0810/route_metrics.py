"""Independent route/accounting checks and scientific diagnostics."""
from math import isclose, isfinite
from statistics import mean, pstdev


def inspect_route(root, live, network, evaluator, consumption):
    seen, costs, packets, nodes, hops = set(), {}, {}, [], []

    def visit(node):
        assert node.id not in seen, f"duplicate/cycle: {node.id}"
        seen.add(node.id)
        received = 0
        for child in node.nxts:
            assert child.prev is node, f"broken parent: {child.id}"
            received += visit(child)
        if node.id == -1:
            return 1
        assert node.id in live, f"non-live node: {node.id}"
        distance = (network.base_dists[node.id] if node.prev.id == -1 else
                    network.dist_matrix[node.id][node.prev.id])
        assert distance <= network.radius + 1e-10, f"out of range: {node.id}"
        sent = 2 if node.isCH else 1 + (received if node.isRelay else 0)
        cost = evaluator.E_tx(distance, sent) + evaluator.E_rx(received)
        if node.isCH:
            cost += evaluator.E_da(received)
        assert isfinite(cost) and cost >= 0
        costs[node.id] = cost
        packets[node.id] = (sent, received)
        hops.append(distance)
        nodes.append(node)
        return sent

    assert root.id == -1 and root.prev is None
    visit(root)
    assert seen - {-1} == set(live), "missing nodes in routing tree"
    assert set(consumption) == set(live), "missing node energy"
    assert all(isclose(costs[i], consumption[i], rel_tol=1e-12, abs_tol=1e-15)
               for i in live), "packet accounting mismatch"
    heads = [n for n in nodes if n.isCH]
    members = [n for n in nodes if not n.isCH and n.prev.isCH]
    sizes = [sum(not child.isCH for child in head.nxts) for head in heads]
    tx = sum(evaluator.E_tx(d, packets[n.id][0]) for n, d in zip(nodes, hops))
    rx = sum(evaluator.E_rx(packets[n.id][1]) for n in nodes)
    da = sum(evaluator.E_da(packets[n.id][1]) for n in heads)
    return dict(
        ch_count=len(heads), member_count=len(members),
        node_ch_distance=mean(network.dist_matrix[n.id][n.prev.id] for n in members)
        if members else 0.0,
        ch_bs_distance=mean(network.base_dists[n.id] for n in heads) if heads else 0.0,
        ch_parent_distance=mean(network.base_dists[n.id] if n.prev.id == -1 else
                                network.dist_matrix[n.id][n.prev.id] for n in heads)
        if heads else 0.0,
        cluster_sizes=sizes, cluster_size_std=pstdev(sizes) if sizes else 0.0,
        unclustered_nodes=len(live) - len(heads) - len(members),
        tx_energy=tx, rx_energy=rx, aggregation_energy=da,
        mean_hop_distance=mean(hops) if hops else 0.0,
    )
