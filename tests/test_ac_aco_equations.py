"""Paper equation checks; these assert consistency, not algorithm optimality."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from algorithms.clustering.ac_aco.ac_aco import (
    logistic_step, evaporation_rate, heuristic_weight, chaos_strength, ACACOClustering)
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class EquationTests(unittest.TestCase):
    def test_logistic_and_schedules(self):
        self.assertAlmostEqual(logistic_step(.37,3.61), 3.61*.37*.63)
        self.assertAlmostEqual(evaporation_rate(1,3000,.1,.9), .8997333333333334)
        self.assertAlmostEqual(evaporation_rate(3000,3000,.1,.9), .1)
        self.assertEqual(heuristic_weight(600,3000,1,5,5), 1)
        self.assertEqual(heuristic_weight(1500,3000,1,5,5), 3)
        self.assertEqual(heuristic_weight(3000,3000,1,5,5), 5)

    def test_chaos_window(self):
        self.assertEqual(chaos_strength(None,None,None,.05,.3), .05)
        self.assertAlmostEqual(chaos_strength(2,1,3,.05,.3), .175)
        self.assertEqual(chaos_strength(10,1,3,.05,.3), .3)

    def test_transition_equation_and_uniform_mix(self):
        network = NetworkInstance([Point(0,0,0), Point(10,0,0), Point(30,0,0)],
                                  Point(0,0,0), 1, 30, 1, 1, 40)
        c = ACACOClustering(network, HyperParameters(), seed=0)
        residual = [1,.8,.4]
        state = c.pre_round([0,1,2],residual)
        c._pheromone_array[0,1] = 2
        weights = np.array([2*(.8/10)**state.beta/c.evaluator.E_m(10),
                            (.4/30)**state.beta/c.evaluator.E_m(30)])
        expected = weights/weights.sum()
        actual = c._transition_probabilities(0,[1,2],residual,state.beta,0)
        np.testing.assert_allclose(actual,expected,rtol=1e-12)
        disturbance = state.strength*c.chaos[0]
        mixed = c._transition_probabilities(0,[1,2],residual,state.beta,state.strength)
        np.testing.assert_allclose(mixed,(expected+disturbance)/(1+2*disturbance))
        self.assertGreater(mixed[0],mixed[1])
        self.assertLess(mixed[0]-mixed[1],actual[0]-actual[1])


if __name__ == '__main__':
    unittest.main()
