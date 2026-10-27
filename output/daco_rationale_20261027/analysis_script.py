"""Interpret the completed mechanism pilot without changing its raw measurements."""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    args=parser.parse_args();out=args.output.resolve()
    spec=importlib.util.spec_from_file_location("frozen_rationale",out/"source_snapshot/daco_rationale.py")
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    jobs=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((out/"jobs").glob("*.json"))]
    assert len(jobs)==72,"Analyze only the complete frozen cohort"
    manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    for rel,digest in manifest["source_hashes"].items():
        assert hashlib.sha256((out/"source_snapshot/src"/rel).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((out/"source_snapshot/daco_rationale.py").read_bytes()).hexdigest()==manifest["runner_sha256"]
    assert all(r["initially_reachable"]==36 for r in jobs)
    assert all(r["params"]["num_ants"]==40 and r["params"]["calibration_ants"]==40
               and r["params"]["max_clustering_attempts"]==10 for r in jobs)
    assert len({(r['distribution'],r['map_seed'],r['search_seed'],r['variant']) for r in jobs})==72
    # Explicit counterexample to density being an exact graph-criticality score.
    points=[mod.Point(18,10,10)]+[mod.Point(23+i*.15,10+i*.1,10) for i in range(10)]
    points += [mod.Point(38,10,10),mod.Point(56,10,10),mod.Point(74,10,10)]
    net=mod.NetworkInstance(points,mod.Point(0,10,10),1,100,20,20,20)
    grid=mod.Grid(net,mod.DACOParameters());grid.compute_density(list(range(net.N)))
    density=grid.get_base_density(list(range(net.N)));base=mod.reachable(net)
    counter=[dict(node=i,x=points[i].x,density=float(density[i]),
        degree=sum(v<=net.radius for j,v in enumerate(net.dist_matrix[i]) if i!=j),
        other_disconnected=len((base-{i})-mod.reachable(net,i))) for i in range(net.N)]
    assert counter[0]["density"]>counter[-1]["density"]
    assert counter[0]["other_disconnected"]==13 and counter[-1]["other_disconnected"]==0
    mod.dump(out/"criticality_counterexample.json",dict(
        note="Post-design deterministic counterexample, not a population estimate.",
        positions=[vars(p) for p in points],sink=vars(net.base_pos),radius=20,rows=counter))
    paired=[]
    for comparator in mod.VARIANTS[1:]:
        cells=[]
        for dist in mod.CONFIG["distributions"]:
            for seed in mod.CONFIG["map_seeds"]:
                trials=[]
                for search in mod.CONFIG["search_seeds"]:
                    match={r["variant"]:r for r in jobs if
                        (r["distribution"],r["map_seed"],r["search_seed"])==(dist,seed,search)}
                    a,b=match["full"],match[comparator]
                    trials.append(dict(service=a["completed_rounds"]-b["completed_rounds"],
                        fnd=a["FND"]-b["FND"] if a["FND"] is not None and b["FND"] is not None else None,
                        energy_ratio=a["energy_at_K"]/b["energy_at_K"]-1 if
                            a["all_alive_at_K"] and b["all_alive_at_K"] else None,
                        cpu_ratio=a["cpu_seconds"]/b["cpu_seconds"]-1))
                cells.append(dict(distribution=dist,map_seed=seed,
                    **{key:statistics.mean(t[key] for t in trials) if all(t[key] is not None for t in trials) else None
                       for key in trials[0]}))
        paired.append(dict(comparator=comparator,cells=cells,
            **{key:statistics.mean(c[key] for c in cells) if all(c[key] is not None for c in cells) else None
               for key in ("service","fnd","energy_ratio","cpu_ratio")},
            longer=sum(c["service"]>0 for c in cells),shorter=sum(c["service"]<0 for c in cells),
            tied=sum(c["service"]==0 for c in cells)))
    mod.dump(out/"paired_metrics.json",paired)
    d=json.loads((out/"mechanism_diagnostics.json").read_text(encoding="utf-8"))
    replay=d["candidate_replay"]["selected"]
    weighted,energy=replay["weighted"],replay["energy_only"]
    delta_energy=weighted["energy"]/energy["energy"]-1
    delta_max=weighted["max_fraction"]/energy["max_fraction"]-1
    fnd_count=sum(r["FND"] is not None for r in jobs)
    terminations={name:sum(r["termination"]==name for r in jobs) for name in ("search_failure","all_dead","horizon")}
    runtime={v:dict(cpu_per_completed_round=sum(r["cpu_seconds"] for r in jobs if r["variant"]==v)/
        sum(r["completed_rounds"] for r in jobs if r["variant"]==v)) for v in ("full","edge_memory")}
    extra_cpu=runtime["full"]["cpu_per_completed_round"]/runtime["edge_memory"]["cpu_per_completed_round"]-1
    lines=["# What the DACO rationale experiments actually support", "",
        "Exploratory pilot, 27 October 2026. See REPORT.md for the frozen configuration and variant definitions; "
        "all 72 paired runs completed. Per-source hashes verified. Production code and existing campaign files were not edited.",
        "", "## Measured online effects", "",
        "Positive values below mean full DACO exceeds the comparator. Search-seed differences are first averaged "
        "within each of six map/distribution cells. Only two generating seeds per distribution were used; "
        "uniform and clustered maps with the same seed share underlying coordinate draws, so the six cells are not fully independent. "
        "these descriptive averages do not establish statistical significance or universal superiority.", "",
        "| Comparator | Change in FND (rounds) | Change in completed rounds | Change in energy at 20 all-alive rounds | Map cells: longer / shorter / tied |",
        "| --- | ---: | ---: | ---: | --- |"]
    def number(x,suffix=""):
        return "not fully observed/comparable" if x is None else f"{x:+.2f}{suffix}"
    for r in paired:lines.append(f"| {r['comparator']} | {number(r['fnd'])} | {number(r['service'])} | {number(100*r['energy_ratio'] if r['energy_ratio'] is not None else None,'%')} | {r['longer']} / {r['shorter']} / {r['tied']} |")
    lines += ["",f"FND was observed in {fnd_count}/72 runs. Terminations: {terminations}. "
        "No run termination is substituted for an unobserved death event. The simulations use reduced initial "
        "energy (0.02 J), 36 nodes, and a 240-round horizon. First-node survival and completed collection duration "
        "are separate outcomes; use both when judging the criterion.",
        "", "## Your four mechanisms", "",
        "### 1. Proximity preference can concentrate successive choices", "",
        "In the synthetic 30-node dense region plus 10-node sparse region, 400 paired construction trials selected eight CHs. "
        f"Uniform selection allocated {d['allocation']['uniform']['mean_dense_heads']:.3f} heads to the dense region; "
        f"the inverse-distance transition rule allocated {d['allocation']['short_transition']['mean_dense_heads']:.3f}; "
        f"density with overlap reduction allocated {d['allocation']['density']['mean_dense_heads']:.3f}. "
        "This supports the local concentration concern in the designed geometry. It is not a full native "
        "SimpleACO/ACACO benchmark: the diagnostic holds other preferences equal.",
        "", "### 2. Density allocates more heads to the dense region, but the overlap reduction was modest here", "",
        f"Without subtracting selected-head support the dense allocation was {d['allocation']['density_no_loss']['mean_dense_heads']:.3f}; "
        f"with subtraction it was {d['allocation']['density']['mean_dense_heads']:.3f}. "
        "The exact diminishing-overlap identity passed across four decay choices and two live-node sets "
        f"(maximum numerical error {d['overlap_identity']['max_absolute_error']:.3g}). "
        "The property is verified; a large practical benefit from this subtraction alone is not established by this one construction geometry.",
        "", "### 3. Proximity weighting resolves the plateau; its end-to-end benefit is a separate result", "",
        f"The one-sensor example has {d['singleton_plateau']['fully_covered_cells']} fully covered cells. "
        f"Their flat weights have {d['singleton_plateau']['flat_unique_values']} distinct value, versus "
        f"{d['singleton_plateau']['proximity_unique_values']} with parabolic decay. "
        "This confirms localization in the intended minimal example. The flat_kernel online ablation also changes "
        "the density used by the score, so it measures the complete proximity-kernel effect, not sampling alone.",
        "", "### 4. Depletion scoring changes load allocation; density is not equivalent to irreplaceability", "",
        f"In a fixed pool of {d['candidate_replay']['feasible']} feasible trees from 600 attempts, with heterogeneous "
        f"residual energies, the weighted score selected a tree with {delta_energy*100:+.2f}% total energy and "
        f"{delta_max*100:+.2f}% maximum fractional drain relative to the energy-minimum tree. "
        "The weighted and unweighted fractional-depletion criteria selected the same tree in this example. "
        "Thus it demonstrates a depletion-versus-energy trade-off, but does not independently support inverse-density weighting.",
        "",f"Across the six random maps, only {d['criticality']['positive_loss_nodes']} of "
        f"{d['criticality']['nodes']} node-removal cases disconnected another sensor from the sink. "
        "That is too little bottleneck variation to validate density as a criticality proxy. "
        "The constructed counterexample makes the limitation explicit: a gateway has degree 11 and density "
        f"{counter[0]['density']:.3f}, yet removing it disconnects 13 other sensors; a leaf has density "
        f"{counter[-1]['density']:.3f}, and removing it disconnects no other sensor. "
        "The hypothesis needs targeted bottleneck maps and alternative-relay measurements before it becomes a general claim.",
        "", "## What to write now", "",
        "Use the analytical claims about overlap, representation, and plateau removal as mechanism properties. "
        "Report online gains and losses by endpoint and deployment regime, not as a single lifetime improvement. "
        "Describe sparse-node importance as a motivation/proxy whose applicability remains to be tested; "
        "the current random-map criticality diagnostic does not establish it.",
        "", "## Important controls", "",
        "- Edge_memory retains DACO's heuristic and score and changes pheromone credit assignment. It is not native edge ACO, and the routing decoder remains order-sensitive.",
        "- Equal ant/attempt limits do not ensure equal successful evaluations. Individual logs include retries, calibration, CPU, and wall time.",
        "- Battery conservation was checked using clamped spending, distinct from nominal requested costs. Terminal-round delivery is not physically validated.",
        "- The energy comparison uses the common first 20 rounds with all initial nodes alive in both members of a pair.",
        "- Variants use fixed existing parameters without retuning; results estimate these settings, not the best possible version of every ablation.",
        "- The 240-round horizon also sets the evaporation schedule's timescale. This pilot therefore cannot be treated as a simple time-rescaled version of a 3500-round production run.",
        "", "## Outputs", "",
        "- mechanism_panels.png: spatial allocation, fixed-pool ranking, singleton weights, and counterexample.",
        "- endpoints.png: FND and completed-round means by distribution and variant.",
        "- paired_metrics.json: map-level paired effects and computational ratios.",
        "- jobs/: every run's history, endpoint, parameters, and search counters.",
        "- source_snapshot/: exact runner and sources used."]
    lines += ["", "## Runtime check", "",
        f"Full node-memory DACO used {runtime['full']['cpu_per_completed_round']:.5f} CPU seconds per completed round, "
        f"versus {runtime['edge_memory']['cpu_per_completed_round']:.5f} for the edge-memory control "
        f"({extra_cpu*100:+.2f}%). This small pilot does not establish a total runtime advantage for node memory. "
        "The edge control uses vectorized matrix updates while native node evaporation uses Python lists; "
        "theoretical pheromone storage savings are not equivalent to a measured overall speedup."]
    replay_path=out/"termination_replay.json"
    if replay_path.exists():
        rr=json.loads(replay_path.read_text(encoding="utf-8"))
        lines += ["", "## Follow-up: exact termination replay", "",
            "After seeing the FND/completed-round trade-off, two uniform-map-37/search-seed-101 cases were replayed "
            "with the frozen source. Every round's nominal cost matched the original run. This follow-up was "
            "selected after the pilot results, and is diagnostic rather than an additional independent replicate.", ""]
        for r in rr:lines.append(f"- {r['variant']}: {r['completed_rounds']} completed rounds; "
            f"{r['live_at_failure']} sensors alive and {r['physically_sink_reachable']} physically sink-reachable at search termination.")
        lines += ["", "Both runs terminated despite the remaining communication graph being connected. "
            "This does not establish feasibility under the fixed CH count and greedy decoder, but it rules out "
            "physical graph disconnection as the reason for these two stops. Their completed-round difference "
            "cannot be attributed solely to preserving physical connectivity."]
    (out/"FINDINGS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    try:
        import matplotlib
    except ImportError:
        plot_deps=Path(__file__).resolve().parents[1]/"tmp/plot_deps"
        if not plot_deps.is_dir():
            raise RuntimeError("matplotlib unavailable; tabular analysis was saved, but plots need its dependencies")
        sys.path.append(str(plot_deps))
        import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    modes=list(d["allocation"]);vals=[d["allocation"][m]["mean_dense_heads"] for m in modes]
    axes[0,0].bar(range(4),vals,color=["gray","#218380","#73bfb8","#e76f51"])
    axes[0,0].axhline(6,ls="--",c="black",lw=1,label="30/40 population share")
    axes[0,0].set(xticks=range(4),xticklabels=["uniform","density","density\nno loss","short\ntransition"],
        ylabel="Mean CHs in dense region (of 8)",ylim=(0,8),title="Designed two-region construction, 400 seeds")
    axes[0,0].legend(fontsize=8)
    labels=["energy-only","depletion","density +\ndepletion"]
    choices=[replay["energy_only"],replay["unweighted"],replay["weighted"]]
    axes[0,1].bar(range(3),[100*c["max_fraction"] for c in choices],color="#218380")
    axes[0,1].set(xticks=range(3),xticklabels=labels,ylabel="Maximum nominal drain (% residual)",
        title="Fixed candidate pool: selected tree")
    with (out/"singleton_cells.csv").open() as stream:cells=list(csv.DictReader(stream))
    x=[float(c["x"]) for c in cells]
    axes[1,0].plot(x,[float(c["flat"]) for c in cells],"o-",label="flat interior")
    axes[1,0].plot(x,[float(c["proximity"]) for c in cells],"o-",label="parabolic proximity")
    axes[1,0].axvline(80,ls=":",c="gray",label="sensor x")
    axes[1,0].set(xlabel="Cell-center x (m)",ylabel="Support weight",title="One sensor; finite grid centers")
    axes[1,0].legend(fontsize=8)
    axes[1,1].scatter([r["density"] for r in counter],[r["other_disconnected"] for r in counter],c="#e76f51")
    axes[1,1].annotate("gateway",(counter[0]["density"],13),xytext=(-45,-20),textcoords="offset points")
    axes[1,1].set(xlabel="Structural density score",ylabel="Other sensors disconnected by removal",
        title="Designed graph counterexample")
    fig.tight_layout();fig.savefig(out/"mechanism_panels.png",dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(13,7),sharex=True,sharey="row")
    for col,dist in enumerate(mod.CONFIG["distributions"]):
        for idx,v in enumerate(mod.VARIANTS):
            rows=[r for r in jobs if r["distribution"]==dist and r["variant"]==v]
            for ax,key in [(axes[0,col],"FND"),(axes[1,col],"completed_rounds")]:
                values=[r[key] for r in rows if r[key] is not None]
                ax.scatter([idx]*len(values),values,s=20,alpha=.6)
                if len(values)==len(rows):ax.plot([idx-.2,idx+.2],[statistics.mean(values)]*2,c="black",lw=2)
                ax.set(xticks=range(len(mod.VARIANTS)),xticklabels=mod.VARIANTS)
                ax.tick_params(axis="x",rotation=70)
        axes[0,col].set_title(dist)
    axes[0,0].set_ylabel("Observed first-node death (round)")
    axes[1,0].set_ylabel("Completed modeled rounds")
    fig.suptitle("Exploratory paired ablations: 36 nodes, reduced battery; points are individual runs")
    fig.tight_layout();fig.savefig(out/"endpoints.png",dpi=170);plt.close(fig)
    shutil_target=out/"analysis_script.py"
    if Path(__file__).resolve()!=shutil_target:
        shutil_target.write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(termination=terminations,FND_observed=fnd_count,paired=paired),indent=2))


if __name__=="__main__":main()
