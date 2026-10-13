"""Continue calibrated x1/x2 to actual service termination, up to T_max.

Configurations are loaded from the previous experiment, not moving defaults.
Energy costs are evaluated by unchanged production code. Snapshots preserve
physical, optimizer and RNG state for reproducible later probes.
"""
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import sys
from time import process_time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance


def connectivity(network,live):
    remaining = set(live)
    reached = {i for i in live if network.base_dists[i]<=network.radius}
    queue = list(reached)
    for node in queue:
        neighbors = {i for i in remaining if network.dist_matrix[node][i]<=network.radius}
        new = neighbors-reached
        reached.update(new)
        queue.extend(sorted(new))
    return dict(base_connected=sorted(reached),disconnected=sorted(remaining-reached))


def snapshot(algorithm,residual,live,completed):
    c = algorithm.clustering
    return dict(completed_rounds=completed,residual=residual,live=live,
        parameters=asdict(algorithm.params),iteration=c.iteration,
        pheromone=c.pheromone,chaos=c.chaos,rng_state=c.rng.getstate(),
        previous_cost=c.previous_cost,lower_cost=c.lower_cost,upper_cost=c.upper_cost)


def restore(state,network):
    a = ACACO(network,HyperParameters(),ACACOParameters(**state['parameters']),seed=0)
    c = a.clustering
    for key in ('iteration','pheromone','chaos','previous_cost','lower_cost','upper_cost'):
        setattr(c,key,deepcopy(state[key]))
    # json converts the RNG's nested tuples to lists.
    raw = state['rng_state']
    c.rng.setstate((raw[0],tuple(raw[1]),raw[2]))
    return a


def run(network,params,seed,name,folder):
    algorithm = ACACO(network,HyperParameters(),params,seed=seed)
    evaluator = Evaluator(HyperParameters())
    residual = [network.init_energy]*network.N
    live = list(range(network.N))
    records,events = [],[]
    result = dict(config=name,seed=seed,parameters=asdict(params),records=records,
        death_events=events,FND=None,HND=None,LND=None,termination_reason=None)
    for t in range(algorithm.hparameters.T_max):
        evaluated = []
        original = algorithm.evaluator.energy_consumption
        def evaluate(*args):
            costs,total = original(*args)
            evaluated.append(total)
            return costs,total
        algorithm.evaluator.energy_consumption = evaluate
        before = residual.copy()
        attempts_before = algorithm.total_routing_attempts
        start = process_time()
        with redirect_stdout(StringIO()):
            root,costs = algorithm.plan_round(live,residual)
        cpu = process_time()-start
        algorithm.evaluator.energy_consumption = original
        assert residual==before
        if root is None:
            result['termination_reason']='no_feasible_route'
            result['failed_round_index']=t
            result['terminal_connectivity']=connectivity(network,live)
            result['failed_search_attempts']=algorithm.total_routing_attempts-attempts_before
            (folder/f'{name}_seed{seed}_terminal.json').write_text(json.dumps(
                snapshot(algorithm,residual,live,t),indent=2),encoding='utf-8')
            break
        checked,total = evaluator.energy_consumption(root,network.dist_matrix,network.base_dists)
        assert costs==checked and set(costs)==set(live)
        residual = [max(0.,e-costs.get(i,0)) for i,e in enumerate(residual)]
        dead = [i for i in live if residual[i]<=0]
        live = [i for i in live if residual[i]>0]
        if dead:
            result['FND'] = result['FND'] or t+1
            if len(live)<=network.N/2:
                result['HND'] = result['HND'] or t+1
            if not live:
                result['LND']=t+1
            events.append(dict(completed_round=t+1,dead=dead,alive=len(live),
                connectivity=connectivity(network,live)))
        tau = np.asarray(algorithm.clustering.pheromone)
        active = tau[np.ix_(live,live)]
        active = active[~np.eye(len(live),dtype=bool)]
        assert np.isfinite(tau).all() and (tau>=params.tau_min).all() and (tau<=params.tau_max).all()
        record = dict(completed_round=t+1,alive=len(live),served=len(costs),energy_J=total,
            energy_deducted_J=sum(before)-sum(residual),residual_total_J=sum(residual),
            min_survivor_residual_J=min((residual[i] for i in live),default=0),
            candidate_median_J=float(np.median(evaluated)),feasible_evaluations=len(evaluated),
            routing_attempts=algorithm.total_routing_attempts-attempts_before,cpu_s=cpu,
            tau_floor_fraction=float(np.mean(active<=params.tau_min+1e-12)) if active.size else 0,
            tau_ceiling_fraction=float(np.mean(active>=params.tau_max-1e-12)) if active.size else 0)
        records.append(record)
        if t+1 in (150,600,1400,1499,1501):
            (folder/f'{name}_seed{seed}_round{t+1}.json').write_text(json.dumps(
                snapshot(algorithm,residual,live,t+1),indent=2),encoding='utf-8')
        if (t+1)%100==0 or dead:
            print(name,seed,'round',t+1,'alive',len(live),'FND',result['FND'],flush=True)
            (folder/f'{name}_seed{seed}_progress.json').write_text(json.dumps(result),encoding='utf-8')
        if not live:
            result['termination_reason']='all_nodes_dead'
            break
    result['termination_reason']=result['termination_reason'] or 'T_max'
    result['completed_rounds']=len(records)
    result['alive_at_end']=len(live)
    result['cpu_s']=sum(r['cpu_s'] for r in records)
    result['modeled_energy_J']=sum(r['energy_J'] for r in records)
    result['deducted_energy_J']=network.N*network.init_energy-sum(residual)
    result['FND_censored']=result['FND'] is None
    result['HND_censored']=result['HND'] is None
    result['LND_censored']=result['LND'] is None
    return result


def main():
    folder = Path(__file__).parent/'long'
    folder.mkdir(exist_ok=True)
    prior = json.loads((folder.parent/'results.json').read_text())
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    hashes = {str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'src').rglob('*.py'))}
    assert hashes==prior['source_hashes'], 'Production source changed since the amplitude study'
    result = dict(map_sha=prior['map_sha'],source_hashes=hashes,
        script_sha=sha256(Path(__file__).read_bytes()).hexdigest(),seeds=[6,7,8],
        T_max=3000,runs=[])
    names = ['calibrated_x1','calibrated_x2']
    for offset,seed in enumerate((6,7,8)):
        for name in names[offset%2:]+names[:offset%2]:
            target = folder/f'{name}_seed{seed}.json'
            if target.exists():
                row = json.loads(target.read_text())
            else:
                params = ACACOParameters(**prior['configs'][name]['parameters'])
                print('START',name,seed,flush=True)
                row = run(network,params,seed,name,folder)
                target.write_text(json.dumps(row,indent=2),encoding='utf-8')
            result['runs'].append(row)
            (folder/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print('END',name,seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)


if __name__=='__main__':
    main()
