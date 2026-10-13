"""Independent full Q/heuristic ablations; current fitness stays fixed."""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import random
import sys
from time import process_time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from algorithms.d_aco import DACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from hparameter import HyperParameters
from network import NetworkInstance

FOLDER = Path(__file__).parent
SEEDS = (24, 25, 26)
BASE = DACOParameters()
CONFIGS = dict(deposit_2x=replace(BASE,Q=10.), deposit_4x=replace(BASE,Q=20.),
    heuristic_half=replace(BASE,beta=.45,gamma=.2),
    heuristic_quarter=replace(BASE,beta=.225,gamma=.1))

def hashes():
    return dict(map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        sources={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
                 for p in sorted((ROOT/'src').rglob('*.py'))})

def provenance():
    return dict(**hashes(),runner_sha=sha256(Path(__file__).read_bytes()).hexdigest(),
        seeds=SEEDS,horizon=3000,configs={k:asdict(v) for k,v in CONFIGS.items()})

def validate_controls():
    current = hashes()
    for name in ('daco','pheromone'):
        for seed in SEEDS:
            row=json.loads((ROOT/'plans/phase10-daco-vs-pheromone/full'/f'{name}_{seed}.json').read_text())
            assert all(row['provenance'][key]==value for key,value in current.items()), 'Control epoch mismatch'
            if name=='daco':
                assert row['parameters']==asdict(BASE), 'Control defaults changed'

def instrument(clustering):
    """Observe actual capped deposits without changing their output or randomness."""
    counters=dict(updates=0,clipped=0,requested=0.,lost=0.)
    original=clustering.deposit
    def deposit(chs,fitness,energy_reference,per_ant=True):
        if chs and fitness is not None and fitness>0:
            amount=clustering.params.Q*energy_reference/fitness
            amount=amount/clustering.params.num_ants if per_ant else amount*clustering.params.theta
            for node in chs:
                excess=max(0.,clustering.pheromone[node]+amount-clustering.params.tau_max)
                counters['updates']+=1
                counters['clipped']+=int(excess>1e-12)
                counters['requested']+=amount
                counters['lost']+=excess
        return original(chs,fitness,energy_reference,per_ant)
    clustering.deposit=deposit
    return counters

def run(name,seed):
    random.seed(seed)
    params=CONFIGS[name]
    network=NetworkInstance.from_pickle(ROOT/'map.pkl')
    begin=process_time()
    algorithm=DACO(network,HyperParameters(),params)
    counters=instrument(algorithm.clustering)
    live=list(range(network.N))
    residual=[network.init_energy]*network.N
    records=[]
    fnd=hnd=lnd=None
    reason='horizon'
    for t in range(3000):
        previous=counters.copy()
        with redirect_stdout(StringIO()):
            root,costs=algorithm.plan_round(live,residual)
        if root is None:
            reason='no_feasible_tree'
            break
        assert set(costs)==set(live)
        assert all(np.isfinite(v) and v>=0 for v in costs.values())
        assert sum(costs.values())>0
        tau=np.asarray(algorithm.clustering.pheromone)[live]
        cap_fraction=float(np.mean(tau>=params.tau_max-1e-12))
        components=algorithm.clustering._score_components
        spreads={key:max(values)-min(values) if values else 0. for key,values in components.items()}
        for i,cost in costs.items():
            residual[i]=max(0.,residual[i]-cost)
        dead=[i for i in live if residual[i]<=0]
        live=[i for i in live if residual[i]>0]
        if dead and fnd is None: fnd=t+1
        if len(live)<=network.N/2 and hnd is None: hnd=t+1
        if not live: lnd,reason=t+1,'all_nodes_dead'
        records.append(dict(round=t+1,energy=sum(costs.values()),alive=len(live),dead=dead,
            tau_cap_fraction=cap_fraction,tau_min=float(tau.min()),tau_max=float(tau.max()),
            tau_spread=float(tau.max()-tau.min()),score_spreads=spreads,
            deposit={key:counters[key]-previous[key] for key in counters}))
        if (t+1)%100==0:
            print('PROGRESS',name,seed,t+1,'alive',len(live),'FND',fnd,
                  'cap',round(cap_fraction,3),flush=True)
        if not live: break
    return dict(configuration=name,seed=seed,parameters=asdict(params),records=records,
        FND=fnd,HND=hnd,LND=lnd,completed_rounds=len(records),termination_reason=reason,
        alive=live,residual=residual,cpu=process_time()-begin,
        clustering_attempts=algorithm.total_clustering_attempts,
        routing_attempts=algorithm.total_routing_attempts,
        calibration_attempts=algorithm.calibration_attempts,
        calibration_routing_attempts=algorithm.calibration_routing_attempts,
        deposits=counters)

def main():
    name,seed=sys.argv[1],int(sys.argv[2])
    assert name in CONFIGS and seed in SEEDS
    validate_controls()
    folder=FOLDER/'full'
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/f'{name}_{seed}.json'
    expected=provenance()
    if target.exists():
        assert json.loads(target.read_text())['provenance']==json.loads(json.dumps(expected))
        return
    print('START',name,seed,flush=True)
    row=run(name,seed)
    assert provenance()==expected, 'Source or map changed during experiment'
    row['provenance']=expected
    target.write_text(json.dumps(row,indent=2))
    print('END',name,seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)

if __name__=='__main__': main()
