"""Run: python -B compare.py --variants tuned old new --seeds 0 1 2 3 4."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout
from dataclasses import asdict, is_dataclass
import hashlib
import gzip
from io import StringIO
import json
from pathlib import Path
import platform
import random
import sys
import time
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from algorithms.aco import SimpleACO
from algorithms.ac_aco import ACACO
from algorithms.clustering.aco.parameters import ACOParameters
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from route_metrics import inspect_route


def result_paths(directory):
    paths = {p.stem: p for p in directory.glob("*.json")}
    paths.update({p.name.removesuffix(".json.gz"): p for p in directory.glob("*.json.gz")})
    return sorted(paths.values())


def read_result(path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as file:
            return json.load(file)
    return json.loads(path.read_text(encoding="utf-8"))


def load_algorithm(directory="baseline", prefix="baseline"):
    replacements = {
        "from algorithms.clustering.ac_aco.parameters import": f"from {prefix}_parameters import",
        "from algorithms.clustering.ac_aco.ac_aco import": f"from {prefix}_clustering import",
    }
    for name, filename in (("parameters", "parameters.py"),
                           ("clustering", "clustering.py"), ("algorithm", "algorithm.py")):
        source = (HERE / directory / filename).read_text(encoding="utf-8")
        for old, new in replacements.items():
            source = source.replace(old, new)
        module = types.ModuleType(prefix + "_" + name)
        sys.modules[module.__name__] = module
        exec(compile(source, str(HERE / directory / filename), "exec"), module.__dict__)
    return sys.modules[prefix + "_algorithm"].ACACO


def old_algorithm():
    return load_algorithm()


def run_case(variant, seed, limit, tag):
    random.seed(seed)
    net, hp = NetworkInstance.from_pickle(ROOT / "map.pkl"), HyperParameters()
    if variant in ("old", "old-q", "old-edge", "old-both"):
        cls = old_algorithm()
        from dataclasses import replace
        base = sys.modules["baseline_parameters"].ACACOParameters()
        overrides = {}
        if variant in ("old-q", "old-both"):
            overrides["Q"] = 0.07
        if variant in ("old-edge", "old-both"):
            overrides["energy_cost_exponent"] = 0.5
        algo = cls(net, hp, params=replace(base, **overrides), seed=seed)
    elif variant == "new":
        algo = ACACO(net, hp, seed=seed)
    elif variant == "normalized":
        algo = load_algorithm("trial-total-mass", "trial")(net, hp, seed=seed)
    else:
        params = ACOParameters()
        if variant in ("aco-before", "aco-old-q"):
            params.Q = 100.0
        if variant in ("aco-before", "aco-old-edge"):
            params.beta = 1.0
        algo = SimpleACO(net, hp, aco_params=params, seed=seed)
        if variant in ("aco-before", "aco-no-ant-deposit"):
            deposit = algo.clustering.deposit
            algo.clustering.deposit = lambda heads, cost, per_ant=True: (
                None if per_ant else deposit(heads, cost, per_ant=False))
    residual, live = [net.init_energy] * net.N, list(range(net.N))
    rows, candidates = [], []
    state_holder = []
    evaluate = algo.evaluator.energy_consumption
    def observe(*args):
        result = evaluate(*args)
        candidates.append(result[1])
        return result
    algo.evaluator.energy_consumption = observe
    pre_round = algo.clustering.pre_round
    def observe_state(*args):
        state = pre_round(*args)
        state_holder[:] = [state]
        return state
    algo.clustering.pre_round = observe_state
    started, reason, first_death = time.perf_counter(), "T_max", None
    for index in range(min(limit, hp.T_max)):
        candidates.clear()
        chaos_before = tuple(getattr(algo.clustering, "chaos", ()))
        with redirect_stdout(StringIO()):
            root, consumption = algo.plan_round(live, residual)
        if root is None:
            reason = "no_feasible_route"
            break
        metrics = inspect_route(root, live, net, Evaluator(hp), consumption)
        before = sum(residual)
        for i, cost in consumption.items():
            residual[i] = max(0.0, residual[i] - cost)
        live = [i for i in live if residual[i] > 0]
        if len(live) < net.N and first_death is None:
            first_death = index + 1
        state = state_holder[0]
        controls = ({k: getattr(state, k) for k in ("beta", "rho", "strength")}
                    if hasattr(state, "rho") else {})
        row = dict(round=index, alive_nodes=len(live), energy=sum(consumption.values()),
                   residual_energy=sum(residual), depleted_energy=before-sum(residual),
                   candidate_costs=list(candidates),
                   convergence=[min(candidates[:i+1]) for i in range(len(candidates))],
                   chaos_changed=chaos_before != tuple(getattr(algo.clustering, "chaos", ())),
                   **metrics, **controls)
        rows.append(row)
        if (index + 1) % 500 == 0:
            print(json.dumps(dict(progress=True, variant=variant, seed=seed,
                                  rounds=index+1, alive=len(live),
                                  seconds=time.perf_counter()-started)), flush=True)
        if not live:
            reason = "all_dead"
            break
    if len(rows) == limit and limit < hp.T_max:
        reason = "measurement_limit"
    params = asdict(algo.params) if is_dataclass(algo.params) else vars(algo.params)
    result = dict(variant=variant, seed=seed, rounds=len(rows), stop_reason=reason,
                  first_death=first_death, total_energy=sum(r["energy"] for r in rows),
                  residual_energy=sum(residual), alive_nodes=len(live),
                  common_100_energy=(sum(r["energy"] for r in rows[:100])
                                     if len(rows) >= 100 else None),
                  seconds=time.perf_counter()-started, parameters=params,
                  hyperparameters=vars(hp), python=platform.python_version(),
                  map_sha256=hashlib.sha256((ROOT / "map.pkl").read_bytes()).hexdigest(),
                  rows=rows)
    target = HERE / "results" / tag / f"{variant}-{seed}.json.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(target, "wt", encoding="utf-8") as file:
        json.dump(result, file, separators=(",", ":"))
    return {k: v for k, v in result.items() if k not in ("rows", "parameters", "hyperparameters")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", nargs="+", default=["tuned", "old", "new"])
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(5)))
    parser.add_argument("--rounds", type=int, default=3000)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--tag", help="Output group; defaults to lifetime or rounds-N.")
    args = parser.parse_args()
    tag = args.tag or ("lifetime" if args.rounds == HyperParameters().T_max else f"rounds-{args.rounds}")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(run_case, variant, seed, args.rounds, tag)
                for variant in args.variants for seed in args.seeds]
        for job in as_completed(jobs):
            print(json.dumps(job.result()), flush=True)
