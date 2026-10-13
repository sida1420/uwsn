"""Common physical runner. Adapter owns native search; runner deducts chosen tree only."""
from contextlib import redirect_stdout,contextmanager
from io import StringIO
from pathlib import Path
import csv,gzip,os,random,time
import numpy as np
from optimizer.storage import atomic,read,lock,unpickle
from optimizer.diagnostics import observe as native_observe,tree_metrics,reachable,owner_alive
from optimizer.adapters import get
from optimizer.provenance import EpochGuard
from optimizer.reference import energy_prefix
from network import NetworkInstance
from hparameter import HyperParameters

@contextmanager
def observe(a):
    with native_observe(a) as counters:
        source=getattr(a.clustering,'rng',a.random_source)
        local_choices=None
        if source is not random:
            local_choices=source.choices
            def choices(population,weights=None,**kwargs):
                if weights is not None:
                    total=sum(weights);probabilities=[w/total for w in weights if w>0]
                    counters['choices']+=1
                    counters['entropy_sum']-=sum(p*np.log(p) for p in probabilities)
                return local_choices(population,weights=weights,**kwargs)
            source.choices=choices
        counters.update(n_feasible_ants=0,n_selected_CH=0,n_rewarded_items=0,
                        elite_reward_raw=0.,per_ant_reward_raw=0.,post_clamp_actual_delta=0.,
                        score_raw=None,score_normalized=None)
        original=None
        if hasattr(a,'references'):
            original=a.clustering.deposit
            def deposit(chs,fitness,reference,per_ant=True):
                if not chs or fitness is None or fitness<=0:
                    return original(chs,fitness,reference,per_ant)
                amount=a.params.Q*reference/fitness if fitness and fitness>0 else 0.
                amount=amount/a.params.num_ants if per_ant else amount*a.params.theta
                before=sum(a.clustering.pheromone[node] for node in chs)
                result=original(chs,fitness,reference,per_ant)
                counters['post_clamp_actual_delta']+=sum(a.clustering.pheromone[node] for node in chs)-before
                counters['n_rewarded_items']+=len(chs)
                if per_ant:
                    counters['n_feasible_ants']+=1;counters['per_ant_reward_raw']+=amount*len(chs)
                else:
                    counters['n_selected_CH']=len(chs);counters['elite_reward_raw']+=amount*len(chs)
                    counters['score_raw']=fitness;counters['score_normalized']=fitness/reference
                return result
            a.clustering.deposit=deposit
        try: yield counters
        finally:
            if original is not None: a.clustering.deposit=original
            if local_choices is not None: del source.choices

