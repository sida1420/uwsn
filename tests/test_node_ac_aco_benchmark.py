"""Check beta selection when routes stop before measurement horizons."""

import importlib.util
from pathlib import Path
import unittest

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "plans/261007-2010-node-acaco/compare-beta.py"
spec = importlib.util.spec_from_file_location("node_acaco_beta_comparison", SCRIPT)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def cases(rounds_a, rounds_b):
    return [dict(label=label, seed=seed, rounds=rounds,
                 energy_1000=16.0 if rounds >= 1000 else None,
                 energy_2000=32.0 if rounds >= 2000 else None,
                 first_node_death=None, wall_seconds=1.0)
            for seed in range(5) for label, rounds in
            (("1-to-5", rounds_a), ("0.6-to-3", rounds_b))]


class BetaBenchmarkTests(unittest.TestCase):
    def test_no_route_at_first_round_has_missing_energy_and_fnd(self):
        metrics = comparison.history_metrics(pd.DataFrame([]), 100, 3000)
        self.assertEqual(metrics["rounds"], 0)
        self.assertEqual(metrics["total_energy"], 0)
        self.assertIsNone(metrics["energy_1000"])
        self.assertIsNone(metrics["energy_2000"])
        self.assertIsNone(metrics["first_node_death"])
        self.assertEqual(metrics["alive_at_stop"], 100)
        self.assertEqual(metrics["stop_reason"], "no_route")

    def test_short_run_display_and_service_fallback(self):
        rows = cases(500, 600)
        self.assertIn("E1000=None", comparison.format_progress(rows[0]))
        summary = comparison.summarize(rows)
        self.assertEqual(summary["chosen"], "0.6-to-3")
        self.assertNotIn("energy_1000", summary["1-to-5"])

    def test_ineligible_range_does_not_win_on_partial_energy(self):
        rows = cases(2100, 1900)
        self.assertEqual(comparison.summarize(rows)["chosen"], "1-to-5")

    def test_paired_energy_selects_lower_mean(self):
        rows = cases(2100, 2100)
        for row in rows:
            if row["label"] == "0.6-to-3":
                row["energy_2000"] -= 0.1
        summary = comparison.summarize(rows)
        self.assertEqual(summary["chosen"], "0.6-to-3")
        self.assertAlmostEqual(summary["paired_0.6-to-3_minus_1-to-5"]["energy_2000"]["mean"], -0.1)


if __name__ == "__main__":
    unittest.main()
