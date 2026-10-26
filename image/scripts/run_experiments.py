"""Run the WSN lifetime/energy experiment matrix with the repository's real
algorithms and Simulator, and log per-round raw data.

    .venv/bin/python image/scripts/run_experiments.py --dry-run
    .venv/bin/python image/scripts/run_experiments.py --algorithms DACO --workers 2

Every (distribution, node count, seed) builds ONE map with map_gen.gen(seed=seed);
all algorithms run on that same map, with the same HyperParameters, the same
algorithm seed and a fresh instance (fair comparison).

Strict vs. extended run
-----------------------
The repository Simulator stops the whole network the first time plan_round
finds no feasible routing tree (some live node has no forwarding path). That
rule is kept unchanged up to the first such failure: the rounds before it are
exactly the strict (repository-default) run, capped at T_max_strict.

To observe lifetime beyond that point, the same run continues (extended mode):
at a failing round, every live node without a greedy forwarding path to the
sink (sink within radius, or a connected live neighbour within radius that is
strictly closer to the sink, the same rule the routing uses) is marked
DISCONNECTED and the round is retried once without those nodes. Disconnected
nodes keep their energy and still count as alive -- they are never declared
dead. The run ends when all nodes are dead, no connected node is left, the
algorithm still finds no routing, or T_max_extended is reached.

Per run the script writes
  raw_data/<group>/<slug>/<dist>_n<N>_seed<S>.csv        per-round log
  raw_data/<group>/<slug>/<dist>_n<N>_seed<S>_sensor-energy.csv
  raw_data/<group>/<slug>/<dist>_n<N>_seed<S>.json       run metadata
  logs/<slug>/<dist>_n<N>_seed<S>.log                    algorithm stdout
where <group> is "d_aco" for D-ACO and "other_algorithms" otherwise.
Runs whose JSON already exists are skipped, so a batch can be resumed.
"""
import argparse
import contextlib
import json
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "image"
CONFIG_PATH = OUT / "configs" / "experiment_config.json"
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLBACKEND", "Agg")  # Simulator builds a Visual figure


def load_config():
    with CONFIG_PATH.open() as f:
        return json.load(f)


def algorithm_classes():
    from algorithms.d_aco import DACO
    from algorithms.aco import SimpleACO
    from algorithms.node_aco import NodeACO
    from algorithms.pso import PSO
    from algorithms.ac_aco import ACACO
    from algorithms.me_aco import MEACO
    return {"DACO": DACO, "SimpleACO": SimpleACO, "NodeACO": NodeACO,
            "PSO": PSO, "ACACO": ACACO, "MEACO": MEACO}


def slug(name):
    return name.lower().replace("-", "_")


def run_stem(dist, n, seed):
    return f"{dist}_n{n}_seed{seed}"


def run_paths(algo_name, dist, n, seed):
    group = "d_aco" if algo_name == "D-ACO" else "other_algorithms"
    base = OUT / "raw_data" / group / slug(algo_name)
    stem = run_stem(dist, n, seed)
    return base / f"{stem}.csv", base / f"{stem}.json", base / f"{stem}_sensor-energy.csv"


def map_path(dist, n, seed):
    return OUT / "configs" / "maps" / f"{run_stem(dist, n, seed)}.pkl"


def build_map(cfg, dist, n, seed):
    from map_gen import gen
    from point import Point
    net = cfg["network"]
    path = map_path(dist, n, seed)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = gen(width=net["width"], height=net["height"], depth=net["depth"],
                  num_sensors=n, energy=net["init_energy"], radius=net["radius"],
                  base_pos=Point(*net["base_pos"]), distribution=dist,
                  num_cluster_points=net["num_cluster_points"], seed=seed)
        with path.open("wb") as f:
            pickle.dump(raw, f)
    return path


