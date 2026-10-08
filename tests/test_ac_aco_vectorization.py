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
from algorithms.clustering.ac_aco.ac_aco import evaporation_rate
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


class ACACOVectorizationTests(unittest.TestCase):
    def setUp(self):
        self.network = NetworkInstance.from_pickle(PROJECT_ROOT / "map.pkl")
        self.algorithm = ACACO(self.network, HyperParameters(), seed=39)
        self.live = list(range(self.network.N))
        self.residual = [self.network.init_energy] * self.network.N

    def test_default_schedule_evaporates_ninety_to_ten_percent(self):
        params = self.algorithm.params
        self.assertEqual((params.rho_max, params.rho_min), (0.90, 0.10))
        for iteration, retained in ((1, 0.1002666666666667), (1500, 0.50), (3000, 0.90)):
            rho = evaporation_rate(iteration, 3000, params.rho_min, params.rho_max)
            self.assertAlmostEqual(1-rho, retained, places=12)

    def test_seeded_rounds_repeat_energy_and_candidate_count(self):
        replica = ACACO(self.network, HyperParameters(), seed=39)
        replica_live = list(self.live)
        replica_residual = list(self.residual)
        with redirect_stdout(StringIO()):
            for _ in range(10):
                root, consumption = self.algorithm.plan_round(self.live, self.residual)
                other_root, other_consumption = replica.plan_round(replica_live, replica_residual)
                self.assertIsNotNone(root)
                self.assertIsNotNone(other_root)
                self.assertEqual(consumption, other_consumption)
                self.assertEqual(set(consumption), set(self.live))
                recomputed, total = self.algorithm.evaluator.energy_consumption(
                    root, self.network.dist_matrix, self.network.base_dists
                )
                self.assertEqual(consumption, recomputed)
                self.assertGreater(total, 0)
                for node_id, energy in consumption.items():
                    self.residual[node_id] = max(0.0, self.residual[node_id] - energy)
                    replica_residual[node_id] = max(0.0, replica_residual[node_id] - other_consumption[node_id])
                self.live = [node_id for node_id in self.live if self.residual[node_id] > 0]
                replica_live = [node_id for node_id in replica_live if replica_residual[node_id] > 0]

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
