"""Reproducible exploratory mechanism checks; production sources are untouched.

python experiments/daco_rationale.py --output output/daco_rationale_20261027
The controller freezes its runner and src/ before launching two owned workers.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import csv
from dataclasses import asdict
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "src" if (HERE / "src").is_dir() else HERE.parent / "src"
sys.path.insert(0, str(SOURCE))
import numpy as np
from algorithms.d_aco import DACO
from algorithms.clustering.d_aco.d_aco import DACOClustering, Grid
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering.d_aco.fitness import power_density_penalty
from algorithms.clustering import build_clusters
from algorithms.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator
from hparameter import HyperParameters
from map_gen import gen
from network import NetworkInstance
from point import Point

VARIANTS = ("full", "energy_only", "no_inverse_density", "no_sampling_density",
            "flat_kernel", "edge_memory")
CONFIG = dict(nodes=36, size=[300, 300, 300], radius=190, initial_energy=.02,
              horizon=240, ants=40, calibration_ants=40, retries=10,
              map_seeds=[11, 37], search_seeds=[101, 307],
              distributions=["uniform", "normal", "clustered"],
              common_energy_window=20, workers=2)


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def csv_write(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_network(raw):
    return NetworkInstance(raw["sensors"], raw["base_pos"], raw["init_energy"],
                           raw["width"], raw["height"], raw["depth"], raw["radius"],
                           raw.get("distribution", "uniform"), raw.get("num_cluster_points", 0))


def reachable(net, removed=None):
    live = set(range(net.N)) - ({removed} if removed is not None else set())
    seen = {i for i in live if net.base_dists[i] <= net.radius}
    queue = list(seen)
    while queue:
        i = queue.pop()
        for j in live - seen:
            if net.dist_matrix[i][j] <= net.radius:
                seen.add(j)
                queue.append(j)
    return seen


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for i in order[start:end]:
            ranks[i] = rank
        start = end
    return ranks


def rank_correlation(x, y):
    a, b = np.array(average_ranks(x)), np.array(average_ranks(y))
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


class ControlledClustering(DACOClustering):
    """Native node behavior, or edge memory with the other DACO terms retained."""
    def __init__(self, network, hp, params, edge=False):
        super().__init__(network, hp, params)
        self.edge = edge
        if edge:
            self.edge_tau = np.full((network.N, network.N), params.tau0)

    def _log_heuristic_dominance(self, *args):
        pass

    def _update_pheromone(self):
        if not self.edge:
            return super()._update_pheromone()
        self.edge_tau *= 1 - self.rho
        np.clip(self.edge_tau, self.params.tau_min, self.params.tau_max, out=self.edge_tau)

    def deposit(self, chs, fitness, energy_reference, per_ant=True):
        if not self.edge:
            return super().deposit(chs, fitness, energy_reference, per_ant)
        if not chs or fitness is None or fitness <= 0:
            return
        amount = self.params.Q * energy_reference / fitness
        amount *= 1 / self.params.num_ants if per_ant else self.params.theta
        self.last_deposit = amount
        for a, b in zip(chs, chs[1:]):
            self.edge_tau[a, b] = min(self.edge_tau[a, b] + amount, self.params.tau_max)

    def _make_path(self, live_nodes, residual_e, start_node):
        if not self.edge:
            return super()._make_path(live_nodes, residual_e, start_node)
        p = self.params
        self.grid.reset_loss()
        k = max(1, round(p.CH_proportion * len(live_nodes)))
        live = np.asarray(live_nodes, dtype=np.intp)
        energy = np.array([residual_e[i] for i in live_nodes])
        selected = live == start_node
        chs = [start_node]
        self.grid.add_loss(start_node)
        while len(chs) < k:
            positions = np.flatnonzero(~selected)
            if positions.size == 0:
                return None
            density = self.grid.get_density(live)[positions]
            tau = self.edge_tau[chs[-1], live[positions]]
            score = (p.alpha * np.log(np.maximum(tau, 1e-12))
                     + p.beta * np.log(np.maximum(energy[positions], 1e-12))
                     + p.gamma * np.log(np.maximum(density, 1e-12)))
            weights = np.exp(score - score.max())
            pick = self.random_source.choices(positions.tolist(), weights.tolist(), k=1)[0]
            selected[pick] = True
            chs.append(int(live[pick]))
            self.grid.add_loss(chs[-1])
        return chs


class Variant(DACO):
    def __init__(self, network, hp, name, seed):
        self.variant_name = name
        params = DACOParameters()
        if name == "energy_only":
            params.load_density_weight = 0.
        if name == "no_sampling_density":
            params.gamma = 0.
        if name == "flat_kernel":
            params.density_decay = "none"
        super().__init__(network, hp, params, seed)
        self.clustering = ControlledClustering(network, hp, params, name == "edge_memory")
        self.clustering._rng = self._rng

    def _load_context(self, live, residual):
        nodes, energies, density = super()._load_context(live, residual)
        if self.variant_name == "no_inverse_density":
            density = np.ones_like(density)
        return nodes, energies, density


def tree_signature(tree):
    if tree is None:
        return None
    pairs, seen, stack = [], set(), [tree]
    while stack:
        node = stack.pop()
        if node.id in seen:
            raise AssertionError("Repeated/cyclic tree node")
        seen.add(node.id)
        for child in node.nxts:
            pairs.append((child.id, node.id))
            stack.append(child)
    return sorted(pairs)


def diagnostics(out):
    results = {}
    # Algebra checked against the real Grid, for full and partial live sets.
    raw = gen(300, 300, 300, 36, .02, 190, seed=11)
    net = make_network(raw)
    hp = HyperParameters()
    p = DACOParameters()
    max_error = 0.
    for decay in ("none", "linear", "quadratic", "parabolic"):
        for live in (list(range(36)), list(range(0, 36, 2))):
            pp = DACOParameters(density_decay=decay)
            grid = Grid(net, pp)
            grid.compute_density(live)
            K = grid.F @ grid.F.T
            D = grid.get_base_density(live)
            for h in live[:3]:
                before = grid.get_density(live)
                grid.add_loss(h)
                after = grid.get_density(live)
                err = float(np.max(np.abs((before - after) - K[live, h])))
                max_error = max(max_error, err)
                assert err < 1e-9
                assert np.all(after <= before + 1e-10)
            assert np.all(D >= 0)
    results["overlap_identity"] = dict(max_absolute_error=max_error, settings=8, status="pass")

    # Single physically present sensor, CH fraction 1; elongated region gives >1 grid cell.
    solo = NetworkInstance([Point(80, 30, 30)], Point(0, 30, 0), 1, 300, 60, 60, 200)
    grids = {}
    for decay in ("none", "parabolic"):
        g = Grid(solo, DACOParameters(CH_proportion=1., density_decay=decay))
        g.compute_density([0])
        grids[decay] = g
    full = grids["none"].F[0] == 1.
    assert sum(full) > 1
    old = grids["none"].F[0, full]
    new = grids["parabolic"].F[0, full]
    assert np.ptp(old) == 0 and np.ptp(new) > 0
    results["singleton_plateau"] = dict(fully_covered_cells=int(sum(full)),
        flat_unique_values=len(np.unique(old)), proximity_unique_values=len(np.unique(new)),
        proximity_weight_range=[float(min(new)), float(max(new))], status="pass")
    csv_write(out / "singleton_cells.csv", [dict(x=float(c[0]), y=float(c[1]), z=float(c[2]),
        flat=float(grids["none"].F[0, j]), proximity=float(grids["parabolic"].F[0, j]))
        for j, c in enumerate(grids["none"]._center)])

    # Confirm experimental full variant is exactly the native algorithm, not a new implementation.
    h = HyperParameters(); h.T_max = CONFIG["horizon"]
    native, wrapped = DACO(net, h, seed=101), Variant(net, h, "full", 101)
    residual = [.02] * net.N
    with contextlib.redirect_stdout(io.StringIO()):
        for _ in range(3):
            t1, c1 = native.plan_round(list(range(net.N)), residual)
            t2, c2 = wrapped.plan_round(list(range(net.N)), residual)
            assert c1 == c2 and tree_signature(t1) == tree_signature(t2)
    results["native_variant_parity"] = dict(rounds=3, status="pass")

    # Density-only construction: count allocation to a 30-node and a 10-node region.
    rng = random.Random(91)
    coords = [Point(60+rng.gauss(0, 5), 50+rng.gauss(0, 5), 50+rng.gauss(0, 5)) for _ in range(30)]
    coords += [Point(240+rng.gauss(0, 18), 50+rng.gauss(0, 18), 50+rng.gauss(0, 18)) for _ in range(10)]
    allocation_net = NetworkInstance(coords, Point(150, 50, 0), 1, 300, 100, 100, 75)
    ag = Grid(allocation_net, DACOParameters()); ag.compute_density(list(range(40)))
    allocation_rows = []
    for seed in range(400):
        for mode in ("uniform", "density", "density_no_loss", "short_transition"):
            rnd = random.Random(seed)
            chosen = [rnd.randrange(40)]
            ag.reset_loss(); ag.add_loss(chosen[0])
            while len(chosen) < 8:
                allowed = [i for i in range(40) if i not in chosen]
                if mode == "uniform": weights = [1.] * len(allowed)
                elif mode == "short_transition":
                    weights = [1/max(allocation_net.dist_matrix[chosen[-1]][i], 1e-9) for i in allowed]
                else:
                    weights = np.maximum(ag.get_density(allowed) if mode == "density" else
                                         ag.get_base_density(allowed), 1e-12) ** .6
                pick = rnd.choices(allowed, list(weights), k=1)[0]
                chosen.append(pick); ag.add_loss(pick)
            dense_heads = sum(i < 30 for i in chosen)
            cross = [allocation_net.dist_matrix[a][b] for a, b in itertools.combinations(chosen, 2)]
            allocation_rows.append(dict(seed=seed, mode=mode, dense_heads=dense_heads,
                                       sparse_heads=8-dense_heads, mean_pair_distance=statistics.mean(cross)))
    csv_write(out / "allocation.csv", allocation_rows)
    results["allocation"] = {m:dict(mean_dense_heads=statistics.mean(r["dense_heads"] for r in allocation_rows if r["mode"]==m),
        mean_sparse_heads=statistics.mean(r["sparse_heads"] for r in allocation_rows if r["mode"]==m),
        mean_pair_distance=statistics.mean(r["mean_pair_distance"] for r in allocation_rows if r["mode"]==m))
        for m in ("uniform", "density", "density_no_loss", "short_transition")}

    # Shared feasible candidate pool: clean ranking diagnostic, no feedback conflation.
    rng = random.Random(705)
    grid = Grid(net, p); grid.compute_density(list(range(net.N)))
    density = grid.get_base_density(list(range(net.N)))
    residual = np.array([.004 + .036 * rng.random() for _ in range(net.N)])
    evaluator = Evaluator(hp)
    candidates = []
    for _ in range(600):
        heads = sorted(rng.sample(range(net.N), round(.2*net.N)))
        ch, nodes, outside = build_clusters(heads, list(range(net.N)), net.dist_matrix, net.radius)
        tree = dropping_member_multi_hop_routing(ch,nodes,list(range(net.N)),outside,
            net.dist_matrix,net.base_dists,residual,net.radius)
        if tree is None: continue
        costs, energy = evaluator.energy_consumption(tree, net.dist_matrix, net.base_dists)
        if set(costs) != set(range(net.N)):continue
        relative = np.array([costs[i] for i in range(net.N)])/residual
        candidates.append(dict(heads=heads, energy=energy,
            weighted=power_density_penalty(costs,list(range(net.N)),residual,density,p.load_power,p.density_epsilon),
            unweighted=power_density_penalty(costs,list(range(net.N)),residual,np.ones(net.N),p.load_power,p.density_epsilon),
            max_fraction=float(max(relative)), p95_fraction=float(np.quantile(relative,.95))))
    assert candidates
    E = statistics.mean(c["energy"] for c in candidates)
    W = statistics.mean(c["weighted"] for c in candidates)
    U = statistics.mean(c["unweighted"] for c in candidates)
    for c in candidates:
        c["score_weighted"] = c["energy"] + p.load_density_weight*E*c["weighted"]/W
        c["score_unweighted"] = c["energy"] + p.load_density_weight*E*c["unweighted"]/U
    results["candidate_replay"] = dict(feasible=len(candidates), attempted=600,
        selected={name:min(candidates,key=lambda c:c[key]) for name,key in
                  [("energy_only","energy"),("weighted","score_weighted"),("unweighted","score_unweighted")]})
    dump(out / "candidate_pool.json", candidates)

    # Density as a proxy for graph criticality, including a designed dense gateway counterexample.
    criticality_rows=[]
    for dist in CONFIG["distributions"]:
        for seed in CONFIG["map_seeds"]:
            n=make_network(gen(300,300,300,36,.02,190,seed=seed,distribution=dist))
            g=Grid(n,p);g.compute_density(list(range(n.N)))
            d=g.get_base_density(list(range(n.N))); base=reachable(n)
            for i in range(n.N):
                loss=len((base-{i})-reachable(n,i))
                degree=sum(x<=n.radius for j,x in enumerate(n.dist_matrix[i]) if i!=j)
                criticality_rows.append(dict(distribution=dist,map_seed=seed,node=i,
                    density=float(d[i]),inverse_density=1/max(float(d[i]),1e-12),degree=degree,
                    other_disconnected=loss,initially_reachable=len(base)))
    csv_write(out / "criticality.csv",criticality_rows)
    results["criticality"] = dict(nodes=len(criticality_rows),
        positive_loss_nodes=sum(r["other_disconnected"]>0 for r in criticality_rows),
        spearman_inverse_density_vs_other_loss=rank_correlation(
            [r["inverse_density"] for r in criticality_rows],[r["other_disconnected"] for r in criticality_rows]),
        caution="Descriptive pooled correlation, not independent-node significance; null when all losses tie.")
    # Dense group sits beside a single geometric gateway to a remote group.
    pts=[Point(5,5,5),Point(25,5,5)]
    pts += [Point(24,5+j*.25,5) for j in range(1,9)]
    pts += [Point(42,5,5),Point(49,5,5),Point(50,6,5)]
    example=NetworkInstance(pts,Point(0,5,5),1,60,20,20,20)
    g=Grid(example,p);g.compute_density(list(range(example.N)))
    d=g.get_base_density(list(range(example.N)));base=reachable(example)
    results["dense_gateway_example"]=[dict(node=i,density=float(d[i]),
        other_disconnected=len((base-{i})-reachable(example,i))) for i in range(example.N)]
    dump(out / "mechanism_diagnostics.json",results)
    return results


def run_job(job):
    net = make_network(gen(*CONFIG["size"],CONFIG["nodes"],CONFIG["initial_energy"],
        CONFIG["radius"],seed=job["map_seed"],distribution=job["distribution"]))
    hp=HyperParameters();hp.T_max=CONFIG["horizon"]
    a=Variant(net,hp,job["variant"],job["search_seed"])
    residual=[net.init_energy]*net.N;live=list(range(net.N))
    history=[];fnd=None;reason="horizon";spent=0.
    started=time.perf_counter();cpu=time.process_time()
    with contextlib.redirect_stdout(io.StringIO()):
        for t in range(hp.T_max):
            before=residual.copy();tick=time.perf_counter()
            tree,costs=a.plan_round(live,residual)
            if tree is None:
                reason="search_failure";break
            assert set(costs)==set(live)
            signature=tree_signature(tree)
            assert len(signature)==len(live)
            for i,j in signature:
                dist=net.base_dists[i] if j==-1 else net.dist_matrix[i][j]
                assert dist<=net.radius+1e-9
            for i,cost in costs.items():residual[i]=max(0.,residual[i]-cost)
            used=sum(before)-sum(residual);spent+=used
            assert abs(spent+sum(residual)-net.init_energy*net.N)<1e-9
            relative=[costs[i]/max(before[i],1e-12) for i in live]
            live=[i for i in live if residual[i]>0]
            if len(live)<net.N and fnd is None:fnd=t+1
            history.append(dict(round=t+1,alive=len(live),nominal_energy=sum(costs.values()),
                spent_energy=used,residual_sd=statistics.pstdev(residual),max_fraction=max(relative),
                time=time.perf_counter()-tick))
            if not live:reason="all_dead";break
    k=CONFIG["common_energy_window"]
    result={**job, "completed_rounds":len(history),"FND":fnd,
        "LND":len(history) if reason=="all_dead" else None,"termination":reason,
        "alive_final":len(live),"initially_reachable":len(reachable(net)),
        "energy_at_K":sum(r["nominal_energy"] for r in history[:k]) if len(history)>=k else None,
        "all_alive_at_K":len(history)>=k and (fnd is None or fnd>k),
        "residual_sd_at_K":history[k-1]["residual_sd"] if len(history)>=k else None,
        "nominal_total":sum(r["nominal_energy"] for r in history),"battery_spent_total":spent,
        "wall_seconds":time.perf_counter()-started,"cpu_seconds":time.process_time()-cpu,
        "clustering_attempts":a.total_clustering_attempts,"routing_attempts":a.total_routing_attempts,
        "calibration_attempts":a.calibration_attempts,"calibration_feasible":a.calibration_feasible,
        "failed_routing_attempts":a.failed_routing_attempts,
        "params":asdict(a.params),"history":history}
    return result


def summary(out):
    jobs=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((out/"jobs").glob("*.json"))]
    rows=[]
    for dist in CONFIG["distributions"]:
        for variant in VARIANTS:
            batch=[r for r in jobs if r["distribution"]==dist and r["variant"]==variant]
            row=dict(distribution=dist,variant=variant,runs=len(batch),
                mean_completed_rounds=statistics.mean(r["completed_rounds"] for r in batch),
                FND_observed=sum(r["FND"] is not None for r in batch),
                horizon_runs=sum(r["termination"]=="horizon" for r in batch),
                search_failure_runs=sum(r["termination"]=="search_failure" for r in batch),
                mean_cpu_seconds=statistics.mean(r["cpu_seconds"] for r in batch),
                mean_energy_at_K=statistics.mean(r["energy_at_K"] for r in batch if r["energy_at_K"] is not None))
            row["mean_FND"]=(statistics.mean(r["FND"] for r in batch) if row["FND_observed"]==len(batch) else None)
            rows.append(row)
    csv_write(out/"summary_by_distribution.csv",rows)
    paired=[]
    for comparator in VARIANTS[1:]:
        cells=[]
        for dist in CONFIG["distributions"]:
            for seed in CONFIG["map_seeds"]:
                differences=[];fd=[];ed=[]
                for search in CONFIG["search_seeds"]:
                    match={r["variant"]:r for r in jobs if (r["distribution"],r["map_seed"],r["search_seed"])==(dist,seed,search)}
                    a,b=match["full"],match[comparator]
                    differences.append(a["completed_rounds"]-b["completed_rounds"])
                    if a["FND"] is not None and b["FND"] is not None:fd.append(a["FND"]-b["FND"])
                    if a["all_alive_at_K"] and b["all_alive_at_K"]:ed.append(a["energy_at_K"]/b["energy_at_K"]-1)
                cells.append(dict(distribution=dist,map_seed=seed,
                    delta_completed=statistics.mean(differences),
                    delta_FND=statistics.mean(fd) if len(fd)==len(differences) else None,
                    relative_energy_K=statistics.mean(ed) if len(ed)==len(differences) else None))
        paired.append(dict(comparator=comparator,map_cells=cells,
            mean_delta_completed=statistics.mean(c["delta_completed"] for c in cells),
            cells_full_longer=sum(c["delta_completed"]>0 for c in cells),
            cells_full_shorter=sum(c["delta_completed"]<0 for c in cells),
            cells_tied=sum(c["delta_completed"]==0 for c in cells)))
    dump(out/"paired_summary.json",paired)
    diagnostics_data=json.loads((out/"mechanism_diagnostics.json").read_text())
    lines=["# DACO rationale: exploratory experiments", "", "Production algorithm sources were frozen and not edited.",
        "", "## Scope", "", "72 runs: 6 variants × 3 distributions × 2 maps × 2 search seeds. "
        "36 nodes, 300 m cube, radius 190 m, initial energy 0.02 J, horizon 240; 40 ants, "
        "40 calibration ants, at most 10 construction attempts per ant. Initial energy is reduced "
        "from ordinary 0.6 J deployments to accelerate depletion. This is a small mechanism pilot, "
        "not a production-scale lifetime benchmark or a tuned final comparison.", "",
        "## Existing tests and direct checks", "", "The existing 13 DACO tests passed before this campaign. "
        "The experiment verifies the native/full wrapper on three rounds, weighted-overlap score identities, "
        "a one-sensor plateau example, routing-tree inclusion/range, and battery conservation in every simulated round.",
        "", "## Completed modeled rounds", "", "| Distribution | Variant | Mean rounds | FND observed | Horizon | Search failure | Mean CPU s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in rows:lines.append(f"| {r['distribution']} | {r['variant']} | {r['mean_completed_rounds']:.1f} | {r['FND_observed']}/{r['runs']} | {r['horizon_runs']} | {r['search_failure_runs']} | {r['mean_cpu_seconds']:.2f} |")
    lines += ["", "## Paired map-level differences", "", "Search-seed differences are averaged inside each of the six map/distribution cells before counting wins. "
        "No independence across nodes or repeated runs is assumed, and no significance claim is made.", "",
        "| Comparator | Full minus comparator rounds | Map cells longer / shorter / tied |",
        "| --- | ---: | --- |"]
    for r in paired:lines.append(f"| {r['comparator']} | {r['mean_delta_completed']:+.2f} | {r['cells_full_longer']} / {r['cells_full_shorter']} / {r['cells_tied']} |")
    lines += ["", "## Variant definitions", "",
        "- full: native DACO; wrapper parity checked.",
        "- energy_only: λ=0; candidate construction, calibration allowance, and feedback schedule retained. Online scores change subsequent samples.",
        "- no_inverse_density: density denominator set to one in scoring only; weighted fractional depletion remains, and density-guided construction remains.",
        "- no_sampling_density: density exponent γ=0 in construction only; density still enters scoring.",
        "- flat_kernel: remove the extra proximity decay in the grid; affects both construction and scoring. The underlying overlap approximation can still decrease near its boundary.",
        "- edge_memory: replace node pheromone with directed transition pheromone while retaining DACO's density, energy score, bounds, and schedule. Deposits reinforce k−1 transitions instead of k nodes; representation credit assignment is inherently different. This is not native SimpleACO/ACACO.",
        "", "All variants use the same ant/attempt budget; feasible evaluation counts and CPU can differ. Calibration, retries, and the first round's cost are included. "
        "Matched seeds do not force identical samples after feedback diverges. The routing decoder retains its current order sensitivity.",
        "", "## Spatial allocation diagnostic", "", "Synthetic two-region case: 30 compact nodes and 10 more dispersed nodes; select 8 heads in each of 400 seeded trials. "
        "Pheromone and energy preferences are held equal. All modes start from the same random node per seed. "
        "The short-transition mode uses an inverse-distance construction preference, not a complete published protocol.", "",
        "| Construction | Mean dense heads | Mean sparse heads | Mean CH pair distance |", "| --- | ---: | ---: | ---: |"]
    for mode,v in diagnostics_data["allocation"].items():lines.append(f"| {mode} | {v['mean_dense_heads']:.3f} | {v['mean_sparse_heads']:.3f} | {v['mean_pair_distance']:.3f} |")
    lines += ["", "Raw numerical checks, singleton cells, fixed candidate ranking, and density-versus-node-removal diagnostics "
        "are in `mechanism_diagnostics.json`, `singleton_cells.csv`, `candidate_pool.json`, and `criticality.csv`.",
        "", "## Interpretation limits", "",
        "- Completed rounds use the existing energy-clamping model; nominal terminal costs may exceed residual energy. Actual battery spending is logged separately.",
        "- Failed bounded search is distinct from physical disconnection. Initial graph reachability is recorded.",
        "- FND means the first observed energy-clamping death; it is never substituted with run termination. Unobserved FND/LND remain null.",
        "- The common energy window is 20 rounds. Compare only pairs where both complete it with all original sensors alive; see paired_summary.json for coverage.",
        "- State-space/score identities do not establish lifetime optimality. A dense gateway counterexample and graph criticality diagnostics test the limits of the sparse-node hypothesis.",
        "- CPU/wall timings come from two concurrent workers on this machine; report them as exploratory, not definitive runtime benchmarks.",
        "- No parameters were tuned to the final comparison results; one uniform 30-round pilot checked run cost before the configuration was frozen.",
        "", "Reproduce with the frozen `source_snapshot/daco_rationale.py` and `source_snapshot/src/`. "
        "The controller configuration, source hashes, maps, individual histories, and all variants are preserved."]
    (out/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,3,figsize=(13,4),sharey=True)
        for ax,dist in zip(axes,CONFIG["distributions"]):
            for idx,v in enumerate(VARIANTS):
                values=[r["completed_rounds"] for r in jobs if r["distribution"]==dist and r["variant"]==v]
                ax.scatter([idx]*len(values),values,s=22,alpha=.7)
                ax.plot([idx-.2,idx+.2],[statistics.mean(values)]*2,color="black",lw=2)
            ax.axhline(CONFIG["horizon"],ls="--",color="gray",lw=1)
            ax.set(title=dist,xticks=range(len(VARIANTS)),xticklabels=VARIANTS)
            ax.tick_params(axis="x",rotation=70)
        axes[0].set_ylabel("Completed modeled rounds (horizon 240)")
        fig.suptitle("Exploratory ablations: 36 nodes, reduced battery, four runs per condition")
        fig.tight_layout();fig.savefig(out/"completed_rounds.png",dpi=160);plt.close(fig)
    except ImportError:
        pass
    print(json.dumps(paired,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    parser.add_argument("--worker",type=Path)
    parser.add_argument("--result",type=Path)
    parser.add_argument("--summarize",action="store_true")
    args=parser.parse_args()
    if args.worker:
        job=json.loads(args.worker.read_text())
        result=run_job(job);dump(args.result,result)
        return
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if args.summarize:
        summary(out);return
    assert not (out/"manifest.json").exists(),"Use a fresh output folder; results never silently overwritten."
    snapshot=out/"source_snapshot";snapshot.mkdir()
    hashes={}
    for p in SOURCE.rglob("*.py"):
        if "__pycache__" in p.parts:continue
        target=snapshot/"src"/p.relative_to(SOURCE);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target);hashes[str(p.relative_to(SOURCE))]=hashlib.sha256(p.read_bytes()).hexdigest()
    runner=snapshot/"daco_rationale.py";shutil.copy2(__file__,runner)
    dump(out/"manifest.json",dict(config=CONFIG,variants=VARIANTS,python=sys.version,
         numpy=np.__version__,platform=platform.platform(),source_hashes=hashes,
         runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),status="running"))
    diagnostic_result=diagnostics(out)
    print("Direct mechanism diagnostics passed.",flush=True)
    jobs=[];(out/"jobs").mkdir();(out/"inputs").mkdir();(out/"logs").mkdir();(out/"maps").mkdir()
    for dist in CONFIG["distributions"]:
        for seed in CONFIG["map_seeds"]:
            raw=gen(*CONFIG["size"],CONFIG["nodes"],CONFIG["initial_energy"],CONFIG["radius"],seed=seed,distribution=dist)
            dump(out/"maps"/f"{dist}_{seed}.json",{**{k:v for k,v in raw.items() if k not in ("sensors","base_pos")},
                "sensors":[asdict(p) for p in raw["sensors"]],"base_pos":asdict(raw["base_pos"])})
            for search in CONFIG["search_seeds"]:
                order=list(VARIANTS);random.Random(seed*1000+search).shuffle(order)
                for variant in order:
                    job=dict(distribution=dist,map_seed=seed,search_seed=search,variant=variant)
                    job_id=f"{dist}_{seed}_{search}_{variant}"
                    dump(out/"inputs"/(job_id+".json"),job);jobs.append(job_id)
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1")
    def execute(job_id):
        with (out/"logs"/(job_id+".log")).open("w",encoding="utf-8") as log:
            proc=subprocess.run([sys.executable,"-B",str(runner),"--worker",str(out/"inputs"/(job_id+".json")),
                "--result",str(out/"jobs"/(job_id+".json"))],stdout=log,stderr=log,env=env)
        if proc.returncode:raise RuntimeError(f"{job_id} failed; inspect its log")
        return json.loads((out/"jobs"/(job_id+".json")).read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG["workers"]) as pool:
        futures=[pool.submit(execute,j) for j in jobs]
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            r=f.result();print(f"{i}/{len(jobs)} {r['distribution']} map={r['map_seed']} search={r['search_seed']} "
                f"{r['variant']}: rounds={r['completed_rounds']} FND={r['FND']} {r['termination']}",flush=True)
    summary(out)
    manifest=json.loads((out/"manifest.json").read_text());manifest["status"]="complete";dump(out/"manifest.json",manifest)


if __name__=="__main__":
    main()
