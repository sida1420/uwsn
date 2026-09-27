import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from algorithms.ac_aco import ACACOClustering, ACACOParameters
from algorithms.ac_aco.adaptive import chaos_strength, evaporation_rate, heuristic_weight, logistic_step
from algorithms.ac_aco.optimizer import ClusterSolution
from algorithms.ac_aco.pheromone import update_pheromone
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


def linear_network():
    return NetworkInstance(
        sensors=[Point(10, 0, 0), Point(30, 0, 0), Point(50, 0, 0), Point(70, 0, 0)],
        base_pos=Point(0, 0, 0), init_energy=0.6,
        width=80, height=10, depth=10, radius=25,
    )


def tree_ids(root, network=None):
    found = set()

    def visit(node):
        if node.id != -1:
            if node.id in found:
                raise AssertionError("duplicate node")
            found.add(node.id)
            assert node.prev is not None
            if network is not None:
                distance = network.base_dists[node.id] if node.prev.id == -1 else network.dist_matrix[node.id][node.prev.id]
                assert distance <= network.radius
        for child in node.nxts:
            assert child.prev is node
            visit(child)

    visit(root)
    return found


class ParameterTests(unittest.TestCase):
    def test_issue_defaults_and_invalid_values(self):
        params = ACACOParameters()
        self.assertEqual((params.num_ants, params.num_iterations, params.Q), (10, 5, 100))
        self.assertEqual((params.chaos_min, params.chaos_max, params.chaos_r), (.05, .3, 3.61))
        for kwargs in ({"num_ants": True}, {"rho_max": 1}, {"beta_max": float("nan")},
                       {"random_seed": True}, {"chaos_r": 3.57}):
            with self.assertRaises(ValueError):
                ACACOParameters(**kwargs)


class EquationTests(unittest.TestCase):
    def test_adaptive_equations_are_bounded(self):
        self.assertAlmostEqual(logistic_step(.37, 3.61), 3.61 * .37 * .63)
        self.assertGreater(evaporation_rate(1, 5, .1, .9), evaporation_rate(5, 5, .1, .9))
        self.assertLess(heuristic_weight(1, 5, 1, 5, 5), heuristic_weight(5, 5, 1, 5, 5))
        self.assertEqual(chaos_strength(None, None, None, .05, .3), .05)
        self.assertEqual(chaos_strength(10, 1, 10, .05, .3), .3)

    def test_iteration_best_path_gets_one_deposit(self):
        params = ACACOParameters(Q=100, tau_min=.01, tau0=1, tau_max=1000)
        pheromone = [[1.0] * 3 for _ in range(3)]
        chaos = [.2, .3, .4]
        path = ClusterSolution((0, 1), None, 2.0, 10.0, 2)
        update_pheromone(pheromone, chaos, [0, 1, 2], params, .1, 0, path)
        self.assertAlmostEqual(pheromone[0][1], 10.9)
        self.assertAlmostEqual(pheromone[0][2], .9)

    def test_transition_probability_applies_and_normalizes_chaos(self):
        network = linear_network()
        algorithm = ACACOClustering(network, HyperParameters(), ACACOParameters())
        optimizer = algorithm.optimizer
        probability = optimizer._transition_probabilities(0, [1, 2], [.6] * 4, 1, .05)
        raw = []
        for target in (1, 2):
            distance = network.dist_matrix[0][target]
            raw.append((.6 / distance) * (1 / optimizer.evaluator.E_m(distance)) ** .1)
        base = [value / sum(raw) for value in raw]
        chaos = .05 * optimizer.chaos[0]
        expected = [(value + chaos) / (1 + 2 * chaos) for value in base]
        self.assertEqual(sum(probability), 1.0)
        self.assertAlmostEqual(probability[0], expected[0])
        self.assertAlmostEqual(probability[1], expected[1])


class ACACOIntegrationTests(unittest.TestCase):
    def make_algorithm(self, seed=7):
        network = linear_network()
        params = ACACOParameters(num_ants=3, num_iterations=2, ch_proportion=.5, random_seed=seed)
        return network, ACACOClustering(network, HyperParameters(), params)

    def test_seeded_search_is_reproducible_and_uses_exact_ch_count(self):
        network, first = self.make_algorithm(11)
        _, second = self.make_algorithm(11)
        energy = [network.init_energy] * network.N
        self.assertEqual(first.select_cluster_heads(list(range(network.N)), energy),
                         second.select_cluster_heads(list(range(network.N)), energy))
        self.assertEqual(len(first.last_solution.cluster_heads), 2)

    def test_multihop_tree_can_use_a_relay_outside_base_range(self):
        network, algorithm = self.make_algorithm()
        live = list(range(network.N))
        root = algorithm.plan_round(live, [network.init_energy] * network.N)
        self.assertEqual(tree_ids(root), set(live))
        self.assertTrue(any(node.id != -1 and node.prev.id != -1 for node in root.nxts[0].nxts))

    def test_search_excludes_dead_nodes_and_preserves_input_energy(self):
        network, algorithm = self.make_algorithm()
        energy = [network.init_energy, network.init_energy, 0.0, network.init_energy]
        before = energy.copy()
        root = algorithm.plan_round([0, 1], energy)
        self.assertEqual(tree_ids(root), {0, 1})
        self.assertEqual(energy, before)
        self.assertNotIn(2, algorithm.last_solution.cluster_heads)

    def test_candidate_cost_is_the_shared_evaluator_cost(self):
        network, algorithm = self.make_algorithm()
        root = algorithm.plan_round(list(range(network.N)), [network.init_energy] * network.N)
        _, cost = Evaluator(HyperParameters()).energy_consumption(root, network.dist_matrix, network.base_dists)
        self.assertTrue(math.isclose(cost, algorithm.last_solution.cost))

    def test_current_map_builds_a_complete_bounded_tree(self):
        network = NetworkInstance.from_pickle(str(ROOT / "map.pkl"))
        params = ACACOParameters(num_ants=2, num_iterations=1, random_seed=42)
        root = ACACOClustering(network, HyperParameters(), params).plan_round(
            list(range(network.N)), [network.init_energy] * network.N
        )
        self.assertEqual(tree_ids(root, network), set(range(network.N)))


if __name__ == "__main__":
    unittest.main()
