import pickle
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from map_gen import gen
from network import NetworkInstance
from point import Point
from run import environment_prefix


class MapDistributionTests(unittest.TestCase):
    def test_normal_distribution_is_stored_without_cluster_centres(self):
        generated = gen(20, 30, 40, 10, 0.6, 100, distribution="normal")

        self.assertEqual(generated["distribution"], "normal")
        self.assertEqual(generated["num_cluster_points"], 0)

    def test_clustered_distribution_metadata_is_stored(self):
        generated = gen(
            20,
            30,
            40,
            10,
            0.6,
            100,
            distribution="clustered",
            num_cluster_points=3,
        )

        self.assertEqual(generated["distribution"], "clustered")
        self.assertEqual(generated["num_cluster_points"], 3)

    def test_legacy_pickle_defaults_to_normal(self):
        legacy = {
            "width": 20,
            "height": 30,
            "depth": 40,
            "base_pos": Point(10, 15, 0),
            "sensors": [Point(1, 2, 3)],
            "init_energy": 0.6,
            "radius": 100,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.pkl"
            with path.open("wb") as file:
                pickle.dump(legacy, file)
            network = NetworkInstance.from_pickle(path)

        self.assertEqual(network.distribution, "normal")
        self.assertEqual(network.num_cluster_points, 0)


class RunFilenameTests(unittest.TestCase):
    def test_environment_prefix_contains_dimensions_nodes_and_distribution(self):
        network = NetworkInstance(
            sensors=[Point(1, 2, 3), Point(4, 5, 6)],
            base_pos=Point(0, 0, 0),
            init_energy=0.6,
            width=500,
            height=400,
            depth=300,
            radius=100,
            distribution="clustered",
            num_cluster_points=4,
        )

        self.assertEqual(environment_prefix(network), "500_400_300_2_clustered")


if __name__ == "__main__":
    unittest.main()
