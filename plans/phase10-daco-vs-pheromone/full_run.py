"""Fresh full paired comparison on the current map; no production overrides."""
from contextlib import redirect_stdout
from dataclasses import asdict
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import random
import sys
from time import process_time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from algorithms.d_aco import DACO
from algorithms.aco import SimpleACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering.aco.parameters import ACOParameters
from hparameter import HyperParameters
from network import NetworkInstance

FOLDER = Path(__file__).parent / 'full'
SEEDS = (24, 25, 26)

def parameters(name):
    if name == 'daco':
        return DACOParameters()
    params = ACOParameters()
    params.beta = params.gamma = 0.
    return params

def provenance():
    return dict(seeds=SEEDS, horizon=3000,
        map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        sources={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
                 for p in sorted((ROOT/'src').rglob('*.py'))},
        runner_sha=sha256(Path(__file__).read_bytes()).hexdigest())

def run(name, seed, network):
    random.seed(seed)
    params = parameters(name)
    begin = process_time()
    algorithm = (DACO if name == 'daco' else SimpleACO)(network, HyperParameters(), params)
    residual = [network.init_energy]*network.N
    live = list(range(network.N))
    records = []
    fnd = hnd = lnd = None
    reason = 'horizon'
    for t in range(3000):
        with redirect_stdout(StringIO()):
            root, costs = algorithm.plan_round(live, residual)
        if root is None:
            reason = 'no_feasible_tree'
            break
        assert set(costs) == set(live)
        assert all(np.isfinite(v) and v >= 0 for v in costs.values())
        assert sum(costs.values()) > 0
        for i, cost in costs.items():
            residual[i] = max(0., residual[i]-cost)
        dead = [i for i in live if residual[i] <= 0]
        live = [i for i in live if residual[i] > 0]
        if dead and fnd is None:
            fnd = t+1
        if len(live) <= network.N/2 and hnd is None:
            hnd = t+1
        if not live:
            lnd, reason = t+1, 'all_nodes_dead'
        records.append(dict(round=t+1, energy=sum(costs.values()), alive=len(live), dead=dead))
        if (t+1) % 100 == 0:
            print('PROGRESS', name, seed, t+1, 'alive', len(live), 'FND', fnd, flush=True)
        if not live:
            break
    return dict(configuration=name, seed=seed,
        parameters=asdict(params) if name == 'daco' else vars(params),
        completed_rounds=len(records), FND=fnd, HND=hnd, LND=lnd,
        termination_reason=reason, cpu=process_time()-begin,
        clustering_attempts=algorithm.total_clustering_attempts,
        routing_attempts=algorithm.total_routing_attempts,
        calibration_attempts=getattr(algorithm, 'calibration_attempts', 0),
        calibration_routing_attempts=getattr(algorithm, 'calibration_routing_attempts', 0),
        alive=live, residual=residual, records=records)

def main():
    seed = int(sys.argv[1])
    assert seed in SEEDS
    FOLDER.mkdir(parents=True, exist_ok=True)
    expected = provenance()
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    order = ['daco', 'pheromone'] if seed % 2 == 0 else ['pheromone', 'daco']
    for name in order:
        target = FOLDER/f'{name}_{seed}.json'
        if target.exists():
            assert json.loads(target.read_text())['provenance'] == json.loads(json.dumps(expected))
            continue
        print('START', name, seed, flush=True)
        result = run(name, seed, network)
        assert provenance() == expected, 'Source or map changed during experiment'
        result['provenance'] = expected
        target.write_text(json.dumps(result, indent=2))
        print('END', name, seed, result['completed_rounds'], result['FND'], result['termination_reason'], flush=True)

if __name__ == '__main__':
    main()
