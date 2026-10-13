"""
Top-level entry point: load the network map, then run and compare one
or more algorithms on it.

To try a new algorithm in the future: subclass Algorithm
(see algorithms/base/base.py), then add the class to ALGORITHMS below --
nothing else in this file needs to change (unless it needs extra
constructor arguments, see create_algorithm).
"""
from datetime import datetime
import random
import os

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
    # NodeACO,
]


def create_algorithm(algo_cls, network, hparameters, seed=None):
    return algo_cls(network, hparameters, seed=SEED if seed is None else seed)


def main(map_path="map.pkl", seed=None):


    network = NetworkInstance.from_pickle(map_path)
    hparameters = HyperParameters()
    run_seed = seed if seed is not None else SEED
    if run_seed is None: run_seed = random.SystemRandom().randrange(2**32)
    if type(run_seed) is not int or run_seed < 0: raise ValueError('seed must be a nonnegative integer')
    print(f'Run seed: {run_seed}')

    results = {}

    os.makedirs("runs", exist_ok=True)

    for algo_cls in ALGORITHMS:
        simulator = Simulator(network, hparameters)

        algorithm = create_algorithm(
            algo_cls,
            network,
            hparameters,
            seed=run_seed,
        )

        history = simulator.run(algorithm)

        now = datetime.now()
        datetime_string = now.strftime("%Y%m%d%H")

        

        history.to_csv(
            f"runs/{datetime_string}_{run_seed}_{algorithm.name}.csv",
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--map', default='map.pkl')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()
    main(args.map, seed=args.seed)
