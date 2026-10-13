"""Fresh matched SimpleACO energy references."""
from statistics import mean
import math

DECLARED_CAP=43.315422

class ReferenceUnavailable(RuntimeError):
    """Completed reference cohort cannot support the declared energy comparison."""

def make_reference(values,origin,paths=None):
    typical=mean(values.values());cap=typical*1.02
    return dict(mean=typical,cap=cap,declared_rounded_policy_cap=DECLARED_CAP,
        exact_minus_declared_cap=cap-DECLARED_CAP,per_seed=values,origin=origin,paths=paths or {})

def energy_prefix(records,nodes):
    """Cumulative energy while the same complete workload stays alive."""
    curve=[];total=0.
    for index,row in enumerate(records,1):
        if int(row['round'])!=index: raise ValueError('Nonsequential reference records')
        if any(int(row[k])!=nodes for k in ('alive_before','alive_after','served')): break
        value=float(row['selected_tree_physical_energy'])
        if not math.isfinite(value) or value<=0: raise ValueError('Invalid reference energy')
        total+=value;curve.append(total)
    return curve

def from_runs(runs,cfg=None):
    if cfg is not None:
        lengths=[len(r['all_alive_energy_prefix']) for r in runs]
        requested=cfg['energy_window'];policy=cfg['energy_window_policy']
        window=min(requested,max(1,math.floor(min(lengths)*cfg['reference_window_fraction']))) if policy=='reference' and min(lengths)>0 else requested
        if min(lengths)>=window:
            result=make_reference({str(r['seed']):r['all_alive_energy_prefix'][window-1] for r in runs},'fresh matched SimpleACO cohort')
            result.update(energy_window=window,requested_energy_window=requested,energy_window_policy=policy,
                          reference_window_fraction=cfg['reference_window_fraction'],
                          available_prefix_per_seed={str(r['seed']):length for r,length in zip(runs,lengths)})
            return result
    elif all(r['energy_status']=='comparable' for r in runs):
        return make_reference({str(r['seed']):r['energy_K'] for r in runs},'fresh matched SimpleACO cohort')
    if cfg is not None or not all(r['energy_status']=='comparable' for r in runs):
        details=', '.join(f"seed {r['seed']}: FND={r.get('FND')}, rounds={r.get('completed_rounds')}" for r in runs)
        raise ReferenceUnavailable('SimpleACO reference cannot support the declared all-alive energy window. '
                                   + details + '. A different map or separately declared shorter window is required.')
