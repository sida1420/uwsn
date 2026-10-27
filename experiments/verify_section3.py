"""Audit Section 3 formulas against production routines, without an ACO campaign.

Run from the repository root with the project dependencies available.
The independent arithmetic below is deliberately separate from Evaluator.
The unused plotting import and final pandas table packaging are substituted
when checking the real Simulator loop; its energy/state logic is unchanged.
"""
from fractions import Fraction
from itertools import permutations, product
from math import dist, isclose
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point
from algorithms.clustering.clustering import build_clusters
from algorithms.clustering.d_aco.d_aco import DACOClustering
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.routing.routing import dropping_member_multi_hop_routing


def close(a, b):
    assert isclose(a, b, rel_tol=2e-13, abs_tol=1e-18), (a, b)


def packet_costs(hp, distance):
    f = hp.freq / 1000
    alpha = .11*f*f/(1+f*f) + 44*f*f/(4100+f*f) + 2.75e-4*f*f + .003
    length = distance / 1000
    loss = length ** hp.spreadking_factor * 10 ** (alpha * length / 10)
    return (hp.P_0 * loss * hp.packet_size / hp.trasmission_rate,
            hp.packet_size * hp.E_elec,
            hp.packet_size * hp.E_integrate)


def reaches_sink(parents):
    for start in range(len(parents)):
        seen = set()
        current = start
        while current != -1:
            if current in seen:
                return False
            seen.add(current)
            current = parents[current]
    return True


def make_tree(parents, heads):
    nodes = {i: Node(i, isCH=i in heads) for i in range(len(parents))}
    sink = Node(-1)
    for i, parent in enumerate(parents):
        target = sink if parent == -1 else nodes[parent]
        nodes[i].set_previous(target)
        target.add_next(nodes[i])
    for node in nodes.values():
        node.isRelay = bool(node.nxts)
    return sink


def formula_costs(parents, heads, points, sink, hp):
    # Bottom-up evaluation over parent indices; no project energy routines.
    outgoing, incoming = {}, {}
    pending = set(range(len(parents)))
    while pending:
        ready = [i for i in pending if all(j in outgoing for j, p in enumerate(parents) if p == i)]
        assert ready, 'not a rooted tree'
        for i in ready:
            incoming[i] = sum(outgoing[j] for j, p in enumerate(parents) if p == i)
            outgoing[i] = 2 if i in heads else 1 + incoming[i]
            pending.remove(i)
    costs = {}
    for i, parent in enumerate(parents):
        tx, rx, agg = packet_costs(hp, dist(points[i], sink if parent == -1 else points[parent]))
        costs[i] = outgoing[i]*tx + incoming[i]*rx + (incoming[i]*agg if i in heads else 0)
    return costs, outgoing, incoming


