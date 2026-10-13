from pathlib import Path
import tempfile,sys,random,pickle,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from map_gen import gen,new_map

class MapSeedingTests(unittest.TestCase):
    def test_seed_reproduces_points_and_preserves_global_rng(self):
        random.seed(123);before=random.getstate()
        for clusters in (0,3):
            kwargs=dict(width=500,height=500,depth=500,num_sensors=20,energy=.6,radius=200,num_cluster_points=clusters)
            a=gen(**kwargs,seed=7);b=gen(**kwargs,seed=7);c=gen(**kwargs,seed=8)
            self.assertEqual(a,b);self.assertNotEqual(a['sensors'],c['sensors'])
            self.assertEqual(a['seed'],7)
        self.assertEqual(before,random.getstate())

    def test_seed_range_and_pickle_metadata(self):
        kwargs=dict(width=500,height=500,depth=500,num_sensors=20,energy=.6,radius=200)
        for seed in (1,99): self.assertEqual(gen(**kwargs,seed=seed)['seed'],seed)
        for seed in (0,100,True,1.5,'01'):
            with self.assertRaises(ValueError): gen(**kwargs,seed=seed)
        self.assertTrue(1<=gen(**kwargs)['seed']<=99)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'map.pkl';new_map(seed=9,save_path=path,plot=False)
            with path.open('rb') as handle: data=pickle.load(handle)
            self.assertEqual(data['seed'],9);self.assertEqual(len(data['sensors']),100)

if __name__=='__main__': unittest.main()
