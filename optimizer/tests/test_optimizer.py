from pathlib import Path
import tempfile,unittest,os
import multiprocessing as mp,time
from optimizer import PACKAGE,ROOT
from optimizer.engine import DEFAULT
from optimizer.storage import read,atomic
from optimizer.provenance import epoch
from optimizer.trajectory import run_seed
from optimizer.adapters import get
from optimizer.engine import initialize,run
from optimizer.audit import compatibility
from network import NetworkInstance
from hparameter import HyperParameters
from contextlib import redirect_stdout
from io import StringIO

def killed_seed(cfg,params,folder,expected):
    run_seed(cfg,params,24,folder,expected)

class OptimizerTests(unittest.TestCase):
    def setUp(self):
        (PACKAGE/'.test-output').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=PACKAGE/'.test-output');self.root=Path(self.tmp.name)
        self.cfg={**DEFAULT, 'mode':'smoke','horizon':5,'energy_window':2,'max_trials':3,
                  'training_seeds':[24], 'map':str(ROOT/'map.pkl'),'adaptive_total_rounds':3000}
    def tearDown(self): self.tmp.cleanup()

    def test_report_exports_complete_winner_without_status_collision(self):
        import yaml
        from optimizer.reporting import report
        params=get('daco').baseline_config()
        atomic(self.root/'config.json',{**self.cfg,'mode':'scientific'})
        atomic(self.root/'state.json',dict(stop_reason='deadline_reserve',jobs={
            '0':dict(status='complete',parameters=params),
            '1':dict(status='paused',parameters=params)}))
        atomic(self.root/'reference.json',dict(energy_window=2,cap=1.02))
        for trial,service in ((0,3000),(1,3500)):
            atomic(self.root/f'trials/{trial}/aggregate.json',dict(
                feasible=True,mean_service_capped=service,energy_K_mean=1.,energy_comparable=True))
        report(self.root)
        winner=yaml.safe_load((self.root/'best-feasible-config.yaml').read_text())
        self.assertEqual(winner['trial'],'0');self.assertEqual(winner['status'],'complete')
        self.assertEqual(winner['validation_status'],'training only; validation pending')
        self.assertEqual(len(read(self.root/'top-five-trials.json')),1)
        self.assertTrue((self.root/'final-report.md').exists())

    def test_adapter_smokes_and_physical_accounting(self):
        for name in ('daco','pso','acaco'):
            cfg=self.cfg;params=get(name).baseline_config()
            result=run_seed(cfg,params,24,self.root/name,epoch(cfg),kind=name)
            self.assertEqual(result['completed_rounds'],5)
            from optimizer.storage import unpickle
            records=unpickle(self.root/name/'checkpoint.pkl')['records']
            self.assertTrue(all(r['time']>=0 for r in records))
            self.assertTrue(result['horizon_censored'])
            network=NetworkInstance.from_pickle(cfg['map'])
            self.assertAlmostEqual(sum(result['residual']),network.N*network.init_energy-sum(
                r['selected_tree_physical_energy'] for r in __import__('optimizer.storage',fromlist=['unpickle']).unpickle(self.root/name/'checkpoint.pkl')['records']))

    def test_daco_native_equivalence_and_resume(self):
        params=get('daco').baseline_config()
        network=NetworkInstance.from_pickle(self.cfg['map']);h=HyperParameters();h.T_max=self.cfg['adaptive_total_rounds']
        native=get('daco').make_algorithm(network,h,params,24);residual=[network.init_energy]*network.N;energy_K=0.
        for round_index in range(self.cfg['horizon']):
            with redirect_stdout(StringIO()): root,costs=native.plan_round(list(range(network.N)),residual)
            self.assertIsNotNone(root)
            for node,cost in costs.items(): residual[node]-=cost
            if round_index<self.cfg['energy_window']: energy_K+=sum(costs.values())
        new=run_seed(self.cfg,params,24,self.root/'new',epoch(self.cfg))
        self.assertEqual(residual,new['residual']);self.assertEqual(energy_K,new['energy_K'])
        run_seed(self.cfg,params,24,self.root/'resume',epoch(self.cfg),pause_after=2)
        resumed=run_seed(self.cfg,params,24,self.root/'resume',epoch(self.cfg))
        self.assertEqual(resumed['residual'],new['residual']);self.assertEqual(resumed['energy_K'],new['energy_K'])

    def test_schedule_prefix_changes(self):
        from algorithms.clustering.ac_aco.ac_aco import evaporation_rate
        self.assertNotEqual(evaporation_rate(1,3000,.1,.6),evaporation_rate(1,3500,.1,.6))
        self.assertAlmostEqual(evaporation_rate(3500,3500,.1,.6),.1)

    def test_killed_checkpoint_recovery(self):
        cfg={**self.cfg,'horizon':10,'checkpoint_every':1};params=get('daco').baseline_config();expected=epoch(cfg);folder=self.root/'killed'
        process=mp.get_context('spawn').Process(target=killed_seed,args=(cfg,params,str(folder),expected));process.start()
        deadline=time.monotonic()+20
        while not (folder/'progress.json').exists() and time.monotonic()<deadline: time.sleep(.02)
        self.assertTrue((folder/'progress.json').exists());process.terminate();process.join(timeout=5)
        resumed=run_seed(cfg,params,24,folder,expected)
        control=run_seed(cfg,params,24,self.root/'control',expected)
        self.assertEqual(resumed['residual'],control['residual'])
        self.assertEqual(resumed['completed_rounds'],10)

    def test_outer_deadline_exhausted_never_launches(self):
        from optimizer.deadline import launch
        atomic(self.root/'config.json',dict(budget_seconds=1))
        atomic(self.root/'state.json',dict(spent_wall=1.))
        self.assertEqual(launch(self.root)['stop_reason'],'deadline_exhausted')

    def test_supervisor_does_not_kill_at_admission_cutoff(self):
        from optimizer.deadline import launch
        from unittest.mock import patch,MagicMock
        atomic(self.root/'config.json',dict(budget_seconds=1))
        atomic(self.root/'state.json',dict(spent_wall=0.,jobs={}))
        process=MagicMock();process.pid=123;process.poll.side_effect=[None,0]
        with patch('optimizer.deadline.subprocess.Popen',return_value=process), \
             patch('optimizer.deadline.time.monotonic',side_effect=[0.,2.,3.]), \
             patch('optimizer.deadline.time.sleep'):
            result=launch(self.root)
        process.kill.assert_not_called()
        self.assertFalse((self.root/'STOP').exists())
        self.assertEqual(result['spent_seconds'],3.)

    def test_cutoff_finishes_active_cohort_without_starting_queued_trial(self):
        import yaml
        from unittest.mock import patch
        from optimizer.engine import open_study
        cfg=dict(mode='smoke',horizon=2,energy_window=1,training_seeds=[24],
                 budget_seconds=5,max_trials=3,max_workers=1)
        config=self.root/'draining.yaml';config.write_text(yaml.safe_dump(cfg));folder=self.root/'draining'
        initialize(config,folder,PACKAGE/'runs/ready-expanded');cfg=read(folder/'config.json')
        params=get('daco').baseline_config()
        result=run_seed(cfg,params,24,self.root/'drain-physical',epoch(cfg))
        energy=result['energy_K']
        atomic(folder/'reference.json',dict(energy_window=1,mean=energy,cap=energy*1.02,per_seed={'24':energy}))
        study,storage=open_study(folder,cfg)
        jobs={}
        for _ in range(2):
            study.enqueue_trial({k:params[k] for k in get('daco').space})
            trial=study.ask();get('daco').suggest(trial)
            jobs[str(trial.number)]=dict(number=trial.number,kind='daco',parameters=params,status='paused')
        storage.remove_session();storage.engine.dispose()
        atomic(folder/'state.json',dict(spent_wall=0.,jobs=jobs,stop_reason='not_started'))
        started=[]
        class Process:
            pid=os.getpid()
            def __init__(self,target,args): self.job=args[1];self.checked=False
            def start(self):
                started.append(self.job['number'])
                atomic(folder/'trials'/str(self.job['number'])/'outcome.json',dict(status='complete',runs=[result]))
            def is_alive(self):
                if not self.checked: self.checked=True;time.sleep(5.1);return True
                return False
            def join(self,timeout=None): pass
            def terminate(self): raise AssertionError('Budget must not kill the active trial')
        class Context: pass
        context=Context();context.Process=Process
        with patch('optimizer.engine.mp.get_context',return_value=context): final=run(folder)
        self.assertEqual(started,[0])
        self.assertEqual(final['jobs']['0']['status'],'complete')
        self.assertEqual(final['jobs']['1']['status'],'paused')
        self.assertEqual(final['stop_reason'],'budget_closed_active_finished')

    def test_epoch_guard_avoids_repeated_hashing(self):
        from unittest.mock import patch
        from optimizer.provenance import EpochGuard,epoch as real_epoch
        expected=real_epoch(self.cfg)
        with patch('optimizer.provenance.epoch',wraps=real_epoch) as hashed:
            guard=EpochGuard(self.cfg,expected)
            for _ in range(100): guard.check()
            self.assertEqual(hashed.call_count,1)
            guard.check(force=True);self.assertEqual(hashed.call_count,2)

    def test_supervised_start_and_resume_ledger(self):
        import yaml
        from optimizer.deadline import launch
        cfg=dict(mode='smoke',horizon=2,adaptive_total_rounds=3500,energy_window=1,
                 training_seeds=[24],max_trials=1,budget_seconds=120,max_workers=1,shutdown_reserve_seconds=10)
        config=self.root/'supervised.yaml';config.write_text(yaml.safe_dump(cfg));folder=self.root/'supervised'
        initialize(config,folder,PACKAGE/'runs/ready-expanded')
        first=launch(folder);self.assertGreater(first['spent_seconds'],0)
        self.assertEqual(read(folder/'state.json')['stop_reason'],'trial_budget')
        second=launch(folder);self.assertGreater(second['spent_seconds'],first['spent_seconds'])
        self.assertTrue((folder/'final-report.md').exists())
        self.assertEqual(len([j for k,j in read(folder/'state.json')['jobs'].items() if k!='reference']),1)

    def test_compatibility_priorities(self):
        configs=compatibility(PACKAGE/'runs/ready-expanded',self.root,self.cfg)
        self.assertEqual(configs[0],read(PACKAGE/'runs/ready-expanded/state.json')['jobs']['25']['parameters'])
        import csv
        with (self.root/'legacy-trials-compatibility.csv').open() as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),32);self.assertTrue(all(r['tier']=='C' for r in rows))

    def test_only_first_trial_is_reused_then_sampler_generates_new_vectors(self):
        import optuna
        from optimizer.engine import ask_parameters
        sampler=optuna.samplers.TPESampler(seed=123,n_startup_trials=2)
        study=optuna.create_study(sampler=sampler,direction='maximize')
        baseline=get('daco').baseline_config();vectors=[]
        for index in range(8):
            trial,parameters,origin=ask_parameters(study,self.cfg,baseline)
            self.assertEqual(origin,'reused_baseline' if index==0 else 'sampler_proposal')
            if index==0: self.assertEqual(parameters,baseline)
            else:
                self.assertNotEqual(parameters,baseline)
                self.assertNotIn(parameters,vectors)
            vectors.append(parameters);study.tell(trial,index)
        self.assertEqual(len(vectors),8)

    def test_engine_smoke_resume(self):
        import yaml
        cfg=dict(mode='smoke',horizon=3,adaptive_total_rounds=3500,energy_window=2,
                 training_seeds=[24],max_trials=2,budget_seconds=120,max_workers=2,shutdown_reserve_seconds=10)
        config=self.root/'config.yaml';config.write_text(yaml.safe_dump(cfg));folder=self.root/'study'
        initialize(config,folder,PACKAGE/'runs/ready-expanded')
        result=run(folder);self.assertEqual(result['stop_reason'],'trial_budget')
        self.assertEqual(len([j for k,j in result['jobs'].items() if k!='reference' and j['status']=='complete']),2)
        # A recycled PID must not make restart wait on or launch duplicate work.
        result['jobs']['0'].update(status='running',pid=os.getpid(),created=-1)
        atomic(folder/'state.json',result)
        again=run(folder);self.assertEqual(again['stop_reason'],'trial_budget')
        self.assertEqual(again['jobs']['0']['status'],'complete')
        self.assertNotIn('pid',again['jobs']['0'])

    def test_noncomparable_reference_stops_without_proposing_trials(self):
        import yaml
        from unittest.mock import patch
        from optimizer.reference import ReferenceUnavailable
        cfg=dict(mode='smoke',horizon=2,adaptive_total_rounds=3500,energy_window=1,
                 training_seeds=[24],max_trials=1,budget_seconds=120,max_workers=1,shutdown_reserve_seconds=10)
        config=self.root/'ineligible.yaml';config.write_text(yaml.safe_dump(cfg));folder=self.root/'ineligible'
        initialize(config,folder,PACKAGE/'runs/ready-expanded')
        with patch('optimizer.engine.from_runs',side_effect=ReferenceUnavailable('Reference dies before K')):
            result=run(folder)
        self.assertEqual(result['stop_reason'],'reference_not_comparable')
        self.assertEqual(result['jobs']['reference']['status'],'not_comparable')
        self.assertEqual(list(result['jobs']),['reference'])
        self.assertFalse((folder/'reference.json').exists())
        self.assertEqual(read(folder/'reference-error.json')['message'],'Reference dies before K')
        self.assertTrue((folder/'final-report.md').exists())

    def test_reference_window_depends_only_on_baseline(self):
        from optimizer.reference import from_runs,ReferenceUnavailable
        runs=[dict(seed=24,all_alive_energy_prefix=[1.,2.,3.,4.,5.]),
              dict(seed=25,all_alive_energy_prefix=[2.,4.,6.])]
        cfg={**self.cfg,'energy_window':5}
        result=from_runs(runs,cfg)
        self.assertEqual(result['energy_window'],2)
        self.assertEqual(result['mean'],3.)
        self.assertAlmostEqual(result['cap'],3.06)
        self.assertEqual(result['available_prefix_per_seed'],{'24':5,'25':3})
        with self.assertRaises(ReferenceUnavailable): from_runs(runs,{**cfg,'energy_window_policy':'fixed'})

    def test_prefix_excludes_death_round_and_supports_any_node_count(self):
        from optimizer.reference import energy_prefix
        rows=[dict(round=1,alive_before=12,alive_after=12,served=12,selected_tree_physical_energy=.5),
              dict(round=2,alive_before=12,alive_after=11,served=12,selected_tree_physical_energy=.4)]
        self.assertEqual(energy_prefix(rows,12),[.5])

    def test_observer_preserves_empty_deposit_and_route_failure(self):
        from optimizer.trajectory import observe
        from unittest.mock import patch
        import pickle,random
        n=NetworkInstance.from_pickle(self.cfg['map']);h=HyperParameters()
        a=get('daco').make_algorithm(n,h,{},24)
        a.references=__import__('algorithms.clustering.d_aco.fitness',fromlist=['FitnessReferences']).FitnessReferences(1.,1.)
        before=a.clustering.pheromone.copy();rng=a.random_source.getstate()
        with observe(a) as counts:
            a.clustering.deposit(None,None,1.,False)
            a.clustering.deposit([],None,1.,False)
        self.assertEqual(before,a.clustering.pheromone)
        self.assertEqual(rng,a.random_source.getstate())
        self.assertEqual(counts['n_rewarded_items'],0)
        pickle.dumps(a)
        with patch.object(a,'_run_ant',return_value=None):
            with redirect_stdout(StringIO()),observe(a): root,costs=a.plan_round(list(range(n.N)),[n.init_energy]*n.N)
        self.assertIsNone(root);self.assertEqual(costs,{})

    def test_map_snapshot_survives_source_regeneration(self):
        import yaml
        from optimizer.storage import digest
        source=self.root/'input-map.pkl';source.write_bytes((ROOT/'map.pkl').read_bytes())
        cfg=dict(mode='smoke',horizon=2,energy_window=1,max_trials=1,map=str(source))
        config=self.root/'snapshot.yaml';config.write_text(yaml.safe_dump(cfg));folder=self.root/'snapshot'
        initialize(config,folder,PACKAGE/'runs/ready-expanded')
        expected=read(folder/'provenance.json');source.write_bytes(b'regenerated source map')
        from optimizer.provenance import assert_campaign
        frozen=assert_campaign(folder)
        self.assertEqual(digest(frozen['map']),expected['map_sha'])

    def test_candidate_window_cannot_change_on_resume(self):
        params=get('daco').baseline_config();expected=epoch(self.cfg);folder=self.root/'window'
        run_seed(self.cfg,params,24,folder,expected,energy_window=1)
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            run_seed(self.cfg,params,24,folder,expected,energy_window=2)

    def test_completed_reference_import_keeps_time_and_skips_replay(self):
        import yaml
        from optimizer.reference_cache import import_reference
        cfg=dict(mode='smoke',horizon=3,energy_window=3,max_trials=1,training_seeds=[24],
                 budget_seconds=120,shutdown_reserve_seconds=10)
        config=self.root/'cached.yaml';config.write_text(yaml.safe_dump(cfg))
        source=self.root/'cached-source';target=self.root/'cached-target'
        initialize(config,source,PACKAGE/'runs/ready-expanded');initialize(config,target,PACKAGE/'runs/ready-expanded')
        saved=read(source/'config.json')
        baseline=run_seed(saved,{},24,source/'trials/reference/24',read(source/'provenance.json'),kind='simple')
        atomic(source/'trials/reference/outcome.json',dict(status='complete',runs=[baseline]))
        state=read(source/'state.json');state.update(spent_wall=17.,jobs={'reference':dict(status='complete')})
        atomic(source/'state.json',state);atomic(source/'deadline-ledger.json',dict(spent_seconds=19.))
        reference=import_reference(source,target)
        self.assertEqual(reference['energy_window'],2)
        self.assertGreaterEqual(read(target/'state.json')['spent_wall'],19.)
        self.assertFalse((target/'trials/reference/24/checkpoint.pkl').exists())
        self.assertEqual(read(target/'reference-import.json')['carried_spent_seconds'],19.)
        result=run(target)
        self.assertEqual(result['stop_reason'],'trial_budget')
        self.assertEqual(read(target/'trials/0/aggregate.json')['energy_window'],2)
        rejected=self.root/'wrong-map-import';initialize(config,rejected,PACKAGE/'runs/ready-expanded')
        corrupted=read(source/'provenance.json');corrupted['map_sha']='different map'
        atomic(source/'provenance.json',corrupted)
        with self.assertRaisesRegex(ValueError,'Reference map differs'): import_reference(source,rejected)
        self.assertFalse((rejected/'reference.json').exists())
        self.assertEqual(read(rejected/'state.json')['spent_wall'],0.)

    def test_small_maps_and_disconnection_preflight(self):
        import yaml,pickle
        from point import Point
        for count,radius in ((10,40),(25,100)):
            network=NetworkInstance([Point(i,0,0) for i in range(count)],Point(0,0,0),.6,100,100,100,radius)
            source=self.root/f'map-{count}.pkl';source.write_bytes(pickle.dumps(vars(network)))
            config=self.root/f'map-{count}.yaml';config.write_text(yaml.safe_dump(dict(
                mode='smoke',horizon=2,energy_window=1,max_trials=1,training_seeds=[24],map=str(source))))
            study=self.root/f'study-{count}';initialize(config,study,PACKAGE/'runs/ready-expanded')
            cfg=read(study/'config.json')
            for kind in ('simple','daco'):
                result=run_seed(cfg,{},24,self.root/f'{kind}-{count}',epoch(cfg),kind=kind)
                self.assertEqual(result['initial_nodes'],count)
                self.assertEqual(len(result['all_alive_energy_prefix']),2)
        network=NetworkInstance([Point(200,0,0)],Point(0,0,0),.6,300,100,100,10)
        source=self.root/'disconnected.pkl';source.write_bytes(pickle.dumps(vars(network)))
        config=self.root/'disconnected.yaml';config.write_text(yaml.safe_dump(dict(map=str(source))))
        with self.assertRaisesRegex(ValueError,'disconnected nodes'):
            initialize(config,self.root/'disconnected',PACKAGE/'runs/ready-expanded')

if __name__=='__main__': unittest.main()
