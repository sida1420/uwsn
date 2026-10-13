"""Export all cohorts and conditional training recommendations, never defaults."""
import csv
import gzip
import json
from pathlib import Path
import numpy as np
import yaml
from optimizer.config import SPACE
from optimizer.storage import read,atomic,assert_epoch
from optimizer.controller import status

def generate(folder):
    folder=Path(folder).resolve();cfg=assert_epoch(folder);current=status(folder)
    state=read(folder/'state.json');reference=read(folder/'reference.json') if (folder/'reference.json').exists() else None
    rows=[];seeds=[]
    for key,job in state['jobs'].items():
        if key=='reference': continue
        aggregate_path=folder/'trials'/key/'aggregate.json'
        row=dict(number=job['number'],status=job['status'],parameters=job['parameters'],errors=job.get('errors',[]))
        if aggregate_path.exists(): row.update(read(aggregate_path))
        rows.append(row)
        for seed in cfg['training_seeds']:
            path=folder/'trials'/key/str(seed)/'metrics.json'
            if path.exists(): seeds.append(dict(trial=job['number'],**read(path)))
    def export(name,items):
        fields=sorted(set().union(*(r.keys() for r in items))) if items else ['number']
        with (folder/name).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
            writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in items)
    export('trials.csv',rows);export('seeds.csv',seeds)
    atomic(folder/'trials.json',rows);atomic(folder/'seeds.json',seeds)
    best=current['best_feasible']
    if best:
        job=state['jobs'][str(best['number'])]
        recommendation=dict(status='training recommendation; independent validation required',
            trial=best['number'],parameters=job['parameters'],mean_service=best['mean_service_capped'],
            energy_mean=best['energy_K_mean'],energy_cap=reference['cap'],provenance=read(folder/'provenance.json'))
        (folder/'best-feasible-config.yaml').write_text(yaml.safe_dump(recommendation,sort_keys=False),encoding='utf-8')
    lines=['# D-ACO constrained parameter study', '',
        '**SMOKE ONLY — no scientific ranking or recommendation.**' if cfg['mode']=='smoke' else
        ('**Held-out validation of a frozen training shortlist; no refitting or selection on validation outcomes.**' if cfg['study_role']=='validation' else
         'Training objective: maximize mean capped completed service, subject to mean full-workload physical energy at most +2% versus matched SimpleACO.'), '',
        f"Seeds: {cfg['training_seeds']}; horizon {cfg['horizon']}; energy window {cfg['energy_window']}. "
        f"Stop: {current['stop_reason']}; {current['complete']} complete configurations, {current['failed']} failed, "
        f"{current['infeasible']} excluded from feasible recommendations.", '',
        f"Reference mean: {reference['mean']:.12f} J; exact cap: {reference['cap']:.12f} J; "
        f"origin: {reference['origin']}." if reference else 'Reference pending; no feasible recommendation is possible.', '',
        '| Trial | State | Mean capped service | Mean energy K (J) | Comparable | Feasible |',
        '|---|---|---:|---:|---|---|']
    for r in rows:
        lines.append(f"| {r['number']} | {r['status']} | {r.get('mean_service_capped','—')} | {r.get('energy_K_mean','—')} | {r.get('energy_comparable','—')} | {r.get('feasible','—')} |")
    lines += ['', 'A missing full all-alive workload is noncomparable and infeasible, never a zero-energy win. '
        'A horizon result is capped/censored. No-feasible-tree-found is a heuristic search outcome; '
        'only the separately reported disconnected-survivor radius-graph certificate demonstrates '
        'physical disconnection. No production source or default is changed.', '',
        'The paired cohort mean is the primary feasibility rule. Per-seed ratios, standard errors, '
        'violation fractions and 0/2/5% sensitivity are diagnostic; they do not replace the +2% rule. '
        'Rounds are not independent replicates. No claim of a global optimum or statistically proven '
        'advantage over random search is made. CPU/wall times include observers and concurrency.', '',
        '## Paired reference comparisons', '',
        '| Trial | Mean service minus SimpleACO | Per-seed energy ratios | Service SE | Ratio SE | Violating seed fraction |',
        '|---|---:|---|---:|---:|---:|']
    ref_services={}
    if reference:
        for seed in cfg['training_seeds']:
            old=reference.get('paths',{}).get(str(seed))
            path=Path(old) if old else folder/'trials/reference'/str(seed)/'metrics.json'
            if path.exists(): ref_services[seed]=read(path)['completed_rounds']
    for r in rows:
        if 'mean_service_capped' not in r: continue
        delta=r['mean_service_capped']-np.mean(list(ref_services.values())) if len(ref_services)==len(cfg['training_seeds']) else 'pending'
        lines.append(f"| {r['number']} | {delta} | {r['energy_ratios_per_seed']} | {r['service_standard_error']} | {r['ratio_standard_error']} | {r['violating_seed_fraction']} |")
    lines += ['', '## Diagnostic energy sensitivity', '', '| Allowance | Comparable cohorts passing |', '|---|---:|']
    for allowance in (0.,.02,.05):
        count=sum(r.get('energy_comparable',False) and r['energy_ratio']<=1+allowance for r in rows)
        lines.append(f'| {100*allowance:g}% | {count} |')
    if cfg['study_role']=='training':
        controls={}
        for r in rows:
            if r['number'] in (0,1) and 'mean_service_capped' in r: controls['default' if r['number']==0 else 'quarter']=r['mean_service_capped']
        lines += ['', 'Training anchor service: '+str(controls)+'.']
    (folder/'final-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    plots(folder,rows,seeds,reference,cfg)
    return current

def plots(folder,rows,seeds,reference,cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    target=folder/'plots';target.mkdir(exist_ok=True)
    label=' (infrastructure smoke only)' if cfg['mode']=='smoke' else ''
    complete=[r for r in rows if 'mean_service_capped' in r]
    comparable=[r for r in complete if r['energy_comparable']]
    def finish(name,title):
        plt.title(title+label);plt.tight_layout();plt.savefig(target/(name+'.png'),dpi=150);plt.close()
    plt.figure()
    for r in comparable: plt.scatter(r['energy_K_mean'],r['mean_service_capped'],c='green' if r['feasible'] else 'red')
    if reference: plt.axvline(reference['cap'],color='black',linestyle='--',label='+2% cap');plt.legend()
    plt.xlabel('Full-workload selected physical energy (J)');plt.ylabel('Mean capped service');finish('service-energy','Service versus energy')
    plt.figure();incumbent=[];best=np.nan
    for r in sorted(complete,key=lambda r:r['number']):
        if r['feasible']: best=r['mean_service_capped'] if np.isnan(best) else max(best,r['mean_service_capped'])
        incumbent.append(best)
    plt.plot(range(1,len(incumbent)+1),incumbent);plt.xlabel('Completed configuration count');plt.ylabel('Best feasible service');finish('incumbent','Feasible training incumbent')
    plt.figure(figsize=(10,5));names=list(SPACE)
    for r in complete:
        values=[(r['parameters'][k]-SPACE[k][0])/(SPACE[k][1]-SPACE[k][0]) for k in names]
        plt.plot(names,values,alpha=.4,color='green' if r['feasible'] else 'grey')
    plt.ylabel('Normalized coordinate');finish('parameters','Parameter parallel coordinates')
    plt.figure();scores=[]
    for k in names:
        x=[r['parameters'][k] for r in complete];y=[r['mean_service_capped'] for r in complete]
        scores.append(abs(float(np.corrcoef(x,y)[0,1])) if len(x)>=3 and np.std(x)>0 and np.std(y)>0 else 0.)
    plt.bar(names,scores);plt.ylabel('Absolute correlation (exploratory, noncausal)');finish('associations','Exploratory parameter associations')
    plt.figure()
    for r in seeds:
        plt.scatter(r['completed_rounds'],r['trial'],marker='>' if r['horizon_censored'] else 'o')
    plt.xlabel('Seed-level completed service (> marker: horizon censored)');plt.ylabel('Trial');finish('service-censoring','Service endpoints and censoring')
    plt.figure()
    for r in complete: plt.scatter(r['cpu'],r['mean_service_capped'],c='green' if r['feasible'] else 'grey')
    plt.xlabel('Total seed process CPU (s; observers included)');plt.ylabel('Mean service');finish('compute','Compute versus service')
    sample=next((r for r in rows if r.get('feasible')),complete[0] if complete else None)
    if sample:
        path=folder/'trials'/str(sample['number'])/str(cfg['training_seeds'][0])/'rounds.csv.gz'
        if path.exists():
            with gzip.open(path,'rt',encoding='utf-8') as f: records=list(csv.DictReader(f))
            if records:
                fig,axes=plt.subplots(3,1,figsize=(8,8));x=[int(r['round']) for r in records]
                for ax,key,title in zip(axes,('total_energy','peak_relative_depletion','mean_choice_entropy'),('Cumulative physical energy (J)','Peak relative depletion','Mean CH-choice entropy')):
                    ax.plot(x,[float(r[key]) if r[key] else np.nan for r in records]);ax.set_ylabel(title)
                axes[-1].set_xlabel('Round');finish('trajectory','Example trajectory')
