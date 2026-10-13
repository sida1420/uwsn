"""Isolated physical trajectories with full algorithm/RNG checkpoints."""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from io import StringIO
import csv
import gzip
import math
import os
from pathlib import Path
import random
import time
import numpy as np
import psutil
from optimizer.storage import atomic, read, lock, unpickle,fingerprint
from algorithms.d_aco import DACO
from algorithms.aco import SimpleACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering.aco.parameters import ACOParameters
from network import NetworkInstance
from hparameter import HyperParameters

@contextmanager
def observe(algorithm):
    """Observers restore every method before checkpointing; no RNG calls added."""
    counters=dict(evaluations=0,choices=0,entropy_sum=0.,updates=0,clipped=0,
                  requested=0.,lost=0.,repeated_ch_sets=0)
    originals=[];sets=set()
    def wrap(obj,name,factory):
        original=getattr(obj,name);originals.append((obj,name))
        setattr(obj,name,factory(original))
    def energy(original):
        def run(*args,**kwargs):
            result=original(*args,**kwargs);counters['evaluations']+=1;return result
        return run
    def clusters(original):
        def run(*args,**kwargs):
            result=original(*args,**kwargs)
            if result and result[0] is not None:
                key=tuple(sorted(result[0]));counters['repeated_ch_sets']+=int(key in sets);sets.add(key)
            return result
        return run
    def deposit(original):
        def run(chs,fitness,energy_reference,per_ant=True):
            if chs and fitness is not None and fitness>0:
                p=algorithm.params;amount=p.Q*energy_reference/fitness
                amount=amount/p.num_ants if per_ant else amount*p.theta
                for node in chs:
                    lost=max(0.,algorithm.clustering.pheromone[node]+amount-p.tau_max)
                    counters['updates']+=1;counters['clipped']+=int(lost>1e-12)
                    counters['requested']+=amount;counters['lost']+=lost
            return original(chs,fitness,energy_reference,per_ant)
        return run
    original_choices=random.choices
    def choices(population,weights=None,**kwargs):
        if weights is not None:
            total=sum(weights)
            probs=[w/total for w in weights if w>0]
            counters['choices']+=1;counters['entropy_sum']-=sum(p*math.log(p) for p in probs)
        return original_choices(population,weights=weights,**kwargs)
    wrap(algorithm.evaluator,'energy_consumption',energy)
    wrap(algorithm.clustering,'create_clusters',clusters)
    if isinstance(algorithm,DACO): wrap(algorithm.clustering,'deposit',deposit)
    random.choices=choices
    try: yield counters
    finally:
        random.choices=original_choices
        for obj,name in originals: delattr(obj,name)

def owner_alive(folder,token):
    if token is None: return True
    if (folder/'STOP').exists(): return False
    try:
        owner=read(folder/'owner.json')
        process=psutil.Process(owner['pid'])
        return owner['token']==token and process.create_time()==owner['created'] and process.is_running() and process.status()!=psutil.STATUS_ZOMBIE
    except (OSError,ValueError,psutil.Error): return False

def tree_metrics(root,costs):
    ids=set();groups=dict(CH=0.,relay=0.,member=0.);stack=[root]
    while stack:
        node=stack.pop();stack.extend(node.nxts)
        if node.id==-1: continue
        if node.id in ids: raise ValueError('Duplicate node in selected tree')
        ids.add(node.id);groups['CH' if node.isCH else 'relay' if node.isRelay else 'member']+=costs[node.id]
    if ids!=set(costs): raise ValueError('Selected tree does not cover consumption nodes')
    return groups

def reachable(network,live):
    """Certificate only for survivors disconnected in the physical radius graph."""
    remaining=set(live);seen={i for i in live if network.base_dists[i]<=network.radius};queue=list(seen)
    while queue:
        i=queue.pop()
        adjacent={j for j in remaining-seen if network.dist_matrix[i][j]<=network.radius}
        seen.update(adjacent);queue.extend(adjacent)
    return sorted(seen),sorted(remaining-seen)

