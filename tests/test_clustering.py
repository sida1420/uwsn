import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.clustering import build_clusters
from algorithms.routing import multi_hop_routing
from network import NetworkInstance
from point import Point


class MultiHopRoutingTests(unittest.TestCase):
    def test_routes_cluster_heads_over_multiple_hops(self):
        network = NetworkInstance([Point(10, 0, 0), Point(25, 0, 0), Point(40, 0, 0)],
                                  Point(0, 0, 0), 1, 50, 10, 10, 16)
        ch_nodes, nodes, outliers = build_clusters([0, 1, 2], [0, 1, 2], network.dist_matrix, network.radius)
        root = multi_hop_routing(ch_nodes, nodes, [0, 1, 2], outliers, network.dist_matrix,
                                 network.base_dists, [1, 1, 1], network.radius)
        self.assertIsNotNone(root)
        self.assertEqual(root.nxts[0].id, 0)
        self.assertEqual(root.nxts[0].nxts[0].id, 1)
        self.assertEqual(root.nxts[0].nxts[0].nxts[0].id, 2)

    def test_returns_none_for_a_disconnected_topology(self):
        network = NetworkInstance([Point(30, 0, 0), Point(45, 0, 0)], Point(0, 0, 0),
                                  1, 50, 10, 10, 16)
        ch_nodes, nodes, outliers = build_clusters([0, 1], [0, 1], network.dist_matrix, network.radius)
        self.assertIsNone(multi_hop_routing(ch_nodes, nodes, [0, 1], outliers,
                                             network.dist_matrix, network.base_dists,
                                             [1, 1], network.radius))


if __name__ == "__main__":
    unittest.main()
