"""Full D-ACO tests of unified powered fitness and live pheromone."""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
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
from algorithms.d_aco import DACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from hparameter import HyperParameters
from network import NetworkInstance

FOLDER = Path(__file__).parent
SEEDS = (15,16,17)
BASE = DACOParameters(load_density_weight=.1)  # freeze the declared experiment controls
CONFIGS = {'energy_live':replace(BASE,load_density_weight=0.),
           'linear_load':replace(BASE,load_power=1.),
           'power_010':BASE,
           'power_025':replace(BASE,load_density_weight=.25)}


def provenance():
    return dict(seeds=list(SEEDS),T_max=3000,configs={k:asdict(v) for k,v in CONFIGS.items()},
        map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src').rglob('*.py'))},
        runner_sha=sha256(Path(__file__).read_bytes()).hexdigest(),python=platform.python_version())


def run(network,params,seed,name):
    random.seed(seed)
    algorithm = DACO(network,HyperParameters(),params)
    live = list(range(network.N))
    residual = [network.init_energy]*network.N
    records = []
    fnd = hnd = lnd = None
    reason = 'horizon'
    begin = process_time()  # includes the initial throwaway calibration
    for t in range(3000):
        old_refs = algorithm.references
        with redirect_stdout(StringIO()):
            root,costs = algorithm.plan_round(live,residual)
        if root is None:
            reason = 'no_feasible_tree' if algorithm.references else 'no_feasible_calibration'
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
        refs = algorithm.references
        records.append(dict(round=t+1,energy=sum(costs.values()),cv=float(loads.std()/loads.mean()),
            peak_depletion=risk,alive=len(live),dead=dead,
            energy_reference=refs.energy,penalty_reference=refs.penalty))
        if (t+1)%100==0:
            progress = dict(configuration=name,seed=seed,completed=t+1,FND=fnd,alive=len(live),
                cpu=process_time()-begin,calibration_attempts=algorithm.calibration_attempts)
            (FOLDER/'full'/f'progress_{name}_{seed}.json').write_text(json.dumps(progress))
            print('PROGRESS',name,seed,t+1,'alive',len(live),'FND',fnd,flush=True)
        if not live:
            break
    return dict(configuration=name,seed=seed,parameters=asdict(params),records=records,
        completed_rounds=len(records),FND=fnd,HND=hnd,LND=lnd,termination_reason=reason,
        alive=live,residual=residual,cpu=process_time()-begin,
        clustering_attempts=algorithm.total_clustering_attempts,
        routing_attempts=algorithm.total_routing_attempts,
        calibration_attempts=algorithm.calibration_attempts,
        calibration_routing_attempts=algorithm.calibration_routing_attempts,
        calibration_feasible=algorithm.calibration_feasible)


def main():
    seed = int(sys.argv[1])
    assert seed in SEEDS
    folder = FOLDER/'full'
    folder.mkdir(parents=True,exist_ok=True)
    expected = provenance()
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    for name,params in CONFIGS.items():
        metadata = folder/f'metadata_{name}_{seed}.json'
        if metadata.exists():
            assert json.loads(metadata.read_text())==expected, 'Different provenance'
        else:
            metadata.write_text(json.dumps(expected,indent=2))
        target = folder/f'{name}_{seed}.json'
        if target.exists():
            continue
        print('START',name,seed,flush=True)
        row = run(network,params,seed,name)
        assert provenance()==expected, 'Source changed during run'
        row['provenance'] = expected
        target.write_text(json.dumps(row,indent=2))
        print('END',name,seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)


if __name__=='__main__':
    main()
