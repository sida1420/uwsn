from pathlib import Path
import tempfile,sys,random,pickle,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from map_gen import gen,new_map
from point import Point
from network import NetworkInstance
from statistics import mean, pstdev

class MapSeedingTests(unittest.TestCase):
    def test_seed_reproduces_points_and_preserves_global_rng(self):
        random.seed(123);before=random.getstate()
        for distribution in ('normal', 'clustered', 'uniform'):
            kwargs=dict(width=500,height=500,depth=500,num_sensors=20,energy=.6,radius=200,num_cluster_points=3,distribution=distribution)
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

    def test_normal_follows_sink_and_stretches_depth(self):
        sink = Point(400, 600, 500)
        points = gen(width=1000, height=1000, depth=1000, num_sensors=10000,
                     energy=.6, radius=200, seed=7, base_pos=sink)['sensors']
        self.assertAlmostEqual(mean(p.x for p in points), sink.x, delta=15)
        self.assertAlmostEqual(mean(p.y for p in points), sink.y, delta=15)
        self.assertAlmostEqual(mean(p.z for p in points), sink.z, delta=15)
        # Truncation reduces the observed depth spread slightly.
        self.assertTrue(1.3 < pstdev(p.z for p in points) / pstdev(p.x for p in points) < 1.6)

    def test_surface_normal_is_underwater_and_shallower_than_uniform(self):
        kwargs = dict(width=500, height=500, depth=500, num_sensors=5000,
                      energy=.6, radius=200, seed=7)
        normal = gen(**kwargs)['sensors']
        uniform = gen(**kwargs, distribution='uniform')['sensors']
        self.assertTrue(all(0 <= p.x <= 500 and 0 <= p.y <= 500 and 0 < p.z <= 500
                            for p in normal))
        self.assertLess(mean(p.z for p in normal), 125)
        self.assertAlmostEqual(mean(p.z for p in uniform), 250, delta=10)

    def test_distribution_validation_and_metadata_loading(self):
        kwargs = dict(width=500, height=500, depth=500, num_sensors=10,
                      energy=.6, radius=200, seed=7)
        with self.assertRaises(ValueError): gen(**kwargs, distribution='unknown')
        with self.assertRaises(ValueError): gen(**kwargs, distribution='clustered', num_cluster_points=0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'map.pkl'
            for distribution in ('normal', 'clustered', 'uniform'):
                data = gen(**kwargs, distribution=distribution, num_cluster_points=3)
                with path.open('wb') as handle: pickle.dump(data, handle)
                network = NetworkInstance.from_pickle(path)
                self.assertEqual(network.distribution, distribution)
                self.assertEqual(network.num_cluster_points, 3 if distribution == 'clustered' else 0)
                if distribution != 'normal':
                    del data['distribution']
                    with path.open('wb') as handle: pickle.dump(data, handle)
                    self.assertEqual(NetworkInstance.from_pickle(path).distribution, distribution)

if __name__=='__main__': unittest.main()