def greedy_connected(network, candidates):
    """Nodes in `candidates` with a greedy forwarding path to the sink through
    other connected candidates (each hop <= radius and strictly closer)."""
    ok = []
    for v in sorted(candidates, key=lambda i: network.base_dists[i]):
        dv = network.base_dists[v]
        row = network.dist_matrix[v]
        if dv <= network.radius or any(
                row[u] <= network.radius and network.base_dists[u] < dv for u in ok):
            ok.append(v)
    return set(ok)


class RecordingAlgorithm:
    """Proxy between the Simulator and the real algorithm.

    Forwards plan_round unchanged while every live node is routable; handles
    the extended-mode disconnection rule (see module docstring) and logs what
    the Simulator does with the result. The Simulator passes the same residual
    list every round and mutates it in place, so the energy actually drawn in
    a round is sum(min(residual_before, demand))."""

    def __init__(self, inner, evaluator, network):
        self.inner = inner
        self.name = inner.name
        self.evaluator = evaluator
        self.network = network
        self.rounds = []
        self.residual_ref = None
        self.disconnected = set()
        self.first_failure_round = None   # strict run ends before this round
        self.stop_detail = None

    def plan_round(self, live_sensors, residual_e):
        self.residual_ref = residual_e
        t = len(self.rounds)
        active = [i for i in live_sensors if i not in self.disconnected]
        retried = False
        root, consumption = (self.inner.plan_round(active, residual_e)
                             if active else (None, {}))
        if root is None and active:
            if self.first_failure_round is None:
                self.first_failure_round = t
            connected = greedy_connected(self.network, active)
            newly = set(active) - connected
            if newly:
                self.disconnected |= newly
                active = [i for i in active if i in connected]
                retried = True
                root, consumption = (self.inner.plan_round(active, residual_e)
                                     if active else (None, {}))
        if root is None:
            self.stop_detail = ("no_connected_nodes" if not active
                                else "no_feasible_routing")
            return root, consumption

        used = consumption
        if not used:  # same fallback the Simulator applies
            used, _ = self.evaluator.energy_consumption(
                root, self.network.dist_matrix, self.network.base_dists)
        after = list(residual_e)
        drawn = 0.0
        for idx, e in used.items():
            take = min(after[idx], e)
            after[idx] -= take
            drawn += take
        alive_after = [after[i] for i in live_sensors if after[i] > 0]
        n_ch = n_relay = 0
        stack = [root]
        while stack:
            node = stack.pop()
            n_ch += node.isCH
            n_relay += node.isRelay
            stack.extend(node.nxts)
        mean = sum(alive_after) / len(alive_after) if alive_after else 0.0
        var = (sum((x - mean) ** 2 for x in alive_after) / len(alive_after)
               if alive_after else 0.0)
        self.rounds.append({
            "connected_alive_nodes": sum(1 for i in active if after[i] > 0),
            "disconnected_alive_nodes": sum(1 for i in self.disconnected if after[i] > 0),
            "strict_mode_round": self.first_failure_round is None,
            "retried_after_disconnect": retried,
            "round_energy_consumed": drawn,
            "residual_energy": sum(after),
            "residual_std_alive": var ** 0.5,
            "num_cluster_heads": n_ch,
            "num_relays": n_relay,
        })
        return root, consumption


def diagnostics(algo):
    keys = ("total_clustering_attempts", "failed_clustering_attempts",
            "total_routing_attempts", "failed_routing_attempts",
            "calibration_attempts", "calibration_routing_attempts", "calibration_feasible")
    out = {k: getattr(algo, k) for k in keys if hasattr(algo, k)}
    out["class"] = f"{type(algo).__module__}.{type(algo).__qualname__}"
    clustering = getattr(algo, "clustering", None)
    if clustering is not None:
        out["clustering_class"] = f"{type(clustering).__module__}.{type(clustering).__qualname__}"
        for k in ("iteration", "rho"):
            if isinstance(getattr(clustering, k, None), (int, float)):
                out[f"clustering_{k}"] = getattr(clustering, k)
        pher = getattr(clustering, "pheromone", None)
        if isinstance(pher, list) and pher and not isinstance(pher[0], list):
            out["pheromone_min"] = min(pher)
            out["pheromone_max"] = max(pher)
            out["pheromone_mean"] = sum(pher) / len(pher)
    refs = getattr(algo, "references", None)
    if refs is not None:
        out["fitness_reference_energy"] = refs.energy
        out["fitness_reference_penalty"] = refs.penalty
    return out


