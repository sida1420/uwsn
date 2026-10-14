"""Read-only source audit probes; write only new audit artifacts beside this file."""
from pathlib import Path
import contextlib
from dataclasses import replace
import hashlib
import io
import itertools
import json
import math
import pickle
import platform
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from algorithms.ac_aco import ACACO
from algorithms.d_aco import DACO
from algorithms.clustering.ac_aco.ac_aco import heuristic_weight
from algorithms.clustering.clustering import build_clusters
from algorithms.routing.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from point import Point


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_checks(root, network, live, costs):
    seen = set()
    heads = []
    def walk(node):
        if node.id != -1:
            assert node.id not in seen
            seen.add(node.id)
            if node.isCH:
                heads.append(node.id)
            distance = (network.base_dists[node.id] if node.prev.id == -1
                        else network.dist_matrix[node.id][node.prev.id])
            assert distance <= network.radius
        for child in node.nxts:
            assert child.prev is node
            walk(child)
    walk(root)
    assert seen == set(live) == set(costs)
    return heads


def short_runs(network):
    rows = []
    for mode in ('fixed_state', 'depleting'):
        for seed in (24, 25, 26):
            for cls in (ACACO, DACO):
                hp = HyperParameters()  # No change to current horizon/physics/defaults.
                algorithm = cls(network, hp, seed=seed)
                residual = [network.init_energy] * network.N
                live = list(range(network.N))
                candidate_costs = []
                candidate_starts = []
                original_eval = algorithm.evaluator.energy_consumption
                original_cluster = algorithm.clustering.create_clusters
                def observed_eval(*args):
                    costs, total = original_eval(*args)
                    candidate_costs.append(total)
                    return costs, total
                def observed_cluster(*args):
                    result = original_cluster(*args)
                    if result is not None:
                        candidate_starts.append(next(iter(result[0])))
                    return result
                algorithm.evaluator.energy_consumption = observed_eval
                algorithm.clustering.create_clusters = observed_cluster
                for t in range(10):
                    candidate_costs.clear()
                    candidate_starts.clear()
                    before = list(residual)
                    started = time.perf_counter()
                    with contextlib.redirect_stdout(io.StringIO()):
                        root, costs = algorithm.plan_round(live, residual)
                    elapsed = time.perf_counter() - started
                    assert residual == before
                    assert root is not None
                    heads = tree_checks(root, network, live, costs)
                    independent, total = Evaluator(hp).energy_consumption(
                        root, network.dist_matrix, network.base_dists)
                    assert independent == costs
                    assert all(math.isfinite(e) and e >= 0 for e in costs.values())
                    pair_distances = [network.dist_matrix[a][b]
                                      for a, b in itertools.combinations(heads, 2)]
                    rows.append(dict(mode=mode, seed=seed, algorithm=algorithm.name,
                        round=t, energy=total, candidates=len(candidate_costs),
                        calibration_included=(cls is DACO and t == 0),
                        unique_starts=len(set(candidate_starts)),
                        minimum_observed_candidate_energy=min(candidate_costs),
                        selection_above_minimum=total/min(candidate_costs)-1,
                        max_relative_depletion=max(e/residual[i] for i, e in costs.items()),
                        load_cv=float(np.std(list(costs.values()))/np.mean(list(costs.values()))),
                        mean_ch_pair_distance=statistics.mean(pair_distances),
                        seconds=elapsed))
                    if mode == 'depleting':
                        residual = [max(0., e-costs.get(i, 0.)) for i, e in enumerate(residual)]
                        live = [i for i in live if residual[i] > 0]
                assert len(live) == network.N
    stats = []
    for mode in ('fixed_state', 'depleting'):
        ac, da = [], []
        for seed in (24, 25, 26):
            ac.append(sum(r['energy'] for r in rows if r['mode'] == mode and r['seed'] == seed and r['algorithm'] == 'AC-ACO'))
            da.append(sum(r['energy'] for r in rows if r['mode'] == mode and r['seed'] == seed and r['algorithm'] == 'D-ACO'))
        delta = [a-d for a, d in zip(ac, da)]
        stats.append(dict(mode=mode, ac=ac, daco=da, mean_ac=statistics.mean(ac),
            sd_ac=statistics.stdev(ac), mean_daco=statistics.mean(da), sd_daco=statistics.stdev(da),
            mean_paired_difference=statistics.mean(delta), sd_paired_difference=statistics.stdev(delta),
            paired_dz=statistics.mean(delta)/statistics.stdev(delta),
            energy_change_pct=100*(statistics.mean(ac)/statistics.mean(da)-1)))
    return rows, stats


