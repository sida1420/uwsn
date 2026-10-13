from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from algorithms.d_aco import DACO, Candidate
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering.d_aco.fitness import FitnessReferences, fitness, power_density_penalty
from network import NetworkInstance
from point import Point
from hparameter import HyperParameters


class FitnessTests(unittest.TestCase):
    def network(self,n=10):
        return NetworkInstance([Point(i,0,0) for i in range(n)],Point(0,0,0),1,n,1,1,20)

    def test_power_penalty_distinguishes_equal_max_and_total(self):
        def penalty(loads):
            return power_density_penalty(dict(enumerate(loads)),list(range(4)),
                np.ones(4),np.ones(4),2.,1e-12)
        self.assertEqual(penalty([2.,2.,0.,0.]),2.)
        self.assertEqual(penalty([2.,1.,1.,0.]),1.5)

    def test_low_density_and_residual_increase_power_penalty(self):
        costs = {0:.08,1:.02}
        args = (costs,[0,1])
        dense = power_density_penalty(*args,np.ones(2),np.ones(2),2.,1e-12)
        sparse = power_density_penalty(*args,np.ones(2),np.array([.5,1.]),2.,1e-12)
        endangered = power_density_penalty(*args,np.array([.2,1.]),np.array([.5,1.]),2.,1e-12)
        self.assertGreater(sparse,dense)
        self.assertGreater(endangered,sparse)
        self.assertTrue(np.isfinite(power_density_penalty(*args,np.ones(2),np.zeros(2),2.,1e-12)))

    def test_geometric_smoothing_and_energy_only_units(self):
        refs = FitnessReferences(4.,9.)
        updated = refs.updated([16.],[81.],.5)
        self.assertAlmostEqual(updated.energy,8.)
        self.assertAlmostEqual(updated.penalty,27.)
        self.assertEqual(refs.energy,4.)
        self.assertEqual(fitness(.01,100.,refs,0.),.01)

    def test_throwaway_calibration_does_not_advance_physical_or_pheromone_state(self):
        a = DACO(self.network(),HyperParameters())
        residual = [1.]*10
        before = a.clustering.pheromone.copy()
        self.assertTrue(a.calibrate(list(range(10)),residual))
        self.assertEqual(a.clustering.pheromone,before)
        self.assertEqual(a.clustering.iteration,0)
        self.assertEqual(residual,[1.]*10)
        self.assertEqual(a.total_clustering_attempts,0)
        self.assertGreater(a.calibration_attempts,0)
        attempts = a.calibration_attempts
        self.assertTrue(a.calibrate(list(range(10)),residual))
        self.assertEqual(a.calibration_attempts,attempts)

    def test_same_cached_score_for_live_ants_and_best_with_frozen_references(self):
        a = DACO(self.network(2),HyperParameters(),DACOParameters(num_ants=2))
        refs = FitnessReferences(.01,.0001)
        a.references = refs
        roots = [object(),object()]
        candidates = [Candidate(roots[0],(0,),{0:.009,1:.001},.01,.00036),
                      Candidate(roots[1],(0,),{0:.0055,1:.0055},.011,.0001)]
        seen_tau = []
        def evaluate(*args):
            self.assertIs(a.references,refs)
            seen_tau.append(a.clustering.pheromone[0])
            return candidates[len(seen_tau)-1]
        with patch.object(a.clustering,'pre_round',wraps=a.clustering.pre_round), \
             patch.object(a,'_run_ant',side_effect=evaluate), \
             patch.object(a.clustering,'deposit',wraps=a.clustering.deposit) as deposit:
            root,_ = a.plan_round([0,1],[1.,1.])
        self.assertIs(root,roots[1])
        self.assertGreater(seen_tau[1],seen_tau[0])
        self.assertEqual(deposit.call_count,3)
        for call,candidate in zip(deposit.call_args_list[:2],candidates):
            self.assertEqual(call.args[1],candidate.fitness)
            self.assertEqual(call.args[2],refs.energy)
        self.assertEqual(deposit.call_args_list[-1].args[1],candidates[1].fitness)
        self.assertEqual(deposit.call_args_list[-1].args[2],refs.energy)
        self.assertIsNot(a.references,refs)

    def test_structural_density_is_independent_of_ch_loss(self):
        a = DACO(self.network(),HyperParameters())
        a.clustering.grid.compute_density(list(range(10)))
        before = a._load_context(list(range(10)),[1.]*10)
        a.clustering.grid.add_loss(0)
        after = a._load_context(list(range(10)),[1.]*10)
        np.testing.assert_array_equal(before[2],after[2])

    def test_obsolete_parameters_are_rejected(self):
        params = DACOParameters()
        params.fitness_mode = 'absolute'
        with self.assertRaisesRegex(ValueError,'obsolete'):
            DACO(self.network(),HyperParameters(),params)
        for kwargs in ({'load_power':.5},{'reference_memory':1.},{'load_density_weight':-.1}):
            with self.assertRaises(ValueError):
                DACOParameters(**kwargs)


if __name__=='__main__':
    unittest.main()
