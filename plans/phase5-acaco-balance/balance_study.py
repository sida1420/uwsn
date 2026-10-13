"""D-ACO-inspired elite/fitness balance and budget-controlled inner updates.

All interventions are local. Shared routing, evaluator and production defaults
are unchanged. Physical schedules advance once, independent of inner batches.
"""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import sys
from time import process_time

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'plans/phase5-acaco-chaos'))
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.routing.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from long_run import restore, snapshot

FOLDER=Path(__file__).parent
CONFIGS={
    'baseline':dict(theta=1.,load_weight=0.,batches=1,ants=40),
    'elite_off':dict(theta=0.,load_weight=0.,batches=1,ants=40),
    'elite_01':dict(theta=.1,load_weight=0.,batches=1,ants=40),
    'elite_05':dict(theta=.5,load_weight=0.,batches=1,ants=40),
    'fitness_cv':dict(theta=1.,load_weight=.1,batches=1,ants=40),
    'combined':dict(theta=.1,load_weight=.1,batches=1,ants=40),
    'split_2':dict(theta=1.,load_weight=0.,batches=2,ants=20),
    'split_4':dict(theta=1.,load_weight=0.,batches=4,ants=10),
    'batch_80':dict(theta=1.,load_weight=0.,batches=1,ants=80),
    'inner_80':dict(theta=1.,load_weight=0.,batches=2,ants=40),
    'batch_160':dict(theta=1.,load_weight=0.,batches=1,ants=160),
    'inner_160':dict(theta=1.,load_weight=0.,batches=4,ants=40),
}
VALIDATION=('baseline','elite_01','fitness_cv','combined','split_2','batch_80','inner_80')
LIVE_VALIDATION=tuple('live_'+name for name in VALIDATION)
for name in VALIDATION:
    CONFIGS['live_'+name]={**CONFIGS[name],'live':True}


def select(candidates,load_weight):
    if not candidates:
        return None
    if load_weight==0:
        return min(candidates,key=lambda x:(x[0],x[1]))
    mean_energy=np.mean([x[0] for x in candidates])
    mean_cv=np.mean([x[4] for x in candidates])
    def score(x):
        cv=x[4]/mean_cv if mean_cv>0 else 1.
        return ((1-load_weight)*x[0]/mean_energy+load_weight*cv,x[0],x[1])
    return min(candidates,key=score)


class ExperimentalACACO(ACACO):
    def __init__(self,network,cfg,params=None,seed=0):
        self.cfg=cfg
        super().__init__(network,HyperParameters(),params or ACACOParameters(energy_cost_exponent=1.,elite_weight=1.,load_weight=0.),seed=seed)
        if not cfg.get('live',False):
            c=self.clustering
            original=c._transition_probabilities
            def frozen(*args):
                live_pheromone=c.pheromone
                c.pheromone=c._pheromone_array
                try:
                    return original(*args)
                finally:
                    c.pheromone=live_pheromone
            c._transition_probabilities=frozen

    def plan_round(self,live,residual):
        c=self.clustering
        state=c.pre_round(live,residual)
        if state is None:
            return None,{}
        m=self.cfg['batches']
        total_ants=m*self.cfg['ants']
        rho=state.rho if m==1 else 1-(1-state.rho)**(1/m)
        decay=1-rho
        disturbance=state.strength if m==1 else state.strength*rho/state.rho
        inner_state=replace(state,rho=rho,strength=disturbance)
        elite_scale=self.cfg['theta']/sum(decay**i for i in range(m))
        chaos_before=c.chaos.copy()
        candidates=[]
        total_ant_mass=total_elite_mass=0.
        for batch in range(m):
            c.chaos=chaos_before.copy()
            c._pheromone_array=np.asarray(c.pheromone,dtype=float)
            # Equal final ant-deposit survival for every batch, as in one update.
            survival_scale=1. if m==1 else (1-state.rho)/decay**(m-batch)
            for _ in range(self.cfg['ants']):
                for _attempt in range(self.params.max_clustering_attempts):
                    self.total_clustering_attempts+=1
                    heads,nodes,outliers=c.create_clusters(live,residual,state)
                    self.total_routing_attempts+=1
                    root=dropping_member_multi_hop_routing(heads,nodes,state.live,outliers,
                        self.network.dist_matrix,self.network.base_dists,residual,
                        self.network.radius,self.params.hopping_factor)
                    if root is None:
                        self.failed_routing_attempts+=1
                        continue
                    consumption,cost=self.evaluator.energy_consumption(root,
                        self.network.dist_matrix,self.network.base_dists)
                    if not np.isfinite(cost) or cost<=0:
                        self.failed_routing_attempts+=1
                        continue
                    loads=np.asarray(list(consumption.values()))
                    cv=float(loads.std()/loads.mean())
                    chs=tuple(heads)
                    amount=self.params.Q/cost/total_ants*survival_scale
                    for source,target in zip(chs,chs[1:]):
                        c.pheromone[source][target]+=amount
                    total_ant_mass+=(len(chs)-1)*amount*decay**(m-batch)
                    candidates.append((cost,chs,root,consumption,cv))
                    break
            best=select(candidates,self.cfg['load_weight'])
            c._update_pheromone(inner_state)
            if best:
                amount=self.params.Q/best[0]*elite_scale
                for source,target in zip(best[1],best[1][1:]):
                    c.pheromone[source][target]=min(c.pheromone[source][target]+amount,self.params.tau_max)
                total_elite_mass+=(len(best[1])-1)*amount*decay**(m-batch-1)
        if candidates:
            low,high=min(x[0] for x in candidates),max(x[0] for x in candidates)
            c.lower_cost=low if c.lower_cost is None else min(c.lower_cost,low)
            c.upper_cost=high if c.upper_cost is None else max(c.upper_cost,high)
        best=select(candidates,self.cfg['load_weight'])
        c.previous_cost=best[0] if best else None
        self.last_metrics=dict(feasible=len(candidates),elite_surviving_mass=total_elite_mass,
            ant_surviving_mass=total_ant_mass,elite_fraction=total_elite_mass/max(total_elite_mass+total_ant_mass,1e-30))
        return (best[2],best[3]) if best else (None,{})


