"""
Top-level entry point: load the network map, then run and compare one
or more algorithms on it.

To try a new algorithm in the future: subclass Algorithm
(see algorithms/base/base.py), then add the class to ALGORITHMS below --
nothing else in this file needs to change (unless it needs extra
constructor arguments, see create_algorithm).
"""
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
import random
from pathlib import Path

from hparameter import HyperParameters
from network import NetworkInstance
from simulate import Simulator

from algorithms.aco import SimpleACO
from algorithms.ac_aco import ACACO
from algorithms.d_aco import DACO
from algorithms.node_aco import NodeACO
from algorithms.pso import PSO

SEED = None  # optional programmatic default; main prints the chosen run seed

ALGORITHMS = [
    PSO,
    DACO,
    SimpleACO,
    ACACO,
    NodeACO,
]


def _filename_value(value):
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number).replace(".", "p")


def environment_prefix(network):
    return "_".join((
        _filename_value(network.width),
        _filename_value(network.height),
        _filename_value(network.depth),
        str(network.N),
        network.distribution,
    ))


def create_algorithm(algo_cls, network, hparameters, seed=None):
    return algo_cls(network, hparameters, seed=SEED if seed is None else seed)


def run_algorithm(algo_cls, network, hparameters, seed, run_dir, run_prefix):
    simulator = Simulator(network, hparameters)
    algorithm = create_algorithm(algo_cls, network, hparameters, seed=seed)
    print(f"[{algorithm.name}] started", flush=True)
    history = simulator.run(algorithm)
    history.to_csv(run_dir / f"{run_prefix}_{algorithm.name}.csv", index=False)
    print(f"[{algorithm.name}] finished: {len(history)} rounds", flush=True)
    return algorithm.name, history


def main(map_path="map.pkl", seed=None):


    network = NetworkInstance.from_pickle(map_path)
    hparameters = HyperParameters()
    run_seed = seed if seed is not None else SEED
    if run_seed is None: run_seed = random.SystemRandom().randint(1, 99)
    if type(run_seed) is not int or not 1 <= run_seed <= 99:
        raise ValueError('run seed must be an integer from 1 to 99')
    print(f'Run seed: {run_seed:02d}')

    results = {}

    run_dir = Path("runs")
    run_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H")
    run_prefix = f"{environment_prefix(network)}_{timestamp}_{run_seed:02d}"

    with ProcessPoolExecutor(max_workers=2, mp_context=get_context("spawn")) as pool:
        futures = [
            pool.submit(run_algorithm, algo_cls, network, hparameters,
                        run_seed, run_dir, run_prefix)
            for algo_cls in ALGORITHMS
        ]
        completed = {}
        for future in as_completed(futures):
            name, history = future.result()
            completed[name] = history
        for future in futures:
            name, _ = future.result()
            results[name] = completed[name]

    summarize(results)
    return results


def summarize(results):
    print("\n=== Comparison ===")

    for name, history in results.items():
        rounds_survived = len(history)

        total_energy = history["round_energy"].sum() if rounds_survived else 0.0

        print(
            f"{name}: "
            f"{rounds_survived} rounds survived, "
            f"{total_energy:.4f} total energy used"
        )


if __name__ == "__main__":
    main()
