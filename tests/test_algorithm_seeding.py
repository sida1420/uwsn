"""Explicit algorithm seeds isolate RNG streams and survive checkpoints."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import pickle,random,sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from algorithms.aco import SimpleACO
from algorithms.d_aco import DACO
from algorithms.ac_aco import ACACO
from algorithms.pso import PSO
from algorithms.node_aco import NodeACO
from network import NetworkInstance
from hparameter import HyperParameters

CLASSES=(SimpleACO,DACO,ACACO,PSO,NodeACO)

def step(a,residual):
    with redirect_stdout(StringIO()): root,costs=a.plan_round(list(range(a.network.N)),residual)
    if root is None: raise AssertionError('Expected feasible test round')
    for node,energy in costs.items(): residual[node]-=energy
    return costs

class SeedingTests(unittest.TestCase):
    def network(self): return NetworkInstance.from_pickle(str(Path(__file__).resolve().parents[1]/'map.pkl'))

    def test_repeatability_interleaving_and_global_isolation(self):
        for cls in CLASSES:
            with self.subTest(algorithm=cls.name):
                random.seed(999);np.random.seed(999)
                py_before=random.getstate();np_before=np.random.get_state()
                a=cls(self.network(),HyperParameters(),seed=24)
                b=cls(self.network(),HyperParameters(),seed=24)
                ar=[.6]*100;br=[.6]*100
                for _ in range(3):
                    self.assertEqual(step(a,ar),step(b,br))
                self.assertEqual(ar,br);self.assertEqual(random.getstate(),py_before)
                current=np.random.get_state();self.assertEqual(current[0],np_before[0]);np.testing.assert_array_equal(current[1],np_before[1])

    def test_checkpoint_preserves_local_stream(self):
        for cls in CLASSES:
            with self.subTest(algorithm=cls.name):
                a=cls(self.network(),HyperParameters(),seed=24);residual=[.6]*100
                step(a,residual);b=pickle.loads(pickle.dumps(a));other=residual.copy()
                self.assertEqual(step(a,residual),step(b,other));self.assertEqual(residual,other)

    def test_explicit_seed_preserves_legacy_draw_order(self):
        for cls in (SimpleACO,DACO,PSO,NodeACO):
            with self.subTest(algorithm=cls.name):
                random.seed(24)
                legacy=cls(self.network(),HyperParameters());old=[.6]*100
                expected=[step(legacy,old) for _ in range(2)]
                seeded=cls(self.network(),HyperParameters(),seed=24);new=[.6]*100
                self.assertEqual([step(seeded,new) for _ in range(2)],expected)
                self.assertEqual(new,old)

    def test_different_seeds_and_seed_validation(self):
        for cls in CLASSES:
            a=cls(self.network(),HyperParameters(),seed=24);b=cls(self.network(),HyperParameters(),seed=25)
            source_a=getattr(a.clustering,'rng',a.random_source)
            source_b=getattr(b.clustering,'rng',b.random_source)
            self.assertNotEqual(source_a.getstate(),source_b.getstate())
            for invalid in (-1,True,1.2,'24'):
                with self.assertRaises(ValueError): cls(self.network(),HyperParameters(),seed=invalid)

if __name__=='__main__': unittest.main()
