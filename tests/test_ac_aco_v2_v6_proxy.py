import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from algorithms.clustering import build_clusters
from algorithms.clustering.ac_aco.surrogate import MarginalEnergyProxy
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point


def network(xs=range(1, 9), radius=200):
    return NetworkInstance([Point(x, 0, 0) for x in xs], Point(0, 0, 0),
                           .6, 500, 500, 500, radius)


@pytest.mark.parametrize("xs,radius", [(range(1, 9), 200), ([1, 1, 3, 3, 300], 2)])
def test_incremental_proxy_matches_set_difference_and_disconnection(xs, radius):
    n = network(xs, radius)
    proxy = MarginalEnergyProxy(n, Evaluator(HyperParameters()), list(range(n.N)))
    rng = random.Random(9)
    for size in range(n.N):
        selected = tuple(rng.sample(range(n.N), size))
        available = [i for i in range(n.N) if i not in selected]
        predicted = proxy.additions(selected, available)
        expected = [proxy.energy(selected + (j,)) - proxy.energy(selected) for j in available]
        np.testing.assert_allclose(predicted, expected, atol=1e-15)
        assert np.isfinite(proxy.energy(selected))
    assert proxy.additions(tuple(range(n.N)), []).size == 0
    if radius == 2:
        assert proxy.unreachable[-1] and np.isfinite(proxy.paths[-1])


def test_all_direct_proxy_matches_packet_accounting():
    n, evaluator = network(), Evaluator(HyperParameters())
    proxy = MarginalEnergyProxy(n, evaluator, list(range(n.N)))
    for selected in ((0,), (0, 4), tuple(range(n.N))):
        heads, _, outliers = build_clusters(selected, range(n.N), n.dist_matrix, n.radius)
        assert not outliers
        root = Node(-1)
        for head in heads.values():
            head.prev = root
            root.nxts.append(head)
        _, cost = evaluator.energy_consumption(root, n.dist_matrix, n.base_dists)
        assert proxy.energy(selected) == pytest.approx(cost)


def test_empty_proxy_and_optimistic_direct_routing_counterexample():
    evaluator = Evaluator(HyperParameters())
    empty = MarginalEnergyProxy(network([]), evaluator, [])
    assert empty.energy(()) == 0 and empty.additions((), []).size == 0
    n = network([100, 200])
    proxy = MarginalEnergyProxy(n, evaluator, [0, 1])
    heads, _, _ = build_clusters((1,), [0, 1], n.dist_matrix, n.radius)
    root = Node(-1)
    heads[1].prev = root
    root.nxts.append(heads[1])
    _, final = evaluator.energy_consumption(root, n.dist_matrix, n.base_dists)
    # Proxy can choose optimistic relay paths even though router chooses sink directly.
    assert proxy.paths[1] < evaluator.E_tx(200) and proxy.energy((1,)) < final
