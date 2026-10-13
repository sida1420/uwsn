"""Regression tests for the confirmed AC-ACO deposit-bound defect."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class PheromoneBoundTests(unittest.TestCase):
    def setUp(self):
        self.network = NetworkInstance([Point(i,0,0) for i in range(10)],
                                      Point(0,0,0), 1, 10, 1, 1, 20)
        # Preserve the historical defect fixture independently of calibration.
        params = ACACOParameters(Q=100, tau_min=.1, tau0=1, tau_max=10)
        self.algorithm = ACACO(self.network, HyperParameters(), params, seed=0)
        self.clustering = self.algorithm.clustering

    def test_elite_deposit_remains_bounded(self):
        self.clustering.deposit([0,1,2], .017, per_ant=False)
        self.assertEqual(self.clustering.pheromone[0][1], 10)
        self.assertEqual(self.clustering.pheromone[1][2], 10)
        self.assertEqual(self.clustering.pheromone[2][1], 1)

    def test_ant_deposits_accumulate_before_evaporation(self):
        self.clustering.deposit([0,1], .017, per_ant=True)
        self.assertAlmostEqual(self.clustering.pheromone[0][1],1+100/(.017*40))
        state = self.clustering.pre_round(list(range(10)),[1]*10)
        self.clustering._update_pheromone(state)
        self.assertEqual(self.clustering.pheromone[0][1],10)

    def test_sub_saturation_deposit_retains_inverse_cost_scaling(self):
        self.clustering.deposit([0,1], 100, per_ant=False)
        self.clustering.deposit([2,3], 200, per_ant=False)
        self.assertEqual(self.clustering.pheromone[0][1]-1,
                         2*(self.clustering.pheromone[2][3]-1))

    def test_complete_round_preserves_bound_and_service(self):
        live = list(range(self.network.N))
        residual = [1]*self.network.N
        with redirect_stdout(StringIO()):
            for _ in range(3):
                root, consumption = self.algorithm.plan_round(live, residual)
                self.assertIsNotNone(root)
                self.assertEqual(set(consumption), set(live))
                self.assertTrue(all(.1<=tau<=10 for row in self.clustering.pheromone for tau in row))

    def test_invalid_cost_does_not_deposit(self):
        self.clustering.deposit([0,1], 0)
        self.assertEqual(self.clustering.pheromone[0][1], 1)


if __name__ == '__main__':
    unittest.main()
