"""Generate compact tables and figures from complete, unchanged-model runs."""
import csv
import hashlib
import gzip
import json
from math import isclose
from pathlib import Path
import platform
from statistics import mean, stdev
import subprocess

import matplotlib
import numpy as np
import pandas as pd

from compare import HERE, ROOT, read_result, result_paths
from plot_results import plot_results


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "|" + "---|" * len(headers)] +
                     ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def fmt(value):
    return "NA" if value is None else f"{value:.6f}"


def main():
    lifetime = [read_result(p) for p in result_paths(HERE / "results/lifetime")]
    final = [read_result(p) for p in result_paths(HERE / "results/final")]
    new_cases = {d["seed"]: d for d in final if d["variant"] == "new"}
    # Default reproduction writes all three variants to lifetime; first-run
    # final jobs were isolated so the rejected trial could not overwrite them.
    new_cases.update({d["seed"]: d for d in lifetime if d["variant"] == "new"})
    results = [d for d in lifetime if d["variant"] in ("tuned", "old")] + list(new_cases.values())
    trials = [d for d in lifetime if d["variant"] == "normalized"]
    assert len(results) == 15, f"expected 15 complete cases, got {len(results)}"
    lookup = {(d["variant"], d["seed"]): d for d in results}
    variants, seeds = ["tuned", "old", "new"], list(range(5))
    assert set(lookup) == {(v, s) for v in variants for s in seeds}
    assert len({d["map_sha256"] for d in results}) == 1
    assert len({json.dumps(d["hyperparameters"], sort_keys=True) for d in results}) == 1
    assert len({d["python"] for d in results}) == 1
    assert all(d["stop_reason"] != "measurement_limit" for d in results)
    for v in variants:
        assert len({json.dumps(d["parameters"], sort_keys=True) for d in results if d["variant"] == v}) == 1
    assert all(d["rounds"] >= 100 and all(r["alive_nodes"] == 100 for r in d["rows"][:100])
               for d in results)
    for d in results:
        assert d["rounds"] == len(d["rows"])
        assert isclose(sum(r["energy"] for r in d["rows"]), d["total_energy"], rel_tol=1e-12)
        for r in d["rows"]:
            assert isclose(r["energy"], r["tx_energy"] + r["rx_energy"] +
                           r["aggregation_energy"], rel_tol=1e-12)
            assert isclose(r["convergence"][-1], r["energy"], rel_tol=1e-12)
            assert sum(r["cluster_sizes"]) == r["member_count"]
            assert len(r["cluster_sizes"]) == r["ch_count"]
    # Prove the separate early controls and lifetime cases have identical prefixes.
    for d in results:
        early = HERE / "results/audit" / f"{d['variant']}-{d['seed']}.json"
        if not early.exists():
            early = early.with_suffix(".json.gz")
        if early.exists():
            prior = read_result(early)
            assert d["rows"][:100] == prior["rows"][:100], "seed/config trajectory mismatch"
    paired = []
    for seed in seeds:
        costs = [lookup[v, seed]["common_100_energy"] for v in variants]
        paired.append([seed, *map(fmt, costs), variants[int(np.argmin(costs))]])
    text = ["# Validation: tuned ACO vs old and updated AC-ACO", "",
            "Seeds 0–4; original map; shared model; T_max=3000; 15 complete cases.", "",
            "## First 100 completed rounds: matched service, all 100 nodes alive", "",
            table(["Seed", "Tuned ACO J", "Old AC-ACO J", "New AC-ACO J", "Lowest energy"], paired)]
    aggregate = []
    for v in variants:
        ds = [lookup[v, s] for s in seeds]
        energy = [d["common_100_energy"] for d in ds]
        aggregate.append([v, f"{mean(energy):.6f} ± {stdev(energy):.6f}",
                          f"{mean(d['rounds'] for d in ds):.1f}",
                          f"{mean(d['residual_energy'] for d in ds):.6f}"])
    text += ["", table(["Algorithm", "100-round J: mean ± sample SD", "Mean completed rounds",
                         "Mean final residual J"], aggregate)]
    energy_means = {v: mean(lookup[v, s]["common_100_energy"] for s in seeds) for v in variants}
    text += ["", "Updated AC-ACO uses "
             f"{100*(1-energy_means['new']/energy_means['tuned']):.2f}% less matched-horizon energy than tuned ACO "
             f"and {100*(1-energy_means['new']/energy_means['old']):.2f}% less than old AC-ACO. "
             "It beats old AC-ACO on energy in four of five seeds. The incremental gain is small; "
             "five seeds on one map do not establish general superiority. Tuned ACO sustains routing longer. "
             "The ACO pre-tuning control and isolated ablations in the companion audit also contradict "
             "a blanket claim that the latest ACO tuning reduces energy."]
    if trials:
        trial_rows = [[d["seed"], d["rounds"], lookup["new", d["seed"]]["rounds"],
                       lookup["tuned", d["seed"]]["rounds"], fmt(d["common_100_energy"])]
                      for d in sorted(trials, key=lambda d: d["seed"])]
        text += ["", "## Rejected total-mass chaos trial (not the final implementation)", "",
                 "Changing `(p+c)/(1+n*c)` to `(p+c/n)/(1+c)` sharply weakened exploration. "
                 "Three completed seeds showed shorter service than tuned ACO; remaining trial seeds "
                 "were stopped to free CPU. No result is imputed. The final patch preserves the original rule.", "",
                 table(["Seed", "Trial service rounds", "Final AC-ACO service rounds",
                        "Tuned ACO service rounds", "Trial 100-round J"], trial_rows)]
    full = []
    flat = []
    for seed in seeds:
        for v in variants:
            d = lookup[v, seed]
            depleted = sum(r["depleted_energy"] for r in d["rows"])
            full.append([seed, v, d["rounds"], d["first_death"], d["alive_nodes"],
                         fmt(d["total_energy"]), fmt(depleted), fmt(d["residual_energy"]),
                         d["stop_reason"]])
            flat.append(dict(seed=seed, algorithm=v, rounds=d["rounds"], first_death=d["first_death"],
                             alive=d["alive_nodes"], total_modeled_energy=d["total_energy"],
                             depleted_energy=depleted, residual_energy=d["residual_energy"],
                             common_100_energy=d["common_100_energy"], stop_reason=d["stop_reason"]))
    text += ["", "## Lifetime and energy at stopping", "",
             "Completed rounds are service lifetime; first death uses a one-based completed-round count. "
             "Energy totals at unequal lifetimes are not an efficiency ranking. "
             "T_max means censored lifetime; no_feasible_route is failed full-network routing search within "
             "the algorithm's budget, not proof that the physical graph is disconnected.", "",
             table(["Seed", "Algorithm", "Rounds", "First death", "Alive at stop", "Modeled J",
                    "Depleted J", "Residual J", "Stop"], full)]
    fields = ["ch_count", "node_ch_distance", "ch_bs_distance", "ch_parent_distance",
              "cluster_size_std", "unclustered_nodes", "tx_energy", "rx_energy", "aggregation_energy"]
    structures = []
    for field in fields:
        structures.append([field, *[fmt(mean(r[field] for s in seeds
                                       for r in lookup[v, s]["rows"][:100])) for v in variants]])
    text += ["", "## Structure and accounting: five-seed means over first 100 rounds", "",
             table(["Metric (distances m, energy J/round)", *variants], structures)]
    distributions = []
    for v in variants:
        sizes = [size for s in seeds for r in lookup[v, s]["rows"][:100] for size in r["cluster_sizes"]]
        hist = {i: sizes.count(i) for i in sorted(set(sizes))}
        distributions.append([v, json.dumps(hist, separators=(",", ":"))])
    text += ["", "Direct non-CH members per CH after routing; distribution is member-count:frequency.", "",
             table(["Algorithm", "Cluster-size distribution"], distributions)]
    alive = []
    for t in [1, 100, 500, 1000, 1500, 2000, 2500, 3000]:
        cells = []
        for v in variants:
            ds = [lookup[v, s] for s in seeds if lookup[v, s]["rounds"] >= t]
            cells.append(f"{mean(d['rows'][t-1]['alive_nodes'] for d in ds):.2f} ({len(ds)}/5 active)"
                         if ds else "NA (0/5 active)")
        alive.append([t, *cells])
    text += ["", "## Alive nodes by round", "",
             "Stopped simulations are NA, not padded with zero deaths. Active-run means can be survivor-biased.",
             "", table(["Completed rounds", *variants], alive)]
    conv = []
    for index in [0, 9, 19, 39]:
        conv.append([index+1, *[fmt(mean(r["convergence"][index] for s in seeds
                                             for r in lookup[v, s]["rows"][:100])) for v in variants]])
    text += ["", "## Objective / within-round convergence", "",
             "Fitness is total raw tree energy in joules. Mean best-so-far candidate cost over first 100 rounds; "
             "40 candidates per round for all cases. There is no inner optimizer iteration or early-convergence rule.",
             "", table(["Feasible ants evaluated", *variants], conv)]
    controls = []
    for v in ("old", "new"):
        rows = [r for s in seeds for r in lookup[v, s]["rows"]]
        controls.append([v, f"{min(r['beta'] for r in rows):.3f}..{max(r['beta'] for r in rows):.3f}",
                         f"{min(r['rho'] for r in rows):.3f}..{max(r['rho'] for r in rows):.3f}",
                         f"{min(r['strength'] for r in rows):.6f}..{max(r['strength'] for r in rows):.6f}",
                         f"{sum(r['chaos_changed'] for r in rows)}/{len(rows)}"])
    text += ["", "## Mechanisms exercised in real lifetime trajectories", "",
             table(["Algorithm", "Adaptive beta range", "Adaptive rho range", "Chaos strength range",
                    "Rounds with logistic state change"], controls), "",
             "Both probability chaos and pheromone chaos execute with positive strength; targeted tests verify "
             "each changes its respective values. Full traces include round-level controls and logistic-change flags.", "",
             "## Reproduction and files", "", "```powershell",
             "C:\\Users\\LOQ\\miniconda3\\python.exe -B plans/reports/aco-transfer-261007-0810/compare.py",
             "C:\\Users\\LOQ\\miniconda3\\python.exe -B plans/reports/aco-transfer-261007-0810/summarize.py", "```", "",
             "`results/lifetime/{tuned,old}-*.json.gz` and `results/final/new-*.json.gz`: compressed "
             "per-round energy/residual/alive/cluster/candidate/convergence/control data. "
             "`summary.csv`: per-seed endpoints; `comparison.png`: four-panel figure; "
             "`baseline/*.py`: exact pre-edit AC-ACO source. `results/audit/*.json.gz`: ablations.", "",
             "[Audit and full mapping](audit-261007-0810-tuned-aco-transfer.md) · "
             "[Comparison figure](aco-transfer-261007-0810/comparison.png) · "
             "[Endpoint CSV](aco-transfer-261007-0810/summary.csv) · "
             "[Source/version manifest](aco-transfer-261007-0810/manifest.json)"]
    output = ROOT / "plans/reports/validation-261007-0810-tuned-aco-transfer.md"
    output.write_text("\n".join(text)+"\n", encoding="utf-8")
    with (HERE / "summary.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    source_paths = [*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/test_aco*.py"),
                    ROOT / "tests/test_ac_aco_vectorization.py", *HERE.glob("*.py"),
                    *HERE.glob("baseline/*.py"), *HERE.glob("trial-total-mass/*.py")]
    manifest = dict(base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                        text=True).strip(),
                    python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                    matplotlib=matplotlib.__version__, seeds=seeds,
                    source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in source_paths})
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    plot_results(results, HERE / "comparison.png")
    # Archive only this harness's generated cases, retaining exact JSON bytes.
    for tag in ("audit", "lifetime", "final"):
        for path in (HERE / "results" / tag).glob("*.json"):
            assert path.resolve().is_relative_to(HERE.resolve())
            case = read_result(path)
            assert path.name == f"{case['variant']}-{case['seed']}.json"
            original = path.read_bytes()
            target = path.with_suffix(".json.gz")
            with gzip.open(target, "wb") as file:
                file.write(original)
            with gzip.open(target, "rb") as file:
                assert file.read() == original
            path.unlink()
    print(output)
    print(table(["Seed", "Tuned J", "Old J", "New J", "Lowest"], paired))


if __name__ == "__main__":
    main()
