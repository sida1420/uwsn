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

    def test_default_particle_refresh_settings(self):
        params = PSOParameters()

        self.assertEqual(params.swarm_size, 15)
        self.assertEqual(params.iterations, 10)
        self.assertEqual(params.early_stopping_patience, 3)
        self.assertEqual(params.particle_delete_percentage, 0.2)

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

    def test_deletes_worst_percentage_and_randomly_refills_next_round(self):
        network = NetworkInstance(
            sensors=[Point(10, 0, 0), Point(20, 0, 0), Point(30, 0, 0)],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=40,
            height=10,
            depth=10,
            radius=40,
        )
        self.params.swarm_size = 5
        self.params.iterations = 1
        self.params.particle_delete_percentage = 0.4
        algorithm = PSOClustering(network, self.hparameters, self.params)

        algorithm.plan_round([0, 1, 2], [1.0, 1.0, 1.0])
        self.assertEqual(algorithm.last_deleted_particles, 2)
        self.assertEqual(len(algorithm._warm_start), 3)

        original_new_particle = algorithm._new_particle
        random_particle_count = 0

        def track_new_particles(dimensions, candidates, previous):
            nonlocal random_particle_count
            if previous is None:
                random_particle_count += 1
            return original_new_particle(dimensions, candidates, previous)

        algorithm._new_particle = track_new_particles
        algorithm.plan_round([0, 1, 2], [1.0, 1.0, 1.0])

        self.assertEqual(random_particle_count, 2)

    def test_rejects_invalid_delete_percentage(self):
        network = NetworkInstance(
            sensors=[Point(10, 0, 0)],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=20,
            height=10,
            depth=10,
            radius=20,
        )
        self.params.swarm_size = 1
        self.params.iterations = 1
        self.params.particle_delete_percentage = 1.1
        algorithm = PSOClustering(network, self.hparameters, self.params)

        with self.assertRaises(ValueError):
            algorithm.plan_round([0], [1.0])


if __name__ == "__main__":
    unittest.main()
