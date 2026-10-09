"""Fitness safety, complete packet costs, and deterministic integration."""

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from math import nan, inf
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.node_ac_aco import NodeACACO
from algorithms.clustering.node_ac_aco.fitness import energy_load, score_candidate
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point
from simulate import Simulator


def network():
    return NetworkInstance([Point(10 + 10 * i, 0, 0) for i in range(4)],
                           Point(0, 0, 0), 1.0, 50, 10, 10, 100)


def tree():
    root, relay, head = Node(-1), Node(0, isRelay=True), Node(1, isCH=True)
    for parent, child in ((root, relay), (relay, head),
                          (head, Node(2)), (head, Node(3))):
        child.prev = parent
        parent.nxts.append(child)
    return root


class FitnessTests(unittest.TestCase):
    def setUp(self):
        self.network, self.hp = network(), HyperParameters()
        self.evaluator = Evaluator(self.hp)
        self.params = NodeACACOParameters()
        self.live, self.residual = list(range(4)), [1.0] * 4

    def score(self, root=None, evaluator=None, params=None):
        return score_candidate(root if root is not None else tree(), self.live,
                               self.residual, self.network, evaluator or self.evaluator,
                               params or self.params, heads=(1,))

    def test_equal_energy_balanced_and_concentrated_loads(self):
        balanced = energy_load(dict.fromkeys(self.live, 0.1), self.residual, self.live)
        uneven = energy_load(dict(enumerate([0.4, 0, 0, 0])), self.residual, self.live)
        self.assertAlmostEqual(balanced, 0)
        self.assertAlmostEqual(uneven, 1)
        self.assertGreater(uneven, balanced)

    def test_load_uses_relative_depletion_and_all_alive_nodes(self):
        self.assertAlmostEqual(energy_load({0: 0.1, 1: 0.2}, [1, 2], [0, 1]), 0)
        self.assertAlmostEqual(energy_load({0: 0.1, 1: 0}, [1, 1], [0, 1]), 1)
        self.assertAlmostEqual(energy_load({1: 0.2, 3: 0.2}, [0, 1, 0, 1], [1, 3]), 0)

    def test_singleton_zero_and_extreme_depletion(self):
        self.assertEqual(energy_load({0: 0.2}, [1], [0]), 0)
        self.assertEqual(energy_load({0: 0, 1: 0}, [1, 1], [0, 1]), 0)
        for value in (1e-300, 1e300):
            with self.subTest(value=value):
                self.assertAlmostEqual(energy_load({0: value, 1: value},
                                                   [value, value], [0, 1]), 0)
        self.assertAlmostEqual(energy_load({0: 1e-300, 1: 0}, [1, 1], [0, 1]), 1)

    def test_invalid_depletion_and_missing_nodes_raise(self):
        cases = [({0: value, 1: 0}, [1, 1]) for value in (-1, nan, inf)]
        cases += [({0: 0, 1: 0}, [value, 1]) for value in (0, -1, nan, inf)]
        cases += [({0: 2, 1: 0}, [1, 1]), ({0: 0.1}, [1, 1])]
        for consumption, residual in cases:
            with self.subTest(consumption=consumption, residual=residual):
                with self.assertRaises(ValueError):
                    energy_load(consumption, residual, [0, 1])

    def test_parameter_validation(self):
        cases = [dict(w_energy=0.8, w_load=0.3), dict(w_energy=-1, w_load=2),
                 dict(w_energy=nan), dict(w_load=inf)]
        cases += [{key: value} for key in ("energy_reference", "fitness_eps")
                  for value in (0, -1, nan, inf)]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                NodeACACOParameters(**kwargs)
        for weight in (1, 0.8, 0.6, 0.5, 0.4):
            NodeACACOParameters(w_energy=weight, w_load=1 - weight)

    def test_energy_only_ranking_and_weighted_load(self):
        with patch.object(self.evaluator, "energy_consumption") as evaluate:
            evaluate.return_value = ({0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1}, 0.4)
            balanced = self.score()
            evaluate.return_value = ({0: 0.3, 1: 0, 2: 0, 3: 0}, 0.3)
            uneven = self.score()
            self.assertLess(uneven.fitness, balanced.fitness)
            evaluate.return_value = ({0: 0.4, 1: 0, 2: 0, 3: 0}, 0.4)
            weighted = replace(self.params, w_energy=0.6, w_load=0.4,
                               energy_reference=2.0)
            uneven = self.score(params=weighted)
            evaluate.return_value = ({0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1}, 0.4)
            balanced = self.score(params=weighted)
            self.assertAlmostEqual(balanced.fitness, 0.6 * 0.4 / 2)
            self.assertAlmostEqual(uneven.fitness, balanced.fitness + 0.4)

    def test_complete_packet_accounting_conservation_and_no_mutation(self):
        before = list(self.residual)
        root = tree()
        root.nxts[0].nxts[0].isRelay = True  # CH aggregation takes precedence.
        result = self.score(root)
        tx, rx, da = self.evaluator.E_tx, self.evaluator.E_rx, self.evaluator.E_da
        expected = {0: rx(2) + tx(10, 3),
                    1: rx(2) + da(2) + tx(10, 2),
                    2: tx(10), 3: tx(20)}
        self.assertEqual(set(result.consumption), set(self.live))
        for node, cost in expected.items():
            self.assertAlmostEqual(result.consumption[node], cost)
        self.assertAlmostEqual(result.total_energy, sum(expected.values()))
        remaining = [self.residual[i] - result.consumption[i] for i in self.live]
        self.assertAlmostEqual(sum(self.residual) - sum(remaining), result.total_energy)
        self.assertEqual(self.residual, before)
        self.assertEqual(self.network.init_energy, 1)

    def test_invalid_incomplete_disconnected_and_malformed_routes(self):
        def mutate(root, kind):
            relay, head = root.nxts[0], root.nxts[0].nxts[0]
            if kind == "missing": head.nxts.pop()
            elif kind == "duplicate": head.nxts.append(Node(2, head))
            elif kind == "cycle": head.nxts.append(relay)
            elif kind == "prev": head.prev = root
            elif kind == "id": head.nxts[0].id = 99
            elif kind == "ordinary_forwarder": relay.isRelay = False
            elif kind == "root": root.id = 0
            return root
        for kind in ("missing", "duplicate", "cycle", "prev", "id",
                     "ordinary_forwarder", "root"):
            with self.subTest(kind=kind):
                self.assertIsNone(self.score(mutate(tree(), kind)))
        self.network.radius = 5
        self.assertIsNone(self.score())

    def test_unaffordable_and_invalid_shared_model_costs_rejected(self):
        cost = self.score().consumption
        self.residual = [cost[i] for i in self.live]
        self.assertIsNotNone(self.score())  # exact depletion remains affordable
        self.residual[0] *= 0.99
        self.assertIsNone(self.score())
        self.residual = [1.0] * 4
        for value in (-1, nan, inf):
            with patch.object(self.evaluator, "energy_consumption",
                              return_value=({0: value, 1: 0, 2: 0, 3: 0}, value)):
                self.assertIsNone(self.score())

    def test_seed_reproducibility_through_simulator(self):
        self.hp.T_max = 6
        params = replace(self.params, num_ants=5, w_energy=0.6, w_load=0.4)
        algorithms = [NodeACACO(self.network, self.hp, params, seed=77) for _ in range(2)]
        with redirect_stdout(StringIO()):
            histories = [Simulator(self.network, self.hp).run(a, verbose=False) for a in algorithms]
        self.assertEqual(len(histories[0]), self.hp.T_max)
        self.assertTrue(histories[0].equals(histories[1]))
        self.assertEqual(algorithms[0].clustering.pheromone, algorithms[1].clustering.pheromone)
        self.assertTrue((histories[0].round_energy > 0).all())

    def test_ant_loop_ranks_and_deposits_fitness_but_returns_joules(self):
        costs = [({0: 0.1, 1: 0.1, 2: 0.1, 3: 0.1}, 0.4),
                 ({0: 0.3, 1: 0, 2: 0, 3: 0}, 0.3)]
        for weight, winning_energy in ((1.0, 0.3), (0.6, 0.4)):
            params = replace(self.params, num_ants=2, w_energy=weight, w_load=1 - weight)
            algorithm = NodeACACO(self.network, self.hp, params, seed=1)
            roots = [tree(), tree()]
            scores = [weight * energy + (1 - weight) * load
                      for energy, load in ((0.4, 0), (0.3, 1))]
            with patch.object(algorithm.clustering, "create_clusters",
                              return_value=({1: Node(1, isCH=True)}, {}, [])), \
                    patch("algorithms.node_ac_aco.dropping_member_multi_hop_routing", side_effect=roots), \
                    patch.object(algorithm.evaluator, "energy_consumption", side_effect=costs), \
                    patch.object(algorithm.clustering, "deposit", wraps=algorithm.clustering.deposit) as deposit, \
                    redirect_stdout(StringIO()):
                root, consumption = algorithm.plan_round(self.live, self.residual)
            self.assertAlmostEqual(sum(consumption.values()), winning_energy)
            self.assertIs(root, roots[0 if winning_energy == 0.4 else 1])
            self.assertEqual(len(deposit.call_args_list), 3)
            for call, fitness in zip(deposit.call_args_list, scores + [min(scores)]):
                self.assertAlmostEqual(call.args[1], fitness)
            self.assertFalse(deposit.call_args_list[-1].kwargs["per_ant"])


if __name__ == "__main__":
    unittest.main()
