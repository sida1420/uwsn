"""Small scheduling checks, with no full scientific trajectories."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimizer import PACKAGE, controller
from optimizer.config import validate
from optimizer.storage import read, assert_epoch
from optimizer.windows.runtime import operational_policy, run, total_time_stop
import yaml


class RuntimeTests(unittest.TestCase):
    def test_no_session_cap_but_total_budget_remains(self):
        cfg=validate({})
        self.assertIsNone(total_time_stop(cfg,0,3*3600))
        self.assertEqual(total_time_stop(cfg,0,6*3600),'wall_budget')
        self.assertEqual(total_time_stop(cfg,5*3600,3600),'wall_budget')

    def test_worker_validation(self):
        for workers in (0,-1,33,True,1.5):
            with self.assertRaises(ValueError):
                with operational_policy(PACKAGE,workers): pass

    def test_three_worker_run_preserves_frozen_identity(self):
        with tempfile.TemporaryDirectory(dir=PACKAGE/'.test-output') as tmp:
            tmp=Path(tmp);folder=tmp/'study'
            cfg=validate(dict(mode='smoke',horizon=2,energy_window=1,max_trials=3,
                              max_workers=1,max_session_hours=.000001,max_wall_hours=.05,
                              training_seeds=[24],validation_seeds=[40],checkpoint_every=1,reuse_history=False))
            config=tmp/'config.yaml';config.write_text(yaml.safe_dump(cfg))
            controller.initialize(config,folder)
            config_before=(folder/'config.json').read_bytes()
            epoch_before=(folder/'provenance.json').read_bytes()
            with operational_policy(folder,3):
                self.assertEqual(controller.assert_epoch(folder)['max_workers'],3)
                self.assertEqual(assert_epoch(folder)['max_workers'],1)
            result=run(folder,3)
            self.assertEqual(result['complete'],3)
            self.assertEqual(result['runtime_workers'],3)
            self.assertIsNone(result['max_session_hours'])
            self.assertEqual(result['stop_reason'],'trial_budget')
            self.assertEqual((folder/'config.json').read_bytes(),config_before)
            self.assertEqual((folder/'provenance.json').read_bytes(),epoch_before)
            self.assertEqual(read(folder/'launch-runtime.json')['workers'],3)
            for metrics_path in (folder/'trials').rglob('metrics.json'):
                self.assertEqual(read(metrics_path)['identity']['config']['max_workers'],1)


if __name__=='__main__': unittest.main()
