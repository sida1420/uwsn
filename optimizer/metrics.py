"""Cohort mean is the hard constraint; incomplete workloads are infeasible."""
import math
from statistics import mean, stdev

def aggregate(runs,reference,cfg):
    if [r['seed'] for r in runs]!=cfg['training_seeds']: raise ValueError('Incomplete or wrong seed cohort')
    window=reference['energy_window']
    if any(r['energy_window']!=window for r in runs): raise ValueError('Candidates must use the frozen reference energy window')
    comparable=all(r['energy_status']=='comparable' for r in runs)
    energy=mean(r['energy_K'] for r in runs) if comparable else None
    cap=reference['cap']
    delta=energy-cap if comparable else max(1.,cap)
    ratios=[r['energy_K']/reference['per_seed'][str(r['seed'])] for r in runs] if comparable else []
    service=[r['completed_rounds'] for r in runs]
    observed=[r['FND'] for r in runs if r['FND'] is not None]
    return dict(mean_service_capped=mean(service),service_per_seed=service,
        service_standard_error=stdev(service)/math.sqrt(len(service)) if len(service)>1 else None,
        mean_fnd_observed_only=mean(observed) if observed else None,
        fnd_observed_count=len(observed),service_terminations=[r['termination_reason'] for r in runs],
        energy_K_mean=energy,energy_K_reference_mean=reference['mean'],energy_window=window,
        energy_constraint_delta_j=delta,energy_ratio=energy/reference['mean'] if comparable else None,
        energy_comparable=comparable,energy_status='comparable' if comparable else 'not_comparable',
        energy_ratios_per_seed=ratios,
        ratio_standard_error=stdev(ratios)/math.sqrt(len(ratios)) if len(ratios)>1 else None,
        violating_seed_fraction=sum(r>1.02 for r in ratios)/len(ratios) if ratios else None,
        feasible=comparable and delta<=0 and cfg['mode']=='scientific',
        smoke_only=cfg['mode']=='smoke',
        cpu=sum(r['cpu'] for r in runs),wall=sum(r['wall'] for r in runs),
        attempts=sum(r['clustering_attempts'] for r in runs),
        routing_attempts=sum(r['routing_attempts'] for r in runs),
        feasible_evaluations=sum(r.get('feasible_evaluations',0) for r in runs),
        calibration_attempts=sum(r['calibration_attempts'] for r in runs))

def constraints(trial):
    return [trial.user_attrs.get('energy_constraint_delta_j',1e12)]
