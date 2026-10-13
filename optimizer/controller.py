"""Single-writer Optuna ask/tell coordinator; bounded spawned simulation workers."""
from dataclasses import asdict
import json
import multiprocessing as mp
import os
from pathlib import Path
import time
import uuid
import optuna
import psutil
from optimizer import ROOT,PACKAGE
from optimizer.config import load, anchors, suggest, SPACE
from optimizer.storage import atomic,read,unpickle,lock,fingerprint,audit,assert_epoch,disk_mb
from optimizer.metrics import aggregate,constraints
from optimizer.reference import historical,from_runs
from optimizer.evaluate import worker

def initialize(config,folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(PACKAGE): raise ValueError('Study outputs must stay inside optimizer/')
    if folder.exists(): raise ValueError('Study path already exists; choose a new path or resume with run')
    cfg=load(config);epoch=fingerprint(cfg)
    folder.mkdir(parents=True)
    atomic(folder/'config.json',cfg);atomic(folder/'provenance.json',epoch);atomic(folder/'audit.json',audit())
    from algorithms.clustering.d_aco.parameters import DACOParameters
    from algorithms.clustering.aco.parameters import ACOParameters
    from hparameter import HyperParameters
    from network import NetworkInstance
    simple=ACOParameters();simple.beta=simple.gamma=0.
    network=NetworkInstance.from_pickle(cfg['map'])
    atomic(folder/'effective-baselines.json',dict(daco=asdict(DACOParameters()),simple=vars(simple),physics=vars(HyperParameters()),
        map=dict(N=network.N,width=network.width,height=network.height,depth=network.depth,radius=network.radius,init_energy=network.init_energy)))
    import yaml
    (folder/'config.snapshot.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False),encoding='utf-8')
    atomic(folder/'state.json',dict(spent_wall=0.,jobs={},stop_reason='not_started'))
    reference=historical(cfg,epoch)
    if reference: atomic(folder/'reference.json',reference)
    text=('# Baseline provenance audit\n\nPASS: current source/map and effective parameters captured.\n\n'
          + ('PASS: historical paired SimpleACO references match source/map/config; full-precision cap '
             f"{reference['cap']:.12f} J.\n\nHistorical NumPy version was not recorded; original trajectories are retained as historical evidence.\n" if reference else
             'PENDING: no reusable full-workload reference; run will obtain matched SimpleACO before suggesting D-ACO trials.\n')
          +'\nNo full trajectory was freshly run by init. No default is promoted.\n')
    (folder/'baseline-reproduction.md').write_text(text,encoding='utf-8')
    return dict(study=str(folder),mode=cfg['mode'],reference=reference,budget={k:cfg[k] for k in ('max_trials','max_wall_hours','max_session_hours','max_workers')})

def time_stop(cfg,spent,session):
    # Reserve shutdown time inside the budget, rather than adding it afterward.
    total=cfg['max_wall_hours']*3600
    single=cfg['max_session_hours']*3600
    if spent+session>=max(0.,total-min(20.,total*.1)): return 'wall_budget'
    if session>=max(0.,single-min(20.,single*.1)): return 'session_budget'
    return None

def open_study(folder,cfg):
    if not optuna.__version__.startswith('4.'):
        raise RuntimeError('This implementation is tested with Optuna 4.6.0; install optimizer/requirements.txt')
    sampler_path=folder/'sampler.pkl'
    if sampler_path.exists(): sampler=unpickle(sampler_path)
    elif cfg['sampler']=='tpe':
        sampler=optuna.samplers.TPESampler(seed=cfg['sampler_seed'],multivariate=True,
            constant_liar=True,n_startup_trials=cfg['startup_trials'],constraints_func=constraints)
    else: sampler=optuna.samplers.RandomSampler(seed=cfg['sampler_seed'])
    storage=optuna.storages.RDBStorage('sqlite:///'+(folder/'study.db').as_posix(),
        engine_kwargs={'connect_args':{'timeout':30}})
    study=optuna.create_study(study_name='daco',storage=storage,sampler=sampler,direction='maximize',load_if_exists=True)
    study._optimizer_storage=storage
    return study

def close_study(study):
    study._optimizer_storage.remove_session()
    study._optimizer_storage.engine.dispose()

def same_process(pid,created):
    try: return psutil.Process(pid).create_time()==created
    except psutil.Error: return False

def run(folder):
    folder=Path(folder).resolve();cfg=assert_epoch(folder)
    with lock(folder/'controller.lock'):
        # A new ownership token makes workers from a killed coordinator pause.
        token=uuid.uuid4().hex
        atomic(folder/'owner.json',dict(token=token,pid=os.getpid(),created=psutil.Process().create_time()))
        if (folder/'STOP').exists(): (folder/'STOP').unlink()
        state=read(folder/'state.json');jobs=state['jobs'];active={};ctx=mp.get_context('spawn')
        for job in jobs.values():
            if job.get('pid') and same_process(job['pid'],job['created']):
                old=psutil.Process(job['pid'])
                try: old.wait(timeout=15)
                except psutil.TimeoutExpired: raise RuntimeError('Previous worker still owns a checkpoint; wait before resuming')
            # A killed coordinator leaves durable jobs marked running although
            # this new controller has no active process for them. Resume first.
            if job['status']=='running':
                job['status']='paused';job.pop('pid',None)
        study=open_study(folder,cfg)
        # Recover an ask() interrupted before a durable manifest was written.
        for t in study.get_trials(deepcopy=False):
            if t.state==optuna.trial.TrialState.RUNNING and str(t.number) not in jobs:
                study.tell(t.number,state=optuna.trial.TrialState.FAIL)
        for t in study.get_trials(deepcopy=False):
            if t.state==optuna.trial.TrialState.WAITING:
                recovered=study.ask()
                jobs[str(recovered.number)]=dict(number=recovered.number,parameters=suggest(recovered),status='paused',failures=0)
        begin=time.monotonic();spent=state['spent_wall'];stop_reason=None
        def persist():
            state['spent_wall']=spent+time.monotonic()-begin
            state['stop_reason']=stop_reason or 'running'
            trials=study.get_trials(deepcopy=False)
            state['trials_total']=len(trials)
            state['failed_trials']=sum(t.state==optuna.trial.TrialState.FAIL for t in trials)
            atomic(folder/'state.json',state)
            atomic(folder/'sampler.pkl',study.sampler,binary=True)
        def finalize(job,outcome):
            assert_epoch(folder)
            number=job['number']
            if number=='reference':
                reference=from_runs(outcome['runs']);atomic(folder/'reference.json',reference)
                job['status']='complete';return
            metrics=aggregate(outcome['runs'],read(folder/'reference.json'),cfg)
            trial=optuna.trial.Trial(study,study.get_trials(deepcopy=False)[number]._trial_id)
            frozen=study.get_trials(deepcopy=False)[number]
            if frozen.state!=optuna.trial.TrialState.COMPLETE:
                for key,value in metrics.items(): trial.set_user_attr(key,value)
                trial.set_user_attr('provenance',read(folder/'provenance.json'))
                trial.set_user_attr('parameters_effective',job['parameters'])
                study.tell(number,metrics['mean_service_capped'])
            job['status']='complete';atomic(folder/'trials'/str(number)/'aggregate.json',metrics)
        try:
            while True:
                elapsed=spent+time.monotonic()-begin
                if (folder/'STOP').exists(): stop_reason=stop_reason or 'operator_stop'
                stop_reason=stop_reason or time_stop(cfg,spent,time.monotonic()-begin)
                if disk_mb(folder)>=max(0.,cfg['max_disk_mb']-max(32.,cfg['max_disk_mb']*.1)):
                    stop_reason=stop_reason or 'disk_budget'
                if stop_reason: (folder/'STOP').touch(exist_ok=True)
                for key,(process,started) in list(active.items()):
                    job=jobs[key]
                    seed_path=folder/'trials'/key/'current_seed.json'
                    seed_start=read(seed_path)['started'] if seed_path.exists() else time.time()-(time.monotonic()-started)
                    too_long=time.time()-seed_start>cfg['seed_timeout_seconds']
                    try: too_big=process.is_alive() and psutil.Process(process.pid).memory_info().rss>cfg['worker_memory_mb']*1024**2
                    except psutil.NoSuchProcess: too_big=False
                    if too_long or too_big:
                        process.terminate();process.join();job['last_error']='worker timeout' if too_long else 'worker memory cap'
                    if process.is_alive(): continue
                    process.join();del active[key]
                    path=folder/'trials'/key/'outcome.json'
                    outcome=read(path) if path.exists() else dict(status='failed',error=job.get('last_error','worker crashed'))
                    if outcome['status']=='complete': finalize(job,outcome)
                    elif outcome['status']=='paused': job['status']='paused'
                    else:
                        job['failures']=job.get('failures',0)+1;job['last_error']=outcome.get('error','failed')
                        job['status']='paused' if job['failures']<=cfg['max_worker_retries'] else 'failed'
                        job.setdefault('errors',[]).append(outcome)
                        if job['status']=='failed':
                            if key=='reference': stop_reason='reference_failure'
                            else: study.tell(job['number'],state=optuna.trial.TrialState.FAIL)
                    job.pop('pid',None)
                # Recover completed artifacts left between worker exit and tell().
                for key,job in list(jobs.items()):
                    path=folder/'trials'/key/'outcome.json'
                    if key not in active and job['status'] not in ('complete','failed') and path.exists() and read(path)['status']=='complete':
                        finalize(job,read(path))
                if stop_reason and active:
                    # Give round-boundary checkpoints a short grace period, then terminate.
                    deadline=state.setdefault('shutdown_started',time.time())
                    if time.time()-deadline>15:
                        for process,_ in active.values(): process.terminate()
                if stop_reason and not active: break
                reference_ready=(folder/'reference.json').exists()
                if not reference_ready and 'reference' not in jobs:
                    jobs['reference']=dict(number='reference',parameters={},kind='simple',status='paused',failures=0)
                pending=[(k,j) for k,j in jobs.items() if j['status']=='paused' and k not in active]
                for key,job in pending:
                    if stop_reason or len(active)>=cfg['max_workers']: break
                    if key!='reference' and not reference_ready: continue
                    path=folder/'trials'/key/'outcome.json'
                    if path.exists():
                        previous=read(path)
                        atomic(folder/'trials'/key/f"outcome-before-start-{job.get('starts',0)}.json",previous)
                        path.unlink()
                    assert_epoch(folder)
                    atomic(folder/'trials'/key/'current_seed.json',dict(seed=None,started=time.time()))
                    process=ctx.Process(target=worker,args=(str(folder),job,token));process.start()
                    job.update(status='running',pid=process.pid,created=psutil.Process(process.pid).create_time(),starts=job.get('starts',0)+1)
                    active[key]=(process,time.monotonic());persist()
                total=len(study.get_trials(deepcopy=False))
                if reference_ready and len(active)<cfg['max_workers'] and total<cfg['max_trials'] and not stop_reason:
                    anchor_list=read(folder/'shortlist.json')['parameters'] if (folder/'shortlist.json').exists() else anchors()
                    if total<len(anchor_list):
                        study.enqueue_trial({k:anchor_list[total][k] for k in SPACE})
                    trial=study.ask()
                    try: parameters=suggest(trial)
                    except ValueError as exc:
                        trial.set_user_attr('invalid_parameters',str(exc));study.tell(trial,state=optuna.trial.TrialState.FAIL)
                    else: jobs[str(trial.number)]=dict(number=trial.number,parameters=parameters,status='paused',failures=0)
                    persist();continue
                unfinished=any(j['status'] not in ('complete','failed') for j in jobs.values())
                if reference_ready and total>=cfg['max_trials'] and not active and not unfinished:
                    stop_reason='trial_budget';break
                persist();time.sleep(.2)
        except KeyboardInterrupt:
            stop_reason='keyboard_interrupt';(folder/'STOP').touch()
        except BaseException as exc:
            import traceback
            stop_reason='controller_error'
            atomic(folder/'controller-error.json',dict(error=repr(exc),traceback=traceback.format_exc()))
            raise
        finally:
            (folder/'STOP').touch()
            for key,(process,_) in active.items():
                process.join(timeout=15)
                if process.is_alive(): process.terminate();process.join()
                jobs[key]['status']='paused';jobs[key].pop('pid',None)
            state.pop('shutdown_started',None);persist();close_study(study)
        return status(folder)

def status(folder):
    folder=Path(folder).resolve();cfg=read(folder/'config.json');state=read(folder/'state.json')
    completed=[]
    for key,job in state['jobs'].items():
        path=folder/'trials'/key/'aggregate.json'
        if path.exists(): completed.append(dict(number=job['number'],**read(path)))
    feasible=[r for r in completed if r['feasible']]
    best=max(feasible,key=lambda r:(r['mean_service_capped'],-r['energy_K_mean'])) if feasible and cfg['study_role']=='training' else None
    answer=dict(study=str(folder),mode=cfg['mode'],stop_reason=state['stop_reason'],spent_wall=state['spent_wall'],
        trials_total=state.get('trials_total',sum(k!='reference' for k in state['jobs'])),complete=len(completed),
        infeasible=sum(not r['feasible'] for r in completed),failed=state.get('failed_trials',sum(j['status']=='failed' for k,j in state['jobs'].items() if k!='reference')),
        running=sum(j['status']=='running' for j in state['jobs'].values()),best_feasible=best,
        disk_mb=disk_mb(folder),max_trials=cfg['max_trials'],reference_ready=(folder/'reference.json').exists(),
        remaining_wall_hours=max(0.,cfg['max_wall_hours']-state['spent_wall']/3600),
        max_session_hours=cfg['max_session_hours'],
        ETA_note='Uncertain; configuration cost and native stopping vary')
    atomic(folder/'status.json',answer);return answer
