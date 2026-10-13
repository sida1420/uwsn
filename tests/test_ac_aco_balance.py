"""Experimental controls must preserve baseline and physical-round timing."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'plans/phase5-acaco-balance'))
from balance_study import ExperimentalACACO, CONFIGS, select
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.ac_aco import logistic_step
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering import build_clusters
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class BalanceControls(unittest.TestCase):
    def setUp(self):
        self.network=NetworkInstance([Point(i,0,0) for i in range(10)],Point(0,0,0),1,10,1,1,20)

    def test_experimental_baseline_matches_production_across_rounds(self):
        a=ACACO(self.network,HyperParameters(),seed=9)
        b=ExperimentalACACO(self.network,CONFIGS['live_elite_01'],a.params,seed=9)
        live=list(range(10))
        residual=[1.]*10
        with redirect_stdout(StringIO()):
            for _ in range(5):
                _,costs=a.plan_round(live,residual)
                _,other=b.plan_round(live,residual)
                self.assertEqual(costs,other)
                self.assertEqual(a.clustering.pheromone,b.clustering.pheromone)
                self.assertEqual(a.clustering.chaos,b.clustering.chaos)
                self.assertEqual(a.clustering.rng.getstate(),b.clustering.rng.getstate())
                residual=[e-costs[i] for i,e in enumerate(residual)]

    def test_frozen_reference_retains_historical_first_round(self):
        network=NetworkInstance.from_pickle(ROOT/'map.pkl')
        a=ExperimentalACACO(network,CONFIGS['baseline'],seed=39)
        _,costs=a.plan_round(list(range(network.N)),[network.init_energy]*network.N)
        self.assertAlmostEqual(sum(costs.values()),.016821386429811486,places=12)

    def test_inner_iterations_advance_physical_clock_and_chaos_once(self):
        a=ExperimentalACACO(self.network,CONFIGS['split_4'],seed=7)
        before=a.clustering.chaos.copy()
        _,costs=a.plan_round(list(range(10)),[1.]*10)
        self.assertEqual(a.clustering.iteration,1)
        self.assertEqual(a.clustering.chaos,[logistic_step(z,a.params.chaos_r) for z in before])
        self.assertEqual(set(costs),set(range(10)))
        self.assertEqual(a.last_metrics['feasible'],40)

    def test_daco_cv_selection_can_choose_more_balanced_higher_energy_tree(self):
        cheap=(1.,(0,1),None,{0:.9,1:.1},.8)
        balanced=(1.1,(1,0),None,{0:.55,1:.55},0.)
        self.assertIs(select([cheap,balanced],0.),cheap)
        self.assertIs(select([cheap,balanced],.1),balanced)

    def test_normalized_updates_preserve_identical_candidate_reinforcement(self):
        arrays=[]
        live=list(range(10))
        for name in ('baseline','split_2','split_4'):
            a=ExperimentalACACO(self.network,CONFIGS[name],ACACOParameters(Q=1e-7),seed=2)
            a.clustering.create_clusters=lambda *args: build_clusters((0,1),live,
                self.network.dist_matrix,self.network.radius)
            root,costs=a.plan_round(live,[1.]*10)
            self.assertIsNotNone(root)
            self.assertEqual(set(costs),set(live))
            arrays.append(np.asarray(a.clustering.pheromone))
        for array in arrays[1:]:
            np.testing.assert_allclose(array,arrays[0],rtol=0,atol=1e-14)

    def test_production_balanced_controls_match_live_experiment(self):
        params=ACACOParameters(elite_weight=.1,load_weight=.1)
        a=ACACO(self.network,HyperParameters(),params,seed=4)
        b=ExperimentalACACO(self.network,CONFIGS['live_combined'],params,seed=4)
        live=list(range(10))
        residual=[1.]*10
        with redirect_stdout(StringIO()):
            for _ in range(4):
                _,costs=a.plan_round(live,residual)
                _,other=b.plan_round(live,residual)
                self.assertEqual(costs,other)
                self.assertEqual(a.clustering.pheromone,b.clustering.pheromone)
                residual=[e-costs[i] for i,e in enumerate(residual)]

    def test_balance_controls_reject_invalid_weights(self):
        for name in ('elite_weight','load_weight'):
            for value in (-.1,1.1,float('nan'),float('inf')):
                with self.subTest(name=name,value=value), self.assertRaises(ValueError):
                    ACACOParameters(**{name:value})


if __name__=='__main__':
    unittest.main()
