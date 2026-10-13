"""Read-only historical compatibility and schedule/source audits."""
import csv,json,sqlite3
from pathlib import Path
from optimizer import ROOT,PACKAGE
from optimizer.storage import atomic,read,digest
from optimizer.adapters import get

def compatibility(legacy,output,cfg):
    legacy=Path(legacy).resolve();output=Path(output);state=read(legacy/'state.json');old=read(legacy/'provenance.json')
    db=legacy/'study.db'
    connection=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    try:
        database=dict(sha=digest(db),trial_count=connection.execute('SELECT COUNT(*) FROM trials').fetchone()[0])
        snapshot=sqlite3.connect(output/'legacy-study-snapshot.db')
        try: connection.backup(snapshot)
        finally: snapshot.close()
        database['snapshot_sha']=digest(output/'legacy-study-snapshot.db')
    finally: connection.close()
    atomic(output/'legacy-database-audit.json',database)
    rows=[];legal=[]
    for key,job in state['jobs'].items():
        if key=='reference': continue
        metric=legacy/'trials'/key/'aggregate.json'
        try:
            get('daco').validate_config(job['parameters']);tier='C'
            adapter=get('daco')
            for name,(low,high,_) in adapter.space.items():
                if not low<=job['parameters'][name]<=high: raise ValueError('Outside current search space')
            for name,value in adapter.baseline_config().items():
                if name not in adapter.space and job['parameters'][name]!=value: raise ValueError('Different fixed policy')
            reason='H/T_max changes 3000 to 3500; evaporation prefix differs. Parameters only, no score/checkpoint transfer.'
        except (TypeError,ValueError): tier='D';reason='Illegal effective parameter vector'
        values=read(metric) if metric.exists() else {}
        row=dict(old_trial_id=key,tier=tier,reason=reason,old_T_max=3000,old_horizon=old['configuration']['horizon'],
                 map_sha=old['map_sha'],seeds=json.dumps(old['configuration']['training_seeds']),
                 full_parameters=json.dumps(job['parameters'],sort_keys=True),theta=job['parameters']['theta'],
                 old_service=values.get('mean_service_capped'),old_energy=values.get('energy_K_mean'))
        rows.append(row)
        if tier=='C' and values.get('feasible'): legal.append((values['mean_service_capped'],-values['energy_K_mean'],job['parameters']))
    with (output/'legacy-trials-compatibility.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    from optimizer.search_space import anchors
    configs=[r[2] for r in sorted(legal,key=lambda r:(r[0],r[1]),reverse=True)]+anchors()
    seen=set();unique=[]
    for config in configs:
        key=json.dumps(config,sort_keys=True)
        if key not in seen: seen.add(key);unique.append(config)
    return unique

def source_audit(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    import re
    pattern=re.compile(r'T_max|total_rounds|max_iterations|network_round|current_iteration|theta|rho|beta|inertia|chaos|warm_start')
    rows=[]
    paths=list((ROOT/'src').rglob('*.py'))+list((ROOT/'plans').rglob('*.py'))
    paths+=list(PACKAGE.glob('*.py'))
    for path in sorted(paths):
        for line,text in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
            if pattern.search(text):
                clock='context-dependent; see source and architecture audit'
                effect='No formula change; exact native expression retained'
                if 'd_aco' in str(path) and ('iteration' in text or 'T_max' in text or 'rho' in text):
                    clock='one-based network round';effect='rho slope decreases in magnitude when T_max grows; prefix differs'
                elif 'pso' in str(path) and ('inertia' in text or 'total_iterations' in text):
                    clock='inner swarm iteration';effect='Network horizon does not change this inner schedule'
                elif 'ac_aco' in str(path) and ('beta' in text or 'T_max' in text or 'rho' in text):
                    clock='network round';effect='rho slope or beta midpoint changes; raw midpoint1500->1750'
                elif 'theta' in text:
                    clock='constant parameter / per-round elite deposit';effect='No direct horizon dependence; state history can differ'
                rows.append(dict(file=str(path.relative_to(ROOT)),line=line,code=text.strip(),clock=clock,
                                 value_at_3000='native; schedule-boundaries.csv where temporal',
                                 value_at_3500='native; schedule-boundaries.csv where temporal',
                                 expected_effect=effect,test='Schedule / adapter smoke / deterministic equivalence'))
    with (output/'adaptive-horizon-inventory.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    from algorithms.clustering.ac_aco.ac_aco import evaporation_rate,heuristic_weight
    schedule=[]
    for horizon in (3000,3500):
        for t in (1,600,1500,1750,2611,2999,3000,3500):
            schedule.append(dict(T_max=horizon,round=t,daco_rho=evaporation_rate(t,horizon,.1,.6),
                                 acaco_beta_raw=heuristic_weight(t,horizon,1,5,5,'raw'),
                                 acaco_beta_normalized=heuristic_weight(t,horizon,1,5,5,'normalized')))
    atomic(output/'schedule-boundaries.json',schedule)
    with (output/'schedule-boundaries.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(schedule[0]));writer.writeheader();writer.writerows(schedule)
    # Controlled unit diagnostics of the exact deposit formula, not physical trajectories.
    scaling=[]
    for N in (50,100,200):
        for ants in (20,40,80):
            for cost_scale in (.5,1.,2.):
                Q=9.511346558794795;theta=.8363876748180215;quality=1/1.426
                per_ant=Q*quality/ants;elite=Q*quality*theta;features=round(.2*N)
                scaling.append(dict(N=N,ants=ants,cost_and_reference_scale=cost_scale,rewarded_features=features,
                    per_ant_raw=per_ant,elite_raw=elite,elite_to_one_ant=theta*ants,
                    elite_to_all_equal_quality_ants=theta,total_elite_mass=features*elite,
                    clamped_elite_actual_per_feature=min(elite,8.-1.),
                    note='Controlled equal-quality formula; geometry/entropy requires separate trajectories'))
    with (output/'theta-scaling-diagnostics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(scaling[0]));writer.writeheader();writer.writerows(scaling)
    (output/'theta-scaling-audit.md').write_text('''# Theta source and scaling audit

`d_aco.py:deposit` requests `Q * energy_reference / fitness / num_ants` per ant and
`Q * energy_reference / fitness * theta` for the best set, depositing on each CH.
Both use the same cached fitness, in joules; energy_reference/fitness is dimensionless.
Evaporation/clamp occurs in pre_round before construction. Live per-ant clipping
occurs during search; the elite deposit follows in post_round. There is no second evaporation.
The literal theta is already a ratio to the full equal-quality ant batch, not one ant.
Elite/one-ant = theta*A; elite/batch = theta when all A ants contribute equal quality.
With fewer feasible ants, unequal costs, differing CHs and clipping the effective ratio varies.
Total requested mass also scales with rewarded CH count. Multiplying both fitness and reference
by a common unit scale leaves deposits unchanged; multiplying only fitness does not.

No normalization policy is promoted. Raw theta remains the reproducible control.
The accompanying 27-case table is an algebraic diagnostic, not a claim of geometry invariance.
N/ant-count physical scaling tests are separate research work; no 50/200-node lifetime runs occurred.
Transition entropy, requested/lost deposit, saturation and native counts are recorded per round.
''',encoding='utf-8')
    (output/'architecture-and-provenance.md').write_text('''# Architecture and provenance

Current orchestration is directly under optimizer/; legacy studies are preserved.
Production algorithms now accept explicit per-instance seeds, and adapters pass them.
Private RNG streams are pickled with the native state; observation consumes no extra draws.
Adapter registry owns native construction, parameter validation/search space and diagnostics.
Shared trajectory runner owns selected-route accounting, checkpoints and energy eligibility.
Shared engine owns Optuna ask/tell, seed cohorts, worker isolation and the wall-time ledger.
PSO and AC-ACO use this runner in smoke tests only. No PSO/AC-ACO tuning is enabled.

Clock inventory: D-ACO rho is rho_max-min(t/T_max,1)*(rho_max-rho_min), one increment
per network round. Beta/gamma/theta are constants. Grid decay is spatial, not temporal.
AC-ACO rho uses the same round clock; raw beta centers at T_max/2 (1500 becomes1750),
normalized beta uses t/T_max-.5; chaos uses the native cost window and logistic sequence.
PSO inertia uses inner_iteration/(iterations-1), not network T_max; warm starts persist
across network rounds. Ant/particle counts and PSO inner iterations are not set to3500.
    All source occurrences are retained in adaptive-horizon-inventory.csv; exact boundary
values for both horizons are in schedule-boundaries.csv. Experiment scripts are legacy
provenance and are not executed or rewritten for this campaign.

Old 3000 trials are tier C parameter-only. Prefix identity fails at round1 when rho changes.
No old objective observations or checkpoint state enter the new surrogate/ranking.
SimpleACO uses matched hparameters. K is frozen before tuning from 90% of the
shortest all-alive reference prefix, capped at the configured limit (default2611).
All candidates share this K and the exact cohort mean*1.02 cap. Completed reference
measurements may be reprojected only after exact map/native-source/runtime checks.
Each campaign snapshots its map; regenerating the input map does not affect it.
The earlier plan's rounded absolute cap is metadata only. Density decay was fixed parabolic,
not tuned, in the previous expanded study.

Performance changes: hash sources at entry/completion and on file-stat changes between
checkpoints; persist state on transitions or every2s; pickle sampler on ask/tell only;
prioritize old feasible settings and deduplicate exact configs. New starts stop at
the cumulative budget cutoff; active cohorts finish every seed without a timer kill.
No proxy scores enter final ranking; reused parameter sets are labeled explicitly.
Concurrent suggestion order can differ; native RNG/physical state checkpoints remain exact.
''',encoding='utf-8')
