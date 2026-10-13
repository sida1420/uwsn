"""Chaos amplitude and mechanism study after coupled pheromone calibration.

All interventions are experiment-local. Production algorithms are unchanged.
"""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from time import process_time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'plans/phase5-acaco-tuning'))
from calibrate import BASE
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance

FACTORS = (0., .25, .5, 1., 2.)


def configs():
    current = ACACOParameters()
    result = {}
    for scale, base in (('historical',BASE), ('calibrated',current)):
        for factor in FACTORS:
            result[f'{scale}_x{factor:g}'] = dict(parameters=asdict(replace(base,
                chaos_min=base.chaos_min*factor, chaos_max=base.chaos_max*factor)),
                transition_chaos=True, pheromone_chaos=True)
    for mechanism in ('transition', 'pheromone'):
        result[f'calibrated_without_{mechanism}'] = dict(parameters=asdict(current),
            transition_chaos=mechanism != 'transition',
            pheromone_chaos=mechanism != 'pheromone')
    return result


def signature(root):
    edges, stack = [], [root]
    while stack:
        node = stack.pop()
        if node.id != -1:
            edges.append((node.id,node.prev.id,node.isCH,node.isRelay))
        stack.extend(node.nxts)
    return tuple(sorted(edges))


def run(network, cfg, seed, rounds, trajectory):
    params = ACACOParameters(**cfg['parameters'])
    hp = HyperParameters()
    algorithm = ACACO(network, hp, params, seed=seed)
    clustering = algorithm.clustering
    original_transition = clustering._transition_probabilities
    if not cfg['transition_chaos']:
        clustering._transition_probabilities = lambda source, available, residual, beta, strength: original_transition(
            source, available, residual, beta, 0.)
    if not cfg['pheromone_chaos']:
        original_update = clustering._update_pheromone
        clustering._update_pheromone = lambda state: original_update(replace(state,strength=0.))
    evaluator = Evaluator(hp)
    residual = [network.init_energy]*network.N
    live = list(range(network.N))
    records = []
    for t in range(rounds):
        candidates, states, outliers = [], [], []
        original_evaluate = algorithm.evaluator.energy_consumption
        original_pre = clustering.pre_round
        original_clusters = clustering.create_clusters
        attempts_before = algorithm.total_routing_attempts
        failures_before = algorithm.failed_routing_attempts
        def evaluate(root, distances, base_distances):
            costs, total = original_evaluate(root,distances,base_distances)
            tree = signature(root)
            candidates.append((tree,total,
                sum(not n[2] and n[1] == -1 for n in tree)))
            return costs,total
        def pre(live_nodes, energies):
            state = original_pre(live_nodes, energies)
            states.append((state,clustering.chaos.copy()))
            return state
        def create(*args):
            clusters = original_clusters(*args)
            if clusters is not None:
                outliers.append(len(clusters[2]))
            return clusters
        algorithm.evaluator.energy_consumption = evaluate
        clustering.pre_round = pre
        clustering.create_clusters = create
        before = residual.copy()
        start = process_time()
        with redirect_stdout(StringIO()):
            root, consumption = algorithm.plan_round(live,residual)
        cpu = process_time()-start
        algorithm.evaluator.energy_consumption = original_evaluate
        clustering.pre_round = original_pre
        clustering.create_clusters = original_clusters
        assert before == residual
        if root is None:
            records.append(dict(round=t,failed=True,cpu_s=cpu))
            break
        costs,total = evaluator.energy_consumption(root,network.dist_matrix,network.base_dists)
        assert costs == consumption and set(costs) == set(live)
        state, chaos_before = states[0]
        rng_state = clustering.rng.getstate()
        # Exact mixture share, averaged over the 99..81 choices of a 20-CH
        # path and live sources. Diagnostics consume no RNG or round hooks.
        sizes = np.arange(len(live)-1,len(live)-state.target,-1)
        chaos = np.asarray(chaos_before)
        strength = state.strength if cfg['transition_chaos'] else 0.
        uniform_share = sizes[:,None]*strength*chaos[np.asarray(live)][None,:]
        uniform_share = uniform_share/(1+uniform_share)
        entropy = []
        chaos_after = clustering.chaos
        clustering.chaos = chaos_before
        for source in live[:10]:
            available = [i for i in live if i != source]
            probs = np.asarray(clustering._transition_probabilities(source,
                available,before,state.beta,strength))
            assert np.isfinite(probs).all() and (probs >= 0).all()
            assert abs(probs.sum()-1) < 1e-12
            entropy.append(float(-np.sum(probs[probs>0]*np.log(probs[probs>0]))/np.log(len(probs))))
        clustering.chaos = chaos_after
        assert rng_state == clustering.rng.getstate()
        tau = np.asarray(clustering.pheromone)[np.ix_(live,live)]
        tau = tau[~np.eye(len(live),dtype=bool)]
        assert np.isfinite(tau).all() and (tau >= params.tau_min).all() and (tau <= params.tau_max).all()
        max_depletion = max(costs[i]/before[i] for i in live)
        if trajectory:
            residual = [max(0.,e-costs.get(i,0)) for i,e in enumerate(residual)]
            live = [i for i in live if residual[i]>0]
        records.append(dict(round=t,failed=False,energy_J=total,cpu_s=cpu,
            actual_feasible_evaluations=len(candidates),
            routing_attempts=algorithm.total_routing_attempts-attempts_before,
            failed_routing_attempts=algorithm.failed_routing_attempts-failures_before,
            mean_clustering_outliers=float(np.mean(outliers)),
            unique_trees=len(set(c[0] for c in candidates)),
            candidate_median_J=float(np.median([c[1] for c in candidates])),
            chaos_strength=state.strength,mean_uniform_share=float(np.mean(uniform_share)),
            normalized_entropy=float(np.mean(entropy)),
            mean_nonCH_direct_nodes=float(np.mean([c[2] for c in candidates])),
            floor_fraction=float(np.mean(tau<=params.tau_min+1e-12)),
            ceiling_fraction=float(np.mean(tau>=params.tau_max-1e-12)),
            tau_p10=float(np.quantile(tau,.1)),tau_p90=float(np.quantile(tau,.9)),
            max_depletion=max_depletion,min_residual=min(residual),alive=len(live)))
    valid = [r for r in records if not r['failed']]
    result = dict(seed=seed,completed_rounds=len(valid),failed=len(valid)!=rounds,
        total_energy_J=sum(r['energy_J'] for r in valid),cpu_s=sum(r['cpu_s'] for r in records),
        feasible_evaluations=sum(r['actual_feasible_evaluations'] for r in valid),
        unique_trees=sum(r['unique_trees'] for r in valid),
        min_residual=min(residual),peak_depletion=max(r['max_depletion'] for r in valid),
        records=records)
    for key in ('chaos_strength','mean_uniform_share','normalized_entropy',
                'floor_fraction','ceiling_fraction','candidate_median_J','mean_nonCH_direct_nodes',
                'mean_clustering_outliers'):
        result[key] = float(np.mean([r[key] for r in valid]))
    return result