def run_seed(cfg,params,seed,folder,epoch,kind='daco',owner=None,pause_after=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    identity=dict(epoch=epoch,config=cfg,parameters=params,seed=seed,kind=kind)
    with lock(folder/'seed.lock'):
        if fingerprint(cfg)!=epoch: raise RuntimeError('Source/map/config changed before seed start')
        if (folder/'metrics.json').exists():
            result=read(folder/'metrics.json')
            if result['identity']!=identity: raise ValueError('Cached seed identity mismatch')
            return result
        checkpoint=folder/'checkpoint.pkl'
        if checkpoint.exists():
            state=unpickle(checkpoint)
            if state['identity']!=identity: raise ValueError('Checkpoint identity mismatch')
            algorithm=state['algorithm'];network=algorithm.network
            random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
        else:
            random.seed(seed);np.random.seed(seed)
            network=NetworkInstance.from_pickle(cfg['map'])
            if kind=='daco': algorithm=DACO(network,HyperParameters(),DACOParameters(**params))
            else:
                p=ACOParameters();p.beta=p.gamma=0.
                algorithm=SimpleACO(network,HyperParameters(),p)
            state=dict(identity=identity,algorithm=algorithm,live=list(range(network.N)),
                residual=[network.init_energy]*network.N,records=[],FND=None,HND=None,LND=None,
                cpu=0.,wall=0.,feasible_evaluations=0,energy=0.,calibration_cpu=0.)
        cpu_start=time.process_time();wall_start=time.monotonic();reason='horizon'
        def save():
            nonlocal cpu_start,wall_start
            if fingerprint(cfg)!=epoch: raise RuntimeError('Source/map/config changed during trajectory')
            state['cpu']+=time.process_time()-cpu_start;state['wall']+=time.monotonic()-wall_start
            cpu_start=time.process_time();wall_start=time.monotonic()
            state['python_rng']=random.getstate();state['numpy_rng']=np.random.get_state()
            atomic(checkpoint,state,binary=True)
            atomic(folder/'progress.json',dict(seed=seed,round=len(state['records']),alive=len(state['live']),
                cpu=state['cpu'],wall=state['wall'],rss_mb=psutil.Process().memory_info().rss/(1024**2)))
        while len(state['records'])<cfg['horizon']:
            if not owner_alive(folder.parents[2],owner) or (pause_after is not None and len(state['records'])>=pause_after):
                save();return dict(paused=True,seed=seed)
            if psutil.Process().memory_info().rss>cfg['worker_memory_mb']*1024**2:
                save();raise MemoryError('Worker memory budget exceeded')
            live=state['live'];residual=state['residual'];before=len(live)
            counters_before=algorithm.total_clustering_attempts
            routing_before=algorithm.total_routing_attempts
            c0=time.process_time()
            if isinstance(algorithm,DACO) and algorithm.references is None:
                with redirect_stdout(StringIO()),observe(algorithm) as calibration:
                    ok=algorithm.calibrate(live,residual)
                state['calibration_cpu']+=time.process_time()-c0
                state['feasible_evaluations']+=calibration['evaluations']
                if not ok: reason='no_feasible_calibration';break
                c0=time.process_time()
            w0=time.monotonic()
            with redirect_stdout(StringIO()),observe(algorithm) as counters:
                root,costs=algorithm.plan_round(live,residual)
            state['feasible_evaluations']+=counters['evaluations']
            if root is None: reason='no_feasible_tree_found';break
            if set(costs)!=set(live) or any(not math.isfinite(v) or v<0 for v in costs.values()) or sum(costs.values())<=0:
                raise ValueError('Invalid full-service physical energy')
            groups=tree_metrics(root,costs)
            risk=max(costs[i]/residual[i] for i in live)
            hottest=max(costs,key=costs.get)
            for i,cost in costs.items(): residual[i]=max(0.,residual[i]-cost)
            state['live']=[i for i in live if residual[i]>0]
            t=len(state['records'])+1
            if len(state['live'])<before and state['FND'] is None: state['FND']=t
            if len(state['live'])<=network.N/2 and state['HND'] is None: state['HND']=t
            if not state['live']: state['LND']=t;reason='all_nodes_dead'
            state['energy']+=sum(costs.values())
            values=np.asarray(residual);tau=np.asarray(algorithm.clustering.pheromone)
            if tau.ndim==1: tau=tau[live]
            else: tau=tau[np.ix_(live,live)]
            row=dict(round=t,alive_before=before,alive_after=len(state['live']),served=len(costs),
                service_success=True,selected_tree_physical_energy=sum(costs.values()),
                total_energy=state['energy'],energy_per_served_sensor_round=sum(costs.values())/len(costs),
                residual_sum=float(values.sum()),residual_min=float(values.min()),residual_std=float(values.std()),
                residual_quantiles=np.quantile(values,[.1,.5,.9]).tolist(),peak_relative_depletion=risk,
                hottest_node=hottest,hottest_node_energy=costs[hottest],cost_groups=groups,
                clustering_attempts=algorithm.total_clustering_attempts-counters_before,
                routing_attempts=algorithm.total_routing_attempts-routing_before,
                feasible_evaluations=counters['evaluations'],repeated_ch_sets=counters['repeated_ch_sets'],
                tau_cap_fraction=float(np.mean(tau>=algorithm.params.tau_max-1e-12)),
                tau_min=float(tau.min()),tau_max=float(tau.max()),deposit_updates=counters['updates'],
                clipped_updates=counters['clipped'],lost_deposit_mass=counters['lost'],requested_deposit_mass=counters['requested'],
                mean_choice_entropy=counters['entropy_sum']/counters['choices'] if counters['choices'] else None,
                cpu=time.process_time()-c0,wall=time.monotonic()-w0)
            state['records'].append(row)
            if t%cfg['checkpoint_every']==0: save()
            if not state['live']: break
        save()
        records=state['records'];K=cfg['energy_window']
        comparable=len(records)>=K and all(r['alive_before']==network.N and r['alive_after']==network.N and r['served']==network.N for r in records[:K])
        reached,disconnected=reachable(network,state['live'])
        result=dict(identity=identity,seed=seed,parameters=params,kind=kind,completed_rounds=len(records),
            FND=state['FND'],HND=state['HND'],LND=state['LND'],termination_reason=reason,
            horizon_censored=reason=='horizon',energy_status='comparable' if comparable else 'not_comparable',
            energy_K=sum(r['selected_tree_physical_energy'] for r in records[:K]) if comparable else None,
            cpu=state['cpu'],wall=state['wall'],calibration_cpu=state['calibration_cpu'],
            clustering_attempts=algorithm.total_clustering_attempts,routing_attempts=algorithm.total_routing_attempts,
            calibration_attempts=getattr(algorithm,'calibration_attempts',0),
            feasible_evaluations=state['feasible_evaluations'],residual=state['residual'],alive=state['live'],
            reachable_survivors=reached,disconnected_survivors=disconnected,
            memory_peak_mb=psutil.Process().memory_info().peak_wset/(1024**2) if os.name=='nt' else None)
        tmp=folder/'rounds.csv.gz.tmp'
        with gzip.open(tmp,'wt',encoding='utf-8',newline='') as f:
            if records:
                writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        os.replace(tmp,folder/'rounds.csv.gz')
        atomic(folder/'metrics.json',result)
        return result

def worker(study,job,token):
    """Spawn target: one cohort sequentially, no nested process pool or DB writes."""
    import traceback
    study=Path(study);folder=study/'trials'/str(job['number'])
    try:
        cfg=read(study/'config.json');epoch=read(study/'provenance.json')
        results=[]
        for seed in cfg['training_seeds']:
            atomic(folder/'current_seed.json',dict(seed=seed,started=time.time()))
            result=run_seed(cfg,job['parameters'],seed,folder/str(seed),epoch,kind=job.get('kind','daco'),owner=token)
            if result.get('paused'):
                atomic(folder/'outcome.json',dict(status='paused'));return
            results.append(result)
        atomic(folder/'outcome.json',dict(status='complete',runs=results))
    except BaseException as exc:
        atomic(folder/'outcome.json',dict(status='failed',error=repr(exc),traceback=traceback.format_exc()))
