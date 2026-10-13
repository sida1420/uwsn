from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'plans/phase7-daco-grid'))
from full_parabolic import ParabolicGrid
from algorithms.clustering.d_aco.d_aco import Grid
from algorithms.clustering.d_aco.parameters import DACOParameters
from network import NetworkInstance
from point import Point


class ParabolicGridTests(unittest.TestCase):
    def test_parabolic_weights_on_original_grid_support(self):
        network = NetworkInstance([Point(x,50,50) for x in (20,80,140,220)],
                                  Point(0,0,0),.6,300,100,100,200)
        original = Grid(network,DACOParameters(density_decay='none'))
        weighted = ParabolicGrid(network,DACOParameters(density_decay='none'))
        for g in (original,weighted):
            g.compute_density([0,1,2,3])
        points = np.array([[p.x,p.y,p.z] for p in network.sensors])
        d = np.linalg.norm(points[:,None,:]-weighted._center[None,:,:],axis=2)
        expected = original.F*np.maximum(1.-(d/(network.radius+weighted._cell_radius))**2,0.)
        np.testing.assert_allclose(weighted.F,expected)
        np.testing.assert_allclose(weighted.density.ravel(),expected.sum(axis=0))
        np.testing.assert_array_equal(weighted.F==0.,original.F==0.)

    def test_decay_gets_steeper_toward_edge(self):
        values = 1.-np.array([0.,.25,.5,.75,1.])**2
        drops = -np.diff(values)
        self.assertTrue(np.all(np.diff(drops)>0.))

    def test_production_option_matches_full_run_adapter(self):
        network = NetworkInstance([Point(x,50,50) for x in (20,80,140,220)],
                                  Point(0,0,0),.6,300,100,100,200)
        params = DACOParameters()
        params.density_decay = 'parabolic'
        production = Grid(network,params)
        historical = ParabolicGrid(network,DACOParameters(density_decay='none'))
        production.compute_density([0,2,3])
        historical.compute_density([0,2,3])
        np.testing.assert_array_equal(production.F,historical.F)
        np.testing.assert_array_equal(production.density,historical.density)
        for sensor in (0,3):
            production.add_loss(sensor)
            historical.add_loss(sensor)
            np.testing.assert_array_equal(production.get_density([0,2,3]),
                                          historical.get_density([0,2,3]))
