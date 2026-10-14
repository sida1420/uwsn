"""Reproducible isolated candidate pools; production defaults/maps are untouched."""
import argparse
import contextlib
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import pickle
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from algorithms.ac_aco import ACACO
from algorithms.d_aco import DACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.research_acaco import ResearchACACO, ResearchOptions
from algorithms.research_acaco.diagnostics import PoolObserver
from hparameter import HyperParameters
from map_gen import gen
from network import NetworkInstance

AUDIT_HASH = 'f5e6ebb66f9f361f5d91cceda44dff85e7eca4d1dc86877a74ab81a6216f1af8'
SINGLES = ['B0', 'V1-0', 'V1-.25', 'V1-.5', 'V1-1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'R0', 'D0', 'D40total']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    paths = (list((ROOT / 'src').rglob('*.py')) + list(Path(__file__).parent.rglob('*.py'))
             + list((ROOT / 'tests').glob('*.py')))
    return {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths}


def make_algorithm(name, network, seed, budget):
    # Explicit audited-original energy-only parameters. Current defaults preserved.
    params = replace(ACACOParameters(), num_ants=budget, load_weight=0, tau_min=.01)
    hp = HyperParameters()  # horizon stays 3500 even for a short trajectory
    if name in ('D0', 'D40total'):
        dp = DACOParameters()
        if name == 'D40total':
            if budget < 2 or budget % 2:
                raise ValueError('equal-total D budget must be even >=2')
            dp = replace(dp, num_ants=budget // 2, calibration_ants=budget // 2)
        else:
            dp = replace(dp, num_ants=budget, calibration_ants=budget)
        return DACO(network, hp, aco_params=dp, seed=seed)
    if name.startswith('V1-'):
        params = replace(params, distance_weight=float(name[3:]))
        return ACACO(network, hp, params=params, seed=seed)
    options = {
        'B0': ResearchOptions(), 'V2': ResearchOptions(heuristic='marginal'),
        'V3': ResearchOptions(chaos_policy='reduced'),
        'V4': ResearchOptions(chaos_policy='normalized'),
        'V5': ResearchOptions(chaos_policy='adaptive'),
        'V6': ResearchOptions(chaos_policy='evaporation'),
        'V6-k0': ResearchOptions(chaos_policy='evaporation', evaporation_kappa=0),
        'V7': ResearchOptions(distinct_starts=True),
        'R0': ResearchOptions(random_sets=True),
        'V2+V5': ResearchOptions(heuristic='marginal', chaos_policy='adaptive'),
        'V2+V6': ResearchOptions(heuristic='marginal', chaos_policy='evaporation'),
        'V2+V6-k0': ResearchOptions(heuristic='marginal', chaos_policy='evaporation', evaporation_kappa=0),
    }
    if name not in options:
        raise ValueError(f'unknown variant {name}')
    if name == 'B0':
        return ACACO(network, hp, params=params, seed=seed)
    return ResearchACACO(network, hp, params=params, seed=seed, options=options[name])


def scenarios(args, output):
    entries = []
    if not args.skip_audited:
        path = ROOT / 'map.pkl'
        if not path.exists() or sha(path) != args.expected_map_sha:
            raise ValueError('Audited map missing/hash differs; no regeneration permitted')
        raw = pickle.loads(path.read_bytes())  # trusted repository map only
        entries.append(('audited-uniform-100-41', path, raw))
    for distribution in args.distributions:
        for count in args.nodes:
            for seed in args.scenario_seeds:
                label = f'{distribution}-{count}-{seed}'
                raw = gen(500, 500, 500, count, .6, 200, distribution=distribution, seed=seed)
                path = output / 'maps' / f'{label}.pkl'
                path.parent.mkdir(exist_ok=True)
                with path.open('xb') as handle:
                    pickle.dump(raw, handle)
                entries.append((label, path, raw))
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variants', nargs='+', default=SINGLES)
    parser.add_argument('--seeds', nargs='+', type=int, default=list(range(24, 34)))
    parser.add_argument('--budget', type=int, default=40)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--distributions', nargs='*', default=[])
    parser.add_argument('--nodes', nargs='+', type=int, default=[50, 100, 200])
    parser.add_argument('--scenario-seeds', nargs='+', type=int, default=[51, 52])
    parser.add_argument('--skip-audited', action='store_true')
    parser.add_argument('--expected-map-sha', default=AUDIT_HASH)
    args = parser.parse_args()
    if args.budget < 1 or not 1 <= args.rounds <= 50 or min(args.nodes) < 1:
        parser.error('positive budgets/nodes; short trajectories restricted to 1..50 rounds')
    output = args.output.resolve()
    allowed = (ROOT / 'plans' / '261014-1051-acaco-candidates').resolve()
    if not output.is_relative_to(allowed):
        parser.error('artifacts must stay inside research plan directory')
    output.mkdir(parents=True, exist_ok=False)
    source = hashes()
    metadata = dict(command=sys.argv, source_hashes=source, python=sys.version,
        platform=platform.platform(), numpy=np.__version__, current_params=asdict(ACACOParameters()),
        scientific_baseline=asdict(replace(ACACOParameters(), load_weight=0, tau_min=.01,
                                         num_ants=args.budget)), physics=vars(HyperParameters()),
        expected_map_sha=args.expected_map_sha, expected_distribution='uniform (audit differs from requested clustered)',
        unit='independent topology; algorithm seeds paired; ants/rounds correlated', scenarios=[])
    entries = scenarios(args, output)
    started = perf_counter()
    runs = 0
    with (output / 'pools.jsonl').open('w', encoding='utf-8') as handle:
        for label, path, raw in entries:
            network = NetworkInstance.from_pickle(path)
            scenario = dict(label=label, sha256=sha(path), seed=raw.get('seed'), N=network.N,
                distribution=network.distribution, radius=network.radius, initial_energy=network.init_energy,
                dimensions=[network.width, network.height, network.depth],
                sink=[network.base_pos.x, network.base_pos.y, network.base_pos.z])
            metadata['scenarios'].append(scenario)
            for seed in args.seeds:
                # Rotate execution order, not any algorithm RNG stream.
                offset = seed % len(args.variants)
                order = args.variants[offset:] + args.variants[:offset]
                for variant in order:
                    setup = perf_counter()
                    algorithm = make_algorithm(variant, network, seed, args.budget)
                    setup_seconds = perf_counter() - setup
                    observer = PoolObserver(algorithm)
                    residual = [network.init_energy] * network.N
                    live = list(range(network.N))
                    for physical_round in range(args.rounds):
                        before = residual.copy()
                        with contextlib.redirect_stdout(io.StringIO()):
                            root, consumption, summary = observer.run(live, residual)
                        assert residual == before, 'search mutated physical energy'
                        proxy = getattr(algorithm.clustering, 'proxy', None)
                        row = dict(scenario=label, scenario_seed=raw.get('seed'), map_sha=scenario['sha256'],
                            variant=variant, algorithm_seed=seed, physical_round=physical_round,
                            requested_feasible=algorithm.params.num_ants,
                            requested_budget=args.budget, setup_seconds=setup_seconds,
                            params=asdict(algorithm.params), options=asdict(algorithm.options)
                                if hasattr(algorithm, 'options') else {},
                            proxy_seconds=getattr(algorithm.clustering, 'proxy_seconds', 0),
                            proxy_cell_operations=proxy.operations if proxy else 0,
                            unreachable_proxy_nodes=int(proxy.unreachable.sum()) if proxy else 0,
                            effective_rhos=getattr(algorithm.clustering, 'effective_rhos', []), **summary)
                        handle.write(json.dumps(row, allow_nan=False) + '\n')
                        handle.flush()
                        if root is None:
                            break
                        assert set(consumption) == set(live), 'incomplete routing tree'
                        for node, energy in consumption.items():
                            residual[node] = max(0.0, residual[node] - energy)
                        live = [i for i in live if residual[i] > 0]
                        if not live:
                            break
                    observer.close()
                    runs += 1
            print(f'{label}: completed {runs} runs, {perf_counter()-started:.1f}s', flush=True)
    metadata['elapsed_seconds'] = perf_counter() - started
    metadata['source_unchanged'] = source == hashes()
    assert metadata['source_unchanged']
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