def audit():
    result = {}
    hp = HyperParameters()
    evaluator = Evaluator(hp)
    frequency_cases = 0
    for frequency in (1, 10, 30, 60, 100):
        local = HyperParameters()
        local.freq = 1000 * frequency
        alpha = .11*frequency**2/(1+frequency**2) + 44*frequency**2/(4100+frequency**2) + 2.75e-4*frequency**2 + .003
        if frequency == 30:
            close(local.absorption_factor, alpha)
            close(local.attenuation_coeff, 10**(alpha/10))
        # Set the frequency-dependent derived value explicitly after changing f.
        local.attenuation_coeff = 10**(alpha/10)
        real = Evaluator(local)
        for distance in (0, .001, 1, 50, 200, 1000, 2500):
            tx, rx, agg = packet_costs(local, distance)
            for count in (0, 1, 2, 7):
                close(real.E_tx(distance, count), count*tx)
                close(real.E_rx(count), count*rx)
                close(real.E_da(count), count*agg)
                frequency_cases += 1
    result['packet_energy_cases'] = frequency_cases
    result['default_200m_packet_j'] = dict(zip(('tx', 'rx', 'aggregation'), packet_costs(hp, 200)))
    result['default_absorption_db_per_km'] = hp.absorption_factor

    trees = 0
    labels = 0
    for n in range(1, 5):
        points = [(10+31*i, 7*(i%2), 5+13*i) for i in range(n)]
        sink_point = (0, 0, 0)
        network = NetworkInstance([Point(*p) for p in points], Point(*sink_point), 1, 200, 100, 100, 500)
        for parents in product(*[[-1]+[j for j in range(n) if j != i] for i in range(n)]):
            if not reaches_sink(parents):
                continue
            trees += 1
            for mask in range(1, 2**n):
                heads = {i for i in range(n) if mask & (1 << i)}
                root = make_tree(parents, heads)
                expected, outgoing, incoming = formula_costs(parents, heads, points, sink_point, hp)
                actual, total = evaluator.energy_consumption(root, network.dist_matrix, network.base_dists)
                assert set(actual) == set(range(n))
                for i in actual:
                    close(actual[i], expected[i])
                close(total, sum(expected.values()))
                labels += 1
    result['rooted_trees_enumerated'] = trees
    result['ch_labeled_tree_energy_cases'] = labels

    # Actual decoder: exhaustive CH orders on a small topology, multiple ranges.
    points = [Point(0,0,40), Point(0,0,95), Point(35,0,145), Point(0,35,190)]
    decoder_success = decoder_failure = 0
    for radius in (55, 80, 120, 250):
        network = NetworkInstance(points, Point(0,0,0), 1, 250, 100, 250, radius)
        for k in range(1, len(points)+1):
            for order in permutations(range(len(points)), k):
                heads, nodes, outliers = build_clusters(order, list(range(4)), network.dist_matrix, radius)
                root = dropping_member_multi_hop_routing(heads, nodes, list(range(4)), outliers,
                    network.dist_matrix, network.base_dists, [1]*4, radius, .4)
                if root is None:
                    decoder_failure += 1
                    continue
                visited = set()
                def walk(node):
                    for child in node.nxts:
                        assert child.id not in visited
                        visited.add(child.id)
                        assert child.prev is node
                        d = network.base_dists[child.id] if node.id == -1 else network.dist_matrix[child.id][node.id]
                        assert d <= radius
                        if child.nxts and not child.isCH:
                            assert child.isRelay
                        walk(child)
                walk(root)
                assert visited == set(range(4))
                actual, total = evaluator.energy_consumption(root, network.dist_matrix, network.base_dists)
                close(total, sum(actual.values()))
                decoder_success += 1
    result['decoder_successes_satisfying_structural_constraints'] = decoder_success
    result['decoder_failures_not_treated_as_physical_proofs'] = decoder_failure

    # Radius equality and 3D Euclidean geometry.
    network = NetworkInstance([Point(3,4,12), Point(6,8,24)], Point(0,0,0), 1, 30, 30, 30, 13)
    close(network.base_dists[0], 13)
    close(network.dist_matrix[0][1], 13)
    heads, nodes, outliers = build_clusters([0], [0,1], network.dist_matrix, 13)
    assert outliers == []
    root = dropping_member_multi_hop_routing(heads, nodes, [0,1], outliers, network.dist_matrix,
        network.base_dists, [1,1], 13, .4)
    assert root is not None
    _, _, outliers = build_clusters([0], [0,1], network.dist_matrix, 13-1e-10)
    assert outliers == [1]
    result['range_and_3d_geometry_boundary'] = 'passed'

    n = 10
    network = NetworkInstance([Point(i,0,1) for i in range(n)], Point(0,0,0), 1, 20, 1, 2, 100)
    rounding = []
    for proportion, expected in ((.2, 2), (.25, 2), (.35, 4), (1., 10)):
        params = DACOParameters(CH_proportion=proportion)
        clustering = DACOClustering(network, hp, params)
        clustering.grid.compute_density(list(range(n)), [1]*n)
        order = clustering._make_path(list(range(n)), [1]*n, 0)
        assert len(order) == expected
        rounding.append({'q': proportion, 'n': n, 'heads': len(order)})
    result['actual_ch_count_rounding'] = rounding

    # Real Simulator.run with only its unrelated visual dependency substituted.
    plotting = ModuleType('visual')
    plotting.Visual = object
    with patch.dict(sys.modules, {'visual': plotting}):
        from simulate import Simulator
    simulator = Simulator.__new__(Simulator)
    simulator.network = SimpleNamespace(init_energy=1., N=2)
    simulator.hparameters = SimpleNamespace(T_max=4)
    simulator.evaluator = evaluator
    seen_states = []
    class PrescribedPlans:
        name = 'formula audit'
        def plan_round(self, live, energies):
            seen_states.append((list(live), list(energies)))
            if len(seen_states) == 1:
                return Node(-1), {0: .25, 1: 2.}
            return Node(-1), {0: 1.}
    # The bundled pandas table constructor fails in its inferred-string
    # extension. Replace only final table packaging, leaving the real loop,
    # energy subtraction, live filtering, and history recording untouched.
    with patch.object(Simulator.run.__globals__['pd'], 'DataFrame', side_effect=lambda data, **kwargs: data):
        history = simulator.run(PrescribedPlans(), verbose=False)
    assert seen_states == [([0,1], [1.,1.]), ([0], [.75,0.])]
    assert [row['alive_nodes'] for row in history] == [1,0]
    assert [row['round_energy'] for row in history] == [2.25,1.]
    result['real_simulator_state_and_live_set'] = {'passed': True, 'observed_pre_round_states': seen_states,
        'counted_updates': len(history), 'nominal_logged_j': sum(row['round_energy'] for row in history), 'initial_battery_j': 2.,
        'output_packaging': 'DataFrame constructor substituted because of bundled pandas StringArray failure'}

    # Independent finite check of the schedule objective and energy tie-break.
    # This is a mathematical definition check, not an implementation of DACO.
    legal_parent_count = 0
    for parents in product((-1,1,2), (-1,0,2), (-1,0,1)):
        chains = reaches_sink(parents)
        bounded = all(any(iterate_parent(parents, i, m) == -1 for m in range(1,4)) for i in range(3))
        assert chains == bounded
        legal_parent_count += int(chains)
    assert legal_parent_count == 16
    def schedules(state, horizon):
        if not any(state) or horizon == 0:
            return [(0, Fraction(0))]
        live = [i for i, energy in enumerate(state) if energy > 0]
        out = [(0, Fraction(0))]
        for heavy in live:
            costs = {i: Fraction(3,4) if i == heavy else Fraction(1,4) for i in live}
            next_state = tuple(max(Fraction(0), energy-costs.get(i,0)) for i,energy in enumerate(state))
            out += [(1+length, sum(costs.values())+energy) for length,energy in schedules(next_state,horizon-1)]
        return out
    outcomes = schedules((Fraction(1), Fraction(1)), 4)
    duration = max(length for length, _ in outcomes)
    tie_energy = min(energy for length, energy in outcomes if length == duration)
    assert (duration, tie_energy) == (3, Fraction(11,4))
    assert schedules((Fraction(0), Fraction(0)), 4) == [(0, Fraction(0))]
    assert schedules((Fraction(1), Fraction(1)), 0) == [(0, Fraction(0))]
    result['schedule_definition_checks'] = {'three_sensor_parent_maps': 16, 'max_duration': duration,
        'min_nominal_energy_at_that_duration': str(tie_energy), 'empty_state_and_zero_horizon': 'passed',
        'implementation_claim': 'ideal objective only; production DACO does not enumerate or optimize these schedules exactly'}
    return result


def iterate_parent(parents, node, count):
    for _ in range(count):
        node = -1 if node == -1 else parents[node]
    return node


if __name__ == '__main__':
    results = audit()
    results['code_sha256'] = {relative: hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() for relative in (
        'src/evaluate.py','src/hparameter.py','src/simulate.py','src/network.py','src/point.py',
        'src/algorithms/d_aco.py','src/algorithms/clustering/d_aco/d_aco.py',
        'src/algorithms/clustering/clustering.py','src/algorithms/routing/routing.py')}
    print(json.dumps(results, indent=2, default=float))
