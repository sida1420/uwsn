"""Read-only packet accounting and tree checks; never call the final evaluator."""
from math import isclose
import numpy as np


def stats(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not values.size:
        return {key: None for key in ("min", "mean", "p10", "median", "std", "max")}
    return dict(min=float(values.min()), mean=float(values.mean()),
                p10=float(np.percentile(values, 10)), median=float(np.median(values)),
                std=float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                max=float(values.max()))


def describe_tree(root, consumption, total, distances, base_distances, hp, radius,
                  live, chs, initial_parents):
    pieces, links, parents, relays, seen = [], [], {}, [], set()
    topology_valid = True

    def visit(node):
        nonlocal topology_valid
        if node.id in seen:
            topology_valid = False
            return 0
        seen.add(node.id)
        topology_valid &= all(child.prev is node for child in node.nxts)
        incoming = sum(visit(child) for child in node.nxts)
        packets = 2 if node.isCH else 1 + incoming if node.isRelay else 1
        if node.id == -1:
            return packets
        parent = node.prev
        parents[node.id] = parent.id if parent is not None else None
        topology_valid &= parent is not None and node in parent.nxts
        distance = base_distances[node.id] if parent is None or parent.id == -1 else distances[node.id][parent.id]
        links.append(float(distance))
        dkm = distance / 1000
        tx = (hp.P_0 * dkm ** hp.spreadking_factor * hp.attenuation_coeff ** dkm
              * hp.packet_size * packets / hp.trasmission_rate)
        rx = hp.packet_size * hp.E_elec * incoming
        da = hp.packet_size * hp.E_integrate * incoming if node.isCH else 0.0
        pieces.append((tx, rx, da))
        topology_valid &= isclose(tx + rx + da, consumption[node.id], rel_tol=1e-10, abs_tol=1e-12)
        if node.isRelay:
            relays.append(int(node.id))
        return packets

    visit(root)
    tx, rx, da = np.sum(pieces, axis=0).tolist() if pieces else (0.0, 0.0, 0.0)
    drops = [int(i) for i, parent in initial_parents.items()
             if parent is not None and parents.get(i) != parent and i not in chs]
    pairs = list(zip(chs, chs[1:]))
    return dict(tx=tx, rx=rx, da=da, link_distance=stats(links),
        relay_ids=relays, dropped_member_ids=drops,
        conservation_valid=isclose(tx + rx + da, total, rel_tol=1e-10, abs_tol=1e-12),
        topology_valid=bool(topology_valid and root.id == -1 and seen - {-1} == set(live)),
        all_live_present=set(consumption) == set(live), radius_valid=all(d <= radius for d in links),
        construction_edge_overlap=(sum(parents.get(j) == i or parents.get(i) == j for i,j in pairs)
                                   / len(pairs) if pairs else None),
        construction_directed_overlap=(sum(parents.get(j) == i for i,j in pairs)
                                       / len(pairs) if pairs else None),
        construction_step_distance=stats([distances[i][j] for i,j in pairs]))
