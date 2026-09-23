import random
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.pso.pso import PSOClustering
from algorithms.pso.pso_parameters import PSOParameters
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class PSOClusteringTests(unittest.TestCase):
    def setUp(self):
        random.seed(7)
        self.hparameters = HyperParameters()
        self.params = PSOParameters()
        self.params.swarm_size = 8
        self.params.iterations = 10
        self.params.CH_proportion = 0.5

    def test_builds_a_complete_routing_tree_for_a_feasible_network(self):
        network = NetworkInstance(
            sensors=[
                Point(10, 0, 0),
                Point(20, 0, 0),
                Point(30, 0, 0),
                Point(40, 0, 0),
            ],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=50,
            height=50,
            depth=50,
            radius=50,
        )
        algorithm = PSOClustering(network, self.hparameters, self.params)

        root = algorithm.plan_round(list(range(network.N)), [1.0] * network.N)

        self.assertIsNotNone(root)
        self.assertEqual(root.id, -1)
        self.assertEqual(len(root.nxts), 2)
        routed_ids = {
            node.id
            for cluster_head in root.nxts
            for node in [cluster_head, *cluster_head.nxts]
        }
        self.assertEqual(routed_ids, set(range(network.N)))

    def test_returns_none_when_no_live_node_can_reach_the_base(self):
        network = NetworkInstance(
            sensors=[Point(100, 0, 0), Point(110, 0, 0)],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=120,
            height=20,
            depth=20,
            radius=20,
        )
        algorithm = PSOClustering(network, self.hparameters, self.params)

        root = algorithm.plan_round([0, 1], [1.0, 1.0])

        self.assertIsNone(root)


if __name__ == "__main__":
    unittest.main()
