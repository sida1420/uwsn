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
from algorithms.pso import PSO

SEED = random.randint(0,100)

ALGORITHMS = [
    ACACO,
    SimpleACO,
    PSO,
]


def create_algorithm(algo_cls, network, hparameters):
    if algo_cls is ACACO:
        return ACACO(network, hparameters, seed=SEED)

    return algo_cls(network, hparameters)


def main(map_path="map.pkl"):


    network = NetworkInstance.from_pickle(map_path)
    hparameters = HyperParameters()

    results = {}

    os.makedirs("../runs", exist_ok=True)

    for algo_cls in ALGORITHMS:
        # SimpleACO (and later PSO) draw from the global RNG; reseed so each
        # algorithm's run is reproducible regardless of run order.
        random.seed(SEED)

        simulator = Simulator(network, hparameters)

        algorithm = create_algorithm(
            algo_cls,
            network,
            hparameters,
        )

        history = simulator.run(algorithm)

        now = datetime.now()
        datetime_string = now.strftime("%Y%m%d%H")

        

        history.to_csv(
            f"runs/{datetime_string}_{SEED}_{algorithm.name}.csv",
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
    main()
