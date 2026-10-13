from pathlib import Path
from optimizer.storage import read,atomic

def report(folder):
    folder=Path(folder);cfg=read(folder/'config.json');state=read(folder/'state.json');rows=[]
    for key,job in state['jobs'].items():
        if key=='reference': continue
        path=folder/'trials'/key/'aggregate.json'
        rows.append(dict(trial=key,status=job['status'],parameters=job['parameters'],parameter_origin=job.get('parameter_origin','unspecified'),
                         **(read(path) if path.exists() else {})))
    atomic(folder/'trial-results.json',rows)
    import csv,json
    fields=sorted(set().union(*(r.keys() for r in rows))) if rows else ['trial','status']
    with (folder/'trial-results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    seeds=[]
    for path in (folder/'trials').rglob('metrics.json'):
        seeds.append(dict(trial=path.parent.parent.name,**read(path)))
    atomic(folder/'per-seed-results.json',seeds)
    atomic(folder/'incomplete-trials.json',[r for r in rows if r['status']!='complete'])
    feasible=sorted([r for r in rows if r['status']=='complete' and r.get('feasible')],key=lambda r:(-r['mean_service_capped'],r['energy_K_mean']))
    atomic(folder/'top-five-trials.json',feasible[:5])
    if feasible and cfg['mode']=='scientific':
        import yaml
        (folder/'best-feasible-config.yaml').write_text(yaml.safe_dump({**feasible[0],'validation_status':'training only; validation pending'}),encoding='utf-8')
    reference_path=folder/'reference.json'
    window=read(reference_path)['energy_window'] if reference_path.exists() else 'pending reference'
    lines=['# Optimizer campaign results','',f"Stop: {state['stop_reason']}. H={cfg['horizon']}, T_max={cfg['adaptive_total_rounds']}, K={window} (configured limit {cfg['energy_window']}).",'',
            '|Trial|Status|Parameter origin|Service|Energy K|Feasible|','|---|---|---|---:|---:|---|']
    for r in rows: lines.append(f"|{r['trial']}|{r['status']}|{r['parameter_origin']}|{r.get('mean_service_capped','incomplete')}|{r.get('energy_K_mean','')}|{r.get('feasible',False)}|")
    lines+=['',f"Completed cohorts: {sum(r['status']=='complete' for r in rows)}. Feasible completed cohorts: {len(feasible)}. Active wall time: {state.get('spent_wall',0)/60:.2f} minutes."]
    if feasible and reference_path.exists():
        reference=read(reference_path);baseline_path=folder/'trials/reference/outcome.json'
        if baseline_path.exists():
            baseline=read(baseline_path)['runs'];best=feasible[0]
            from statistics import mean
            baseline_service=mean(r['completed_rounds'] for r in baseline)
            gain=(best['mean_service_capped']/baseline_service-1)*100
            savings=(1-best['energy_K_mean']/reference['mean'])*100
            lines+=['','## Best completed trial versus matched SimpleACO','',
                    f"Trial {best['trial']}: mean service {best['mean_service_capped']:.2f} versus {baseline_service:.2f} rounds ({gain:+.2f}%).",
                    f"Mean physical energy over K={window}: {best['energy_K_mean']:.6f} versus {reference['mean']:.6f} J ({savings:.2f}% lower). The +2% cap is {reference['cap']:.6f} J.",'',
                    '|Seed|SimpleACO rounds|D-ACO rounds|SimpleACO energy K (J)|D-ACO energy K (J)|','|---|---:|---:|---:|---:|']
            for run in baseline:
                seed=run['seed'];candidate_path=folder/'trials'/best['trial']/str(seed)/'metrics.json'
                if candidate_path.exists():
                    candidate=read(candidate_path)
                    lines.append(f"|{seed}|{run['completed_rounds']}|{candidate['completed_rounds']}|{reference['per_seed'][str(seed)]:.6f}|{candidate['energy_K']:.6f}|")
    lines+=['','## Five best feasible configurations','']
    if 0<len(feasible)<5: lines += [f'Only {len(feasible)} completed feasible configuration is available; incomplete cohorts are excluded.','']
    for r in feasible[:5]: lines += [f"### Trial {r['trial']}",'','```json',__import__('json').dumps(r['parameters'],indent=2),'```','']
    if not feasible: lines+=['No complete feasible cohort; no winner selected.']
    lines+=['','3500 is right-censored, not observed termination. Partial cohorts are not ranked. No defaults are promoted.']
    (folder/'final-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if rows:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        target=folder/'plots';target.mkdir(exist_ok=True)
        comparable=[r for r in rows if r.get('energy_comparable')]
        fig,ax=plt.subplots()
        for r in comparable: ax.scatter(r['energy_K_mean'],r['mean_service_capped'],color='green' if r['feasible'] else 'red')
        ref=folder/'reference.json'
        if ref.exists(): ax.axvline(read(ref)['cap'],linestyle='--',color='black')
        ax.set(xlabel='Selected physical energy over K rounds (J)',ylabel='Mean completed service',title='Service and energy')
        fig.tight_layout();fig.savefig(target/'service-energy.png');plt.close(fig)
    return rows
