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
from algorithms.clustering.ac_aco.parameters import ACACOParameters


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
        c.pheromone[0][1] = 2
        gamma = c.params.energy_cost_exponent
        weights = np.array([2*(.8/10)**state.beta/c.evaluator.E_m(10)**gamma,
                            (.4/30)**state.beta/c.evaluator.E_m(30)**gamma])
        expected = weights/weights.sum()
        actual = c._transition_probabilities(0,[1,2],residual,state.beta,0)
        np.testing.assert_allclose(actual,expected,rtol=1e-12)
        disturbance = state.strength*c.chaos[0]
        mixed = c._transition_probabilities(0,[1,2],residual,state.beta,state.strength)
        np.testing.assert_allclose(mixed,(expected+disturbance)/(1+2*disturbance))
        self.assertGreater(mixed[0],mixed[1])
        self.assertLess(mixed[0]-mixed[1],actual[0]-actual[1])

    def test_default_weakens_hop_cost_preference(self):
        network = NetworkInstance([Point(0,0,0), Point(10,0,0), Point(30,0,0)],
                                  Point(0,0,0), 1, 30, 1, 1, 40)
        weak = ACACOClustering(network, HyperParameters(), seed=0)
        strong = ACACOClustering(network, HyperParameters(),
                                ACACOParameters(energy_cost_exponent=1.), seed=0)
        self.assertEqual(weak.params.energy_cost_exponent, .1)
        # Equal residual/distance and pheromone isolate the E_m term.
        residual = [1., .1, .3]
        odds = []
        for c in (weak, strong):
            c.pre_round([0,1,2], residual)
            p = c._transition_probabilities(0, [1,2], residual, 1., 0.)
            odds.append(p[0]/p[1])
        self.assertGreater(odds[0], 1.)
        self.assertLess(odds[0], odds[1])
        self.assertAlmostEqual(odds[0], odds[1]**.1)
        self.assertEqual(weak.evaluator.E_m(30), strong.evaluator.E_m(30))


if __name__ == '__main__':
    unittest.main()
