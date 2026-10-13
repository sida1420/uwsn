"""Reuse only matching historical cohorts; otherwise request fresh references."""
from dataclasses import asdict
from statistics import mean
from optimizer import ROOT
from optimizer.storage import read,atomic
from algorithms.clustering.aco.parameters import ACOParameters

DECLARED_CAP=43.315422

def historical(cfg,epoch):
    if cfg['mode']!='scientific' or not cfg['reuse_history']: return None
    p=ACOParameters();p.beta=p.gamma=0.
    values={};paths={}
    for seed in cfg['training_seeds']:
        path=ROOT/'plans/phase10-daco-vs-pheromone/full'/f'pheromone_{seed}.json'
        if not path.exists(): return None
        row=read(path)
        if row['parameters']!=vars(p) or any(row['provenance'][k]!=epoch[k] for k in ('map_sha','sources')): return None
        records=row['records'];K=cfg['energy_window']
        if len(records)<K or any(x['round']!=i+1 or x['alive']!=100 for i,x in enumerate(records[:K])): return None
        if row['FND'] is not None and row['FND']<=K: return None
        values[str(seed)]=sum(x['energy'] for x in records[:K]);paths[str(seed)]=str(path)
    return make_reference(values,'fingerprint-matched historical trajectories',paths)

def make_reference(values,origin,paths=None):
    typical=mean(values.values());cap=typical*1.02
    return dict(mean=typical,cap=cap,declared_rounded_policy_cap=DECLARED_CAP,
        exact_minus_declared_cap=cap-DECLARED_CAP,per_seed=values,origin=origin,paths=paths or {})

def from_runs(runs):
    if not all(r['energy_status']=='comparable' for r in runs):
        raise RuntimeError('Matched SimpleACO reference lacks the full all-alive workload. Choose a separately declared study window/map.')
    return make_reference({str(r['seed']):r['energy_K'] for r in runs},'fresh matched SimpleACO cohort')
