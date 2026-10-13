"""Fresh matched SimpleACO energy references."""
from statistics import mean

DECLARED_CAP=43.315422

def make_reference(values,origin,paths=None):
    typical=mean(values.values());cap=typical*1.02
    return dict(mean=typical,cap=cap,declared_rounded_policy_cap=DECLARED_CAP,
        exact_minus_declared_cap=cap-DECLARED_CAP,per_seed=values,origin=origin,paths=paths or {})

def from_runs(runs):
    if not all(r['energy_status']=='comparable' for r in runs):
        raise RuntimeError('Matched SimpleACO reference lacks the full all-alive workload. Choose a separately declared study window/map.')
    return make_reference({str(r['seed']):r['energy_K'] for r in runs},'fresh matched SimpleACO cohort')
