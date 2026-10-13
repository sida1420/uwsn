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
        self.tmp=tempfile.TemporaryDirectory(dir=PACKAGE/'.test-output');self.root=Path(self.tmp.name)
        self.cfg={**DEFAULT, 'mode':'smoke','horizon':5,'energy_window':2,'max_trials':3,
                  'training_seeds':[24], 'map':str(ROOT/'map.pkl'),'adaptive_total_rounds':3000}
    def tearDown(self): self.tmp.cleanup()

    def test_adapter_smokes_and_physical_accounting(self):
        for name in ('daco','pso','acaco'):
            cfg=self.cfg;params=get(name).baseline_config()
            result=run_seed(cfg,params,24,self.root/name,epoch(cfg),kind=name)
            self.assertEqual(result['completed_rounds'],5)
            self.assertTrue(result['horizon_censored'])
            self.assertAlmostEqual(sum(result['residual']),60.-sum(
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

if __name__=='__main__': unittest.main()
