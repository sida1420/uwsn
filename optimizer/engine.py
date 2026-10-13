"""Generic constrained search with a cumulative active-time deadline."""
import multiprocessing as mp
from pathlib import Path
import os,time,uuid
import optuna,psutil
from optimizer import PACKAGE
from optimizer.storage import atomic,read,lock,unpickle,disk_mb
from optimizer.metrics import aggregate,constraints
from optimizer.reference import from_runs,ReferenceUnavailable
from optimizer.provenance import epoch,assert_campaign,EpochGuard
from optimizer.adapters import get
from optimizer.trajectory import worker

DEFAULT=dict(algorithm='daco',mode='scientific',study_role='training',horizon=3500,adaptive_total_rounds=3500,
             energy_window=2611,energy_window_policy='reference',reference_window_fraction=.9,
             energy_allowance=.02,training_seeds=[24,25,26],budget_seconds=5400,
             max_trials=32,max_workers=2,checkpoint_every=25,max_disk_mb=4096,worker_memory_mb=1024,
             startup_trials=6,sampler_seed=20261013,max_retries=1)

def same_process(pid,created):
    try: return psutil.Process(pid).create_time()==created
    except psutil.Error: return False

def initialize(config,folder,legacy):
    import yaml
    from optimizer import ROOT
    raw=yaml.safe_load(Path(config).read_text()) or {}
    raw.pop('shutdown_reserve_seconds',None)  # legacy hard-deadline field
    cfg={**DEFAULT,**raw}
    if set(cfg)-set(DEFAULT)-{'map'}: raise ValueError('Unknown config fields')
    if cfg['algorithm']!='daco': raise ValueError('Only D-ACO tuning is authorized; other adapters are smoke-only')
    for name in ('horizon','adaptive_total_rounds','energy_window','budget_seconds','max_trials','max_workers','checkpoint_every','max_disk_mb','worker_memory_mb','startup_trials'):
        if type(cfg[name]) is not int or cfg[name]<1: raise ValueError(f'Invalid {name}')
    if cfg['mode'] not in ('smoke','scientific') or cfg['study_role']!='training': raise ValueError('Invalid study mode/role')
    if cfg['max_retries'] not in (0,1): raise ValueError('At most one retry')
    if cfg['energy_window']>cfg['horizon']: raise ValueError('Energy window exceeds horizon')
    if cfg['energy_window_policy'] not in ('reference','fixed'): raise ValueError('Invalid energy window policy')
    if type(cfg['reference_window_fraction']) not in (int,float) or not 0<cfg['reference_window_fraction']<=1: raise ValueError('Invalid reference window fraction')
    if not cfg['training_seeds'] or any(type(s) is not int or s<0 for s in cfg['training_seeds']): raise ValueError('Invalid seeds')
    if not 0<cfg['budget_seconds']<=5400 or not 1<=cfg['max_workers']<=4: raise ValueError('Invalid campaign budget/concurrency')
    if cfg['mode']=='scientific' and (cfg['horizon'],cfg['adaptive_total_rounds'])!=(3500,3500):
        raise ValueError('Scientific tuning requires H=T_max=3500')
    if cfg['mode']=='smoke' and (cfg['horizon']>10 or cfg['max_trials']>3): raise ValueError('Smoke bounds exceeded')
    if cfg['energy_allowance']!=.02: raise ValueError('Energy policy is fixed')
    if len(set(cfg['training_seeds']))!=len(cfg['training_seeds']): raise ValueError('Duplicate seeds')
    cfg['map']=str((ROOT/cfg.get('map','map.pkl')).resolve())
    from network import NetworkInstance
    from optimizer.diagnostics import reachable
    network=NetworkInstance.from_pickle(cfg['map'])
    if network.N<1: raise ValueError('Map has no sensors')
    _,disconnected=reachable(network,list(range(network.N)))
    if disconnected: raise ValueError(f'Map cannot initially serve all sensors; disconnected nodes: {disconnected}')
    folder=Path(folder).resolve()
    if not folder.is_relative_to(PACKAGE) or folder.exists(): raise ValueError('Choose a new directory under optimizer/')
    folder.mkdir(parents=True)
    # Freeze the exact bytes used for preflight; rerandomizing the source map is safe.
    import shutil
    shutil.copyfile(cfg['map'],folder/'map.pkl');cfg['map']=str(folder/'map.pkl')
    atomic(folder/'config.json',cfg);atomic(folder/'provenance.json',epoch(cfg))
    atomic(folder/'state.json',dict(spent_wall=0.,jobs={},stop_reason='not_started',next_number=0))
    from optimizer.audit import compatibility
    priorities=compatibility(legacy,folder,cfg)
    atomic(folder/'anchors.json',priorities)
    return str(folder)

