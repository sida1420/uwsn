"""Regression checks for AC-ACO's seeded route and static edge costs."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from algorithms.ac_aco import ACACO
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class ACACOVectorizationTests(unittest.TestCase):
    def setUp(self):
        self.network = NetworkInstance.from_pickle(PROJECT_ROOT / "map.pkl")
        self.algorithm = ACACO(self.network, HyperParameters(), seed=39)
        self.live = list(range(self.network.N))
        self.residual = [self.network.init_energy] * self.network.N

    def test_seeded_rounds_keep_recorded_energy_and_candidate_count(self):
        expected_costs = (
            0.016821386429811486,
            0.017200815068502497,
            0.016628742411225098,
            0.01680795162319645,
            0.016860344911641973,
            0.017586454445611525,
            0.016942108589113724,
            0.01721483500419933,
            0.0172196228708459,
            0.01765641073622438,
        )
        with redirect_stdout(StringIO()):
            for expected in expected_costs:
                root, consumption = self.algorithm.plan_round(self.live, self.residual)
                self.assertIsNotNone(root)
                self.assertAlmostEqual(sum(consumption.values()), expected, places=12)
                for node_id, energy in consumption.items():
                    self.residual[node_id] = max(0.0, self.residual[node_id] - energy)
                self.live = [node_id for node_id in self.live if self.residual[node_id] > 0]

        self.assertEqual(len(self.live), self.network.N)
        self.assertEqual(self.algorithm.total_clustering_attempts, 400)
        self.assertEqual(self.algorithm.failed_routing_attempts, 0)

    def test_edge_cost_is_not_recomputed_during_round(self):
        with patch.object(
            self.algorithm.clustering.evaluator,
            "E_m",
            side_effect=AssertionError("static edge cost was recalculated"),
        ):
            with redirect_stdout(StringIO()):
                root, consumption = self.algorithm.plan_round(self.live, self.residual)

        self.assertIsNotNone(root)
        self.assertEqual(len(consumption), self.network.N)

    def test_zero_distance_candidate_uses_clipped_hop_cost(self):
        network = NetworkInstance(
            sensors=[Point(0, 0, 0), Point(0, 0, 0), Point(1, 0, 0)],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=1,
            height=1,
            depth=1,
            radius=2,
        )
        parameters = HyperParameters()
        parameters.E_elec = 0.0
        parameters.E_integrate = 0.0
        clustering = ACACO(network, parameters, seed=0).clustering
        residual = [1.0] * network.N
        state = clustering.pre_round(list(range(network.N)), residual)

        probabilities = clustering._transition_probabilities(
            source=0,
            available=[1, 2],
            residual_e=residual,
            beta=state.beta,
            strength=0.0,
        )

        self.assertGreater(probabilities[0], 0.999999)
        self.assertAlmostEqual(sum(probabilities), 1.0)

    def test_transition_uses_explicit_residual_energy(self):
        network = NetworkInstance(
            sensors=[Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0)],
            base_pos=Point(0, 0, 0),
            init_energy=1.0,
            width=1,
            height=1,
            depth=1,
            radius=2,
        )
        clustering = ACACO(network, HyperParameters(), seed=0).clustering
        state = clustering.pre_round([0, 1, 2], [1.0, 1.0, 1.0])

        equal = clustering._transition_probabilities(0, [1, 2], [1.0, 1.0, 1.0], state.beta, 0)
        changed = clustering._transition_probabilities(0, [1, 2], [1.0, 4.0, 1.0], state.beta, 0)

        self.assertAlmostEqual(equal[0], 0.5)
        self.assertGreater(changed[0], equal[0])


if __name__ == "__main__":
    unittest.main()
