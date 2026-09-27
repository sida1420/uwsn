"""
Top-level entry point: load the network map, then run and compare one
or more clustering algorithms on it.

To try a new algorithm in the future: implement ClusteringAlgorithm
(see algorithms/base.py), then add the class to ALGORITHMS below --
nothing else in this file needs to change.
"""

from hparameter import HyperParameters
from network import NetworkInstance
from simulate import Simulator

from algorithms.aco.simple_aco import SimpleACO
from algorithms.pso.pso import PSOClustering
from algorithms.ac_aco import ACACOClustering, ACACOParameters


ALGORITHMS = [
    ACACOClustering,
    # SimpleACO,
    # PSOClustering,
]


def create_algorithm(algo_cls, network, hparameters):
    if algo_cls is ACACOClustering:
        return ACACOClustering(
            network,
            hparameters,
            ACACOParameters(random_seed=42),
        )

    return algo_cls(network, hparameters)


def main(map_path="map.pkl"):
    network = NetworkInstance.from_pickle(map_path)
    hparameters = HyperParameters()

    results = {}

    for algo_cls in ALGORITHMS:
        simulator = Simulator(network, hparameters)

        algorithm = create_algorithm(
            algo_cls,
            network,
            hparameters,
        )

        history = simulator.run(algorithm)

        history.to_csv(
            f"results_{algorithm.name}.csv",
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
