"""Behavior checks for the NodeACO -> adaptive chaotic mapping."""

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from math import isfinite
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algorithms.node_ac_aco import NodeACACO
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters
from algorithms.clustering.node_ac_aco.node_ac_aco import NodeACACOClustering
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering.ac_aco.ac_aco import logistic_step
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


def make_network():
    return NetworkInstance(
        sensors=[Point(5 * i, 0, 0) for i in range(10)],
        base_pos=Point(0, 0, 0), init_energy=1,
        width=50, height=10, depth=10, radius=100,
    )


class NodeACACOTests(unittest.TestCase):
    def setUp(self):
        self.network = make_network()
        self.algorithm = NodeACACO(self.network, HyperParameters(), seed=39)
        self.live = list(range(self.network.N))
        self.residual = [1.0] * self.network.N

    def test_wrong_parameter_type_is_rejected_at_construction(self):
        for constructor in (NodeACACO, NodeACACOClustering):
            for params in (ACACOParameters(), {}, 0):
                with self.assertRaisesRegex(TypeError, "NodeACACOParameters"):
                    constructor(self.network, HyperParameters(), params)
        self.assertEqual((self.algorithm.params.beta_min, self.algorithm.params.beta_max), (1.0, 5.0))

    def test_node_storage_and_deposit_include_single_head_with_bounds(self):
        clustering = self.algorithm.clustering
        self.assertEqual(len(clustering.pheromone), self.network.N)
        self.assertTrue(all(isinstance(tau, float) for tau in clustering.pheromone))
        clustering.deposit([2], 0.1)
        self.assertAlmostEqual(clustering.pheromone[2], 1 + 0.03 / (40 * 0.1))
        clustering.deposit([2], 0.1, per_ant=False)
        self.assertAlmostEqual(clustering.pheromone[2], 1 + 0.03 / (40 * 0.1) + 0.1 * 0.03 / 0.1)
        clustering.deposit([2], 1e-12, per_ant=False)
        self.assertEqual(clustering.pheromone[2], self.algorithm.params.tau_max)
        self.assertEqual(clustering.pheromone[1], 1)
        before = list(clustering.pheromone)
        for cost in (None, 0, -1, float("inf"), float("nan")):
            clustering.deposit([1], cost)
        self.assertEqual(clustering.pheromone, before)

    def test_heuristic_has_no_extra_distance_factor(self):
        p = replace(NodeACACOParameters(), energy_cost_exponent=0)
        clustering = NodeACACO(self.network, HyperParameters(), p, seed=1).clustering
        state = clustering.pre_round(self.live, self.residual)
        equal = clustering._transition_probabilities(0, [1, 9], self.residual, state.beta, 0)
        self.assertEqual(equal, [0.5, 0.5])
        changed = list(self.residual)
        changed[1] = 4
        probabilities = clustering._transition_probabilities(0, [1, 9], changed, 0.6, 0)
        self.assertAlmostEqual(probabilities[0] / probabilities[1], 4 ** 0.6)

    def test_later_ants_see_node_deposit_and_chaos_mixes_probabilities(self):
        clustering = self.algorithm.clustering
        state = clustering.pre_round(self.live, self.residual)
        before = clustering._transition_probabilities(0, [1, 2], self.residual, state.beta, 0)
        clustering.deposit([1], 0.0001)
        after = clustering._transition_probabilities(0, [1, 2], self.residual, state.beta, 0)
        mixed = clustering._transition_probabilities(0, [1, 2], self.residual, state.beta, 0.3)
        self.assertGreater(after[0], before[0])
        self.assertAlmostEqual(sum(mixed), 1)
        self.assertLess(abs(mixed[0] - 0.5), abs(after[0] - 0.5))

    def test_schedules_chaos_and_failed_round_advance(self):
        for low, high in ((1, 5), (0.6, 3)):
            algorithm = NodeACACO(self.network, HyperParameters(),
                                  replace(NodeACACOParameters(), beta_min=low, beta_max=high), seed=0)
            clustering = algorithm.clustering
            state = clustering.pre_round([1, 2], self.residual)
            self.assertAlmostEqual(state.beta, low)
            self.assertAlmostEqual(state.rho, 0.90 - 0.80 / 3000)
            old_chaos = list(clustering.chaos)
            with redirect_stdout(StringIO()):
                clustering.post_round([1, 2], self.residual, {}, state=state)
            self.assertIsNone(clustering.previous_cost)
            self.assertAlmostEqual(clustering.chaos[1], logistic_step(old_chaos[1], algorithm.params.chaos_r))
            self.assertEqual(clustering.chaos[0], old_chaos[0])
            clustering.iteration = 2999
            late = clustering.pre_round([1, 2], self.residual)
            self.assertAlmostEqual(late.beta, high)
            self.assertAlmostEqual(late.rho, 0.1)

    def test_routes_are_repeatable_cover_live_ids_and_respect_radius(self):
        replica = NodeACACO(self.network, HyperParameters(), seed=39)
        self.live = [0, 2, 4, 6, 8, 9]
        self.residual[1] = 0
        with redirect_stdout(StringIO()):
            for _ in range(3):
                root, consumption = self.algorithm.plan_round(self.live, self.residual)
                other, other_consumption = replica.plan_round(self.live, self.residual)
                self.assertIsNotNone(root)
                self.assertIsNotNone(other)
                self.assertEqual(consumption, other_consumption)
                self.assertEqual(set(consumption), set(self.live))
                self.assertTrue(all(isfinite(e) and e >= 0 for e in consumption.values()))
                seen, pending = set(), [root]
                while pending:
                    parent = pending.pop()
                    for child in parent.nxts:
                        self.assertNotIn(child.id, seen)
                        seen.add(child.id)
                        self.assertIs(child.prev, parent)
                        distance = self.network.base_dists[child.id] if parent.id == -1 else self.network.dist_matrix[parent.id][child.id]
                        self.assertLessEqual(distance, self.network.radius)
                        pending.append(child)
                self.assertEqual(seen, set(self.live))
                recomputed, _ = self.algorithm.evaluator.energy_consumption(root, self.network.dist_matrix, self.network.base_dists)
                self.assertEqual(consumption, recomputed)

    def test_static_energy_is_cached_empty_live_and_unreachable_route(self):
        with patch.object(self.algorithm.clustering.evaluator, "E_m",
                          side_effect=AssertionError("recomputed static cost")):
            with redirect_stdout(StringIO()):
                root, _ = self.algorithm.plan_round(self.live, self.residual)
        self.assertIsNotNone(root)
        self.assertEqual(self.algorithm.plan_round([], self.residual), (None, {}))
        network = make_network()
        network.radius = 0.1
        algorithm = NodeACACO(network, HyperParameters(), seed=1)
        with redirect_stdout(StringIO()):
            self.assertEqual(algorithm.plan_round(self.live, self.residual), (None, {}))
        self.assertEqual(algorithm.clustering.iteration, 1)
        self.assertEqual(algorithm.failed_routing_attempts, 400)

    def test_zero_distance_and_validation(self):
        self.network.dist_matrix[0][1] = 0
        p = HyperParameters()
        p.E_elec = p.E_integrate = 0
        clustering = NodeACACO(self.network, p, seed=1).clustering
        state = clustering.pre_round(self.live, self.residual)
        probabilities = clustering._transition_probabilities(0, [1, 2], self.residual, state.beta, 0)
        self.assertTrue(all(isfinite(value) for value in probabilities))
        self.assertAlmostEqual(sum(probabilities), 1)
        for theta in (-1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                NodeACACOParameters(theta=theta)


if __name__ == "__main__":
    unittest.main()
