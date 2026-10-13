"""Verify D-ACO's search budget and update lifecycle per physical round."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from algorithms.d_aco import DACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class DACORoundTests(unittest.TestCase):
    def test_one_batch_and_one_pheromone_update(self):
        network = NetworkInstance([Point(i,0,0) for i in range(10)],
                                  Point(0,0,0), 1, 10, 1, 1, 20)
        params = DACOParameters()
        params.num_ants = 4
        algorithm = DACO(network, HyperParameters(), params)
        self.assertTrue(algorithm.calibrate(list(range(10)),[1.]*10))
        c = algorithm.clustering
        with patch.object(c, 'pre_round', wraps=c.pre_round) as pre, \
             patch.object(c, 'post_round', wraps=c.post_round) as post, \
             patch.object(c.grid, 'compute_density', wraps=c.grid.compute_density) as density, \
             patch.object(c, '_update_pheromone', wraps=c._update_pheromone) as update:
            root, costs = algorithm.plan_round(list(range(10)), [1.]*10)
        self.assertIsNotNone(root)
        self.assertEqual(set(costs), set(range(10)))
        self.assertEqual(c.iteration, 1)
        self.assertEqual(algorithm.total_routing_attempts, 4)
        for operation in (pre, post, density, update):
            operation.assert_called_once()


if __name__ == '__main__':
    unittest.main()
