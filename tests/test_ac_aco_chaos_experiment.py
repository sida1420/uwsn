"""Ensure experiment-local chaos interventions do not distort the control."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'plans/phase5-acaco-chaos'))
from experiment import configs, run
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class ChaosExperimentTests(unittest.TestCase):
    def setUp(self):
        self.network = NetworkInstance([Point(i*5,0,0) for i in range(10)],
            Point(0,0,0), 1, 60, 1, 1, 100)

    def test_instrumentation_preserves_control_trajectory(self):
        control = run(self.network, configs()['calibrated_x1'], 7, 4, True)
        algorithm = ACACO(self.network,HyperParameters(),ACACOParameters(),seed=7)
        residual = [1.]*10
        with redirect_stdout(StringIO()):
            for record in control['records']:
                root,costs = algorithm.plan_round(list(range(10)),residual)
                self.assertIsNotNone(root)
                self.assertEqual(record['energy_J'],sum(costs.values()))
                residual = [e-costs[i] for i,e in enumerate(residual)]
                self.assertEqual(record['min_residual'],min(residual))
                self.assertEqual(record['actual_feasible_evaluations'],40)

    def test_disabling_both_mechanisms_matches_zero_amplitude(self):
        current = configs()['calibrated_x1']
        disabled = {**current,'transition_chaos':False,'pheromone_chaos':False}
        zero = run(self.network,configs()['calibrated_x0'],7,4,True)
        ablated = run(self.network,disabled,7,4,True)
        self.assertEqual([r['energy_J'] for r in zero['records']],
                         [r['energy_J'] for r in ablated['records']])
        self.assertEqual(zero['min_residual'],ablated['min_residual'])
        self.assertEqual(ablated['mean_uniform_share'],0)

    def test_strength_overrides_preserve_other_parameters(self):
        cases = configs()
        baseline = cases['calibrated_x1']['parameters']
        for name in ('calibrated_x0','calibrated_x0.25','calibrated_x0.5','calibrated_x2'):
            changed = {key for key,value in cases[name]['parameters'].items()
                       if value != baseline[key]}
            self.assertEqual(changed,{'chaos_min','chaos_max'})


if __name__ == '__main__':
    unittest.main()
