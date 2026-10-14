"""Small controlled enumeration; all full evaluations kept outside pool budgets."""
import argparse
import itertools
import hashlib
import json
from pathlib import Path
import random
import pickle
import sys
from time import perf_counter
import warnings

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from scipy.stats import spearmanr, kendalltau
from algorithms.clustering.clustering import build_clusters
from algorithms.routing.routing import dropping_member_multi_hop_routing
from algorithms.research_acaco.surrogate import MarginalEnergyProxy
from evaluate import Evaluator
from hparameter import HyperParameters
from map_gen import gen
from network import NetworkInstance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario-seeds', nargs='+', type=int, default=[51, 52, 53])
    parser.add_argument('--prefixes', type=int, default=12)
    args = parser.parse_args()
    plan = Path(__file__).resolve().parent
    if not args.output.resolve().is_relative_to(plan) or args.prefixes < 1:
        parser.error('output must stay in research plan; prefixes must be positive')
    evaluator = Evaluator(HyperParameters())
    groups, comparisons, scenarios = [], [], []
    evaluation_count = attempts = 0
    proxy_seconds = full_seconds = 0.0
    for distribution in ('uniform', 'normal', 'clustered'):
        for seed in args.scenario_seeds:
            raw = gen(250, 250, 150, 12, .6, 180, seed=seed, distribution=distribution)
            network = NetworkInstance(raw['sensors'], raw['base_pos'], .6, 250, 250, 150, 180)
            scenarios.append(dict(distribution=distribution, scenario_seed=seed,
                map_pickle_sha256=hashlib.sha256(pickle.dumps(raw, protocol=5)).hexdigest(),
                dimensions=[250,250,150], radius=180, N=12, energy=.6, target_ch=3,
                prefix_sample_seed=1800+seed, sink=[raw['base_pos'].x,raw['base_pos'].y,raw['base_pos'].z]))
            live, residual = list(range(12)), [.6] * 12
            started = perf_counter()
            proxy = MarginalEnergyProxy(network, evaluator, live)
            proxy_seconds += perf_counter() - started
            prefixes = list(itertools.combinations(live, 2))
            prefixes = random.Random(1800 + seed).sample(prefixes, min(args.prefixes, len(prefixes)))
            for selected in prefixes:
                available = [j for j in live if j not in selected]
                started = perf_counter()
                deltas = proxy.additions(selected, available)
                proxy_seconds += perf_counter() - started
                predicted, actual, candidates = [], [], []
                for j, delta in zip(available, deltas):
                    chs = selected + (j,)
                    started = perf_counter()
                    heads, nodes, outliers = build_clusters(chs, live, network.dist_matrix, network.radius)
                    root = dropping_member_multi_hop_routing(heads, nodes, live, outliers,
                        network.dist_matrix, network.base_dists, residual, network.radius, .4)
                    attempts += 1
                    if root is not None:
                        consumption, total = evaluator.energy_consumption(root, network.dist_matrix, network.base_dists)
                        evaluation_count += 1
                        assert set(consumption) == set(live)
                        candidates.append(j)
                        predicted.append(float(delta))
                        actual.append(total)
                        full_seconds += perf_counter() - started
                        proxy_started = perf_counter()
                        approximate = proxy.energy(chs)
                        proxy_seconds += perf_counter() - proxy_started
                        comparisons.append(dict(distribution=distribution, seed=seed, prefix=selected,
                            candidate=j, proxy=approximate, actual=total, relative_error=(approximate-total)/total))
                    else:
                        full_seconds += perf_counter() - started
                rho = tau = None
                agreement = regret = None
                if len(actual) >= 3:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        rho = float(spearmanr(predicted, actual).statistic)
                        tau = float(kendalltau(predicted, actual).statistic)
                    rho = rho if np.isfinite(rho) else None
                    tau = tau if np.isfinite(tau) else None
                    winner = int(np.argmin(predicted))
                    agreement = actual[winner] <= min(actual) + 1e-14
                    regret = actual[winner] / min(actual) - 1
                groups.append(dict(distribution=distribution, scenario_seed=seed, prefix=selected,
                    feasible=len(actual), attempts=len(available), spearman=rho, kendall=tau,
                    top1_agreement=agreement, top1_relative_regret=regret,
                    disconnected_proxy_nodes=int(proxy.unreachable.sum())))
    paths=list((ROOT/'src').rglob('*.py'))+[Path(__file__)]
    provenance=dict(command=sys.argv,python=sys.version,numpy=np.__version__,physics=vars(HyperParameters()),
        scenarios=scenarios,source_hashes={str(p.relative_to(ROOT)).replace('\\','/'):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    result = dict(provenance=provenance, groups=groups, comparisons=comparisons, full_evaluation_count=evaluation_count,
        routing_attempts=attempts, proxy_seconds=proxy_seconds, full_seconds=full_seconds,
        note='Validation enumeration only; not counted as algorithm search, 12 nodes, target3, compact connected domain')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in result if k not in ('groups', 'comparisons','provenance')}))


if __name__ == '__main__':
    main()
