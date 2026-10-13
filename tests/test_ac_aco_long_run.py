"""Checkpoint fidelity and exact mixture mathematics."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'plans/phase5-acaco-chaos'))
from long_run import snapshot,restore,connectivity
from math_probe import minimum_expectation
from algorithms.ac_aco import ACACO
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class LongRunTests(unittest.TestCase):
    def test_restored_optimizers_do_not_share_checkpoint_pheromone(self):
        network=NetworkInstance([Point(i,0,0) for i in range(10)],Point(0,0,0),1,10,1,1,20)
        state=snapshot(ACACO(network,HyperParameters(),seed=1),[1.]*10,list(range(10)),0)
        a=restore(state,network)
        b=restore(state,network)
        a.clustering.deposit([0,1],1.,per_ant=True)
        self.assertEqual(b.clustering.pheromone[0][1],1.)
        self.assertEqual(state['pheromone'][0][1],1.)

    def test_checkpoint_preserves_next_round_after_dead_node(self):
        network=NetworkInstance([Point(i,0,0) for i in range(10)],Point(0,0,0),1,10,1,1,20)
        a=ACACO(network,HyperParameters(),seed=8)
        residual=[1.]*10
        with redirect_stdout(StringIO()):
            a.plan_round(list(range(10)),residual)
            residual[3]=0
            live=[i for i in range(10) if i!=3]
            state=json.loads(json.dumps(snapshot(a,residual,live,1)))
            paired=restore(state,network)
            root,costs=a.plan_round(live,residual)
            paired_root,paired_costs=paired.plan_round(live,residual)
        self.assertIsNotNone(root)
        self.assertIsNotNone(paired_root)
        self.assertEqual(costs,paired_costs)
        self.assertEqual(a.clustering.rng.getstate(),paired.clustering.rng.getstate())
        self.assertEqual(a.clustering.pheromone,paired.clustering.pheromone)

    def test_connectivity_detects_living_node_cut_off_by_dead_relay(self):
        network=NetworkInstance([Point(5,0,0),Point(15,0,0)],Point(0,0,0),1,20,1,1,10)
        self.assertEqual(connectivity(network,[0,1])['disconnected'],[])
        self.assertEqual(connectivity(network,[1])['disconnected'],[1])

    def test_doubled_disturbance_is_exact_diminishing_uniform_mix(self):
        p=np.array([.8,.15,.05])
        c=.2
        n=len(p)
        lam=n*c/(1+n*c)
        doubled=2*lam/(1+lam)
        np.testing.assert_allclose((p+2*c)/(1+2*n*c),
            (1-doubled)*p+doubled/n)
        self.assertGreater(doubled,lam)
        self.assertLess(doubled-lam,lam)
        self.assertAlmostEqual(np.linalg.norm((p+2*c)/(1+2*n*c)-1/n),
            np.linalg.norm((p+c)/(1+n*c)-1/n)/(1+lam))

    def test_empirical_order_statistic_matches_two_point_distribution(self):
        self.assertAlmostEqual(minimum_expectation([1,3],2),1*.75+3*.25)


if __name__=='__main__':
    unittest.main()
