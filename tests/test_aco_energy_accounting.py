"""Independent packet accounting and complete, bounded 3D route checks."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from algorithms.aco import SimpleACO
from algorithms.ac_aco import ACACO
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point


class ACOEnergyAccountingTests(unittest.TestCase):
    def test_member_ch_relay_and_empty_ch_packet_costs(self):
        net = NetworkInstance([Point(0, 0, i) for i in (1, 2, 3, 4)],
                              Point(0, 0, 0), 1, 4, 4, 4, 10)
        evaluator = Evaluator(HyperParameters())
        root, relay, head, member, empty = (Node(-1), Node(0, isRelay=True),
                                          Node(1, isCH=True), Node(2), Node(3, isCH=True))
        for parent, child in ((root, relay), (relay, head), (head, member), (root, empty)):
            child.set_previous(parent)
            parent.add_next(child)
        actual, total = evaluator.energy_consumption(root, net.dist_matrix, net.base_dists)
        expected = {
            2: evaluator.E_tx(1),
            1: evaluator.E_tx(1, 2) + evaluator.E_rx(1) + evaluator.E_da(1),
            0: evaluator.E_tx(1, 3) + evaluator.E_rx(2),
            3: evaluator.E_tx(4, 2),
        }
        for i in expected:
            self.assertAlmostEqual(actual[i], expected[i], places=15)
        self.assertAlmostEqual(total, sum(expected.values()), places=15)

    def test_real_routes_cover_every_live_node_once_within_3d_radius(self):
        net, hp = NetworkInstance.from_pickle(ROOT / "map.pkl"), HyperParameters()
        for cls in (SimpleACO, ACACO):
            for seed in (0, 1, 2):
                algorithm = cls(net, hp, seed=seed)
                residual, live = [net.init_energy]*net.N, list(range(net.N))
                with redirect_stdout(StringIO()):
                    for _ in range(3):
                        root, costs = algorithm.plan_round(live, residual)
                        self.assertIsNotNone(root)
                        seen = set()
                        def visit(node):
                            self.assertNotIn(node.id, seen)
                            seen.add(node.id)
                            for child in node.nxts:
                                self.assertIs(child.prev, node)
                                distance = (net.base_dists[child.id] if node.id == -1 else
                                            net.dist_matrix[node.id][child.id])
                                self.assertLessEqual(distance, net.radius)
                                visit(child)
                        visit(root)
                        self.assertEqual(seen - {-1}, set(live))
                        self.assertEqual(set(costs), set(live))
                        for i, cost in costs.items():
                            residual[i] = max(0, residual[i]-cost)
                        live = [i for i in live if residual[i] > 0]

    def test_distances_include_depth(self):
        net = NetworkInstance([Point(0, 0, 12), Point(3, 4, 0)],
                              Point(0, 0, 0), 1, 20, 20, 20, 20)
        self.assertEqual(net.dist_matrix[0][1], 13)
        self.assertEqual(net.base_dists, [12, 5])