def open_study(folder,cfg):
    sampler=unpickle(folder/'sampler.pkl') if (folder/'sampler.pkl').exists() else optuna.samplers.TPESampler(
        seed=cfg['sampler_seed'],n_startup_trials=cfg['startup_trials'],multivariate=True,constant_liar=True,constraints_func=constraints)
    storage=optuna.storages.RDBStorage('sqlite:///'+(folder/'study.db').as_posix(),engine_kwargs={'connect_args':{'timeout':30}})
    study=optuna.create_study(study_name='service3500',storage=storage,sampler=sampler,direction='maximize',load_if_exists=True)
    return study,storage

def run(folder,workers=None):
    folder=Path(folder).resolve();cfg=assert_campaign(folder)
    worker_limit=cfg['max_workers'] if workers is None else workers
    if type(worker_limit) is not int or not 1<=worker_limit<=4: raise ValueError('Optimizer supports 1-4 isolated workers')
    with lock(folder/'controller.lock'):
        state=read(folder/'state.json');start=time.monotonic();spent=state['spent_wall'];active={}
        token=uuid.uuid4().hex;atomic(folder/'owner.json',dict(token=token,pid=os.getpid(),created=psutil.Process().create_time()))
        atomic(folder/'launch-runtime.json',dict(workers=worker_limit,session_limit_disabled=True,started=time.time()))
        (folder/'STOP').unlink(missing_ok=True)
        study,storage=open_study(folder,cfg);guard=EpochGuard(cfg,read(folder/'provenance.json'))
        for job in state['jobs'].values():
            if job.get('pid'):
                if same_process(job['pid'],job['created']): psutil.Process(job['pid']).wait(timeout=15)
            if job['status']=='running': job['status']='paused';job.pop('pid',None)
        for trial in study.get_trials(deepcopy=False):
            if trial.state==optuna.trial.TrialState.RUNNING and str(trial.number) not in state['jobs']:
                study.tell(trial.number,state=optuna.trial.TrialState.FAIL)
            if trial.state==optuna.trial.TrialState.COMPLETE and str(trial.number) in state['jobs']:
                state['jobs'][str(trial.number)]['status']='complete'
        state['stop_reason']='running'
        state.pop('error',None)
        def persist(sampler=False):
            state['spent_wall']=spent+time.monotonic()-start;atomic(folder/'state.json',state)
            if sampler: atomic(folder/'sampler.pkl',study.sampler,binary=True)
        context=mp.get_context('spawn');last_save=0.;reason=None
        draining=bool(state.get('drain_trials'))
        try:
            while True:
                elapsed=spent+time.monotonic()-start
                remaining=cfg['budget_seconds']-elapsed
                if (folder/'STOP').exists(): reason=reason or 'operator_stop'
                if remaining<=0 and not draining:
                    draining=True;state['drain_trials']=list(active)
                if draining: state['stop_reason']='finishing_active_trials'
                if disk_mb(folder)>=cfg['max_disk_mb']*.9: reason=reason or 'disk_budget'
                for key,process in list(active.items()):
                    if process.is_alive():
                        try:
                            if psutil.Process(process.pid).memory_info().rss>cfg['worker_memory_mb']*1024**2: process.terminate()
                        except psutil.Error: pass
                        continue
                    process.join();del active[key];job=state['jobs'][key];job.pop('pid',None)
                    out=folder/'trials'/key/'outcome.json'
                    result=read(out) if out.exists() else dict(status='failed',error='worker exited without outcome')
                    if result['status']=='complete':
                        if key=='reference':
                            try: reference=from_runs(result['runs'],cfg)
                            except ReferenceUnavailable as exc:
                                job.update(status='not_comparable',error=str(exc))
                                state['error']=str(exc);reason='reference_not_comparable'
                                atomic(folder/'reference-error.json',dict(reason=reason,message=str(exc),energy_window=cfg['energy_window'],
                                    seeds=[{k:r.get(k) for k in ('seed','FND','completed_rounds','energy_status','termination_reason')} for r in result['runs']]))
                                persist();continue
                            atomic(folder/'reference.json',reference)
                        else:
                            metrics=aggregate(result['runs'],read(folder/'reference.json'),cfg)
                            atomic(folder/'trials'/key/'aggregate.json',metrics)
                            trial=optuna.trial.Trial(study,study.get_trials(deepcopy=False)[int(key)]._trial_id)
                            for k,v in metrics.items(): trial.set_user_attr(k,v)
                            trial.set_user_attr('parameters_effective',job['parameters'])
                            study.tell(int(key),metrics['mean_service_capped'])
                        job['status']='complete';persist(sampler=True)
                    elif result['status']=='paused': job['status']='paused'
                    else:
                        job['failures']=job.get('failures',0)+1;job['error']=result
                        job['status']='paused' if job['failures']<=cfg['max_retries'] else 'failed'
                        if job['status']=='failed':
                            if key=='reference': reason='reference_failure'
                            else: study.tell(int(key),state=optuna.trial.TrialState.FAIL)
                    persist()
                if reason:
                    (folder/'STOP').touch();break
                if not (folder/'reference.json').exists() and 'reference' not in state['jobs']:
                    state['jobs']['reference']=dict(number='reference',kind='simple',parameters={},status='paused')
                reference_ready=(folder/'reference.json').exists()
                pending=[(k,j) for k,j in state['jobs'].items() if j['status']=='paused' and k not in active
                         and (not draining or k in state['drain_trials'])]
                if draining and not active and not pending:
                    reason='budget_closed_active_finished';break
                if not draining and not pending and reference_ready and len(study.trials)<cfg['max_trials'] and len(active)<worker_limit:
                    priorities=read(folder/'anchors.json');number=len(study.trials)
                    waiting=any(t.state==optuna.trial.TrialState.WAITING for t in study.get_trials(deepcopy=False))
                    if number<len(priorities) and not waiting: study.enqueue_trial({k:priorities[number][k] for k in get(cfg['algorithm']).space},skip_if_exists=True)
                    trial=study.ask()
                    try: parameters=get(cfg['algorithm']).suggest(trial)
                    except ValueError: study.tell(trial.number,state=optuna.trial.TrialState.FAIL);persist(sampler=True);continue
                    origin='reused_anchor' if trial.system_attrs.get('fixed_params') else 'sampler_proposal'
                    state['jobs'][str(trial.number)]=dict(number=trial.number,kind=cfg['algorithm'],parameters=parameters,status='paused',parameter_origin=origin)
                    persist(sampler=True);continue
                for key,job in pending:
                    if len(active)>=worker_limit: break
                    if key!='reference' and not reference_ready: continue
                    guard.check();out=folder/'trials'/key/'outcome.json';out.unlink(missing_ok=True)
                    process=context.Process(target=worker,args=(str(folder),job,token));process.start()
                    active[key]=process;job.update(status='running',pid=process.pid,created=psutil.Process(process.pid).create_time());persist()
                if reference_ready and len(study.trials)>=cfg['max_trials'] and not active and not any(j['status']=='paused' for j in state['jobs'].values()):
                    reason='trial_budget';break
                if time.monotonic()-last_save>=2: guard.check();persist();last_save=time.monotonic()
                time.sleep(.5)
        except KeyboardInterrupt: reason='operator_stop'
        except Exception as exc:
            reason='controller_error';state['error']=f'{type(exc).__name__}: {exc}'
            for key,job in state['jobs'].items():
                if job['status']=='running' and key not in active:
                    job.update(status='failed',error=state['error']);job.pop('pid',None)
            raise
        finally:
            (folder/'STOP').touch();deadline=time.monotonic()+min(15,max(0,cfg['budget_seconds']-(spent+time.monotonic()-start)))
            for key,p in active.items():
                p.join(timeout=max(0,deadline-time.monotonic()))
                if p.is_alive(): p.terminate();p.join(timeout=2)
                state['jobs'][key]['status']='paused';state['jobs'][key].pop('pid',None)
            state['stop_reason']=reason or 'controller_error';persist(sampler=True)
            storage.remove_session();storage.engine.dispose()
        from optimizer.reporting import report
        try: report(folder)
        finally: persist()
        return state
