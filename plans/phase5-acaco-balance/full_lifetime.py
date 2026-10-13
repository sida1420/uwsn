"""Full production trajectories isolating elite weight, without inner batches."""
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'plans/phase5-acaco-chaos'))
from long_run import ACACOParameters, NetworkInstance, run

FOLDER = Path(__file__).parent/'full'
SEEDS = (15, 16, 17)
BASE = ACACOParameters(num_ants=40, max_clustering_attempts=10,
    energy_cost_exponent=1.,  # historical study; isolate elite weight
    elite_weight=1., load_weight=0., Q=.01, tau_min=.01, tau0=1.,
    tau_max=20., rho_min=.1, rho_max=.6, chaos_min=.05, chaos_max=.30)
CONFIGS = {'elite_1': BASE, 'elite_01': replace(BASE, elite_weight=.1)}


def provenance():
    return dict(seeds=list(SEEDS), T_max=3000, sampler='live', batches_per_round=1,
        configs={name:asdict(params) for name,params in CONFIGS.items()},
        map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src').rglob('*.py'))},
        runner_sha=sha256(Path(__file__).read_bytes()).hexdigest(),
        helper_sha=sha256((ROOT/'plans/phase5-acaco-chaos/long_run.py').read_bytes()).hexdigest(),
        python=platform.python_version())


def main():
    seed = int(sys.argv[1])
    assert seed in SEEDS
    name = sys.argv[2]
    assert name in CONFIGS
    FOLDER.mkdir(exist_ok=True)
    expected = provenance()
    metadata = FOLDER/f'metadata_{name}_seed{seed}.json'
    if metadata.exists():
        assert json.loads(metadata.read_text()) == expected, 'Existing run has different provenance'
    else:
        metadata.write_text(json.dumps(expected, indent=2), encoding='utf-8')
    target = FOLDER/f'{name}_seed{seed}.json'
    if target.exists():
        print('COMPLETE ALREADY', name, seed, flush=True)
        return
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    print('START', name, seed, 'one batch, 40 ants, live pheromone', flush=True)
    result = run(network, CONFIGS[name], seed, name, FOLDER)
    assert provenance() == expected, 'Source changed during run'
    result['provenance'] = expected
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('END', name, seed, 'FND', result['FND'], 'completed', result['completed_rounds'],
        'termination', result['termination_reason'], flush=True)


if __name__ == '__main__':
    main()
