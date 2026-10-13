from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import simulate

class RoundTimeTests(unittest.TestCase):
    def simulator(self):
        network=SimpleNamespace(N=1,init_energy=.6,width=1,height=1,depth=1,
                                sensors=[],base_pos=None,dist_matrix=[[0.]],base_dists=[0.])
        with patch.object(simulate,'Visual'):
            return simulate.Simulator(network,SimpleNamespace(T_max=2))

    def test_time_is_per_round_elapsed_seconds(self):
        algorithm=Mock();algorithm.plan_round.return_value=(object(),{0:.1})
        with patch.object(simulate,'perf_counter',side_effect=[10.,10.25,20.,20.5]):
            history=self.simulator().run(algorithm,verbose=False)
        self.assertEqual(list(history.columns),['round','alive_nodes','round_energy','time'])
        self.assertEqual(history['time'].tolist(),[.25,.5])
        self.assertEqual(history['round_energy'].tolist(),[.1,.1])

    def test_empty_run_still_has_time_header(self):
        algorithm=Mock();algorithm.plan_round.return_value=(None,{})
        history=self.simulator().run(algorithm,verbose=False)
        self.assertTrue(history.empty)
        self.assertIn('time',history.columns)
