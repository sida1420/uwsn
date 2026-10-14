"""Small parameter-search check, not a lifetime optimizer or validated winner."""
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from concurrent.futures.process import BrokenProcessPool
from multiprocessing import get_context
from pathlib import Path
import csv
import json
import shutil
from statistics import mean
import time

import optuna
from optimizer import ROOT, PACKAGE
from optimizer.adapters import get
from optimizer.engine import DEFAULT
from optimizer.provenance import epoch, EpochGuard
from optimizer.storage import atomic
from optimizer.trajectory import run_seed
from optimizer.diagnostics import reachable
from network import NetworkInstance


def smoke_search(folder, trials=3, rounds=3, seeds=(24, 25), sampler_seed=20261014):
    """One baseline, then sampler proposals; fixed 40 ants and original T_max3500."""
    if type(trials) is not int or not 2 <= trials <= 3:
        raise ValueError('Smoke permits 2..3 trials')
    if type(rounds) is not int or not 1 <= rounds <= 10:
        raise ValueError('Smoke permits 1..10 physical rounds')
    if not 1 <= len(seeds) <= 3 or len(set(seeds)) != len(seeds):
        raise ValueError('Use 1..3 unique development seeds')
    if any(type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError('Seeds must be nonnegative integers')
    if not hasattr(ProcessPoolExecutor, 'terminate_workers'):
        raise RuntimeError('Bounded smoke requires Python3.14+ worker termination support')
    folder = Path(folder).resolve()
    if not folder.is_relative_to(PACKAGE) or folder.exists():
        raise ValueError('Choose a new output directory under optimizer/')
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    if not 1 <= network.N <= 200:
        raise ValueError('Cheap smoke is limited to 1..200 sensors')
    if reachable(network, list(range(network.N)))[1]:
        raise ValueError('Initial physical radius graph is disconnected')
    folder.mkdir(parents=True)
    shutil.copyfile(ROOT/'map.pkl', folder/'map.pkl')
    cfg = {**DEFAULT, 'algorithm':'acaco_v2_v6', 'mode':'smoke', 'horizon':rounds,
        'adaptive_total_rounds':3500, 'energy_window':rounds, 'energy_window_policy':'fixed',
        'training_seeds':list(seeds), 'max_trials':trials, 'max_workers':1,
        'map':str(folder/'map.pkl'), 'sampler_seed':sampler_seed}
    expected = epoch(cfg)
    atomic(folder/'config.json', cfg)
    atomic(folder/'provenance.json', expected)
    adapter = get('acaco_v2_v6')
    baseline = adapter.baseline_config()
    atomic(folder/'search-space.json', adapter.space)
    storage = optuna.storages.RDBStorage('sqlite:///'+(folder/'study.db').as_posix())
    study = optuna.create_study(study_name='acaco-v2-v6-smoke', direction='minimize',
        storage=storage, sampler=optuna.samplers.TPESampler(seed=sampler_seed, n_startup_trials=2))
    study.enqueue_trial({name:baseline[name] for name in adapter.space},
                         user_attrs={'origin':'reported_baseline'})
    guard = EpochGuard(cfg, expected)
    rows = []
    abort_reason = None
    started = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=1, mp_context=get_context('spawn')) as pool:
            for _ in range(trials):
                guard.check(force=True)
                trial = study.ask()
                params = adapter.suggest(trial)
                try:
                    runs = [pool.submit(run_seed, cfg, params, seed,
                        folder/'trials'/str(trial.number)/str(seed), expected,
                        kind='acaco_v2_v6').result(timeout=120) for seed in seeds]
                    complete = all(r['completed_rounds']==rounds and r['energy_status']=='comparable' for r in runs)
                    value = mean(r['energy_K'] for r in runs) if complete else None
                    row = dict(trial=trial.number, origin=trial.user_attrs.get('origin','sampler_proposal'),
                        parameters=params, mean_short_energy_J=value, comparable=complete,
                        evaluation_count=sum(r['feasible_evaluations'] for r in runs),
                        rounds_per_seed=[r['completed_rounds'] for r in runs])
                    for name in ('mean_short_energy_J','comparable','evaluation_count'):
                        trial.set_user_attr(name, row[name])
                    if complete:
                        study.tell(trial, value)
                    else:
                        study.tell(trial, state=optuna.trial.TrialState.FAIL)
                except Exception as exc:
                    if isinstance(exc, (TimeoutError, BrokenProcessPool)):
                        pool.terminate_workers()
                        abort_reason = 'worker_timeout_or_failure'
                    study.tell(trial, state=optuna.trial.TrialState.FAIL)
                    row = dict(trial=trial.number,parameters=params,error=repr(exc),comparable=False,
                               origin=trial.user_attrs.get('origin','sampler_proposal'),mean_short_energy_J=None)
                rows.append(row)
                atomic(folder/'trial-results.json', rows)
                print(f"trial={trial.number} origin={row['origin']} short_energy_J={row['mean_short_energy_J']}",flush=True)
                if row['origin']=='reported_baseline' and not row['comparable']:
                    abort_reason = abort_reason or 'reported_baseline_not_comparable'
                if abort_reason:
                    break
        guard.check(force=True)
    finally:
        storage.remove_session()
        storage.engine.dispose()
    valid = [r for r in rows if r['comparable']]
    reference = next((r['mean_short_energy_J'] for r in valid if r['origin']=='reported_baseline'), None)
    for row in rows:
        row['relative_to_baseline_pct'] = (100*(1-row['mean_short_energy_J']/reference)
            if reference and row['comparable'] else None)
    complete = not abort_reason and len(valid)==trials
    summary = dict(mode='smoke',objective='mean selected physical energy over short fixed all-alive horizon',
        validation_status='pipeline check only; not a scientifically validated optimum',
        pipeline_status='complete' if complete else 'failed', abort_reason=abort_reason,
        full_lifetime_tested=False, production_defaults_changed=False, legacy_required=False,
        trials=rows, elapsed_seconds=time.perf_counter()-started,
        provisional_best=min(valid,key=lambda r:r['mean_short_energy_J']) if complete else None)
    atomic(folder/'summary.json', summary)
    atomic(folder/'trial-results.json', rows)
    with (folder/'trial-results.csv').open('w',newline='',encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['trial','origin','comparable','mean_short_energy_J','relative_to_baseline_pct','parameters'])
        for r in rows:
            writer.writerow([r['trial'],r['origin'],r['comparable'],r['mean_short_energy_J'],
                             r['relative_to_baseline_pct'],json.dumps(r['parameters'],sort_keys=True)])
    return summary
