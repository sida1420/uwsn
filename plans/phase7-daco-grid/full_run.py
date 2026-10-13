"""Full D-ACO trajectories: only grid distance attenuation changes."""
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

FOLDER = Path(__file__).parent/'full'
DECAYS = ('none','linear','quadratic')
SEEDS = (15,16,17)


def provenance():
    return dict(seeds=list(SEEDS),decays=list(DECAYS),T_max=3000,
        map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src').rglob('*.py'))},
        runner_sha=sha256(Path(__file__).read_bytes()).hexdigest(),python=platform.python_version())


def run(network, decay, seed):
    random.seed(seed)
    params = DACOParameters()
    params.density_decay = decay
    algorithm = DACO(network,HyperParameters(),params)
    live = list(range(network.N))
    residual = [network.init_energy]*network.N
    records = []
    fnd = hnd = lnd = None
    reason = 'horizon'
    begin = process_time()
    for t in range(3000):
        with redirect_stdout(StringIO()):
            root, costs = algorithm.plan_round(live,residual)
        if root is None:
            reason = 'no_feasible_tree'
            break
        assert set(costs)==set(live), 'Every surviving sensor must be served'
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
            lnd = t+1
            reason = 'all_nodes_dead'
        records.append(dict(round=t+1,energy=sum(costs.values()),
            cv=float(loads.std()/loads.mean()),peak_depletion=risk,alive=len(live),dead=dead))
        if (t+1)%100==0 or not live:
            progress = dict(decay=decay,seed=seed,completed=t+1,FND=fnd,alive=len(live),cpu=process_time()-begin)
            (FOLDER/f'progress_{decay}_{seed}.json').write_text(json.dumps(progress))
            print('PROGRESS',decay,seed,t+1,'alive',len(live),'FND',fnd,flush=True)
        if not live:
            break
    return dict(decay=decay,seed=seed,parameters=vars(params),records=records,
        completed_rounds=len(records),FND=fnd,HND=hnd,LND=lnd,termination_reason=reason,
        alive=live,residual=residual,cpu=process_time()-begin,
        clustering_attempts=algorithm.total_clustering_attempts,
        routing_attempts=algorithm.total_routing_attempts)


def main():
    seed = int(sys.argv[1])
    assert seed in SEEDS
    FOLDER.mkdir(parents=True,exist_ok=True)
    expected = provenance()
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    for decay in DECAYS:
        metadata = FOLDER/f'metadata_{decay}_{seed}.json'
        if metadata.exists():
            assert json.loads(metadata.read_text())==expected, 'Different provenance'
        else:
            metadata.write_text(json.dumps(expected,indent=2))
        target = FOLDER/f'{decay}_{seed}.json'
        if target.exists():
            continue
        print('START',decay,seed,flush=True)
        row = run(network,decay,seed)
        assert provenance()==expected, 'Source changed during run'
        row['provenance'] = expected
        target.write_text(json.dumps(row,indent=2))
        print('END',decay,seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)


if __name__=='__main__':
    main()
