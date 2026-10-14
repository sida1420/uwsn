"""Topology-level paired analysis and standalone scientific figures."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def finite_mean(values):
    values = [v for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(values)) if values else None

def interval(values):
    values = np.asarray(values, dtype=float)
    mean = float(values.mean()) if values.size else None
    sd = float(values.std(ddof=1)) if values.size > 1 else None
    if values.size < 2:
        return mean, sd, None, None
    width = float(t.ppf(.975, len(values) - 1) * sd / np.sqrt(len(values)))
    return mean, sd, mean - width, mean + width

def condition(row):
    return row['map_sha'], row['algorithm_seed']

def feasible(candidate):
    return bool(candidate['positive_finite'] and all(candidate[key] for key in
        ('conservation_valid','topology_valid','radius_valid','all_live_present')))

def validate_rows(rows):
    keys=set()
    configs=defaultdict(set)
    for row in rows:
        key=(row['variant'], *condition(row), row['physical_round'])
        if key in keys:
            raise ValueError(f'duplicate condition: {key}')
        keys.add(key)
        if row['invalid_probability_count'] or any(not feasible(c) for c in row['candidate_records']):
            raise ValueError(f'invalid probability/tree: {key}; no statistical claim permitted')
        configs[row['variant']].add(json.dumps(dict(params=row['params'],options=row.get('options',{})),sort_keys=True))
    if any(len(values)>1 for values in configs.values()):
        raise ValueError('different effective parameters/options under same variant; analyze separately')

def analyze(rows, metric='min', independent=False, total_budget=False):
    first = [r for r in rows if r['physical_round'] == 0]
    baseline = {condition(r): r for r in first if r['variant'] == 'B0'}
    results = []
    for variant in sorted({r['variant'] for r in first}):
        group = [r for r in first if r['variant'] == variant]
        pairs = []
        for row in group:
            base = baseline.get(condition(row))
            if (base is None or row['feasible_count'] != row['params']['num_ants']
                    or base['feasible_count'] != base['params']['num_ants']):
                continue
            if total_budget:
                if row['evaluation_count'] != base['evaluation_count']:
                    continue
            elif row['params']['num_ants'] != base['params']['num_ants']:
                continue
            energy, reference = row['energy'][metric], base['energy'][metric]
            pairs.append((row['map_sha'], 100 * (1 - energy / reference), reference - energy))
        topology = defaultdict(list)
        differences = defaultdict(list)
        for scenario, improvement, difference in pairs:
            topology[scenario].append(improvement)
            differences[scenario].append(difference)
        values = [float(np.mean(x)) for x in topology.values()]
        mean, sd, lo, hi = interval(values)
        results.append(dict(variant=variant, paired_runs=len(pairs), valid_topologies=len(topology),
            improvement_pct=mean, topology_sd_pct=sd, ci95_low=lo if independent else None,
            ci95_high=hi if independent else None, median_topology_improvement_pct=finite_mean([])
                if not values else float(np.median(values)),
            paired_difference_J=finite_mean([np.mean(v) for v in differences.values()]),
            topology_effects={k: float(np.mean(v)) for k, v in topology.items()},
            energy_mean_J=finite_mean([r['energy'][metric] for r in group]),
            energy_sd_J=float(np.std([r['energy'][metric] for r in group if r['energy'][metric] is not None], ddof=1))
                if sum(r['energy'][metric] is not None for r in group) > 1 else None,
            energy_median_J=None if not any(r['energy'][metric] is not None for r in group)
                else float(np.median([r['energy'][metric] for r in group if r['energy'][metric] is not None])),
            complete_pools=sum(r['feasible_count'] == r['params']['num_ants'] for r in group),
            total_pools=len(group), feasible_fraction=finite_mean([r['feasibility_rate'] for r in group]),
            algorithm_seconds=finite_mean([r['algorithm_seconds'] for r in group]),
            setup_seconds=finite_mean([r['setup_seconds'] for r in group]),
            total_evaluations=finite_mean([r['evaluation_count'] for r in group]),
            routing_attempts=finite_mean([r['attempt_count']+r['calibration_attempt_count'] for r in group]),
            diversity=finite_mean([r['jaccard_diversity'] for r in group]),
            outliers=finite_mean([r['outliers']['mean'] for r in group]),
            coverage=finite_mean([r['coverage']['mean'] for r in group]),
            entropy=finite_mean([r['transition_entropy']['mean'] for r in group]),
            chaos_lambda=finite_mean([r['effective_lambda']['mean'] for r in group]),
            pheromone_cv=finite_mean([r['pheromone_after']['concentration_cv'] for r in group])))
    return results

def table(results):
    lines = ['| Variant | Topology hợp lệ | ΔE tốt nhất (%) | CI95 topology | Pool đủ | Feasible/attempt | Runtime thuật toán (s) |',
             '|---|---:|---:|---|---:|---:|---:|']
    for r in results:
        effect = '—' if r['improvement_pct'] is None else f"{r['improvement_pct']:.3f}"
        ci = '—' if r['ci95_low'] is None else f"[{r['ci95_low']:.3f}; {r['ci95_high']:.3f}]"
        fraction = '—' if r['feasible_fraction'] is None else f"{r['feasible_fraction']:.3f}"
        lines.append(f"| {r['variant']} | {r['valid_topologies']} | {effect} | {ci} | {r['complete_pools']}/{r['total_pools']} | {fraction} | {r['algorithm_seconds']:.4f} |")
    return '\n'.join(lines)

def figures(rows, results, output):
    variants = [v for v in ('B0','V2','V3','V4','V5','V6','V2+V5','V2+V6','R0','D0')
                if any(r['variant']==v for r in rows)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for variant in variants:
        pools = [r for r in rows if r['variant']==variant and r['physical_round']==0
                 and len(r['best_so_far'])==r['params']['num_ants']]
        if not pools:
            continue
        # Normalize each scenario to paired B0 minimum; these curves are descriptive.
        baseline = {condition(r):r['energy']['min'] for r in rows
                    if r['variant']=='B0' and r['physical_round']==0
                    and r['feasible_count']==r['params']['num_ants']}
        curves = [np.asarray(r['best_so_far'])/baseline[condition(r)]
                  for r in pools if baseline.get(condition(r))]
        if curves:
            length=min(map(len,curves))
            axes[0].plot(range(1,length+1),np.mean([c[:length] for c in curves],axis=0),label=variant)
    axes[0].set(xlabel='Candidate khả thi đã đánh giá',ylabel='Best-so-far / B0 best (ghép cặp)',
                title='Tiến trình tìm kiếm (mô tả)')
    axes[0].legend(fontsize=8)
    metrics = [r for r in results if r['variant'] in variants and r['improvement_pct'] is not None]
    for i,r in enumerate(metrics):
        lo,hi = r['ci95_low'],r['ci95_high']
        error = None if lo is None else [[r['improvement_pct']-lo],[hi-r['improvement_pct']]]
        axes[1].errorbar(r['improvement_pct'],i,xerr=error,fmt='o',capsize=3)
    axes[1].set_yticks(range(len(metrics)),[r['variant'] for r in metrics])
    axes[1].axvline(0,color='gray',linewidth=.8)
    axes[1].set(xlabel='Giảm E tốt nhất so với B0 (%)',title='Mean topology; CI95 nếu độc lập')
    fig.tight_layout(); fig.savefig(output/'search-and-paired.png',dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4))
    data,labels=[],[]
    for variant in variants:
        energies=[c['energy'] for r in rows if r['variant']==variant and r['physical_round']==0
                  for c in r['candidate_records'] if c['stage']=='search' and feasible(c)]
        if energies:
            data.append(energies);labels.append(variant)
    if data:
        ax.boxplot(data,tick_labels=labels,showfliers=False)
    ax.set(ylabel='Năng lượng candidate (J)',title='Phân phối pool mô tả; ants không độc lập')
    fig.tight_layout();fig.savefig(output/'pool-energy.png',dpi=170);plt.close(fig)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--independent-topologies',action='store_true')
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error('output must stay in research plan')
    rows=[]
    signatures=set()
    for path in args.inputs:
        metadata=json.loads((path.parent/'metadata.json').read_text(encoding='utf-8'))
        signature=dict(physics=metadata['physics'], source={k:v for k,v in metadata['source_hashes'].items()
            if k.startswith('src/')})
        signatures.add(hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest())
        rows.extend(json.loads(line) for line in path.read_text(encoding='utf-8').splitlines())
    if len(signatures)>1:
        raise ValueError('different source/physical snapshots; analyze separately')
    validate_rows(rows)
    args.output.mkdir(parents=True,exist_ok=True)
    results={metric:analyze(rows,metric,args.independent_topologies) for metric in ('min','mean','p10')}
    validation=dict(rows=len(rows),topologies=len({r['map_sha'] for r in rows}),
        invalid_probabilities=sum(r['invalid_probability_count'] for r in rows),
        invalid_trees=sum(not all(c[k] for k in ('conservation_valid','topology_valid','radius_valid','all_live_present'))
            for r in rows for c in r['candidate_records']),
        incomplete_pools=sum(r['feasible_count'] != r['params']['num_ants'] for r in rows),
        full_evaluations=sum(r['evaluation_count'] for r in rows),
        interpretation='D40total has 20 search+20 calibration and is intentionally excluded from 40-feasible paired energy table')
    results['equal_total_evaluations']=analyze(rows,'min',args.independent_topologies,True)
    with (args.output/'statistics.json').open('w',encoding='utf-8') as handle:
        json.dump(dict(results=results,validation=validation),handle,indent=2,allow_nan=False)
    (args.output/'analysis.md').write_text('# Phân tích candidate pool\n\n'+table(results['min'])+
        '\n\nDấu dương = giảm năng lượng. CI dùng mean seed trong mỗi topology; chỉ bật khi scenario seeds độc lập. '
        'Không xem candidate/round là replicate. D40total cố ý pool20 nên không có pair pool40.\n\n'+json.dumps(validation,ensure_ascii=False),encoding='utf-8')
    fields=[k for k in results['min'][0] if k!='topology_effects']
    with (args.output/'summary.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in results['min'])
    figures(rows,results['min'],args.output)
    print(table(results['min']))
    print(json.dumps(validation))

if __name__=='__main__':
    main()