def checkpoint(network,completed):
    folder=ROOT/'plans/phase5-acaco-chaos/long'
    if completed==600:
        return json.loads((folder/'calibrated_x1_seed6_round600.json').read_text())
    # Reproduce nine rounds from an exact saved state to the first death.
    state=json.loads((folder/'calibrated_x1_seed6_round1501.json').read_text())
    saved=restore(state,network)
    a=ExperimentalACACO(network,CONFIGS['baseline'],saved.params)
    for key in ('iteration','pheromone','chaos','previous_cost','lower_cost','upper_cost'):
        setattr(a.clustering,key,getattr(saved.clustering,key))
    a.clustering.rng.setstate(saved.clustering.rng.getstate())
    residual=state['residual']
    live=state['live']
    prior=json.loads((folder/'calibrated_x1_seed6.json').read_text())
    with redirect_stdout(StringIO()):
        for t in range(1501,1510):
            root,costs=a.plan_round(live,residual)
            assert root is not None
            assert sum(costs.values())==prior['records'][t]['energy_J']
            residual=[max(0.,e-costs.get(i,0.)) for i,e in enumerate(residual)]
            live=[i for i in live if residual[i]>0]
    assert len(live)==99 and 33 not in live
    return snapshot(a,residual,live,1510)


def measure(network,cfg,seed,rounds,state=None):
    params=ACACOParameters(**state['parameters']) if state else ACACOParameters(energy_cost_exponent=1.,elite_weight=1.,load_weight=0.)
    a=ExperimentalACACO(network,cfg,params,seed)
    if state:
        saved=restore(state,network).clustering
        for key in ('iteration','pheromone','chaos','previous_cost','lower_cost','upper_cost'):
            setattr(a.clustering,key,getattr(saved,key))
        a.clustering.rng.seed(seed)
    residual=state['residual'].copy() if state else [network.init_energy]*network.N
    live=state['live'].copy() if state else list(range(network.N))
    evaluator=Evaluator(HyperParameters())
    records=[]
    for t in range(rounds):
        before=residual.copy()
        attempts=a.total_routing_attempts
        start=process_time()
        root,costs=a.plan_round(live,residual)
        cpu=process_time()-start
        assert before==residual
        if root is None:
            records.append(dict(failed=True,round=t,cpu_s=cpu))
            break
        checked,total=evaluator.energy_consumption(root,network.dist_matrix,network.base_dists)
        assert checked==costs and set(costs)==set(live)
        loads=np.asarray([costs[i] for i in live])
        risks=np.asarray([costs[i]/residual[i] for i in live])
        tau=np.asarray(a.clustering.pheromone)
        assert np.isfinite(tau).all() and tau.min()>=params.tau_min and tau.max()<=params.tau_max
        records.append(dict(round=t,failed=False,energy_J=total,cpu_s=cpu,
            load_cv=float(loads.std()/loads.mean()),peak_relative_depletion=float(risks.max()),
            attempts=a.total_routing_attempts-attempts,**a.last_metrics))
        if state is None:
            residual=[max(0.,e-costs.get(i,0.)) for i,e in enumerate(residual)]
            live=[i for i in live if residual[i]>0]
    valid=[r for r in records if not r['failed']]
    return dict(config=cfg,seed=seed,parameters=asdict(params),records=records,
        completed=len(valid),energy_J=sum(r['energy_J'] for r in valid),
        cpu_s=sum(r['cpu_s'] for r in records),alive=len(live),
        min_residual=min(residual[i] for i in live),critical_residual={str(i):residual[i] for i in (33,65)})


def main():
    mode=sys.argv[1]
    seed=int(sys.argv[2])
    network=NetworkInstance.from_pickle(ROOT/'map.pkl')
    folder=Path(sys.argv[3]) if len(sys.argv)>3 else FOLDER/'results'
    folder.mkdir(parents=True,exist_ok=True)
    meta=dict(configs=CONFIGS,validation=list(VALIDATION),validation_rounds=300,
        live_validation_rounds=150,live_validation=['baseline',*LIVE_VALIDATION],
        source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*.py'))},
        map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest(),script_sha=sha256(Path(__file__).read_bytes()).hexdigest())
    metadata_path=folder/f'metadata_{mode}_{seed}.json'
    if metadata_path.exists():
        prior=json.loads(metadata_path.read_text())
        if prior!=meta:
            raise ValueError('Existing results have different provenance; pass a fresh output directory as argument 3')
    else:
        metadata_path.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    live_mode=mode.startswith('live_')
    contexts=(600,1510) if mode.endswith('screen') else (None,)
    for context in contexts:
        state=checkpoint(network,context) if context else None
        if live_mode:
            names=['baseline',*LIVE_VALIDATION]
        else:
            names=[n for n in CONFIGS if not n.startswith('live_')] if mode=='screen' else list(VALIDATION)
        names=names[seed%len(names):]+names[:seed%len(names)]
        for name in names:
            path=folder/f'{mode}_{context}_{name}_seed{seed}.json'
            if path.exists():
                continue
            row=measure(network,CONFIGS[name],seed,12 if state else (150 if live_mode else 300),state)
            path.write_text(json.dumps(row,indent=2),encoding='utf-8')
            print(mode,context,name,seed,'energy',row['energy_J'],'CPU',row['cpu_s'],flush=True)


if __name__=='__main__':
    main()
