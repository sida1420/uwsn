"""Campaign scheduling, physical accounting, deadline and publication checks."""
import csv
from pathlib import Path
import pickle
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import tmp_experiments as batch


class ExperimentTests(unittest.TestCase):
    def test_plain_launch_resumes_latest_compatible_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root/"map.pkl"
            map_path.write_bytes(b"map-identity")
            folder = root/"runs"/"paper_20261027_070150_test"
            folder.mkdir(parents=True)
            batch.atomic_json(folder/"campaign.json", dict(algorithms=list(batch.ALGORITHMS),
                horizon=3500, workers=2, budget_seconds=32400, original_map_sha256=batch.digest(map_path),
                source_hashes={}, cohorts=[dict(id="remaining")]))
            batch.atomic_json(folder/"state.json", dict(spent_seconds=600, completed=[], outcomes={}))
            with patch.object(batch, "ROOT", root), patch.object(sys, "argv", ["tmp_experiments.py", "--map", str(map_path)]), \
                 patch.object(batch, "run_campaign") as resume, patch.object(batch, "create_campaign") as create:
                batch.main()
            resume.assert_called_once_with(folder)
            create.assert_not_called()

    def test_complete_workers_are_reused_without_spawning(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for algo in batch.ALGORITHMS:
                work = folder/"work"/"cohort"/algo
                work.mkdir(parents=True)
                batch.atomic_json(work/"result.json", dict(status="complete"))
            with patch.object(batch.subprocess, "Popen") as spawn:
                results = batch.run_cohort(folder, dict(rates={}), dict(id="cohort", nodes=150),
                                           batch.time.monotonic()+10, lambda: None)
            spawn.assert_not_called()
            self.assertEqual(set(results), set(batch.ALGORITHMS))

    def test_atomic_json_retries_transient_windows_denials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"state.json"
            batch.atomic_json(path, {"version": 1})
            real_replace = batch.os.replace
            calls = []
            def busy_twice(source, target):
                calls.append((source, target))
                if len(calls) <= 2:
                    self.assertEqual(batch.load_json(path), {"version": 1})
                    raise PermissionError(5, "Access denied")
                return real_replace(source, target)
            with patch.object(batch.os, "replace", side_effect=busy_twice), patch.object(batch.time, "sleep"):
                batch.atomic_json(path, {"version": 2})
            self.assertEqual(len(calls), 3)
            self.assertEqual(batch.load_json(path), {"version": 2})
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_atomic_json_permanent_denial_keeps_previous_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"state.json"
            batch.atomic_json(path, {"old": True})
            with patch.object(batch.os, "replace", side_effect=PermissionError(5, "Denied")), \
                 patch.object(batch.time, "sleep"):
                with self.assertRaises(PermissionError):
                    batch.atomic_json(path, {"new": True})
            self.assertEqual(batch.load_json(path), {"old": True})
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_controller_releases_lock_even_when_final_save_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            batch.atomic_json(folder/"campaign.json", dict(algorithms=list(batch.ALGORITHMS),
                source_hashes={}, rates={}, budget_seconds=50, cohorts=[]))
            batch.atomic_json(folder/"state.json", dict(spent_seconds=0, completed=[], outcomes={}))
            with patch.object(batch, "atomic_json", side_effect=PermissionError(5, "Denied")):
                with self.assertRaises(PermissionError):
                    batch.run_campaign(folder)
            self.assertFalse((folder/"controller.lock").exists())

    def job(self, folder, horizon=2, deadline=100):
        return dict(folder=str(folder), deadline=deadline, algorithm="SimpleACO",
                    cohort=dict(map_path="unused.pkl", horizon=horizon, map_sha256="maphash",
                                map_seed=17, algorithm_seed=36))

    def network(self):
        return SimpleNamespace(N=2, init_energy=.6, dist_matrix=[[0., 1.], [1., 0.]], base_dists=[1., 1.])

    def algorithm(self, plans):
        class Fake:
            params = SimpleNamespace(num_ants=40)
            def __init__(self, *args, **kwargs):
                self.plans = iter(plans)
            def plan_round(self, *args):
                return next(self.plans)
        return Fake

    def run_fake(self, job, plans, clock=lambda: 0.):
        with patch("network.NetworkInstance.from_pickle", return_value=self.network()), \
             patch.object(batch, "algorithm_class", return_value=self.algorithm(plans)):
            return batch.simulate_job(job, clock=clock)

    def test_plan_prioritizes_150_and_reduces_secondary_repeats(self):
        plan = batch.configurations()
        main = [c for c in plan if c["phase"] == "main"]
        self.assertTrue(all(c["horizon"] == 3500 for c in main))
        counts = lambda n, d: sum(c["nodes"] == n and c["distribution"] == d and c["size"] == [500]*3 for c in main)
        self.assertGreater(counts(150, "uniform"), counts(200, "clustered"))
        self.assertEqual(counts(200, "clustered"), 1)
        self.assertEqual({c["nodes"] for c in plan if c["size"] == [800]*3}, {400, 600})
        self.assertEqual(len(batch.ALGORITHMS), 5)
        keys = [(c["name"], c["map_seed"], c["phase"]) for c in plan]
        self.assertEqual(len(keys), len(set(keys)))

    def test_budget_estimate_never_admits_more_than_allowance(self):
        cohorts = batch.configurations()
        chosen, deferred, cost = batch.planned_cohorts(cohorts, {}, 1000, 2)
        self.assertLessEqual(cost, 700)
        self.assertEqual(len(chosen)+len(deferred), len(cohorts))
        self.assertGreater(batch.seconds_per_round({}, 600, "PSO"), batch.seconds_per_round({}, 150, "PSO"))

    def test_demand_and_battery_spending_are_distinct_and_conserved(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_fake(self.job(folder), [(object(), {0: 1., 1: .1}), (None, {})])
            rows = list(csv.DictReader((Path(folder)/"history.csv").open()))
            self.assertEqual(result["termination_reason"], "no_feasible_route")
            self.assertEqual(result["FND"], 1)
            self.assertEqual(result["final_alive"], 1)
            self.assertAlmostEqual(float(rows[0]["round_energy"]), 1.1)
            self.assertAlmostEqual(float(rows[0]["round_spent_energy"]), .7)
            self.assertAlmostEqual(float(rows[0]["residual_energy_mean"])*2+.7, 1.2)
            self.assertAlmostEqual(float(rows[0]["residual_energy_sd"]), .25)

    def test_horizon_has_exactly_requested_completed_rounds(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_fake(self.job(folder), [(object(), {0:.1, 1:.1})]*2)
            self.assertEqual(result["termination_reason"], "horizon")
            self.assertEqual(result["completed_rounds"], 2)
            self.assertIsNone(result["FND"])

    def test_deadline_keeps_partial_file_out_of_published_results(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_fake(self.job(folder, deadline=0), [])
            self.assertEqual(result["status"], "interrupted")
            self.assertTrue((Path(folder)/"history.partial.csv").exists())
            self.assertFalse((Path(folder)/"history.csv").exists())

    def test_empty_routing_failure_is_not_a_zero_fnd(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_fake(self.job(folder), [(None, {})])
            self.assertEqual(result["completed_rounds"], 0)
            self.assertIsNone(result["FND"])
            self.assertEqual(list(csv.DictReader((Path(folder)/"history.csv").open())), [])

    def test_physical_connectivity_counts_reachable_nodes(self):
        from point import Point
        raw = dict(sensors=[Point(0,0,1), Point(0,0,2)], base_pos=Point(0,0,0), radius=1.1)
        self.assertEqual(batch.connected_to_sink(raw), (True, 2))
        raw["sensors"].append(Point(100,100,100))
        self.assertEqual(batch.connected_to_sink(raw), (False, 2))

    def test_exhausted_resume_does_not_reset_budget_or_launch_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            batch.atomic_json(folder/"campaign.json", dict(algorithms=list(batch.ALGORITHMS),
                source_hashes={}, rates={}, budget_seconds=50, cohorts=[dict(id="one")]))
            batch.atomic_json(folder/"state.json", dict(spent_seconds=100, completed=[], outcomes={}))
            with patch.object(batch, "run_cohort") as launch:
                state = batch.run_campaign(folder)
            launch.assert_not_called()
            self.assertGreaterEqual(state["spent_seconds"], 100)
            self.assertEqual(state["stop_reason"], "budget_exhausted")
            self.assertIsNone(state["controller_pid"])
            self.assertFalse((folder/"controller.lock").exists())

    def test_second_controller_cannot_enter_the_same_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            batch.atomic_json(folder/"campaign.json", dict(algorithms=list(batch.ALGORITHMS), source_hashes={}))
            batch.atomic_json(folder/"state.json", dict(spent_seconds=0))
            (folder/"controller.lock").write_text("existing-controller")
            with self.assertRaises(FileExistsError):
                batch.run_campaign(folder)

    def test_streaming_worker_matches_original_simulator_energy(self):
        import simulate
        from hparameter import HyperParameters
        from map_gen import gen
        from network import NetworkInstance
        from algorithms.aco import SimpleACO
        raw = gen(100,100,100,12,.6,200,seed=17)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"map.pkl"
            with path.open("wb") as stream:
                pickle.dump(raw, stream)
            job = self.job(Path(folder)/"work", horizon=4)
            job["cohort"]["map_path"] = str(path)
            batch.simulate_job(job, clock=lambda: 0.)
            observed = list(csv.DictReader((Path(job["folder"])/"history.csv").open()))
            hp = HyperParameters(); hp.T_max = 4
            network = NetworkInstance.from_pickle(path)
            with patch.object(simulate, "Visual"):
                simulator = simulate.Simulator(network, hp)
            expected = simulator.run(SimpleACO(network, hp, seed=36), verbose=False)
            self.assertEqual([int(r["alive_nodes"]) for r in observed], expected.alive_nodes.tolist())
            self.assertEqual([float(r["round_energy"]) for r in observed], expected.round_energy.tolist())


if __name__ == "__main__":
    unittest.main()
