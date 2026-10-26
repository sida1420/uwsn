"""Render the summary CSVs as Markdown tables for experiment_report.md.

    .venv/bin/python image/scripts/report_tables.py   # -> image/summary/tables.md

Every number in the report tables comes from image/summary/*.csv; nothing is
typed by hand. "n.r." = not reached within the horizon; "k/5" = observed in
k of 5 seeds (mean then covers only the observed seeds and is not plotted).
"""
import json
import math
from pathlib import Path

import pandas as pd

import plot_style as ps

OUT = Path(__file__).resolve().parents[1]
SUMMARY = OUT / "summary"
CFG = json.loads((OUT / "configs" / "experiment_config.json").read_text())


def ms(row, col, digits=0):
    n, runs = row.get(f"{col}_n", 0), row["runs"]
    if n == 0 or (isinstance(n, float) and math.isnan(n)):
        return "n.r."
    mean, sd = row[f"{col}_mean"], row[f"{col}_std"]
    txt = f"{mean:,.{digits}f}"
    if not math.isnan(sd):
        txt += f" ± {sd:,.{digits}f}"
    if n < runs:
        txt += f" ({int(n)}/{int(runs)})"
    return txt


def table(df, columns, header):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(c(r) if callable(c) else str(r[c]) for c in columns) + " |")
    return "\n".join(lines)


def ordered(df):
    df = df.copy()
    df["_o"] = df.algorithm.map(ps.ALGORITHM_ORDER.index)
    return df.sort_values(["distribution", "n_nodes", "_o"])


def main():
    lm = ordered(pd.read_csv(SUMMARY / "lifetime_metrics.csv"))
    em = ordered(pd.read_csv(SUMMARY / "energy_metrics.csv"))
    rm = ordered(pd.read_csv(SUMMARY / "runtime_metrics.csv"))
    st = pd.read_csv(SUMMARY / "statistical_tests.csv")
    rc = CFG["lifetime_round_config"]
    out = []

    def section(title, body):
        out.append(f"### {title}\n\n{body}\n")

    focus = lambda d: d[(d.distribution == rc["distribution"]) & (d.n_nodes == rc["n_nodes"])]  # noqa: E731
    section(f"Lifetime, {rc['distribution']} N = {rc['n_nodes']} (extended run, T_max = {CFG['T_max_extended']})",
            table(focus(lm), ["algorithm", "runs", lambda r: ms(r, "FND"), lambda r: ms(r, "HND"),
                              lambda r: ms(r, "LND"), lambda r: ms(r, "alive_final", 1),
                              lambda r: ms(r, "disconnected_final", 1)],
                  ["Algorithm", "Seeds", "FND", "HND", "LND", "Alive at end", "Disconnected at end"]))
    section(f"Strict repository rule, {rc['distribution']} N = {rc['n_nodes']} (T_max = {CFG['T_max_strict']})",
            table(focus(lm), ["algorithm", lambda r: ms(r, "strict_FND"), lambda r: ms(r, "strict_HND"),
                              lambda r: ms(r, "strict_LND"), lambda r: ms(r, "strict_rounds_completed")],
                  ["Algorithm", "FND", "HND", "LND", "Completed rounds"]))
    section(f"Energy, {rc['distribution']} N = {rc['n_nodes']}",
            table(focus(em), ["algorithm", lambda r: ms(r, "cumulative_energy_r1000", 3),
                              lambda r: ms(r, "cumulative_energy_r2000", 3),
                              lambda r: ms(r, "cumulative_energy_r3500", 3),
                              lambda r: ms(r, "cumulative_energy_at_FND", 3),
                              lambda r: ms(r, "rounds_per_joule_to_FND", 1),
                              lambda r: ms(r, "total_energy_consumed", 2),
                              lambda r: ms(r, "sensor_energy_cv", 3)],
                  ["Algorithm", "Cum. E @1000 (J)", "Cum. E @2000 (J)", "Cum. E @3500 (J)",
                   "Cum. E @FND (J)", "Rounds/J to FND", "Total consumed (J)", "CV per-sensor E"]))
    cl = lm[lm.distribution == rc["distribution"]]
    section("FND / HND / LND vs. number of nodes (clustered)",
            table(cl, ["n_nodes", "algorithm", "runs", lambda r: ms(r, "FND"), lambda r: ms(r, "HND"),
                       lambda r: ms(r, "LND"), lambda r: ms(r, "strict_rounds_completed")],
                  ["N", "Algorithm", "Seeds", "FND", "HND", "LND", "Strict completed rounds"]))
    ce = em[em.distribution == rc["distribution"]]
    section("Energy vs. number of nodes (clustered)",
            table(ce, ["n_nodes", "algorithm", lambda r: ms(r, "cumulative_energy_r1000", 3),
                       lambda r: ms(r, "cumulative_energy_at_FND", 3),
                       lambda r: ms(r, "rounds_per_joule_to_FND", 1),
                       lambda r: ms(r, "sensor_energy_cv", 3),
                       lambda r: ms(r, "energy_balance_error", 1)],
                  ["N", "Algorithm", "Cum. E @1000 (J)", "Cum. E @FND (J)", "Rounds/J to FND",
                   "CV per-sensor E", "Balance error (J)"]))
    other = lm[lm.distribution != rc["distribution"]]
    if len(other):
        section("Other deployments (N = 100)",
                table(other, ["distribution", "algorithm", "runs", lambda r: ms(r, "FND"),
                              lambda r: ms(r, "HND"), lambda r: ms(r, "LND")],
                      ["Deployment", "Algorithm", "Seeds", "FND", "HND", "LND"]))
    section("Runtime",
            table(rm, ["distribution", "n_nodes", "algorithm", "runs",
                       lambda r: ms(r, "runtime_s", 0), lambda r: ms(r, "mean_round_time_s", 4),
                       lambda r: ms(r, "mean_cluster_heads_first1000", 1)],
                  ["Deployment", "N", "Algorithm", "Runs", "Wall time (s)", "Time/round (s)",
                   "Mean CHs (rounds 1-1000)"]))
    fmt = lambda v, d=1: "–" if pd.isna(v) else f"{v:,.{d}f}"  # noqa: E731
    st = st.assign(p=st.p_value_two_sided.map(lambda p: "–" if pd.isna(p) else f"{p:.3g}"))
    section("Paired Wilcoxon signed-rank tests, D-ACO vs. each algorithm (all maps pooled)",
            table(st, ["compared_with", "metric", "paired_maps",
                       lambda r: f"{r.reference_better_count}/{r.paired_maps}",
                       lambda r: fmt(r.median_reference, 3), lambda r: fmt(r.median_other, 3), "p"],
                  ["Compared with", "Metric", "Paired maps", "D-ACO better", "Median D-ACO",
                   "Median other", "p (two-sided)"]))
    (SUMMARY / "tables.md").write_text("\n".join(out))
    print("wrote", SUMMARY / "tables.md")


if __name__ == "__main__":
    main()
