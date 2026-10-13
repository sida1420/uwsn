"""Matched-state candidate distributions: isolate probability mixing only.

Both proposals share physical state, pheromone, chaos sequence, beta and RNG
seed. No ant deposits or optimizer updates occur between sampled candidates.
"""
from dataclasses import replace
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from long_run import restore
from algorithms.routing.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance


def minimum_expectation(values,m=40):
    """Exact expected minimum for iid draws from the empirical distribution."""
    values=np.sort(np.asarray(values,dtype=float))
    survival=(1-np.arange(len(values)+1)/len(values))**m
    return float(np.dot(values,survival[:-1]-survival[1:]))


def sample(network,snapshot,factor,count=400):
    a=restore(snapshot,network)
    a.clustering.rng.seed(10000+snapshot['completed_rounds'])
    c=a.clustering
    residual=snapshot['residual']
    live=snapshot['live']
    state=c.pre_round(live,residual)
    state=replace(state,strength=state.strength*factor)
    evaluator=Evaluator(HyperParameters())
    rows=[]
    for _ in range(count):
        heads,nodes,outliers=c.create_clusters(live,residual,state)
        head_ids=list(heads)
        dispersion=np.asarray(network.dist_matrix)[np.ix_(head_ids,head_ids)]
        dispersion=dispersion[~np.eye(len(head_ids),dtype=bool)]
        root=dropping_member_multi_hop_routing(heads,nodes,live,outliers,
            network.dist_matrix,network.base_dists,residual,network.radius,a.params.hopping_factor)
        if root is None:
            rows.append(dict(feasible=False,outliers=len(outliers)))
            continue
        costs,total=evaluator.energy_consumption(root,network.dist_matrix,network.base_dists)
        assert set(costs)==set(live)
        rows.append(dict(feasible=True,energy_J=total,outliers=len(outliers),
            CH_pair_distance_m=float(np.mean(dispersion))))
    energies=[r['energy_J'] for r in rows if r['feasible']]
    valid=[r for r in rows if r['feasible']]
    strength=state.strength
    sizes=np.arange(len(live)-1,len(live)-state.target,-1)
    nz=sizes[:,None]*strength*np.asarray(c.chaos)[np.asarray(live)][None,:]
    return dict(factor=factor,count=count,feasible=len(valid),
        mean_energy_J=float(np.mean(energies)),median_energy_J=float(np.median(energies)),
        q10_J=float(np.quantile(energies,.1)),q90_J=float(np.quantile(energies,.9)),
        empirical_best40_J=minimum_expectation(energies),
        mean_outliers=float(np.mean([r['outliers'] for r in rows])),
        mean_CH_pair_distance_m=float(np.mean([r['CH_pair_distance_m'] for r in valid])),
        outlier_energy_correlation=float(np.corrcoef([r['outliers'] for r in valid],energies)[0,1]),
        strength=strength,uniform_mixture_diagnostic=float(np.mean(nz/(1+nz))),records=rows)


def main():
    folder=Path(__file__).parent/'long'
    network=NetworkInstance.from_pickle(ROOT/'map.pkl')
    result={}
    for completed in (600,1499,1501):
        path=folder/f'calibrated_x1_seed6_round{completed}.json'
        if not path.exists():
            continue
        state=json.loads(path.read_text())
        result[str(completed)]={}
        for factor in (1.,2.):
            row=sample(network,state,factor)
            result[str(completed)][str(factor)]=row
            print(completed,factor,'mean',row['mean_energy_J'],'best40',row['empirical_best40_J'],
                  'outliers',row['mean_outliers'],flush=True)
        baseline=result[str(completed)]['1.0']
        doubled=result[str(completed)]['2.0']
        threshold=baseline['q10_J']
        for row in (baseline,doubled):
            p=sum(r.get('energy_J',float('inf'))<=threshold for r in row['records'])/row['feasible']
            row['prob_below_baseline_q10']=p
            row['iid_best40_success_at_threshold']=1-(1-p)**40
    (folder/'math-probes.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
