import gzip
import json
import multiprocessing as mp
from pathlib import Path
import tempfile
import time
import unittest
from optimizer import PACKAGE,ROOT
import yaml
import optuna
from optimizer.config import validate,anchors,suggest
from optimizer.storage import atomic,read,fingerprint,lock,assert_epoch
from optimizer.metrics import aggregate,constraints
from optimizer.reference import historical
from optimizer.evaluate import run_seed
from optimizer.controller import initialize,run,open_study,close_study,time_stop
from optimizer.report import generate

def kill_target(cfg,params,path,epoch):
    run_seed(cfg,params,24,path,epoch)

class OptimizerTests(unittest.TestCase):
    def setUp(self):
        base=PACKAGE/'.test-output';base.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.tmp.name)
        self.cfg=validate(dict(mode='smoke',horizon=4,energy_window=2,training_seeds=[24,25],
            validation_seeds=[40],max_trials=3,max_workers=2,checkpoint_every=1,max_wall_hours=.05,reuse_history=False))
        self.epoch=fingerprint(self.cfg);self.params=anchors()[0]
    def tearDown(self): self.tmp.cleanup()
    def init(self,name='study'):
        config=self.root/'config.yaml';config.write_text(yaml.safe_dump(self.cfg))
        folder=self.root/name;initialize(config,folder);return folder

    def test_domains_and_rejection(self):
        from optimizer.config import SPACE
        self.assertEqual(SPACE['theta'],(0.,1.,False))
        self.assertEqual(SPACE['load_density_weight'],(0.,1.,False))
        self.assertEqual(SPACE['load_power'],(1.,4.,False))
        for params in anchors():
            from algorithms.clustering.d_aco.parameters import DACOParameters
            DACOParameters(**params)
            self.assertEqual(params['density_decay'],'parabolic')
        for change in (dict(energy_allowance=.05),dict(training_seeds=[24,24]),dict(max_workers=5),dict(horizon=3000)):
            with self.assertRaises(ValueError): validate({**self.cfg,**change})

    def test_session_and_total_time_limits(self):
        cfg=validate({})
        self.assertEqual(cfg['max_trials'],32)
        self.assertEqual(time_stop(cfg,0,7200),'session_budget')
        self.assertIsNone(time_stop(cfg,7000,100))
        self.assertEqual(time_stop(cfg,21500,100),'wall_budget')
        # Idle time is absent: only accumulated active sessions consume budget.
        self.assertEqual(time_stop(cfg,14000,7200),'session_budget')
        with self.assertRaises(ValueError): validate(dict(max_wall_hours=24))
        with self.assertRaises(ValueError): validate(dict(study_role='validation',max_wall_hours=3))

    def test_energy_ineligibility_and_mean_rule(self):
        cfg={**self.cfg,'mode':'scientific'}
        def sample(seed,energy,status='comparable'):
            return dict(seed=seed,energy_status=status,energy_K=energy,completed_rounds=2800,FND=2700,
                termination_reason='no_feasible_tree_found',cpu=1,wall=2,clustering_attempts=40,routing_attempts=40,calibration_attempts=40)
        reference=dict(mean=10.,cap=10.2,per_seed={'24':10.,'25':10.})
        result=aggregate([sample(24,10.3),sample(25,10.1)],reference,cfg)
        self.assertTrue(result['feasible']);self.assertEqual(result['violating_seed_fraction'],.5)
        bad=aggregate([sample(24,None,'not_comparable'),sample(25,1)],reference,cfg)
        self.assertFalse(bad['feasible']);self.assertGreater(bad['energy_constraint_delta_j'],0)
        with self.assertRaises(ValueError): aggregate([sample(25,10),sample(24,10)],reference,cfg)

    def test_checkpoint_resume_exact_and_no_double_energy(self):
        a=run_seed(self.cfg,self.params,24,self.root/'a',self.epoch)
        paused=run_seed(self.cfg,self.params,24,self.root/'b',self.epoch,pause_after=2)
        self.assertTrue(paused['paused'])
        b=run_seed(self.cfg,self.params,24,self.root/'b',self.epoch)
        for key in ('residual','completed_rounds','FND','energy_K','clustering_attempts','feasible_evaluations'):
            self.assertEqual(a[key],b[key])
        self.assertEqual(b['termination_reason'],'horizon');self.assertTrue(b['horizon_censored'])
        self.assertEqual(b['energy_status'],'comparable')
        cached=run_seed(self.cfg,self.params,24,self.root/'b',self.epoch)
        self.assertEqual(cached,b)

    def test_crash_after_durable_checkpoint(self):
        cfg={**self.cfg,'horizon':20}
        epoch=fingerprint(cfg)
        folder=self.root/'killed'
        p=mp.get_context('spawn').Process(target=kill_target,args=(cfg,self.params,str(folder),epoch));p.start()
        deadline=time.time()+20
        while not (folder/'progress.json').exists() and time.time()<deadline: time.sleep(.02)
        self.assertTrue((folder/'progress.json').exists());p.terminate();p.join(timeout=10)
        resumed=run_seed(cfg,self.params,24,folder,epoch)
        control=run_seed(cfg,self.params,24,self.root/'control',epoch)
        for key in ('residual','energy_K','completed_rounds','clustering_attempts'):
            self.assertEqual(resumed[key],control[key])

    def test_full_precision_reference_and_short_historical_replay(self):
        cfg=validate({});epoch=fingerprint(cfg)
        old_epoch=read(ROOT/'plans/phase10-daco-vs-pheromone/full/pheromone_24.json')['provenance']
        reference=historical(cfg,old_epoch)
        self.assertIsNotNone(reference)
        self.assertIsNone(historical(cfg,epoch))
        self.assertAlmostEqual(reference['mean'],42.46611648006099,places=12)
        self.assertEqual(reference['cap'],reference['mean']*1.02)
        for kind,params,label in (('daco',anchors()[0],'daco'),('daco',anchors()[1],'heuristic_quarter'),('simple',{},'pheromone')):
            source=ROOT/('plans/phase11-daco-concentration/full/heuristic_quarter_24.json' if label=='heuristic_quarter' else f'plans/phase10-daco-vs-pheromone/full/{label}_24.json')
            old=read(source)
            # Reproduce the old explicitly frozen parameters, including none
            # decay; current defaults now deliberately use parabolic decay.
            result=run_seed(self.cfg,old['parameters'] if kind=='daco' else {},24,self.root/label,self.epoch,kind=kind)
            self.assertEqual(result['energy_K'],sum(r['energy'] for r in old['records'][:2]))
        invalid={**epoch,'map_sha':'changed'};self.assertIsNone(historical(cfg,invalid))

    def test_two_worker_study_constraints_resume_and_reports(self):
        folder=self.init()
        controller=mp.get_context('spawn').Process(target=run,args=(str(folder),));controller.start()
        deadline=time.time()+20
        while not read(folder/'state.json')['jobs'] and time.time()<deadline: time.sleep(.05)
        self.assertTrue(read(folder/'state.json')['jobs'])
        (folder/'STOP').touch();controller.join(timeout=20)
        self.assertFalse(controller.is_alive());self.assertEqual(controller.exitcode,0)
        self.assertEqual(read(folder/'state.json')['stop_reason'],'operator_stop')
        # Simulate durable RUNNING statuses left by a controller killed before
        # its finally block. These jobs must resume, rather than be skipped.
        stale=read(folder/'state.json')
        for job in stale['jobs'].values():
            if job['status']=='paused': job['status']='running';job.pop('pid',None)
        atomic(folder/'state.json',stale)
        result=run(folder)
        self.assertEqual(result['complete'],3);self.assertIsNone(result['best_feasible'])
        self.assertEqual(result['stop_reason'],'trial_budget')
        study=open_study(folder,self.cfg)
        trials=study.get_trials();self.assertEqual(len(trials),3)
        self.assertTrue(all(t.state==optuna.trial.TrialState.COMPLETE for t in trials))
        self.assertTrue(all(tuple(t.system_attrs['constraints'])==tuple(constraints(t)) for t in trials))
        close_study(study)
        again=run(folder);self.assertEqual(again['complete'],3)
        generate(folder)
        self.assertTrue((folder/'final-report.md').exists());self.assertTrue((folder/'plots/service-energy.png').exists())
        self.assertFalse((folder/'best-feasible-config.yaml').exists())

    def test_synthetic_adaptive_tpe_and_failed_constraints(self):
        calls=[]
        def constraint(t): calls.append(t.number);return constraints(t)
        study=optuna.create_study(direction='maximize',sampler=optuna.samplers.TPESampler(
            seed=9,multivariate=True,n_startup_trials=2,constraints_func=constraint))
        for _ in range(10):
            trial=study.ask();p=suggest(trial)
            trial.set_user_attr('energy_constraint_delta_j',p['Q']-10)
            study.tell(trial,3000-100*p['beta']-50*p['gamma'])
        failed=study.ask();study.tell(failed,state=optuna.trial.TrialState.FAIL)
        pruned=study.ask();study.tell(pruned,state=optuna.trial.TrialState.PRUNED)
        self.assertNotIn(failed.number,calls)
        # Installed Optuna 4.6 also calls constraints for PRUNED trials;
        # missing workload attributes must therefore remain infeasible.
        self.assertIn(pruned.number,calls)
        self.assertTrue(all(tuple(t.system_attrs['constraints'])==tuple(constraints(t)) for t in study.get_trials()[:10]))
        self.assertGreater(study.get_trials()[-1].system_attrs['constraints'][0],0)

    def test_config_epoch_cannot_silently_change(self):
        folder=self.init();cfg=read(folder/'config.json');cfg['max_trials']=2;atomic(folder/'config.json',cfg)
        with self.assertRaises(RuntimeError): assert_epoch(folder)

    def test_disk_scan_tolerates_atomic_file_replacement(self):
        from unittest.mock import Mock,patch
        from optimizer.storage import disk_mb
        vanished=Mock();vanished.is_file.return_value=True
        vanished.stat.side_effect=FileNotFoundError('atomic temporary file moved')
        committed=self.root/'committed';committed.write_bytes(b'12345')
        with patch('optimizer.storage.Path.rglob',return_value=iter([vanished,committed])):
            self.assertEqual(disk_mb(self.root),5/(1024**2))

    def test_stop_and_kernel_lock(self):
        folder=self.init()
        with lock(folder/'controller.lock'):
            with self.assertRaises(RuntimeError):
                with lock(folder/'controller.lock'): pass
        # stop requests cannot change experiment settings or promote a default.
        (folder/'STOP').touch();self.assertTrue((folder/'STOP').exists())

if __name__=='__main__': unittest.main()