def run_seed(cfg,requested,seed,folder,epoch,kind='daco',owner=None,pause_after=None,energy_window=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    adapter=get(kind);effective=adapter.effective_config(requested)
    window=cfg['energy_window'] if energy_window is None else energy_window
    if type(window) is not int or not 1<=window<=cfg['horizon']: raise ValueError('Invalid resolved energy window')
    identity=dict(epoch=epoch,config=cfg,requested=requested,effective=effective,seed=seed,kind=kind,energy_window=window,
                  adapter_version=adapter.adapter_version,native_fitness_id=adapter.native_fitness_id)
    guard=EpochGuard(cfg,epoch)
    with lock(folder/'seed.lock'):
        if (folder/'metrics.json').exists():
            result=read(folder/'metrics.json')
            if result['identity']!=identity: raise ValueError('Cached identity mismatch')
            return result
        if (folder/'checkpoint.pkl').exists():
            state=unpickle(folder/'checkpoint.pkl')
            if state['identity']!=identity: raise ValueError('Checkpoint identity mismatch')
            random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
        else:
            random.seed(seed);np.random.seed(seed)
            network=NetworkInstance.from_pickle(cfg['map']);h=HyperParameters();h.T_max=cfg['adaptive_total_rounds']
            a=adapter.make_algorithm(network,h,effective,seed)
            state=dict(identity=identity,algorithm=a,live=list(range(network.N)),residual=[network.init_energy]*network.N,
                       records=[],FND=None,HND=None,LND=None,cpu=0.,wall=0.,calibration_cpu=0.,evaluations=0)
        a=state['algorithm'];network=a.network;c0=time.process_time();w0=time.monotonic();reason='horizon'
        def save():
            nonlocal c0,w0
            guard.check();state['cpu']+=time.process_time()-c0;state['wall']+=time.monotonic()-w0
            c0=time.process_time();w0=time.monotonic()
            state['python_rng']=random.getstate();state['numpy_rng']=np.random.get_state()
            atomic(folder/'checkpoint.pkl',state,binary=True)
            atomic(folder/'progress.json',dict(seed=seed,round=len(state['records']),alive=len(state['live']),cpu=state['cpu'],wall=state['wall']))
        while len(state['records'])<cfg['horizon']:
            if not owner_alive(folder.parents[2],owner) or (pause_after is not None and len(state['records'])>=pause_after):
                save();return dict(paused=True,seed=seed)
            round_start=time.perf_counter()
            live=state['live'];before=len(live)
            if hasattr(a,'calibrate') and a.references is None:
                cal=time.process_time()
                with redirect_stdout(StringIO()),observe(a) as observed: ok=a.calibrate(live,state['residual'])
                state['evaluations']+=observed['evaluations'];state['calibration_cpu']+=time.process_time()-cal
                if not ok: reason='no_feasible_calibration';break
            with redirect_stdout(StringIO()),observe(a) as observed: root,costs=a.plan_round(live,state['residual'])
            state['evaluations']+=observed['evaluations']
            if root is None: reason='no_feasible_tree_found';break
            if set(costs)!=set(live) or any(not np.isfinite(v) or v<0 for v in costs.values()) or sum(costs.values())<=0:
                raise ValueError('Invalid full-service selected energy')
            groups=tree_metrics(root,costs)
            for i,e in costs.items(): state['residual'][i]=max(0.,state['residual'][i]-e)
            state['live']=[i for i in live if state['residual'][i]>0];t=len(state['records'])+1
            if len(state['live'])<before and state['FND'] is None: state['FND']=t
            if len(state['live'])<=network.N/2 and state['HND'] is None: state['HND']=t
            if not state['live']: state['LND']=t;reason='all_nodes_dead'
            row=dict(round=t,time=time.perf_counter()-round_start,alive_before=before,alive_after=len(state['live']),served=len(costs),
                     selected_tree_physical_energy=sum(costs.values()),cost_groups=groups,
                     evaluations=observed['evaluations'],deposit_updates=observed['updates'],
                     requested_deposit=observed['requested'],lost_deposit=observed['lost'],
                     transition_entropy=observed['entropy_sum']/observed['choices'] if observed['choices'] else None,
                     n_live=before,n_feasible_ants=observed['n_feasible_ants'],n_selected_CH=observed['n_selected_CH'],
                     n_rewarded_items=observed['n_rewarded_items'],score_raw=observed['score_raw'],score_normalized=observed['score_normalized'],
                     elite_reward_raw=observed['elite_reward_raw'],per_ant_reward_raw=observed['per_ant_reward_raw'],
                     elite_to_ant_deposit_ratio=observed['elite_reward_raw']/observed['per_ant_reward_raw'] if observed['per_ant_reward_raw'] else None,
                     post_clamp_actual_delta=observed['post_clamp_actual_delta'],
                     diagnostics=adapter.diagnostics(a))
            state['records'].append(row)
            if t%cfg['checkpoint_every']==0: save()
            if not state['live']: break
        save();guard.check(force=True);records=state['records'];K=window
        curve=energy_prefix(records,network.N)
        comparable=len(records)>=K and all(r['alive_before']==r['alive_after']==r['served']==network.N for r in records[:K])
        seen,disconnected=reachable(network,state['live'])
        result=dict(identity=identity,seed=seed,completed_rounds=len(records),FND=state['FND'],HND=state['HND'],LND=state['LND'],
                    energy_status='comparable' if comparable else 'not_comparable',energy_window=K,
                    initial_nodes=network.N,all_alive_energy_prefix=curve,
                    energy_K=sum(r['selected_tree_physical_energy'] for r in records[:K]) if comparable else None,
                    termination_reason=reason,horizon_censored=reason=='horizon',residual=state['residual'],alive=state['live'],
                    cpu=state['cpu'],wall=state['wall'],calibration_cpu=state['calibration_cpu'],
                    clustering_attempts=a.total_clustering_attempts,routing_attempts=a.total_routing_attempts,
                    calibration_attempts=getattr(a,'calibration_attempts',0),feasible_evaluations=state['evaluations'],
                    reachable_survivors=seen,disconnected_survivors=disconnected)
        with gzip.open(folder/'rounds.csv.gz','wt',newline='',encoding='utf-8') as f:
            if records:
                writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        atomic(folder/'metrics.json',result);return result

def worker(study,job,token):
    import traceback
    study=Path(study);folder=study/'trials'/str(job['number'])
    try:
        cfg=read(study/'config.json');epoch=read(study/'provenance.json');runs=[]
        window=cfg['energy_window'] if job['kind']=='simple' else read(study/'reference.json')['energy_window']
        for seed in cfg['training_seeds']:
            atomic(folder/'current_seed.json',dict(seed=seed,started=time.time()))
            result=run_seed(cfg,job['parameters'],seed,folder/str(seed),epoch,kind=job['kind'],owner=token,energy_window=window)
            if result.get('paused'): atomic(folder/'outcome.json',dict(status='paused'));return
            runs.append(result)
        atomic(folder/'outcome.json',dict(status='complete',runs=runs))
    except BaseException as exc: atomic(folder/'outcome.json',dict(status='failed',error=repr(exc),traceback=traceback.format_exc()))