def run_one(class_key, dist, n, seed):
    import pandas as pd
    from evaluate import Evaluator
    from hparameter import HyperParameters
    from network import NetworkInstance
    from simulate import Simulator

    cfg = load_config()
    cls = algorithm_classes()[class_key]
    csv_path, json_path, sensor_path = run_paths(cls.name, dist, n, seed)
    if json_path.exists():
        return cls.name, dist, n, seed, "skipped (exists)"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    lock = json_path.with_suffix(".lock")
    if not acquire_lock(lock):
        return cls.name, dist, n, seed, "skipped (running in another process)"
    try:
        return _run_locked(cfg, cls, class_key, dist, n, seed)
    finally:
        lock.unlink(missing_ok=True)


def acquire_lock(lock):
    """Let several runner processes share the job list without duplicates.
    A lock whose owner PID no longer exists is stale and is taken over."""
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                os.kill(int(lock.read_text().strip() or 0), 0)
                return False  # owner alive
            except (ProcessLookupError, ValueError):
                lock.unlink(missing_ok=True)
                continue
            except PermissionError:
                return False
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
        return True
    return False


def _run_locked(cfg, cls, class_key, dist, n, seed):
    import pandas as pd
    from evaluate import Evaluator
    from hparameter import HyperParameters
    from network import NetworkInstance
    from simulate import Simulator

    csv_path, json_path, sensor_path = run_paths(cls.name, dist, n, seed)
    log_path = OUT / "logs" / slug(cls.name) / f"{run_stem(dist, n, seed)}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    network = NetworkInstance.from_pickle(build_map(cfg, dist, n, seed))
    hp = HyperParameters()
    hp.T_max = cfg["T_max_extended"]
    simulator = Simulator(network, hp)
    algorithm = cls(network, hp, seed=seed)
    recorder = RecordingAlgorithm(algorithm, Evaluator(hp), network)

    start = time.perf_counter()
    with log_path.open("w") as log, contextlib.redirect_stdout(log):
        history = simulator.run(recorder, verbose=True)
    runtime = time.perf_counter() - start

    extra = pd.DataFrame(recorder.rounds)
    assert len(extra) == len(history), "recorder and simulator round counts differ"
    df = pd.concat([history.reset_index(drop=True), extra], axis=1)
    df.insert(1, "round_number", df["round"] + 1)  # 1-based: rounds completed
    df = df.rename(columns={"round_energy": "round_energy_demand"})
    df["cumulative_energy"] = df["round_energy_consumed"].cumsum()
    df.to_csv(csv_path, index=False)
    simulator.sensor_energy_totals.to_csv(sensor_path, index=False)

    total_init = network.init_energy * network.N
    final_residual = sum(recorder.residual_ref) if recorder.residual_ref is not None else total_init
    rounds = len(df)
    alive_final = int(df["alive_nodes"].iloc[-1]) if rounds else n
    if rounds and alive_final == 0:
        stop = "all_nodes_dead"
    elif rounds >= hp.T_max:
        stop = "T_max_reached"
    else:
        stop = recorder.stop_detail or "no_feasible_routing"
    strict_rounds = (recorder.first_failure_round if recorder.first_failure_round is not None
                     else rounds)
    strict_rounds = min(strict_rounds, cfg["T_max_strict"])
    if recorder.first_failure_round is not None and recorder.first_failure_round < cfg["T_max_strict"]:
        strict_stop = "no_feasible_routing"
    elif strict_rounds and int(df["alive_nodes"].iloc[strict_rounds - 1]) == 0:
        strict_stop = "all_nodes_dead"
    else:
        strict_stop = "T_max_reached"
    cum = float(df["cumulative_energy"].iloc[-1]) if rounds else 0.0
    meta = {
        "algorithm": cls.name, "class_key": class_key, "distribution": dist,
        "n_nodes": n, "seed": seed, "map_seed": seed,
        "map_file": str(map_path(dist, n, seed).relative_to(OUT)),
        "rounds_completed": rounds, "stop_reason": stop, "alive_final": alive_final,
        "disconnected_final": len(recorder.disconnected),
        "strict_rounds_completed": strict_rounds, "strict_stop_reason": strict_stop,
        "runtime_s": runtime, "T_max_extended": hp.T_max, "T_max_strict": cfg["T_max_strict"],
        "total_initial_energy": total_init,
        "final_residual_energy_simulator": final_residual,
        "cumulative_energy_logged": cum,
        "energy_balance_error": (total_init - final_residual) - cum,
        "diagnostics": diagnostics(algorithm),
    }
    with json_path.open("w") as f:
        json.dump(meta, f, indent=2)
    return cls.name, dist, n, seed, f"{rounds} rounds ({stop}), strict {strict_rounds}, {runtime:.0f}s"


