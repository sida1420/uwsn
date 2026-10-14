"""Smoke parameter search contracts without historical D-ACO studies."""
from dataclasses import asdict
import json
from pathlib import Path
from unittest.mock import patch
import tempfile
from concurrent.futures import TimeoutError

import pytest
import yaml
from optimizer import ROOT, PACKAGE
from optimizer.adapters import get
from optimizer.engine import DEFAULT, initialize
from optimizer.provenance import epoch
from optimizer.storage import unpickle
from optimizer.trajectory import run_seed
from optimizer.v2_v6_smoke import smoke_search
from algorithms.ac_aco_v2_v6 import ACACO_V2_V6
from hparameter import HyperParameters
from network import NetworkInstance


def config():
    return {**DEFAULT,'algorithm':'acaco_v2_v6','mode':'smoke','horizon':2,
        'adaptive_total_rounds':3500,'energy_window':2,'training_seeds':[24],
        'map':str(ROOT/'map.pkl')}


def test_reported_preset_is_exact_and_default_unchanged():
    n=NetworkInstance.from_pickle(ROOT/'map.pkl')
    native=ACACO_V2_V6(n,HyperParameters(),seed=24)
    adapter=get('acaco_v2_v6')
    assert adapter.baseline_config()==asdict(native.params)
    observed=adapter.make_algorithm(n,HyperParameters(),{},24)
    assert asdict(observed.options)==asdict(native.options)
    assert observed.params.load_weight==0 and observed.params.num_ants==40
    assert observed.clustering.options.chaos_policy=='evaporation'
    residual=[n.init_energy]*n.N
    live=list(range(n.N))
    for _ in range(2):
        root,costs=observed.plan_round(live,residual)
        other,expected=native.plan_round(live,residual)
        assert root is not None and other is not None and costs==expected
        assert observed.clustering.rng.getstate()==native.clustering.rng.getstate()
        assert observed.clustering.last_exploration==0
        for node,energy in costs.items(): residual[node]=max(0.,residual[node]-energy)


@pytest.mark.parametrize('change',[{'num_ants':41},{'load_weight':.25},{'tau_min':1},
    {'beta_schedule':'normalized'},{'hopping_factor':.9},{'unknown':1},
    {'Q':.1},{'rho_max':.8},{'beta_min':3}])
def test_search_rejects_budget_objective_operator_and_out_of_range_changes(change):
    with pytest.raises(ValueError): get('acaco_v2_v6').effective_config(change)


def test_native_trajectory_and_rng_checkpoint_resume(tmp_path):
    cfg=config();params=get('acaco_v2_v6').baseline_config()
    full=run_seed(cfg,params,24,tmp_path/'full',epoch(cfg),kind='acaco_v2_v6')
    paused=run_seed(cfg,params,24,tmp_path/'resume',epoch(cfg),kind='acaco_v2_v6',pause_after=1)
    assert paused['paused']
    resumed=run_seed(cfg,params,24,tmp_path/'resume',epoch(cfg),kind='acaco_v2_v6')
    assert full['energy_K']==resumed['energy_K'] and full['residual']==resumed['residual']
    assert full['completed_rounds']==2 and full['feasible_evaluations']==80
    assert full['energy_status']=='comparable' and full['horizon_censored']
    records=unpickle(tmp_path/'full/checkpoint.pkl')['records']
    assert all(r['diagnostics']['selection_chaos']==0 for r in records)
    assert sum(r['evaluations'] for r in records)==80


@pytest.mark.parametrize('kwargs',[{'trials':1},{'trials':4},{'rounds':0},{'rounds':11},
    {'seeds':[]},{'seeds':[24,24]},{'seeds':[True]},{'seeds':[1,2,3,4]}])
def test_smoke_rejects_invalid_scope_before_writing(tmp_path,kwargs):
    target=tmp_path/'blocked'
    with pytest.raises(ValueError): smoke_search(target,**kwargs)
    assert not target.exists()


def test_output_must_be_new_and_under_optimizer(tmp_path):
    with pytest.raises(ValueError): smoke_search(tmp_path/'outside')
    with pytest.raises(ValueError): smoke_search(PACKAGE)


def test_full_controller_still_refuses_v2_v6_tuning(tmp_path):
    path=tmp_path/'config.yaml'
    path.write_text(yaml.safe_dump({'algorithm':'acaco_v2_v6'}),encoding='utf-8')
    with pytest.raises(ValueError,match='Only D-ACO'):
        initialize(path,tmp_path/'study',None)


def test_actual_smoke_export_has_baseline_and_distinct_trials():
    # This is an explicit validation replay of the separately executed CLI artifact.
    folder=PACKAGE/'runs/acaco-v2-v6-check-261014-verified'
    if not (folder/'summary.json').exists():
        pytest.skip('CLI smoke artifact not generated; physical adapter tests cover execution')
    result=json.loads((folder/'summary.json').read_text())
    assert result['mode']=='smoke' and not result['full_lifetime_tested']
    assert not result['production_defaults_changed'] and result['legacy_required'] is False
    assert len(result['trials'])==3 and result['trials'][0]['origin']=='reported_baseline'
    assert all(r['comparable'] and r['evaluation_count']==240 for r in result['trials'])
    assert len({json.dumps(r['parameters'],sort_keys=True) for r in result['trials']})==3
    assert (folder/'study.db').exists() and (folder/'trial-results.csv').exists()


@pytest.mark.parametrize('timeout',[False,True])
def test_failed_baseline_stops_proposals_and_timeout_terminates_worker(timeout):
    base=PACKAGE/'test-output'
    base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as temporary:
        folder=Path(temporary)/'study'
        with patch('optimizer.v2_v6_smoke.ProcessPoolExecutor') as executor:
            pool=executor.return_value.__enter__.return_value
            future=pool.submit.return_value
            if timeout:
                future.result.side_effect=TimeoutError('forced timeout')
            else:
                future.result.return_value=dict(completed_rounds=0,energy_status='not_comparable',
                    energy_K=None,feasible_evaluations=0)
            summary=smoke_search(folder,trials=3,rounds=1,seeds=[24])
            assert pool.submit.call_count==1
            assert summary['pipeline_status']=='failed' and summary['provisional_best'] is None
            assert len(summary['trials'])==1
            if timeout: pool.terminate_workers.assert_called_once()
            else: pool.terminate_workers.assert_not_called()
