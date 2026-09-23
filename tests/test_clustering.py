import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.clustering import multi_hop_routing
from network import NetworkInstance
from point import Point


class MultiHopRoutingTests(unittest.TestCase):
    def test_routes_cluster_heads_over_multiple_3d_hops(self):
        network = NetworkInstance(
            sensors=[
                Point(6, 0, 8),    # 10 m from base
                Point(15, 0, 20),  # 15 m from CH 0, 25 m from base
                Point(24, 0, 32),  # 15 m from CH 1, 40 m from base
            ],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=50,
            height=50,
            depth=50,
            radius=16,
        )

        root = multi_hop_routing(
            CHs=[0, 1, 2],
            live_nodes=[0, 1, 2],
            dist_matrix=network.dist_matrix,
            base_dists=network.base_dists,
            residual_e=[1.0, 1.0, 1.0],
            radius=network.radius,
        )

        self.assertIsNotNone(root)
        self.assertEqual([node.id for node in root.nxts], [0])
        self.assertEqual([node.id for node in root.nxts[0].nxts], [1])
        self.assertEqual([node.id for node in root.nxts[0].nxts[0].nxts], [2])

    def test_returns_none_without_a_progressively_closer_relay(self):
        network = NetworkInstance(
            sensors=[Point(30, 0, 0), Point(45, 0, 0)],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=50,
            height=10,
            depth=10,
            radius=16,
        )

        root = multi_hop_routing(
            CHs=[0, 1],
            live_nodes=[0, 1],
            dist_matrix=network.dist_matrix,
            base_dists=network.base_dists,
            residual_e=[1.0, 1.0],
            radius=network.radius,
        )

        self.assertIsNone(root)


if __name__ == "__main__":
    unittest.main()
