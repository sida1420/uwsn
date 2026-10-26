"""Compute lifetime / energy / runtime metrics from image/raw_data.

    .venv/bin/python image/scripts/summarize.py

Definitions (rounds are 1-based: round_number = rounds completed):
  FND  first round after which alive_nodes < N             (first node dies)
  HND  first round after which alive_nodes <= N/2          (half nodes dead)
  LND  first round after which alive_nodes == 0            (last node dies)
A metric that never happens within the logged rounds is NaN and flagged
`*_observed = False`; the run's end is never substituted for it.
`strict_*` restricts the same metric to the rounds of the repository-default
run (before the first routing failure, capped at T_max_strict).

Writes image/summary/{per_run_metrics,lifetime_metrics,energy_metrics,
runtime_metrics,statistical_tests,d_aco_verification}.csv
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1]
RAW = OUT / "raw_data"
SUMMARY = OUT / "summary"
ENERGY_CHECKPOINTS = (1000, 2000, 3500)


def first_round(df, mask):
    hit = df.loc[mask, "round_number"]
    return float(hit.iloc[0]) if len(hit) else math.nan


def run_metrics(csv_path):
    meta = json.loads(csv_path.with_suffix(".json").read_text())
    df = pd.read_csv(csv_path)
    n = meta["n_nodes"]
    strict_n = meta["strict_rounds_completed"]
    row = {k: meta[k] for k in ("algorithm", "distribution", "n_nodes", "seed",
                                "rounds_completed", "stop_reason", "alive_final",
                                "disconnected_final", "strict_rounds_completed",
                                "strict_stop_reason", "runtime_s",
                                "energy_balance_error")}
    for name, mask in (("FND", df["alive_nodes"] < n),
                       ("HND", df["alive_nodes"] <= n / 2),
                       ("LND", df["alive_nodes"] == 0)):
        value = first_round(df, mask)
        row[name] = value
        row[f"{name}_observed"] = not math.isnan(value)
        strict = value if not math.isnan(value) and value <= strict_n else math.nan
        row[f"strict_{name}"] = strict
        row[f"strict_{name}_observed"] = not math.isnan(strict)
    cum = df["cumulative_energy"]
    row["total_energy_consumed"] = float(cum.iloc[-1]) if len(df) else 0.0
    row["initial_energy"] = meta["total_initial_energy"]
    row["energy_consumed_pct"] = 100 * row["total_energy_consumed"] / row["initial_energy"]
    for r in ENERGY_CHECKPOINTS:
        # Only defined if the run actually reached round r.
        row[f"cumulative_energy_r{r}"] = float(cum.iloc[r - 1]) if len(df) >= r else math.nan
    if row["FND_observed"]:
        i = int(row["FND"]) - 1
        row["cumulative_energy_at_FND"] = float(cum.iloc[i])
        row["residual_std_at_FND"] = float(df["residual_std_alive"].iloc[max(i - 1, 0)])
        row["rounds_per_joule_to_FND"] = row["FND"] / row["cumulative_energy_at_FND"]
    else:
        row["cumulative_energy_at_FND"] = math.nan
        row["residual_std_at_FND"] = math.nan
        row["rounds_per_joule_to_FND"] = math.nan
    head = df.iloc[:min(1000, len(df))]
    row["mean_round_energy_first1000"] = float(head["round_energy_consumed"].mean())
    row["mean_cluster_heads_first1000"] = float(head["num_cluster_heads"].mean())
    row["mean_round_time_s"] = float(df["time"].mean()) if len(df) else math.nan
    sensor = pd.read_csv(csv_path.with_name(csv_path.stem + "_sensor-energy.csv"))
    e = sensor["total_energy"].to_numpy()
    row["sensor_energy_cv"] = float(e.std() / e.mean()) if e.mean() > 0 else math.nan
    row["sensor_energy_gini"] = gini(e)
    row["diagnostics"] = json.dumps(meta.get("diagnostics", {}))
    return row


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    if x.sum() <= 0:
        return math.nan
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def included(json_path):
    """Only algorithms listed in experiment_config.json (excluded ones are ignored)."""
    cfg = json.loads((OUT / "configs" / "experiment_config.json").read_text())
    return json.loads(json_path.read_text()).get("class_key") in cfg["algorithms"]


def load_all():
    rows = [run_metrics(p) for p in sorted(RAW.glob("*/*/*.csv"))
            if not p.name.endswith("_sensor-energy.csv") and p.with_suffix(".json").exists()
            and included(p.with_suffix(".json"))]
    return pd.DataFrame(rows)


def mean_std(group, col):
    vals = group[col].dropna()
    return pd.Series({f"{col}_mean": vals.mean() if len(vals) else math.nan,
                      f"{col}_std": vals.std(ddof=1) if len(vals) > 1 else math.nan,
                      f"{col}_n": len(vals)})


def aggregate(runs, cols):
    keys = ["distribution", "n_nodes", "algorithm"]
    parts = []
    for key, g in runs.groupby(keys, sort=True):
        s = pd.concat([mean_std(g, c) for c in cols])
        s["runs"] = len(g)
        s["seeds"] = " ".join(str(v) for v in sorted(g["seed"]))
        parts.append(pd.concat([pd.Series(dict(zip(keys, key))), s]))
    return pd.DataFrame(parts)


def wilcoxon_signed_rank(x, y):
    """Two-sided Wilcoxon signed-rank test, normal approximation with tie and
    continuity correction (scipy is not installed in this environment).
    Zero differences are dropped (Wilcoxon's original method)."""
    d = np.asarray(x, float) - np.asarray(y, float)
    d = d[~np.isnan(d)]
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return n, math.nan, math.nan
    ranks = pd.Series(np.abs(d)).rank().to_numpy()
    w_plus = ranks[d > 0].sum()
    mean = n * (n + 1) / 4
    _, counts = np.unique(np.abs(d), return_counts=True)
    var = n * (n + 1) * (2 * n + 1) / 24 - (counts ** 3 - counts).sum() / 48
    if var <= 0:
        return n, w_plus, math.nan
    z = (abs(w_plus - mean) - 0.5) / math.sqrt(var)
    p = math.erfc(z / math.sqrt(2))
    return n, w_plus, p


def statistical_tests(runs, reference="D-ACO"):
    metrics = ["FND", "HND", "cumulative_energy_r1000", "rounds_per_joule_to_FND",
               "sensor_energy_cv"]
    keys = ["distribution", "n_nodes", "seed"]
    ref = runs[runs.algorithm == reference].set_index(keys)
    rows = []
    for algo in sorted(set(runs.algorithm) - {reference}):
        other = runs[runs.algorithm == algo].set_index(keys)
        common = ref.index.intersection(other.index)
        for m in metrics:
            a, b = ref.loc[common, m], other.loc[common, m]
            ok = a.notna() & b.notna()
            n_eff, w, p = wilcoxon_signed_rank(a[ok], b[ok])
            rows.append({
                "reference": reference, "compared_with": algo, "metric": m,
                "paired_maps": int(ok.sum()), "nonzero_differences": n_eff,
                "reference_better_count": int(((a[ok] > b[ok]) if m in ("FND", "HND", "rounds_per_joule_to_FND")
                                               else (a[ok] < b[ok])).sum()),
                "median_reference": float(a[ok].median()) if ok.any() else math.nan,
                "median_other": float(b[ok].median()) if ok.any() else math.nan,
                "W_plus": w, "p_value_two_sided": p,
            })
    return pd.DataFrame(rows)


def d_aco_verification(runs):
    d = runs[runs.algorithm == "D-ACO"].copy()
    diag = d["diagnostics"].map(json.loads)
    for k in ("class", "clustering_class", "total_clustering_attempts",
              "failed_clustering_attempts", "total_routing_attempts",
              "failed_routing_attempts", "calibration_feasible", "clustering_iteration",
              "pheromone_min", "pheromone_max", "fitness_reference_energy"):
        d[k] = diag.map(lambda x, k=k: x.get(k))
    cols = ["distribution", "n_nodes", "seed", "class", "clustering_class",
            "rounds_completed", "stop_reason", "strict_rounds_completed", "FND", "HND", "LND",
            "total_energy_consumed", "energy_balance_error", "runtime_s",
            "mean_cluster_heads_first1000", "total_clustering_attempts",
            "failed_clustering_attempts", "total_routing_attempts", "failed_routing_attempts",
            "calibration_feasible", "clustering_iteration", "pheromone_min",
            "pheromone_max", "fitness_reference_energy"]
    return d[cols].sort_values(["distribution", "n_nodes", "seed"])


def main():
    SUMMARY.mkdir(parents=True, exist_ok=True)
    runs = load_all()
    runs.drop(columns="diagnostics").to_csv(SUMMARY / "per_run_metrics.csv", index=False)
    aggregate(runs, ["FND", "HND", "LND", "strict_FND", "strict_HND", "strict_LND",
                     "rounds_completed", "strict_rounds_completed", "alive_final",
                     "disconnected_final"]).to_csv(SUMMARY / "lifetime_metrics.csv", index=False)
    aggregate(runs, ["total_energy_consumed", "energy_consumed_pct"]
              + [f"cumulative_energy_r{r}" for r in ENERGY_CHECKPOINTS]
              + ["cumulative_energy_at_FND", "rounds_per_joule_to_FND",
                 "mean_round_energy_first1000", "residual_std_at_FND",
                 "sensor_energy_cv", "sensor_energy_gini",
                 "energy_balance_error"]).to_csv(SUMMARY / "energy_metrics.csv", index=False)
    aggregate(runs, ["runtime_s", "mean_round_time_s", "mean_cluster_heads_first1000"]
              ).to_csv(SUMMARY / "runtime_metrics.csv", index=False)
    statistical_tests(runs).to_csv(SUMMARY / "statistical_tests.csv", index=False)
    d_aco_verification(runs).to_csv(SUMMARY / "d_aco_verification.csv", index=False)
    print(f"{len(runs)} runs summarised -> {SUMMARY}")
    print(runs.groupby("algorithm").size().to_string())
    print("max |energy balance error| (J):", runs["energy_balance_error"].abs().max())


if __name__ == "__main__":
    main()