def all_jobs(cfg, algos, seeds, nodes=None, dists=None):
    jobs = []
    for ms in cfg["map_sets"]:
        if dists and ms["distribution"] not in dists:
            continue
        for n in ms["node_counts"]:
            if nodes and n not in nodes:
                continue
            for s in seeds:
                for a in algos:
                    jobs.append((a, ms["distribution"], n, s))
    # Priority (cheapest-first after the round-based configuration), so that
    # complete groups of seeds become available early if the batch cannot
    # finish: focus config, then focus-distribution sizes up to the focus
    # size + 50, then the other distributions, then the largest sizes.
    focus = cfg["lifetime_round_config"]

    def rank(job):
        _, dist, n, seed = job
        if dist == focus["distribution"] and n == focus["n_nodes"]:
            tier = 0
        elif dist == focus["distribution"] and n <= focus["n_nodes"] + 50:
            tier = 1
        elif dist != focus["distribution"]:
            tier = 2
        else:
            tier = 3
        return (tier, n, seed, dist)
    return sorted(jobs, key=rank)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-maps", action="store_true", help="only create the map files")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--nodes", type=int, nargs="*")
    parser.add_argument("--seeds", type=int, nargs="*")
    parser.add_argument("--distributions", nargs="*")
    parser.add_argument("--algorithms", nargs="*", help="class keys, e.g. DACO PSO")
    args = parser.parse_args()

    cfg = load_config()
    algos = args.algorithms or cfg["algorithms"]
    seeds = args.seeds or cfg["seeds"]
    jobs = all_jobs(cfg, algos, seeds, args.nodes, args.distributions)
    print(f"{len(jobs)} runs: algorithms={algos} seeds={seeds}", flush=True)
    if args.dry_run:
        for j in jobs:
            print("  ", j)
        return
    for _, dist, n, s in jobs:  # build maps before workers could race on them
        build_map(cfg, dist, n, s)
    if args.build_maps:
        return
    with ProcessPoolExecutor(args.workers, mp_context=get_context("spawn")) as pool:
        futures = {pool.submit(run_one, *job): job for job in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            job = futures[fut]
            try:
                name, dist, n, s, msg = fut.result()
                print(f"[{i}/{len(jobs)}] {name} {dist} N={n} seed={s}: {msg}", flush=True)
            except Exception as exc:  # report and keep the batch going
                print(f"[{i}/{len(jobs)}] FAILED {job}: {exc!r}", flush=True)


if __name__ == "__main__":
    main()
