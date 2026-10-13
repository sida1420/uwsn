"""Full D-ACO transfer and density-fitness trials; no inner iterations."""
import ast
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import platform
import random
import sys
from time import process_time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'plans/phase9-daco-power/archive'))
from legacy_daco_algorithm import DACO
from legacy_daco_parameters import DACOParameters
from hparameter import HyperParameters
from network import NetworkInstance

FOLDER = Path(__file__).parent
SEEDS = (15,16,17)
SIBLING = ROOT.parent/'uwsn'


def sibling_values():
    tree = ast.parse((SIBLING/'src/algorithms/clustering/d_aco/parameters.py').read_text())
    cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DACOParameters')
    init = next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    return {n.targets[0].attr:ast.literal_eval(n.value) for n in init.body
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Attribute)}


TUNED = sibling_values()
BASELINE = vars(DACOParameters()).copy()
TRANSFER = BASELINE | {k:v for k,v in TUNED.items() if k in BASELINE}
TRANSFER.update(num_ants=40,fitness_mode='absolute',deposit_mode='live',elite_per_ant=True)


def config(name):
    if name=='baseline':
        return BASELINE.copy()
    if name=='tuned':
        return TRANSFER.copy()
    chosen = json.loads((FOLDER/'chosen_base.json').read_text())['parameters'].copy()
    options = {'risk_control':dict(density_load_weight=.1,density_load_kappa=0.),
        'density_005':dict(density_load_weight=.05,density_load_kappa=1.),
        'density_010':dict(density_load_weight=.1,density_load_kappa=1.)}
    return chosen | options[name]


def provenance(name):
    return dict(seeds=list(SEEDS),T_max=3000,configuration=name,parameters=config(name),
        tuned_original=TUNED,adaptation='one batch of 40 ants; absolute fitness and live deposits',
        map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src').rglob('*.py'))},
        sibling_hashes={str(p.relative_to(SIBLING)):sha256(p.read_bytes()).hexdigest()
            for p in (SIBLING/'src/algorithms/d_aco.py',SIBLING/'src/algorithms/clustering/d_aco/d_aco.py',
                      SIBLING/'src/algorithms/clustering/d_aco/parameters.py')},
        runner_sha=sha256(Path(__file__).read_bytes()).hexdigest(),python=platform.python_version())


def run(network, parameters, seed, name):
    random.seed(seed)
    params = DACOParameters()
    for key,value in parameters.items():
        setattr(params,key,value)
    algorithm = DACO(network,HyperParameters(),params)
    live = list(range(network.N))
    residual = [network.init_energy]*network.N
    records = []
    fnd = hnd = lnd = None
    reason = 'horizon'
    begin = process_time()
    for t in range(3000):
        with redirect_stdout(StringIO()):
            root,costs = algorithm.plan_round(live,residual)
        if root is None:
            reason = 'no_feasible_tree'
            break
        assert set(costs)==set(live)
        assert all(np.isfinite(v) and v>=0 for v in costs.values())
        loads = np.asarray([costs[i] for i in live])
        risk = max(costs[i]/residual[i] for i in live)
        for i,cost in costs.items():
            residual[i] = max(0.,residual[i]-cost)
        dead = [i for i in live if residual[i]<=0]
        live = [i for i in live if residual[i]>0]
        if dead and fnd is None:
            fnd = t+1
        if len(live)<=network.N/2 and hnd is None:
            hnd = t+1
        if not live:
            lnd,reason = t+1,'all_nodes_dead'
        records.append(dict(round=t+1,energy=sum(costs.values()),cv=float(loads.std()/loads.mean()),
            peak_depletion=risk,alive=len(live),dead=dead))
        if (t+1)%100==0:
            progress = dict(configuration=name,seed=seed,completed=t+1,FND=fnd,alive=len(live),cpu=process_time()-begin)
            (FOLDER/'full'/f'progress_{name}_{seed}.json').write_text(json.dumps(progress))
            print('PROGRESS',name,seed,t+1,'alive',len(live),'FND',fnd,flush=True)
        if not live:
            break
    return dict(configuration=name,seed=seed,parameters=vars(params),records=records,
        completed_rounds=len(records),FND=fnd,HND=hnd,LND=lnd,termination_reason=reason,
        alive=live,residual=residual,cpu=process_time()-begin,
        clustering_attempts=algorithm.total_clustering_attempts,
        routing_attempts=algorithm.total_routing_attempts)


def main():
    seed,name = int(sys.argv[1]),sys.argv[2]
    assert seed in SEEDS
    folder = FOLDER/'full'
    folder.mkdir(parents=True,exist_ok=True)
    expected = provenance(name)
    metadata = folder/f'metadata_{name}_{seed}.json'
    if metadata.exists():
        assert json.loads(metadata.read_text())==expected, 'Different provenance'
    else:
        metadata.write_text(json.dumps(expected,indent=2))
    target = folder/f'{name}_{seed}.json'
    if target.exists():
        return
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    print('START',name,seed,flush=True)
    row = run(network,config(name),seed,name)
    assert provenance(name)==expected, 'Source changed during run'
    row['provenance'] = expected
    target.write_text(json.dumps(row,indent=2))
    print('END',name,seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)


if __name__=='__main__':
    main()
