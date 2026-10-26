"""Budgeted paper experiments. Five algorithms, paired maps, priority for N=150.

python src/tmp_experiments.py --dry-run
python src/tmp_experiments.py --prepare-only
python src/tmp_experiments.py --campaign runs/paper_<id>

Main CSVs have one common T_max. Short pilots live in diagnostics/csv.
Only complete five-algorithm cohorts are published. A frozen source snapshot,
map hashes, parameters, explicit map/algorithm seeds and termination reasons
are saved. Resume skips completed work; interrupted jobs restart from round 0.
The elapsed budget is cumulative across resumes. Create a STOP file in the
campaign folder to stop its owned workers. Original map.pkl/run.py are intact.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import shutil
import statistics
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ("SimpleACO", "NodeACO", "PSO", "AC-ACO", "D-ACO")
SEEDS = (17, 29, 41, 53, 67, 79)
FIELDS = ("round", "alive_nodes", "round_energy", "time", "round_spent_energy",
          "residual_energy_mean", "residual_energy_sd")


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configuration_name(size, count, distribution):
    return "_".join(map(str, (*size, count, distribution)))


def historical_rates(root=ROOT):
    """Trim pauses only for scheduling estimates, never from scientific CSVs."""
    samples = {}
    for path in (root / "runs").glob("*.csv"):
        if path.name.endswith("_sensor-energy.csv"):
            continue
        try:
            parts = path.stem.rsplit("_", 2)
            n, algo = int(parts[0].split("_")[3]), parts[-1]
            if algo not in ALGORITHMS:
                continue
            with path.open(newline="", encoding="utf-8-sig") as stream:
                values = [float(r["time"]) for r in csv.DictReader(stream) if r.get("time")]
            samples.setdefault((n, algo), []).extend(t for t in values if math.isfinite(t) and t > 0)
        except (ValueError, KeyError, IndexError):
            continue
    rates = {}
    for (n, algo), values in samples.items():
        values.sort()
        rates[f"{n}:{algo}"] = statistics.mean(values[:max(1, int(len(values)*.99))])
    return rates


def seconds_per_round(rates, n, algo):
    if f"{n}:{algo}" in rates:
        return rates[f"{n}:{algo}"]
    known = [(int(k.split(":")[0]), v) for k, v in rates.items() if k.split(":")[1] == algo]
    if not known:
        return .15 * (n/100)**2
    nearest, rate = min(known, key=lambda pair: abs(math.log(n/pair[0])))
    return rate * (n/nearest)**2


def cohort_seconds(cohort, rates, workers=2):
    costs = [15 + 1.4*cohort["horizon"]*seconds_per_round(rates, cohort["nodes"], a) for a in ALGORITHMS]
    lanes = [0.] * workers
    for cost in sorted(costs, reverse=True):
        lanes[min(range(workers), key=lanes.__getitem__)] += cost
    return max(lanes)


def configurations(horizon=3500):
    result = []
    def add(n, dist, seed, tier, size=(500, 500, 500), rounds=None, phase="main"):
        result.append(dict(size=list(size), nodes=n, distribution=dist, map_seed=seed,
                           algorithm_seed=(seed*37) % 99+1, horizon=rounds or horizon,
                           tier=tier, phase=phase, name=configuration_name(size, n, dist)))
    # Replace sparse 800 m trials with approximately density-matched deployments.
    for n in (400, 600):
        add(n, "clustered", SEEDS[0], "large-field pilot", (800, 800, 800), 100, "diagnostic")
    for seed in SEEDS[:2]:
        for n, dist in ((150, "uniform"), (100, "uniform"), (150, "clustered"), (100, "clustered")):
            add(n, dist, seed, "core curves")
        for n in (50, 200):
            if n == 50 or seed == SEEDS[0]:
                add(n, "clustered", seed, "node-count sweep")
    for seed in SEEDS[2:]:
        for n in (150, 100):
            add(n, "uniform", seed, "extra core repeats")
        if seed in SEEDS[2:4]:
            for n in (150, 100):
                add(n, "clustered", seed, "extra clustered repeats")
    add(400, "clustered", SEEDS[0], "optional large-field lifetime", (800, 800, 800))
    for n in (100, 150):
        add(n, "clustered", SEEDS[0], "geometry check", (300, 300, 300), 1000, "diagnostic")
        add(n, "normal", SEEDS[0], "distribution check", rounds=1000, phase="diagnostic")
    for i, cohort in enumerate(result):
        cohort["id"] = f"c{i:03d}"
    return result


def planned_cohorts(cohorts, rates, budget_seconds, workers):
    used, selected, deferred = 0., [], []
    for cohort in cohorts:
        seconds = cohort_seconds(cohort, rates, workers)
        record = dict(cohort, estimated_seconds=seconds)
        if used+seconds <= max(0., budget_seconds-300):
            selected.append(record)
            used += seconds
        else:
            deferred.append(record)
    return selected, deferred, used


def connected_to_sink(raw):
    """Necessary physical feasibility; never resample to choose nicer seeds."""
    points, radius = raw["sensors"], raw["radius"]
    reached = {i for i, p in enumerate(points) if abs(p-raw["base_pos"]) <= radius}
    frontier = list(reached)
    while frontier:
        i = frontier.pop()
        for j in range(len(points)):
            if j not in reached and abs(points[i]-points[j]) <= radius:
                reached.add(j)
                frontier.append(j)
    return len(reached) == len(points), len(reached)


def create_campaign(args):
    import numpy as np
    from map_gen import gen
    from point import Point
    with Path(args.map).open("rb") as stream:
        current = pickle.load(stream)
    now = datetime.now(timezone(timedelta(hours=7)))
    folder = ROOT / "runs" / f"paper_{now:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    folder.mkdir(parents=True)
    for name in ("csv", "maps", "work", "diagnostics/csv", "source/src"):
        (folder/name).mkdir(parents=True)
    sources = {}
    for src in (ROOT/"src").rglob("*.py"):
        if "__pycache__" in src.parts:
            continue
        relative = src.relative_to(ROOT/"src")
        target = folder/"source"/"src"/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        sources[str(relative)] = digest(target)
    config = dict(version=1, created_utc=datetime.now(timezone.utc).isoformat(), timestamp=f"{now:%Y%m%d%H}",
                  original_map_sha256=digest(args.map), source_hashes=sources, algorithms=list(ALGORITHMS),
                  workers=args.workers, budget_seconds=args.budget_hours*3600, horizon=args.horizon,
                  rates=historical_rates(), cohorts=configurations(args.horizon),
                  host_python=sys.executable, cpu_count=os.cpu_count(),
                  python_version=sys.version, numpy_version=np.__version__,
                  budget_policy="cumulative elapsed time across resumes; incomplete cohorts not published",
                  seed_policy="independent map seeds; explicit algorithm seed shared by comparators on each map")
    for cohort in config["cohorts"]:
        w, h, d = cohort["size"]
        sink = current["base_pos"]
        base = Point(sink.x*w/current["width"], sink.y*h/current["height"], sink.z*d/current["depth"])
        raw = gen(w, h, d, cohort["nodes"], current["init_energy"], current["radius"], base_pos=base,
                  seed=cohort["map_seed"], distribution=cohort["distribution"], num_cluster_points=5)
        path = folder/"maps"/f"{cohort['id']}.pkl"
        with path.open("wb") as stream:
            pickle.dump(raw, stream)
        feasible, reachable = connected_to_sink(raw)
        cohort.update(map_path=str(path), map_sha256=digest(path), connected=feasible,
                      reachable_nodes=reachable, energy=current["init_energy"], radius=current["radius"])
    atomic_json(folder/"campaign.json", config)
    atomic_json(folder/"state.json", dict(spent_seconds=0., completed=[], outcomes={}, stop_reason="prepared"))
    return folder, config


def algorithm_class(name):
    from algorithms.aco import SimpleACO
    from algorithms.node_aco import NodeACO
    from algorithms.pso import PSO
    from algorithms.ac_aco import ACACO
    from algorithms.d_aco import DACO
    return {a.name: a for a in (SimpleACO, NodeACO, PSO, ACACO, DACO)}[name]


def simulate_job(job, clock=time.monotonic):
    """Same communication/energy semantics as Simulator, without GUI overhead."""
    from evaluate import Evaluator
    from hparameter import HyperParameters
    from network import NetworkInstance
    folder = Path(job["folder"])
    folder.mkdir(parents=True, exist_ok=True)
    begin = clock()
    network = NetworkInstance.from_pickle(job["cohort"]["map_path"])
    hp = HyperParameters()
    hp.T_max = job["cohort"]["horizon"]
    algorithm = algorithm_class(job["algorithm"])(network, hp, seed=job["cohort"]["algorithm_seed"])
    parameters = dict(vars(algorithm.params))
    evaluator = Evaluator(hp)
    residual = [network.init_energy]*network.N
    live, totals, spent_totals = list(range(network.N)), [0.]*network.N, [0.]*network.N
    history_path = folder/"history.partial.csv"
    reason, count, fnd = "horizon", 0, None
    with history_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for t in range(hp.T_max):
            if clock() >= job["deadline"]:
                reason = "budget_interrupted"
                break
            start = time.perf_counter()
            root, costs = algorithm.plan_round(live, residual)
            if root is None:
                reason = "no_feasible_route"
                break
            if not costs:
                costs, _ = evaluator.energy_consumption(root, network.dist_matrix, network.base_dists)
            demand = sum(costs.values())
            if not math.isfinite(demand) or demand <= 0 or any(not math.isfinite(e) or e < 0 for e in costs.values()):
                raise ValueError("Invalid selected-round energy")
            spent = 0.
            for i, cost in costs.items():
                charged = min(residual[i], cost)
                spent += charged
                spent_totals[i] += charged
                residual[i] = max(0., residual[i]-cost)
                totals[i] += cost
            live = [i for i in live if residual[i] > 0]
            elapsed = time.perf_counter()-start
            count = t+1
            if fnd is None and len(live) < network.N:
                fnd = count
            mean = statistics.mean(residual)
            writer.writerow(dict(round=t, alive_nodes=len(live), round_energy=demand, time=elapsed,
                                 round_spent_energy=spent, residual_energy_mean=mean,
                                 residual_energy_sd=statistics.pstdev(residual, mu=mean)))
            if count % 25 == 0:
                stream.flush()
                atomic_json(folder/"progress.json", dict(completed_rounds=count, alive=len(live),
                            wall_seconds=clock()-begin, FND=fnd))
            if not live:
                reason = "all_nodes_dead"
                break
    status = "interrupted" if reason == "budget_interrupted" else "complete"
    if status == "complete":
        history_path.replace(folder/"history.csv")
        with (folder/"sensor-energy.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("sensor", "total_energy", "spent_energy", "residual_energy"))
            writer.writerows((f"sensor_{i}", totals[i], spent_totals[i], residual[i]) for i in range(network.N))
    result = dict(status=status, termination_reason=reason, completed_rounds=count, FND=fnd,
                  final_alive=len(live), wall_seconds=clock()-begin, horizon=hp.T_max,
                  map_sha256=job["cohort"]["map_sha256"], map_seed=job["cohort"]["map_seed"],
                  algorithm_seed=job["cohort"]["algorithm_seed"], algorithm=job["algorithm"],
                  parameters=parameters, hyperparameters=vars(hp))
    atomic_json(folder/"result.json", result)
    return result


def run_worker(path):
    job = load_json(path)
    try:
        simulate_job(job)
    except Exception:
        atomic_json(Path(job["folder"])/"result.json", dict(status="error", traceback=traceback.format_exc()))
        raise


def run_cohort(folder, config, cohort, deadline, record_tick):
    script = folder/"source"/"src"/"tmp_experiments.py"
    waiting = sorted(ALGORITHMS, key=lambda a: seconds_per_round(config["rates"], cohort["nodes"], a), reverse=True)
    active, results = {}, {}
    for algo in list(waiting):
        path = folder/"work"/cohort["id"]/algo/"result.json"
        if path.exists() and load_json(path).get("status") == "complete":
            results[algo] = load_json(path)
            waiting.remove(algo)
    try:
        while waiting or active:
            remaining = deadline-time.monotonic()
            if remaining <= 3 or (folder/"STOP").exists():
                break
            while waiting and len(active) < config["workers"] and remaining > 15:
                algo = waiting.pop(0)
                work = folder/"work"/cohort["id"]/algo
                work.mkdir(parents=True, exist_ok=True)
                atomic_json(work/"job.json", dict(folder=str(work), cohort=cohort, algorithm=algo, deadline=deadline-5))
                log = (work/"worker.log").open("a", encoding="utf-8")
                process = subprocess.Popen([sys.executable, "-B", str(script), "--worker", str(work/"job.json")],
                    stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                active[algo] = (process, log, work)
            for algo, (process, log, work) in list(active.items()):
                if process.poll() is not None:
                    log.close()
                    path = work/"result.json"
                    results[algo] = load_json(path) if path.exists() else dict(status="error", exitcode=process.returncode)
                    del active[algo]
            record_tick()
            time.sleep(min(.5, max(.01, deadline-time.monotonic())))
    finally:
        for process, log, work in active.values():
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
            log.close()
    return results


def publish_cohort(folder, config, cohort, results):
    destination = folder/("csv" if cohort["phase"] == "main" else "diagnostics/csv")
    for algo in ALGORITHMS:
        work = folder/"work"/cohort["id"]/algo
        prefix = f"{cohort['name']}_{config['timestamp']}_{cohort['map_seed']:02d}_{algo}"
        for source, suffix in (("history.csv", ".csv"), ("sensor-energy.csv", "_sensor-energy.csv")):
            target = destination/(prefix+suffix)
            temporary = target.with_suffix(target.suffix+".tmp")
            shutil.copy2(work/source, temporary)
            temporary.replace(target)
        atomic_json(destination/(prefix+".meta.json"), dict(results[algo], cohort_id=cohort["id"], phase=cohort["phase"]))


def run_campaign(folder):
    folder = Path(folder).resolve()
    config, state = load_json(folder/"campaign.json"), load_json(folder/"state.json")
    if tuple(config["algorithms"]) != ALGORITHMS:
        raise ValueError("Campaign algorithm set does not match this runner")
    for name, expected in config["source_hashes"].items():
        if digest(folder/"source"/"src"/name) != expected:
            raise ValueError(f"Source snapshot changed: {name}")
    lock = folder/"controller.lock"
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    config["rates"].update(state.get("planning_rates", {}))
    spent, begin = float(state["spent_seconds"]), time.monotonic()
    deadline = begin+max(0., config["budget_seconds"]-spent)
    def tick():
        state["spent_seconds"] = spent+time.monotonic()-begin
        state["planning_rates"] = config["rates"]
        atomic_json(folder/"state.json", state)
    state.update(controller_pid=os.getpid(), stop_reason="running")
    tick()
    try:
        for cohort in config["cohorts"]:
            if cohort["id"] in state["completed"]:
                continue
            if (folder/"STOP").exists() or deadline-time.monotonic() < 20:
                state["stop_reason"] = "stop_requested" if (folder/"STOP").exists() else "budget_exhausted"
                break
            if not cohort["connected"]:
                state["outcomes"][cohort["id"]] = dict(status="disconnected_deployment", reachable=cohort["reachable_nodes"], nodes=cohort["nodes"])
                state["completed"].append(cohort["id"])
                tick()
                continue
            expected = cohort_seconds(cohort, config["rates"], config["workers"])
            if expected+60 > deadline-time.monotonic():
                state["outcomes"][cohort["id"]] = dict(status="deferred_for_budget", estimated_seconds=expected)
                continue
            print(f"START {cohort['id']} {cohort['name']} seed={cohort['map_seed']} {cohort['phase']} T={cohort['horizon']} estimated={expected/60:.1f} min", flush=True)
            results = run_cohort(folder, config, cohort, deadline, tick)
            complete = len(results) == len(ALGORITHMS) and all(r.get("status") == "complete" for r in results.values())
            state["outcomes"][cohort["id"]] = dict(status="complete" if complete else "incomplete", results=results)
            if complete:
                publish_cohort(folder, config, cohort, results)
                state["completed"].append(cohort["id"])
                for algo, result in results.items():
                    if result["completed_rounds"] >= 50:
                        key = f"{cohort['nodes']}:{algo}"
                        config["rates"][key] = max(result["wall_seconds"]/result["completed_rounds"], config["rates"].get(key, 0))
            print(f"END {cohort['id']} {'complete' if complete else 'incomplete'} spent={(spent+time.monotonic()-begin)/3600:.2f} h", flush=True)
            tick()
            if not complete and deadline-time.monotonic() < 30:
                state["stop_reason"] = "budget_exhausted"
                break
        else:
            state["stop_reason"] = "queue_finished_or_deferred"
    finally:
        tick()
        state["controller_pid"] = None
        atomic_json(folder/"state.json", state)
        lock.unlink()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--map", type=Path, default=ROOT/"map.pkl")
    parser.add_argument("--budget-hours", type=float, default=9.)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--horizon", type=int, default=3500)
    args = parser.parse_args()
    if args.worker:
        run_worker(args.worker)
        return
    if not math.isfinite(args.budget_hours) or not 0 < args.budget_hours <= 9.75:
        parser.error("budget-hours must be in (0, 9.75], strictly below ten hours")
    if args.horizon < 1:
        parser.error("horizon must be positive")
    os.environ["MPLBACKEND"] = "Agg"
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    if args.campaign:
        run_campaign(args.campaign)
        return
    selected, deferred, estimate = planned_cohorts(configurations(args.horizon), historical_rates(), args.budget_hours*3600, args.workers)
    print(f"Five algorithms: {', '.join(ALGORITHMS)}; {args.workers} workers; hard elapsed budget {args.budget_hours:g} h")
    print(f"Conservative admitted-plan estimate: {estimate/3600:.2f} h; {len(selected)} cohorts ({len(selected)*5} jobs); {len(deferred)} deferred")
    for cohort in selected:
        print(f"  {cohort['name']:36} seed={cohort['map_seed']:02} T={cohort['horizon']:4} {cohort['phase']:10} {cohort['estimated_seconds']/60:6.1f} min | {cohort['tier']}")
    if args.dry_run:
        return
    folder, config = create_campaign(args)
    print(f"CAMPAIGN={folder}", flush=True)
    if not args.prepare_only:
        run_campaign(folder)


if __name__ == "__main__":
    main()
