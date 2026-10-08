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
from pathlib import Path

from hparameter import HyperParameters
from network import NetworkInstance
from simulate import Simulator

from algorithms.aco import SimpleACO
from algorithms.ac_aco import ACACO
from algorithms.d_aco import DACO
from algorithms.node_aco import NodeACO
from algorithms.pso import PSO

SEED = random.randint(0,100)

ALGORITHMS = [
    DACO,
    ACACO,
    SimpleACO,
    NodeACO,
    PSO,
]


def _filename_value(value):
    """Format an environment value without filename-hostile punctuation."""
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number).replace(".", "p")


def environment_prefix(network):
    """Return W_H_D_node-count_distribution for run artifact names."""
    distribution = getattr(network, "distribution", "normal")
    return "_".join((
        _filename_value(network.width),
        _filename_value(network.height),
        _filename_value(network.depth),
        str(network.N),
        distribution,
    ))


def plot_convergence(results, output_path):
    """Save alive-node and smoothed round-energy convergence curves."""
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
    plotted = False

    for name, history in results.items():
        if history.empty:
            continue
        plotted = True
        rounds = history["round"]
        axes[0].plot(rounds, history["alive_nodes"], label=name)

        window = min(25, len(history))
        smoothed_energy = history["round_energy"].rolling(
            window=window,
            min_periods=1,
        ).mean()
        axes[1].plot(rounds, smoothed_energy, label=name)

    axes[0].set_ylabel("Alive sensors")
    axes[0].set_title("Network lifetime convergence")
    axes[0].grid(alpha=0.3)
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("Mean round energy (25-round window)")
    axes[1].set_title("Energy convergence")
    axes[1].grid(alpha=0.3)

    if plotted:
        axes[0].legend()
        axes[1].legend()

    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def create_algorithm(algo_cls, network, hparameters):
    if algo_cls is ACACO:
        return ACACO(network, hparameters, seed=SEED)

    return algo_cls(network, hparameters)


def main(map_path="map.pkl"):


    network = NetworkInstance.from_pickle(map_path)
    hparameters = HyperParameters()

    results = {}

    run_dir = Path("runs")
    run_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_prefix = f"{environment_prefix(network)}_{timestamp}_{SEED}"

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

        history.to_csv(
            run_dir / f"{run_prefix}_{algorithm.name}.csv",
            index=False,
        )

        results[algorithm.name] = history

    summarize(results)
    plot_convergence(results, run_dir / f"{run_prefix}_convergence.png")
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
