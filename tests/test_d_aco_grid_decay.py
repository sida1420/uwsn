from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from algorithms.clustering.d_aco.d_aco import Grid
from algorithms.clustering.d_aco.parameters import DACOParameters
from network import NetworkInstance
from point import Point


class GridDecayTests(unittest.TestCase):
    def setUp(self):
        self.network = NetworkInstance([Point(x,50,50) for x in (20,80,140,220)],
                                       Point(0,0,0), .6, 300, 100, 100, 200)

    def grid(self, decay):
        params = DACOParameters()
        params.CH_proportion = 1.
        params.density_decay = decay
        grid = Grid(self.network, params)
        grid.compute_density(list(range(4)))
        return grid

    def test_original_grid_retains_overlap_formula(self):
        g = self.grid('none')
        points = np.array([[p.x,p.y,p.z] for p in self.network.sensors])
        distance = np.linalg.norm(points[:,None,:]-g._center[None,:,:],axis=2)
        reach = self.network.radius+g._cell_radius
        expected = np.minimum(min(1.,g.sphere_vol/g.cube_vol)*
                              np.maximum(1.-distance/reach,0.)**3,1.)
        expected[distance+g._cell_radius<=self.network.radius] = 1.
        expected[distance>=reach] = 0.
        np.testing.assert_array_equal(g.F, expected)

    def test_decay_removes_fully_covered_cell_plateau(self):
        original, linear, quadratic = [self.grid(name) for name in ('none','linear','quadratic')]
        full = original.F[0] == 1.
        self.assertGreater(np.count_nonzero(full), 1)
        self.assertGreater(np.ptp(linear.F[0,full]), 0.)
        self.assertTrue(np.all(quadratic.F <= linear.F))
        self.assertTrue(np.all(linear.F <= original.F))
        np.testing.assert_array_equal(linear.F==0., original.F==0.)

    def test_live_density_and_loss_use_same_weighted_grid(self):
        g = self.grid('linear')
        g.compute_density([0,2])
        np.testing.assert_allclose(g.density.ravel(),g.F[[0,2]].sum(axis=0))
        baseline = g.density.copy()
        before = g.get_density([0,2])
        g.add_loss(0)
        np.testing.assert_allclose(g.loss.ravel(),g.F[0])
        self.assertTrue(np.all(g.get_density([0,2])<=before))
        np.testing.assert_array_equal(g.density,baseline)
        g.reset_loss()
        np.testing.assert_allclose(g.get_density([0,2]),before)

    def test_invalid_decay_is_rejected(self):
        with self.assertRaises(ValueError):
            self.grid('unknown')
