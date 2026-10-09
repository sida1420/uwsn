"""Strict validation at the public NodeACACO candidate boundary."""

from unittest import TestCase
from unittest.mock import patch

from test_node_ac_aco_fitness import network, tree
from algorithms.clustering.node_ac_aco.fitness import score_candidate
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters
from evaluate import Evaluator
from hparameter import HyperParameters


class CandidateValidationTests(TestCase):
    def setUp(self):
        self.network = network()
        self.evaluator = Evaluator(HyperParameters())
        self.params = NodeACACOParameters()

    def score(self, heads=(1,)):
        return score_candidate(tree(), list(range(4)), [1.0] * 4,
                               self.network, self.evaluator, self.params, heads)

    def test_heads_are_nonempty_unique_integral_and_match_tree(self):
        self.assertIsNotNone(self.score())
        for heads in ((), None, (1.0,), (True,), (1, 1), (0,), ([1],), (99,)):
            with self.subTest(heads=heads):
                self.assertIsNone(self.score(heads))

    def test_invalid_radius_is_rejected(self):
        for radius in (-1, float("nan"), float("inf")):
            self.network.radius = radius
            with self.subTest(radius=radius):
                self.assertIsNone(self.score())

    def test_malformed_model_values_are_rejected(self):
        for value in (object(), "invalid", None):
            with patch.object(self.evaluator, "energy_consumption",
                              return_value=({0: value, 1: 0, 2: 0, 3: 0}, 0)):
                self.assertIsNone(self.score())
