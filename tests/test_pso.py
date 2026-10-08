import random
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.clustering.pso.parameters import PSOParameters
from algorithms.clustering.pso.pso import PSOClustering
from algorithms.pso import PSO
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


def make_network(count=10):
    return NetworkInstance(
        sensors=[Point(5 * (index + 1), 0, 0) for index in range(count)],
        base_pos=Point(0, 0, 0),
        init_energy=1.0,
        width=5 * (count + 1),
        height=10,
        depth=10,
        radius=100,
    )


class PSOImprovementTests(unittest.TestCase):
    def setUp(self):
        random.seed(7)

    def test_lifetime_oriented_defaults(self):
        params = PSOParameters()

        self.assertEqual(params.CH_proportion, 0.20)
        self.assertEqual(params.max_CH_proportion, 0.30)
        self.assertEqual(params.early_stopping_patience, 5)
        self.assertEqual(params.particle_delete_percentage, 0.25)

    def test_fitness_prefers_balanced_load(self):
        algorithm = PSO(make_network(2), HyperParameters())
        residual = [1.0, 1.0]

        balanced = algorithm._lifetime_score(
            0.0020, {0: 0.0010, 1: 0.0010}, residual
        )
        concentrated = algorithm._lifetime_score(
            0.0015, {0: 0.0015, 1: 0.0}, residual
        )

        self.assertLess(balanced, concentrated)

    def test_positions_remain_bounded_after_move(self):
        clustering = PSOClustering(make_network(3), HyperParameters())
        particle = {
            "position": [0.95, 0.05, 0.50],
            "velocity": [4.0, -4.0, 4.0],
            "best_position": [0.95, 0.05, 0.50],
            "best_score": 1.0,
        }

        clustering.move(particle, [1.0, 0.0, 1.0], iteration=0, total_iterations=20)

        self.assertTrue(all(0.0 <= value <= 1.0 for value in particle["position"]))

    def test_ch_count_adapts_as_nodes_die(self):
        network = make_network(100)
        clustering = PSOClustering(network, HyperParameters())

        initial = clustering.decode([1.0] * 100, list(range(100)))
        later = clustering.decode([1.0] * 50, list(range(50)))

        self.assertEqual(len(initial), 20)
        self.assertEqual(len(later), 15)

    def test_plan_round_returns_a_feasible_result(self):
        algorithm = PSO(make_network(10), HyperParameters())

        root, consumption = algorithm.plan_round(list(range(10)), [1.0] * 10)

        self.assertIsNotNone(root)
        self.assertEqual(set(consumption), set(range(10)))


if __name__ == "__main__":
    unittest.main()
