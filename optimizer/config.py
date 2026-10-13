"""Strict fixed-policy configuration and independent search coordinates."""
from dataclasses import asdict, replace
import math
from pathlib import Path
import yaml
from optimizer import ROOT
from algorithms.clustering.d_aco.parameters import DACOParameters

SPACE = dict(alpha=(.25,3.,False), beta=(0.,1.5,False), gamma=(0.,1.,False),
             Q=(.1,60.,True), tau_max=(4.,32.,False),
             rho_min=(.05,.4,False), rho_max=(.4,.9,False),
             theta=(0.,1.,False), load_density_weight=(0.,1.,False), load_power=(1.,4.,False))
DEFAULT = dict(mode='scientific', study_role='training', map='map.pkl', training_seeds=[24,25,26],
    validation_seeds=[40,41,42], horizon=3000, energy_window=2611, energy_allowance=.02,
    max_trials=32, max_wall_hours=6., max_session_hours=2., max_workers=2, sampler='tpe', sampler_seed=20261012,
    startup_trials=12, checkpoint_every=25, max_disk_mb=4096, worker_memory_mb=1024,
    seed_timeout_seconds=3600, max_worker_retries=2, reuse_history=True)

def validate(raw):
    unknown=set(raw)-set(DEFAULT)
    if unknown: raise ValueError(f'Unknown configuration fields: {sorted(unknown)}')
    cfg={**DEFAULT,**raw}
    if cfg['mode'] not in ('scientific','smoke'): raise ValueError('mode must be scientific or smoke')
    if cfg['study_role'] not in ('training','validation'): raise ValueError('Unknown study role')
    for key in ('training_seeds','validation_seeds'):
        values=cfg[key]
        if not isinstance(values,list) or not values or any(type(s) is not int or s<0 for s in values) or len(values)!=len(set(values)):
            raise ValueError(f'{key} must contain distinct nonnegative integers')
    if set(cfg['training_seeds']) & set(cfg['validation_seeds']): raise ValueError('Training and validation seeds overlap')
    for key in ('horizon','energy_window','max_trials','max_workers','startup_trials','checkpoint_every','max_disk_mb','worker_memory_mb','seed_timeout_seconds'):
        if type(cfg[key]) is not int or cfg[key]<1: raise ValueError(f'{key} must be a positive integer')
    if type(cfg['max_worker_retries']) is not int or cfg['max_worker_retries']<0: raise ValueError('Invalid retry budget')
    if cfg['max_workers']>4: raise ValueError('At most four simulation workers')
    if cfg['sampler'] not in ('tpe','random'): raise ValueError('sampler must be tpe or random')
    if type(cfg['sampler_seed']) is not int or cfg['sampler_seed']<0: raise ValueError('Invalid sampler seed')
    if cfg['max_disk_mb']<64: raise ValueError('At least 64 MiB storage is required for checkpoint headroom')
    if type(cfg['reuse_history']) is not bool: raise ValueError('reuse_history must be boolean')
    if cfg['energy_window']>cfg['horizon']: raise ValueError('Energy window exceeds horizon')
    if not math.isfinite(cfg['max_wall_hours']) or cfg['max_wall_hours']<=0: raise ValueError('Invalid wall budget')
    if not math.isfinite(cfg['max_session_hours']) or cfg['max_session_hours']<=0: raise ValueError('Invalid session budget')
    limit=6. if cfg['study_role']=='training' else 2.
    if cfg['max_wall_hours']>limit: raise ValueError(f'{cfg["study_role"]} budget must be at most {limit:g} hours')
    if cfg['energy_allowance']!=.02: raise ValueError('Primary energy allowance is fixed at +2%')
    if cfg['mode']=='scientific' and (cfg['horizon']!=3000 or cfg['energy_window']!=2611):
        raise ValueError('Scientific study requires H=3000 and K=2611')
    if cfg['mode']=='smoke' and (cfg['horizon']>20 or cfg['max_trials']>3):
        raise ValueError('Smoke studies allow at most 20 rounds and three configurations')
    cfg['map']=str((ROOT / cfg['map']).resolve())
    if not Path(cfg['map']).is_file(): raise ValueError('Map does not exist')
    return cfg

def load(path):
    return validate(yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {})

def anchors():
    base=DACOParameters()
    return [asdict(p) for p in (base,replace(base,beta=.225,gamma=.1),replace(base,beta=.45,gamma=.2),
        replace(base,Q=20.),replace(base,Q=30.),
        replace(base,beta=0.,theta=0.,load_density_weight=0.,load_power=1.),
        replace(base,gamma=0.,theta=.5,load_density_weight=.5,load_power=3.),
        replace(base,beta=0.,gamma=0.,theta=1.,load_density_weight=1.,load_power=4.))]

def suggest(trial):
    values={key:trial.suggest_float(key,lo,hi,log=log) for key,(lo,hi,log) in SPACE.items()}
    params=replace(DACOParameters(),**values)
    if params.rho_min>=params.rho_max: raise ValueError('rho_min must be strictly below rho_max')
    return asdict(params)
