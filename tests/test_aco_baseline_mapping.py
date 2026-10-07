"""Behavioral regression checks for the tuned ACO -> AC-ACO transfer."""
from contextlib import redirect_stdout
from io import StringIO
from math import inf, nan
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from algorithms.aco import SimpleACO
from algorithms.ac_aco import ACACO
from algorithms.clustering.aco.parameters import ACOParameters
from algorithms.clustering.ac_aco.ac_aco import logistic_step
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


def make_network(count=6):
    return NetworkInstance([Point(i, i % 2, i % 3) for i in range(count)],
                           Point(0, 0, 0), 1.0, count, count, count, 100)


class ACOBaselineMappingTests(unittest.TestCase):
    def setUp(self):
        self.network = make_network()
        self.hp = HyperParameters()
        self.residual = [1.0] * self.network.N
        self.live = list(range(self.network.N))
        self.algorithm = ACACO(self.network, self.hp, seed=7)
        self.clustering = self.algorithm.clustering

    def test_mapped_weights_match_tuned_aco_without_adaptation_or_chaos(self):
        c, p = self.clustering, ACOParameters()
        c.pre_round(self.live, self.residual)
        available = [1, 2, 3]
        energies = [1.0, 0.1, 0.7, 0.9, 1.0, 1.0]
        actual = c._transition_probabilities(0, available, energies, p.gamma, 0)
        weights = [(energies[i] / self.network.dist_matrix[0][i]) ** p.gamma
                   * c.evaluator.E_m(self.network.dist_matrix[0][i]) ** -p.beta
                   for i in available]
        for a, w in zip(actual, weights):
            self.assertAlmostEqual(a, w / sum(weights), places=12)

    def test_deposits_change_same_round_probabilities_and_respect_bounds(self):
        c = self.clustering
        c.pre_round(self.live, self.residual)
        before = c._transition_probabilities(0, [1, 2], self.residual, 1, 0)
        c.deposit([0, 1], 0.02)
        after = c._transition_probabilities(0, [1, 2], self.residual, 1, 0)
        self.assertGreater(after[0], before[0])
        self.assertEqual(c._pheromone_array[0, 1], c.pheromone[0][1])
        c.deposit([0, 1], 1e-300, per_ant=False)
        self.assertEqual(c.pheromone[0][1], c.params.tau_max)

    def test_invalid_deposit_costs_leave_pheromone_unchanged(self):
        c = self.clustering
        c.pre_round(self.live, self.residual)
        for cost in (None, 0, -1, inf, nan):
            c.deposit([0, 1], cost)
        self.assertEqual(c.pheromone[0][1], c.params.tau0)

    def test_distinct_starts_exclude_dead_nodes(self):
        energies = [1, 0, 1, 1, 0, 1]
        state = self.clustering.pre_round(self.live, energies)
        self.assertEqual(set(state.starts), {0, 2, 3, 5})
        self.assertEqual(len(state.starts), len(set(state.starts)))
        for start in state.starts:
            candidate = self.clustering._construct_candidate(state, energies, start)
            self.assertEqual(candidate[0], start)
            self.assertEqual(len(candidate), len(set(candidate)))
            self.assertTrue(set(candidate) <= set(state.live))

    def test_original_chaotic_probability_rule_is_preserved(self):
        c = self.clustering
        state = c.pre_round(self.live, self.residual)
        mass = state.strength * c.chaos[0]
        for available in ([1, 2], [1, 2, 3, 4, 5]):
            base = c._transition_probabilities(0, available, self.residual, 1, 0)
            mixed = c._transition_probabilities(0, available, self.residual, 1, state.strength)
            for a, b in zip(mixed, base):
                self.assertAlmostEqual(a, (b + mass) / (1 + len(available)*mass))
            self.assertAlmostEqual(sum(mixed), 1.0)
            self.assertNotEqual(base, mixed)

    def test_adaptive_schedules_and_both_chaos_hooks_remain_active(self):
        c = self.clustering
        early = c.pre_round(self.live, self.residual)
        c.iteration = self.hp.T_max // 2 - 1
        middle = c.pre_round(self.live, self.residual)
        c.iteration = self.hp.T_max - 1
        late = c.pre_round(self.live, self.residual)
        self.assertLess(early.beta, middle.beta)
        self.assertLess(middle.beta, late.beta)
        self.assertGreater(early.rho, late.rho)
        chaos, tau = c.chaos[0], c.pheromone[0][1]
        c._update_pheromone(late)
        self.assertAlmostEqual(c.chaos[0], logistic_step(chaos, c.params.chaos_r))
        self.assertAlmostEqual(c.pheromone[0][1],
                               (1-late.rho)*tau + late.strength*chaos)
        c.previous_cost, c.lower_cost, c.upper_cost = 2, 1, 3
        state = c.pre_round(self.live, self.residual)
        self.assertGreater(state.strength, c.params.chaos_min)
        self.assertLess(state.strength, c.params.chaos_max)

    def test_all_failed_routes_still_advance_chaos_once(self):
        before = self.clustering.chaos[0]
        with patch("algorithms.ac_aco.dropping_member_multi_hop_routing", return_value=None):
            with redirect_stdout(StringIO()):
                result = self.algorithm.plan_round(self.live, self.residual)
        self.assertEqual(result, (None, {}))
        self.assertEqual(self.clustering.iteration, 1)
        self.assertEqual(self.algorithm.total_clustering_attempts,
                         len(self.live) * self.algorithm.params.max_clustering_attempts)
        self.assertAlmostEqual(self.clustering.chaos[0],
                               logistic_step(before, self.algorithm.params.chaos_r))

    def test_empty_live_set_returns_no_route(self):
        self.assertEqual(self.algorithm.plan_round([], self.residual), (None, {}))

    def test_explicit_seed_is_independent_of_global_rng_for_both_algorithms(self):
        network = make_network(20)  # multiple CH transitions per ant
        live, residual = list(range(network.N)), [1.0] * network.N
        for cls in (SimpleACO, ACACO):
            a, b = cls(network, self.hp, seed=2), cls(network, self.hp, seed=2)
            with redirect_stdout(StringIO()):
                for _ in range(3):
                    random.seed(123)
                    _, cost_a = a.plan_round(live, residual)
                    random.seed(999)
                    _, cost_b = b.plan_round(live, residual)
                    self.assertEqual(cost_a, cost_b)

    def test_legacy_global_seed_callers_remain_reproducible(self):
        for cls in (SimpleACO, ACACO):
            with redirect_stdout(StringIO()):
                random.seed(17)
                a = cls(self.network, self.hp)
                _, first = a.plan_round(self.live, self.residual)
                random.seed(17)
                b = cls(self.network, self.hp)
                _, second = b.plan_round(self.live, self.residual)
            self.assertEqual(first, second)

    def test_run_factory_passes_supplied_seed(self):
        from run import create_algorithm
        for cls in (SimpleACO, ACACO):
            a = create_algorithm(cls, self.network, self.hp, seed=3)
            b = cls(self.network, self.hp, seed=3)
            self.assertEqual(a.clustering.rng.getstate(), b.clustering.rng.getstate())