def main():
    folder = Path(__file__).parent
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    source_hashes = {str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'src').rglob('*.py'))}
    result = dict(configs=configs(),map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes=source_hashes,script_sha=sha256(Path(__file__).read_bytes()).hexdigest(),
        schedule_horizon=3000,screening_seeds=[0,1,2],validation_seeds=[6,7,8],
        screening={},validation={})
    saved = folder/'results.json'
    if saved.exists():
        previous = json.loads(saved.read_text())
        for key in ('configs','map_sha','source_hashes','script_sha'):
            assert previous[key] == result[key], f'Mismatched {key}; move results.json for a fresh experiment'
        result['screening'],result['validation'] = previous['screening'],previous['validation']
    # Config-major fixed-state screening; all strengths predeclared, no
    # default promotion or holdout-driven hyperparameter selection.
    for name,cfg in result['configs'].items():
        if name in result['screening']:
            continue
        rows = [run(network,cfg,seed,20,False) for seed in (0,1,2)]
        result['screening'][name] = rows
        print('SCREEN',name,'energy',np.mean([r['total_energy_J'] for r in rows]),flush=True)
        saved.write_text(json.dumps(result,indent=2))
    # Seed-major rotating order mitigates systematic timing/order drift.
    names = [f'calibrated_x{factor:g}' for factor in FACTORS]
    for offset,seed in enumerate((6,7,8)):
        order = names[offset:]+names[:offset]
        for name in order:
            rows = result['validation'].setdefault(name,[])
            if any(r['seed']==seed for r in rows):
                continue
            print('VALIDATE',name,'seed',seed,flush=True)
            row = run(network,result['configs'][name],seed,150,True)
            rows.append(row)
            print('DONE',name,seed,row['total_energy_J'],row['min_residual'],flush=True)
            saved.write_text(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
