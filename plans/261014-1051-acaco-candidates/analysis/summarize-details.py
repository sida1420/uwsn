"""Descriptive topology/energy and short-trajectory evidence, no new search."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def mean(values):
    values=[v for v in values if v is not None]
    return float(np.mean(values)) if values else None


def load(paths):
    return [json.loads(line) for path in paths for line in path.read_text(encoding='utf-8').splitlines()]


def pool_details(rows):
    baseline={(r['map_sha'],r['algorithm_seed']):r for r in rows if r['variant']=='B0'}
    out={}
    for variant in sorted({r['variant'] for r in rows}):
        group=[r for r in rows if r['variant']==variant]
        valid=[r for r in group if r['feasible_count']==r['params']['num_ants']
               and baseline.get((r['map_sha'],r['algorithm_seed']),{}).get('feasible_count')==40]
        by_topology=defaultdict(list)
        for row in valid:
            candidates=[c for c in row['candidate_records'] if c['stage']=='search']
            selected=min(candidates,key=lambda c:abs(c['energy']-row['selected_energy']))
            point=dict(outliers=row['outliers']['mean'],coverage=row['coverage']['mean'],
                diversity=row['jaccard_diversity'],unique_sets=row['unique_ch_sets'],
                entropy=row['transition_entropy']['mean'],chaos_lambda=row['effective_lambda']['mean'],
                pheromone_cv=row['pheromone_after']['concentration_cv'],
                pheromone_floor=row['pheromone_after']['floor_fraction'],
                pheromone_ceiling=row['pheromone_after']['ceiling_fraction'],
                pool_tx=mean([c['tx'] for c in candidates]),pool_rx=mean([c['rx'] for c in candidates]),
                pool_da=mean([c['da'] for c in candidates]),selected_tx=selected['tx'],selected_rx=selected['rx'],
                selected_da=selected['da'],selected_node_max=selected['node_energy']['max'],
                selected_node_cv=selected['node_energy']['std']/selected['node_energy']['mean'],
                mean_ch_pair_distance=mean([c['inter_ch_distance']['mean'] for c in candidates]),
                algorithm_seconds=row['algorithm_seconds'],setup_seconds=row['setup_seconds'],
                observer_seconds=row['total_observer_seconds'],proxy_seconds=row['proxy_seconds'],
                proxy_cell_operations=row['proxy_cell_operations'],max_stagnation=row['max_stagnation'])
            by_topology[row['map_sha']].append(point)
        out[variant]={k:mean([mean([p[k] for p in points]) for points in by_topology.values()])
                      for k in next(iter(by_topology.values()))[0]} if by_topology else {}
        out[variant]['matched_runs']=len(valid)
        out[variant]['topologies']=len(by_topology)
        out[variant]['incomplete_conditions']=[dict(scenario=r['scenario'],seed=r['algorithm_seed'],
            feasible=r['feasible_count'],attempts=r['attempt_count']) for r in group
            if r['feasible_count']!=r['params']['num_ants']]
    return out


def trajectories(rows, output):
    groups=defaultdict(list)
    for r in rows:
        groups[(r['map_sha'],r['algorithm_seed'],r['variant'])].append(r)
    summaries=[]
    for (map_sha,seed,variant),group in groups.items():
        group.sort(key=lambda r:r['physical_round'])
        summaries.append(dict(map_sha=map_sha,scenario=group[0]['scenario'],seed=seed,variant=variant,
            rounds=len(group),total_energy=sum(r['selected_energy'] for r in group),
            energy_curve=[r['selected_energy'] for r in group],
            pheromone_cv_curve=[r['pheromone_after']['concentration_cv'] for r in group],
            entropy_curve=[r['transition_entropy']['mean'] for r in group],
            diversity_curve=[r['jaccard_diversity'] for r in group],
            max_stagnation_curve=[r['max_stagnation'] for r in group],
            rho_curve=[r['effective_evaporation']['mean'] for r in group],
            alive_curve=[len(r['candidate_records'][-1]['per_node_energy']) for r in group]))
    base={(s['map_sha'],s['seed']):s for s in summaries if s['variant']=='B0'}
    for s in summaries:
        reference=base.get((s['map_sha'],s['seed']))
        s['relative_total_improvement_pct']=None if reference is None else 100*(1-s['total_energy']/reference['total_energy'])
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    variants=sorted({s['variant'] for s in summaries})
    for variant in variants:
        group=[s for s in summaries if s['variant']==variant]
        for ax,key in zip(axes,['energy_curve','pheromone_cv_curve','diversity_curve']):
            curves=[s[key] for s in group if len(s[key])==10]
            if curves:
                ax.plot(range(10),np.mean(curves,axis=0),label=variant)
    for ax,title,y in zip(axes,['Năng lượng round','Pheromone concentration','Đa dạng pool'],['J','CV','Jaccard distance']):
        ax.set(xlabel='Physical round',ylabel=y,title=title)
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(output/'short-trajectories.png',dpi=170);plt.close(fig)
    return summaries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--holdout',type=Path,required=True)
    parser.add_argument('--trajectories',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error('output must stay in research plan')
    args.output.mkdir(parents=True,exist_ok=True)
    pool=pool_details(load(sorted(args.holdout.glob('*/pools.jsonl'))))
    trajectory_rows=load(args.trajectories)
    # κ controls are separate reruns: do not count repeated V6 as independent deployments.
    unique={}
    for r in trajectory_rows:
        key=(r['map_sha'],r['algorithm_seed'],r['variant'],r['physical_round'])
        if key in unique:
            assert unique[key]['selected_energy']==r['selected_energy']
        unique[key]=r
    result=dict(holdout_pool=pool,trajectories=trajectories(list(unique.values()),args.output),
        descriptive_only=True,note='Short trajectories have 3 scenarios, repeated scenario seed19; no lifetime/independence CI')
    (args.output/'details.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')


if __name__=='__main__':
    main()
