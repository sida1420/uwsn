"""Scientific contracts for opt-in AC-ACO policies, without changing physics."""
import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from algorithms.ac_aco import ACACO
from algorithms.clustering import build_clusters
from algorithms.clustering.ac_aco.ac_aco import logistic_step
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.research_acaco.diagnostics import PoolObserver
from algorithms.research_acaco.operators import evaporation_only
from algorithms.research_acaco.surrogate import MarginalEnergyProxy
from algorithms.research_acaco.variants import ResearchACACO, ResearchOptions
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point


def network(xs=range(1, 9), radius=200):
    return NetworkInstance([Point(x, 0, 0) for x in xs], Point(0, 0, 0),
                           .6, 500, 500, 500, radius)


def params(**kwargs):
    return ACACOParameters(num_ants=6, max_clustering_attempts=3,
                           ch_proportion=.5, **kwargs)


def signature(root):
    return None if root is None else (root.id, root.isCH, root.isRelay,
                                     tuple(signature(n) for n in root.nxts))


@pytest.mark.parametrize("audited", [False, True])
def test_default_exact_baseline_and_observer_is_read_only(audited):
    p = params(**(dict(load_weight=0, tau_min=.01) if audited else {}))
    algorithms = [ACACO(network(), HyperParameters(), p, 24),
                  ResearchACACO(network(), HyperParameters(), p, 24)]
    observers = [PoolObserver(a) for a in algorithms]
    plain = ACACO(network(), HyperParameters(), p, 24)
    count = [0]
    evaluate = plain.evaluator.energy_consumption
    def counted(*args):
        count[0] += 1
        return evaluate(*args)
    plain.evaluator.energy_consumption = counted
    residual = [.6] * 8
    for _ in range(3):
        outcomes = [o.run(list(range(8)), residual) for o in observers]
        tree, consumption = plain.plan_round(list(range(8)), residual)
        assert outcomes[0][2]["candidate_records"] == outcomes[1][2]["candidate_records"]
        for a, (root, energy, summary) in zip(algorithms, outcomes):
            assert signature(root) == signature(tree) and energy == consumption
            assert a.clustering.rng.getstate() == plain.clustering.rng.getstate()
            assert a.clustering.pheromone == plain.clustering.pheromone
            assert a.clustering.chaos == plain.clustering.chaos
            assert summary["evaluation_count"] == p.num_ants
            assert all(r["conservation_valid"] and r["radius_valid"]
                       and r["all_live_present"] and r["topology_valid"]
                       for r in summary["candidate_records"])
        assert residual == [.6] * 8
    assert count[0] == 3 * p.num_ants
    for observer in observers:
        observer.close()


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


@pytest.mark.parametrize("policy", ["baseline", "reduced", "normalized", "evaporation"])
def test_nonadaptive_unused_exploration_max_zero(policy):
    options = ResearchOptions(chaos_policy=policy, exploration_max=0)
    a = ResearchACACO(network(), HyperParameters(), params(load_weight=0), 24, options)
    assert a.plan_round(list(range(8)), [.6] * 8)[0] is not None
    with pytest.raises(ValueError):
        ResearchOptions(chaos_policy="adaptive", exploration_max=0)


def test_evaporation_exclusive_and_distinct_retry_starts():
    a = ResearchACACO(network(), HyperParameters(), params(load_weight=0, tau_min=.01, tau0=.5), 24,
                     ResearchOptions(chaos_policy="evaporation"))
    c, residual = a.clustering, [.6] * 8
    state = c.pre_round(range(8), residual)
    base = ACACO(network(), HyperParameters(), a.params, 24).clustering
    base.pre_round(range(8), residual)
    np.testing.assert_allclose(c._transition_probabilities(0, [1, 2], residual, 1, .3),
                              base._transition_probabilities(0, [1, 2], residual, 1, 0))
    previous = c.chaos.copy()
    c._update_pheromone(state)
    for i, chaos in enumerate(previous):
        rho = evaporation_only(state.rho, chaos, .5, .1, .6)
        assert c.pheromone[i][(i + 1) % 8] == pytest.approx(.5 * (1 - rho))
        assert c.chaos[i] == logistic_step(chaos, a.params.chaos_r)
    c = ResearchACACO(network(), HyperParameters(), params(), 24,
                     ResearchOptions(distinct_starts=True)).clustering
    state = c.pre_round(range(8), residual)
    starts = [c._construct_candidate(state, residual)[0] for _ in range(6)]
    assert starts[:3] == [starts[0]] * 3 and starts[3:] == [starts[3]] * 3
    assert starts[0] != starts[3]
    c.deposit((starts[3], 0), .01)
    assert c._construct_candidate(state, residual)[0] not in starts
    successful = []
    for _ in range(4):
        chs = c._construct_candidate(state, residual)
        successful.append(chs[0])
        c.deposit(chs, .01)
    assert len(set(successful)) == len(successful)


@pytest.mark.parametrize("options", [ResearchOptions(heuristic="marginal"),
    *[ResearchOptions(chaos_policy=p) for p in ("reduced", "normalized", "adaptive", "evaporation")],
    ResearchOptions(distinct_starts=True), ResearchOptions(random_sets=True),
    ResearchOptions(heuristic="marginal", chaos_policy="adaptive"),
    ResearchOptions(heuristic="marginal", chaos_policy="evaporation")])
def test_variant_reproducibility_edges_and_final_evaluation_budget(options):
    for n, residual in [(network(), [.6] * 8), (network(range(20, 231, 30), 90), [.6] * 8),
                        (network([1]), [1e-300]),
                        (network([300, 600], 1), [.6, .6]), (network([1]), [0.])]:
        results = []
        for _ in range(2):
            a = ResearchACACO(n, HyperParameters(), params(load_weight=0), 33, options)
            observer = PoolObserver(a)
            root, consumption, summary = observer.run(list(range(n.N)), residual)
            assert summary["invalid_probability_count"] == 0
            assert summary["evaluation_count"] <= a.params.num_ants
            assert all(all(r[k] for k in ("conservation_valid", "topology_valid", "radius_valid",
                       "all_live_present")) for r in summary["candidate_records"])
            results.append((signature(root), consumption, summary["candidate_records"],
                            a.clustering.rng.getstate(), a.clustering.pheromone))
            observer.close()
        assert results[0] == results[1]
