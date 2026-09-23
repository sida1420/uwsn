import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from algorithms.ac_aco import ACACOClustering, ACACOParameters
from algorithms.ac_aco.adaptive import (
    chaos_weight,
    evaporation_rate,
    heuristic_weight,
    logistic_step,
)
from algorithms.ac_aco.optimizer import ClusterSolution
from algorithms.ac_aco.pheromone import update_pheromone
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point
from evaluate import Evaluator


def small_network():
    return NetworkInstance(
        sensors=[
            Point(10, 0, 0),
            Point(30, 0, 0),
            Point(90, 0, 0),
            Point(120, 0, 0),
        ],
        base_pos=Point(0, 0, 0),
        init_energy=0.6,
        width=150,
        height=20,
        depth=20,
        radius=45,
    )


def flatten_tree(root):
    nodes = []

    def visit(node):
        if node.id != -1:
            nodes.append(node)
        for child in node.nxts:
            assert child.prev is node
            visit(child)

    visit(root)
    return nodes


class ParameterTests(unittest.TestCase):
    def test_default_search_budget_uses_ten_ants(self):
        self.assertEqual(ACACOParameters().num_ants, 10)
        self.assertEqual(ACACOParameters().num_iterations, 5)

    def test_invalid_parameters_fail_early(self):
        with self.assertRaises(ValueError):
            ACACOParameters(num_ants=0)
        with self.assertRaises(ValueError):
            ACACOParameters(ch_proportion=0)
        with self.assertRaises(ValueError):
            ACACOParameters(chaos_r=3.0)
        with self.assertRaises(ValueError):
            ACACOParameters(beta_max=float("nan"))
        with self.assertRaises(ValueError):
            ACACOParameters(num_ants=1.5)
        with self.assertRaises(ValueError):
            ACACOParameters(tau0=20.0)


class AdaptiveScheduleTests(unittest.TestCase):
    def test_logistic_and_schedules_stay_bounded(self):
        value = logistic_step(0.37, 3.58)
        self.assertGreater(value, 0)
        self.assertLess(value, 1)
        self.assertAlmostEqual(evaporation_rate(0, 0.1, 0.9), 0.9)
        self.assertAlmostEqual(evaporation_rate(1, 0.1, 0.9), 0.1)
        self.assertLess(
            heuristic_weight(0, 1, 5, 5),
            heuristic_weight(1, 1, 5, 5),
        )
        self.assertLess(chaos_weight(1, 0.02, 0.25), chaos_weight(0, 0.02, 0.25))


class EvaluatorTests(unittest.TestCase):
    def test_empty_cluster_head_still_pays_aggregation_cost(self):
        hparameters = HyperParameters()
        evaluator = Evaluator(hparameters)
        root = Node(-1)
        cluster_head = Node(0, prev=root, isCH=True)
        root.add_next(cluster_head)
        consumption, _ = evaluator.energy_consumption(root, [[0.0]], [10.0])
        expected = evaluator.E_tx(10.0) + evaluator.E_da()
        self.assertAlmostEqual(consumption[0], expected)


