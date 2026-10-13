"""Reproducible bounded AC-ACO calibration; does not alter shared physics.

Run from the repository root. Screening uses fixed physical state but retains
optimizer memory. Validation uses independent energy-depleting trajectories.
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
sys.path.insert(0, str(ROOT / 'src'))
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance

# Explicit historical snapshot: future default changes cannot move the control.
BASE = ACACOParameters(num_ants=40, max_clustering_attempts=10,
    ch_proportion=.2, pheromone_exponent=1, energy_cost_exponent=1,
    distance_weight=1, beta_min=1, beta_max=5, beta_slope=5,
    beta_schedule='raw', rho_min=.1, rho_max=.9, chaos_min=.05,
    chaos_max=.3, chaos_r=3.61, chaos_seed=.37, Q=100,
    tau0=1, tau_min=.1, tau_max=10, hopping_factor=.4)


def candidates():
    configs = {'historical': BASE}
    # Coupled scales, not a Cartesian sweep of all parameter dimensions.
    for maximum in (2., 5.):
        for q in (.003, .01, .03):
            for rho in (.4, .6):
                name = f'q{q}_max{maximum}_rho{rho}'
                configs[name] = replace(BASE, Q=q, tau_min=.01,
                    tau_max=maximum, tau0=1, rho_max=rho)
    # Wider limits account for the lowest evaporation and maximum chaos,
    # including both ant and elite reinforcement (reference cost .015 J).
    for q, maximum in ((.003, 8.), (.01, 20.)):
        for rho in (.4, .6):
            configs[f'q{q}_max{maximum}_rho{rho}'] = replace(BASE,
                Q=q, tau_min=.01, tau_max=maximum, tau0=1, rho_max=rho)
    configs['low_floor'] = replace(configs['q0.01_max2.0_rho0.4'], tau_min=.001)
    configs['high_floor'] = replace(configs['q0.01_max2.0_rho0.4'], tau_min=.05)
    configs['high_initial'] = replace(configs['q0.01_max2.0_rho0.4'], tau0=2)
    configs['moderate_heuristic'] = replace(configs['q0.01_max2.0_rho0.4'],
        energy_cost_exponent=.25, beta_max=3)
    configs['moderate_heuristic_wide'] = replace(configs['q0.01_max20.0_rho0.4'],
        energy_cost_exponent=.25)
    return configs


def measure(network, config, seed, rounds, trajectory):
    hp = HyperParameters()  # Keep the schedule horizon at 3000.
    algo = ACACO(network, hp, config, seed=seed)
    evaluator = Evaluator(hp)
    residual = [network.init_energy] * network.N
    live = list(range(network.N))
    records = []
    for t in range(rounds):
        before = residual.copy()
        calls = []
        original = algo.evaluator.energy_consumption
        def counted(*args):
            result = original(*args)
            calls.append(result[1])
            return result
        algo.evaluator.energy_consumption = counted
        start = process_time()
        with redirect_stdout(StringIO()):
            root, consumption = algo.plan_round(live, residual)
        cpu = process_time() - start
        algo.evaluator.energy_consumption = original
        assert before == residual, 'Search mutated physical energy'
        if root is None:
            records.append(dict(round=t, failure=True, cpu_s=cpu))
            break
        verified, energy = evaluator.energy_consumption(root,
            network.dist_matrix, network.base_dists)
        assert verified == consumption and set(consumption) == set(live)
        c = algo.clustering
        tau = np.asarray(c.pheromone)[np.ix_(live, live)]
        tau = tau[~np.eye(len(live), dtype=bool)]
        assert np.isfinite(tau).all()
        assert (tau >= config.tau_min).all() and (tau <= config.tau_max).all()
        state = c.pre_round(live, residual)
        c.iteration -= 1  # Probability diagnostic only; no RNG/chaos mutation.
        probs = c._transition_probabilities(live[0], live[1:], residual,
            state.beta, state.strength)
        assert np.isfinite(probs).all() and min(probs) >= 0
        assert abs(sum(probs) - 1) < 1e-12
        max_depletion = max(consumption[i] / residual[i] for i in live)
        if trajectory:
            residual = [max(0., e - consumption.get(i, 0))
                        for i, e in enumerate(residual)]
            live = [i for i in live if residual[i] > 0]
        records.append(dict(round=t, failure=False, energy_J=energy,
            cpu_s=cpu, feasible_evaluations=len(calls),
            attempts=algo.total_clustering_attempts,
            tau_floor_fraction=float(np.mean(tau <= config.tau_min + 1e-12)),
            tau_ceiling_fraction=float(np.mean(tau >= config.tau_max - 1e-12)),
            tau_p10=float(np.quantile(tau, .1)), tau_p90=float(np.quantile(tau, .9)),
            max_depletion=max_depletion, alive=len(live)))
    valid = [r for r in records if not r['failure']]
    return dict(seed=seed, rounds=len(valid), failed=len(valid) != rounds,
        energy_J=sum(r['energy_J'] for r in valid),
        cpu_s=sum(r['cpu_s'] for r in records),
        feasible_evaluations=sum(r['feasible_evaluations'] for r in valid),
        mean_ceiling=float(np.mean([r['tau_ceiling_fraction'] for r in valid])),
        mean_floor=float(np.mean([r['tau_floor_fraction'] for r in valid])),
        peak_depletion=max(r['max_depletion'] for r in valid), records=records)


def main():
    out = Path(__file__).parent
    network = NetworkInstance.from_pickle(ROOT / 'map.pkl')
    configs = candidates()
    result = dict(git_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'],
        cwd=ROOT, text=True).strip(), map_sha=sha256((ROOT / 'map.pkl').read_bytes()).hexdigest(),
        schedule_horizon=3000, screening_seeds=[0,1,2], validation_seeds=[3,4,5],
        configs={k:asdict(v) for k,v in configs.items()}, screening={}, validation={})
    saved = out / 'results.json'
    if saved.exists():
        previous = json.loads(saved.read_text())
        assert previous['git_sha'] == result['git_sha'] and previous['map_sha'] == result['map_sha']
        if 'source_hashes' in previous:
            for relative, digest in previous['source_hashes'].items():
                if sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                    raise RuntimeError('Source changed; move results.json before a fresh calibration')
        for name in previous['screening']:
            assert previous['configs'][name] == result['configs'][name]
        result['screening'] = previous['screening']
        result['validation'] = previous['validation']
    result['source_hashes'] = {str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'src').rglob('*.py'))}
    for name, config in configs.items():
        if name in result['screening']:
            continue
        result['screening'][name] = [measure(network, config, s, 20, False) for s in (0,1,2)]
        rows = result['screening'][name]
        print(name, 'energy', np.mean([r['energy_J'] for r in rows]),
            'ceiling', np.mean([r['mean_ceiling'] for r in rows]), flush=True)
        (out / 'results.json').write_text(json.dumps(result, indent=2))
    eligible = [name for name, rows in result['screening'].items()
        if name != 'historical' and not any(r['failed'] for r in rows)
        and np.mean([r['mean_ceiling'] for r in rows]) < .01
        and np.mean([r['mean_floor'] for r in rows]) < .1
        and ((2-configs[name].rho_min)*configs[name].Q/.015
             + configs[name].chaos_max*configs[name].chaos_r/4)
            / configs[name].rho_min < configs[name].tau_max]
    ranked = sorted(eligible, key=lambda name: sum(r['energy_J'] for r in result['screening'][name]))
    result['finalists'] = ranked[:2]
    for name in ['historical'] + result['finalists']:
        if name in result['validation']:
            continue
        rows = []
        for seed in (3,4,5):
            print('VALIDATING', name, 'seed', seed, flush=True)
            rows.append(measure(network, configs[name], seed, 150, True))
        result['validation'][name] = rows
        print('VALIDATION', name, [(r['energy_J'], r['rounds']) for r in result['validation'][name]], flush=True)
        (out / 'results.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
