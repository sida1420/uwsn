"""Behavioral checks across coupled deposit/pheromone scales."""
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.ac_aco import RoundState
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.network = NetworkInstance([Point(i, 0, 0) for i in range(10)],
            Point(0, 0, 0), 1, 10, 1, 1, 20)

    def test_zero_width_pheromone_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            ACACOParameters(tau_min=1, tau_max=1, tau0=1)

    def test_scaled_deposits_keep_inverse_cost_information(self):
        c = ACACO(self.network, HyperParameters(),
            ACACOParameters(Q=.01, tau_min=.01, tau0=1, tau_max=20), seed=0).clustering
        c.deposit([0, 1], .02, per_ant=False)
        c.deposit([2, 3], .04, per_ant=False)
        self.assertAlmostEqual(c.pheromone[0][1] - 1,
            2 * (c.pheromone[2][3] - 1))
        self.assertLess(c.pheromone[0][1], c.params.tau_max)

    def test_late_worst_case_reinforcement_has_ceiling_headroom(self):
        p = ACACOParameters(Q=.01, tau_min=.01, tau0=1, tau_max=20)
        c = ACACO(self.network, HyperParameters(), p, seed=0).clustering
        # .015 is a reference scenario, not a guaranteed lower bound on costs.
        # All ants and the elite repeatedly reinforce the same edge; maximum
        # chaos and minimum evaporation stress the full update ordering.
        disturbance = p.chaos_max * p.chaos_r / 4
        bound = ((1 - p.rho_min + p.elite_weight) * p.Q / .015 + disturbance) / p.rho_min
        self.assertLess(bound, p.tau_max)
        for _ in range(200):
            for _ant in range(p.num_ants):
                c.deposit([0, 1], .015)
            c.chaos = [p.chaos_r / 4] * self.network.N
            c._update_pheromone(RoundState(tuple(range(10)), 2,
                p.rho_min, p.beta_max, p.chaos_max))
            c.deposit([0, 1], .015, per_ant=False)
        self.assertAlmostEqual(c.pheromone[0][1], bound, places=6)
        self.assertLess(c.pheromone[0][1], p.tau_max)

    def test_coupled_scales_keep_finite_probabilities_and_full_service(self):
        for q, floor, ceiling, initial in ((.003,.001,8,1), (.01,.01,20,1), (.03,.05,5,2)):
            p = replace(ACACOParameters(), Q=q, tau_min=floor,
                tau_max=ceiling, tau0=initial, num_ants=4)
            a = ACACO(self.network, HyperParameters(), p, seed=7)
            residual = [1.] * 10
            with redirect_stdout(StringIO()):
                for _ in range(5):
                    root, costs = a.plan_round(list(range(10)), residual)
                    self.assertIsNotNone(root)
                    self.assertEqual(set(costs), set(range(10)))
                    np.testing.assert_array_equal(residual, [1.] * 10)
                    tau = np.asarray(a.clustering.pheromone)
                    self.assertTrue(np.isfinite(tau).all())
                    self.assertTrue(((tau >= floor) & (tau <= ceiling)).all())
                    probabilities = a.clustering._transition_probabilities(
                        0, list(range(1,10)), residual, p.beta_max, p.chaos_max)
                    self.assertTrue(np.isfinite(probabilities).all())
                    self.assertGreaterEqual(min(probabilities), 0)
                    self.assertAlmostEqual(sum(probabilities), 1)


if __name__ == '__main__':
    unittest.main()
