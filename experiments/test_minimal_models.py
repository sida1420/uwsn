"""Checks for standalone models. No production algorithm import is allowed."""
import ast
from fractions import Fraction as F
from itertools import combinations, permutations
from pathlib import Path
import unittest

from minimal_models import (collection_cost, short_transition_model, memory_model,
    allocation_probabilities, density_model, proximity_model, actions, run_policy,
    exact_best_service, protection_model)


class MinimalModelTests(unittest.TestCase):
    def test_source_imports_only_standard_library(self):
        tree=ast.parse((Path(__file__).parent/"minimal_models.py").read_text())
        allowed={"__future__","argparse","collections","functools","fractions","itertools",
                 "json","math","pathlib"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                self.assertTrue(all(a.name.split('.')[0] in allowed for a in node.names))
            if isinstance(node,ast.ImportFrom):
                self.assertIn(node.module.split('.')[0],allowed)

    def test_four_sensor_hand_calculation(self):
        r=short_transition_model()
        self.assertEqual(r['nearest_pair_cost'],145)
        self.assertEqual(r['optimal_cost'],2)
        self.assertEqual(r['next_probabilities'][1],F(90,109))
        self.assertEqual(r['expected_inverse'],F(13088,109))
        self.assertEqual(r['expected_uniform'],F(149,3))

    def test_distance_family_against_closed_form(self):
        for L in range(2,31):
            r=short_transition_model(L)
            self.assertEqual(r['nearest_pair_cost'],(L-1)**2+L**2)
            self.assertEqual(r['optimal_cost'],2)
            self.assertGreater(r['expected_inverse'],r['expected_uniform'])

    def test_objective_invariance_under_head_permutation(self):
        points=(0,1,9,10)
        for heads in combinations(range(4),3):
            self.assertEqual(len({collection_cost(points,order) for order in permutations(heads)}),1)
        r=memory_model()
        self.assertEqual(r['distinct_node_updates'],1)
        self.assertEqual(r['distinct_edge_updates'],6)
        self.assertEqual(r['additive_strict_separations'],0)

    def test_density_capacity_optimum_attains_lower_bound(self):
        r=density_model()
        self.assertEqual(r['uniform_space_max_load'],3)
        self.assertEqual(r['optimal_allocations'],[(3,1)])
        self.assertEqual(r['optimal_max_load'],r['lower_bound'])

    def test_exact_allocation_matches_independent_order_enumeration(self):
        # Different implementation: enumerate every ordered list of four node IDs.
        for mode in ('uniform','density','density_no_subtraction'):
            sums={}
            for order in permutations(range(8),4):
                probability=F(1);chosen=[]
                for pick in order:
                    left=[i for i in range(8) if i not in chosen]
                    remaining=[sum(i<6 for i in left),sum(i>=6 for i in left)]
                    weights={i:(1 if mode=='uniform' else remaining[i>=6] if mode=='density'
                                else (6 if i<6 else 2)) for i in left}
                    probability*=F(weights[pick],sum(weights.values()))
                    chosen.append(pick)
                key=(sum(i<6 for i in chosen),sum(i>=6 for i in chosen))
                sums[key]=sums.get(key,F(0))+probability
            self.assertEqual(sums,allocation_probabilities(mode=mode))

    def test_density_bias_does_not_guarantee_sparse_service(self):
        r=density_model()['sampling']
        self.assertGreater(r['density']['expected_dense_heads'],r['uniform']['expected_dense_heads'])
        self.assertGreater(r['density']['probability_no_sparse_head'],0)

    def test_proximity_breaks_plateau_and_off_grid_tie_is_retained(self):
        r=proximity_model()
        self.assertEqual(r['flat'],[F(1)]*5)
        self.assertEqual(r['proximity'],[F(3,4),F(15,16),F(1),F(15,16),F(3,4)])
        self.assertEqual(r['proximity_maximizers'],[F(0)])
        self.assertEqual(proximity_model(F(1,4))['proximity_maximizers'],[F(0),F(1,2)])

    def test_protection_service_and_exact_upper_bound(self):
        r=protection_model()
        self.assertEqual(r['policies']['energy_only']['rounds'],2)
        self.assertEqual(r['policies']['relative_only']['rounds'],4)
        self.assertEqual(r['policies']['relative_with_correct_redundancy']['rounds'],6)
        self.assertEqual(r['policies']['relative_with_reversed_density']['rounds'],4)
        self.assertEqual(r['all_policy_optimum'],6)

    def test_energy_policy_histories_are_feasible_and_conserve_energy(self):
        for r in protection_model()['policies'].values():
            self.assertEqual(r['total_spent']+sum(r['final_energy']),24)
            self.assertFalse(actions(r['final_energy']))
            for h in r['history']:
                self.assertTrue(all(e>=0 for e in h['after']))
                self.assertEqual(tuple(e-c for e,c in zip(h['before'],h['cost'])),h['after'])


if __name__=='__main__':unittest.main()
