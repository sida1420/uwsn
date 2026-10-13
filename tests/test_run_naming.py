"""Run artifacts carry map metadata and share a timestamp across algorithms."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import run


class RunNamingTests(unittest.TestCase):
    def test_automatic_run_seed_uses_small_range(self):
        network=SimpleNamespace(width=500,height=500,depth=500,N=100,distribution='uniform')
        with patch.object(run.NetworkInstance,'from_pickle',return_value=network), \
             patch.object(run,'SEED',None), patch.object(run,'ALGORITHMS',[]), \
             patch.object(run.Path,'mkdir'), patch.object(run,'summarize'), \
             patch.object(run.random,'SystemRandom') as rng:
            rng.return_value.randint.return_value=99
            run.main()
        rng.return_value.randint.assert_called_once_with(1,99)

    def test_out_of_range_run_seeds_are_rejected(self):
        with patch.object(run.NetworkInstance,'from_pickle',return_value=Mock()):
            for seed in (0,100,-1,1000000,True):
                with self.assertRaisesRegex(ValueError,'1 to 99'): run.main(seed=seed)

    def test_shared_prefix_and_preserved_algorithm_seed(self):
        network = SimpleNamespace(width=500, height=500.5, depth=500,
                                  N=100, distribution='clustered')
        clock = Mock()
        clock.now.return_value.strftime.return_value = '20261013_143025'
        histories = [Mock(), Mock()]
        algorithms = [SimpleNamespace(name='first'), SimpleNamespace(name='second')]
        with patch.object(run.NetworkInstance, 'from_pickle', return_value=network), \
             patch.object(run, 'datetime', clock), \
             patch.object(run.Path, 'mkdir'), \
             patch.object(run, 'ALGORITHMS', [object, str]), \
             patch.object(run, 'create_algorithm', side_effect=algorithms) as create, \
             patch.object(run, 'Simulator') as simulator, \
             patch.object(run, 'summarize'):
            simulator.return_value.run.side_effect = histories
            results = run.main(seed=42)
        clock.now.assert_called_once()
        for history, name in zip(histories, ('first', 'second')):
            history.to_csv.assert_called_once_with(
                Path('runs') / f'500_500p5_500_100_clustered_20261013_143025_42_{name}.csv',
                index=False,
            )
        self.assertEqual(list(results), ['first', 'second'])
        self.assertTrue(all(call.kwargs['seed'] == 42 for call in create.call_args_list))


if __name__ == '__main__':
    unittest.main()