def operators(network):
    c = ACACO(network, HyperParameters(), seed=24).clustering
    residual = [network.init_energy] * network.N
    state = c.pre_round(list(range(network.N)), residual)
    probs = c._transition_probabilities(0, list(range(1, network.N)), residual, state.beta, state.strength)
    uniform_share = (network.N-1)*state.strength*c.chaos[0]/(1+(network.N-1)*state.strength*c.chaos[0])
    assert abs(sum(probs)-1) < 1e-12
    assert min(probs) >= 0 and all(map(math.isfinite, probs))
    horizon = HyperParameters().T_max
    beta = {str(t): heuristic_weight(t, horizon, 1, 5, 5) for t in (1, 1500, 1749, 1750, 1751, 2000, 3500)}
    fixture = ACACO(network, HyperParameters(), seed=24)
    low_energy = (.01, (0, 1), None, {0: .009, 1: .001}, 0.)
    balanced = (.011, (0, 2), None, {0: .0055, 1: .0055}, 0.)
    assert fixture._best_candidate([low_energy, balanced]) is low_energy
    return dict(first_strength=state.strength, chaos_source0=c.chaos[0],
        first_uniform_share=uniform_share, first_probability_min=min(probs),
        first_probability_max=max(probs), beta_schedule=beta,
        objective_fixture=dict(ac_choice_energy=.01, balanced_energy=.011,
            equal_residual_max_depletion_ratio=.009/.0055),
        expected_unique_starts=network.N*(1-(1-1/network.N)**40))


def order_probe():
    rng = random.Random(1729)
    for case in range(150):
        points = [Point(rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 1)) for _ in range(12)]
        residual = [rng.uniform(.1, 1) for _ in points]
        n = NetworkInstance(points, Point(0, 0, 0), 1, 3, 3, 1, 1.5)
        energies = []
        for chs in itertools.permutations(range(4)):
            ch_nodes, nodes, outliers = build_clusters(chs, list(range(12)), n.dist_matrix, n.radius)
            root = dropping_member_multi_hop_routing(ch_nodes, nodes, list(range(12)), outliers,
                    n.dist_matrix, n.base_dists, residual, n.radius)
            if root:
                energies.append(Evaluator(HyperParameters()).energy_consumption(root, n.dist_matrix, n.base_dists)[1])
        if len(energies) == 24 and max(energies) > min(energies)*1.01:
            return dict(case=case, minimum=min(energies), maximum=max(energies),
                        difference_pct=100*(max(energies)/min(energies)-1))
    return None


def ablations(network):
    observations = []
    for variant in ('transition_no_chaos', 'distance_weight_zero', 'load_weight_0_1'):
        for seed in (24, 25, 26):
            algorithm = ACACO(network, HyperParameters(), seed=seed)
            if variant == 'transition_no_chaos':
                original = algorithm.clustering._transition_probabilities
                def no_transition_chaos(source, available, residual, beta, strength):
                    return original(source, available, residual, beta, 0.)
                algorithm.clustering._transition_probabilities = no_transition_chaos
            else:
                changes = {'distance_weight': 0.} if variant == 'distance_weight_zero' else {'load_weight': .1}
                params = replace(algorithm.params, **changes)
                algorithm = ACACO(network, HyperParameters(), params, seed=seed)
            energy = 0.
            peaks, distances = [], []
            residual = [network.init_energy]*network.N
            live = list(range(network.N))
            for _ in range(10):
                with contextlib.redirect_stdout(io.StringIO()):
                    root, costs = algorithm.plan_round(live, residual)
                assert root is not None
                heads = tree_checks(root, network, live, costs)
                energy += sum(costs.values())
                peaks.append(max(e/residual[i] for i, e in costs.items()))
                distances.append(statistics.mean(network.dist_matrix[a][b] for a, b in itertools.combinations(heads, 2)))
            observations.append(dict(variant=variant, seed=seed, energy_10_decisions=energy,
                mean_max_relative_depletion=statistics.mean(peaks), mean_ch_pair_distance=statistics.mean(distances)))
    return observations


def main():
    paths = sorted((ROOT/'src').rglob('*.py')) + [ROOT/'map.pkl']
    before = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    n = NetworkInstance.from_pickle(ROOT/'map.pkl')
    with (ROOT/'map.pkl').open('rb') as handle:
        raw = pickle.load(handle)
    rows, stats = short_runs(n)
    result = dict(python=sys.version, platform=platform.platform(), numpy=np.__version__,
        map=dict(sha256=sha(ROOT/'map.pkl'), seed=raw.get('seed'), N=n.N,
            dimensions=[n.width, n.height, n.depth], radius=n.radius,
            init_energy=n.init_energy, directly_reachable=sum(d <= n.radius for d in n.base_dists)),
        hparameters=vars(HyperParameters()),
        ac_parameters=vars(ACACO(n, HyperParameters(), seed=24).params),
        daco_parameters=vars(DACO(n, HyperParameters(), seed=24).params),
        operators=operators(n), order_probe=order_probe(), stats=stats, rows=rows,
        fixed_state_ablations=ablations(n), source_hashes=before)
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in paths}
    (Path(__file__).parent/'diagnostics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('map', 'operators', 'order_probe', 'stats')}, indent=2))


if __name__ == '__main__':
    main()
