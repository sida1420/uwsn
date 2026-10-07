"""
Top-level entry point: load the network map, then run and compare one
or more algorithms on it.

To try a new algorithm in the future: subclass Algorithm
(see algorithms/base/base.py), then add the class to ALGORITHMS below --
nothing else in this file needs to change (unless it needs extra
constructor arguments, see create_algorithm).
"""
from datetime import datetime
import argparse
import random
import os

from hparameter import HyperParameters
from network import NetworkInstance
from simulate import Simulator

from algorithms.aco import SimpleACO
from algorithms.ac_aco import ACACO
from algorithms.node_aco import NodeACO
from algorithms.pso import PSO

SEED = 0

ALGORITHMS = [
    NodeACO,
    PSO,
]


def create_algorithm(algo_cls, network, hparameters, seed=None):
    seed = SEED if seed is None else seed
    if algo_cls in (ACACO, SimpleACO):
        return algo_cls(network, hparameters, seed=seed)

    return algo_cls(network, hparameters)


def main(map_path="map.pkl", seed=None):


    network = NetworkInstance.from_pickle(map_path)
    hparameters = HyperParameters()
    seed = SEED if seed is None else seed

    results = {}

    os.makedirs("runs", exist_ok=True)

    for algo_cls in ALGORITHMS:
        # Legacy algorithms use the global RNG; ACO/AC-ACO receive this
        # same seed explicitly and own their random state.
        random.seed(seed)

        simulator = Simulator(network, hparameters)

        algorithm = create_algorithm(
            algo_cls,
            network,
            hparameters,
            seed=seed,
        )

        history = simulator.run(algorithm)

        now = datetime.now()
        datetime_string = now.strftime("%Y%m%d%H")

        

        history.to_csv(
            f"runs/{datetime_string}_{seed}_{algorithm.name}.csv",
            index=False,
        )

        results[algorithm.name] = history

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
    parser = argparse.ArgumentParser(description="Run a reproducible UWSN benchmark.")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--map", default="map.pkl", dest="map_path")
    main(**vars(parser.parse_args()))