class ACACOClusteringTests(unittest.TestCase):
    def make_algorithm(self, network=None, seed=7):
        network = network or small_network()
        params = ACACOParameters(
            num_ants=10,
            num_iterations=2,
            enforce_sink_radius=False,
            random_seed=seed,
        )
        return network, ACACOClustering(network, HyperParameters(), params)

    def test_fixed_seed_is_reproducible(self):
        network, first = self.make_algorithm(seed=11)
        _, second = self.make_algorithm(network, seed=11)
        energy = [network.init_energy] * network.N
        first_heads = first.select_cluster_heads(list(range(network.N)), energy)
        second_heads = second.select_cluster_heads(list(range(network.N)), energy)
        self.assertEqual(first_heads, second_heads)

    def test_edge_pheromone_is_updated_by_search(self):
        network, algorithm = self.make_algorithm(seed=5)
        initial = algorithm.params.tau0
        algorithm.select_cluster_heads(
            list(range(network.N)), [network.init_energy] * network.N
        )
        matrix = algorithm.optimizer.pheromone
        self.assertEqual(len(matrix), network.N)
        self.assertTrue(any(
            matrix[i][j] != initial
            for i in range(network.N)
            for j in range(network.N)
            if i != j
        ))

    def test_selected_path_edge_receives_deposit(self):
        network, algorithm = self.make_algorithm(seed=5)
        optimizer = algorithm.optimizer
        solution = ClusterSolution(
            aco_heads=(0, 1),
            cluster_heads=(0, 1),
            assignments={0: 0, 1: 1},
            cost=1.0,
            target_head_count=2,
        )
        energy = [network.init_energy] * network.N
        update_pheromone(
            optimizer.start_pheromone,
            optimizer.pheromone,
            optimizer.chaos,
            [solution],
            list(range(network.N)),
            energy,
            network,
            algorithm.params,
            progress=0.0,
        )
        self.assertGreater(optimizer.pheromone[0][1], optimizer.pheromone[0][2])

    def test_plan_round_builds_valid_covered_tree(self):
        network, algorithm = self.make_algorithm()
        live = list(range(network.N))
        root = algorithm.plan_round(live, [network.init_energy] * network.N)
        nodes = flatten_tree(root)
        self.assertEqual(root.id, -1)
        self.assertEqual({node.id for node in nodes}, set(live))
        self.assertEqual(len(nodes), len({node.id for node in nodes}))
        solution = algorithm.last_solution
        self.assertEqual(len(solution.assignments), len(live))
        self.assertTrue(all(
            network.dist_matrix[node_id][ch_id] <= network.radius
            for node_id, ch_id in solution.assignments.items()
        ))

    def test_dead_nodes_never_reappear(self):
        network, algorithm = self.make_algorithm()
        live = [0, 1, 3]
        energy = [network.init_energy, network.init_energy, 0.0, network.init_energy]
        root = algorithm.plan_round(live, energy)
        self.assertEqual({node.id for node in flatten_tree(root)}, set(live))
        self.assertNotIn(2, algorithm.last_solution.cluster_heads)

    def test_current_map_keeps_radius_and_covers_all_members(self):
        network = NetworkInstance.from_pickle(str(ROOT / "map.pkl"))
        _, algorithm = self.make_algorithm(network, seed=42)
        cluster_heads = algorithm.select_cluster_heads(
            list(range(network.N)), [network.init_energy] * network.N
        )
        self.assertTrue(cluster_heads)
        self.assertEqual(algorithm.params.num_ants, 10)
        self.assertEqual(
            len(algorithm.last_solution.aco_heads),
            algorithm.last_solution.target_head_count,
        )
        self.assertTrue(all(
            math.isfinite(network.dist_matrix[node_id][ch_id])
            and network.dist_matrix[node_id][ch_id] <= network.radius
            for node_id, ch_id in algorithm.last_solution.assignments.items()
        ))

    def test_default_adapter_rejects_out_of_range_sink_links(self):
        network = NetworkInstance.from_pickle(str(ROOT / "map.pkl"))
        params = ACACOParameters(num_ants=2, num_iterations=1, random_seed=3)
        algorithm = ACACOClustering(network, HyperParameters(), params)
        root = algorithm.plan_round(
            list(range(network.N)), [network.init_energy] * network.N
        )
        self.assertIsNone(root)

    def test_sink_filter_finds_feasible_direct_tree(self):
        network = small_network()
        network.radius = 150
        params = ACACOParameters(num_ants=2, num_iterations=1, random_seed=3)
        algorithm = ACACOClustering(network, HyperParameters(), params)
        root = algorithm.plan_round(
            list(range(network.N)), [network.init_energy] * network.N
        )
        self.assertIsNotNone(root)
        self.assertTrue(all(
            network.base_dists[ch.id] <= network.radius for ch in root.nxts
        ))


if __name__ == "__main__":
    unittest.main()
