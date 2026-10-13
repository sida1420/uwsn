import pandas as pd
from time import perf_counter

from evaluate import Evaluator

from visual import Visual
class Simulator:
    """
    Runs an Algorithm round by round on a NetworkInstance until either
    every node has died, no feasible routing is found, or
    hparameters.T_max rounds have passed, tracking residual energy and
    how many nodes stay alive.

    Each call to run() gives the algorithm a fresh copy of residual
    energy, so multiple algorithms can be compared fairly on the same
    network (see run.py).

    Algorithm.plan_round returns (root, consumption); the Evaluator is
    only used as a fallback when an algorithm returns a tree without its
    per-node consumption.
    """

    def __init__(self, network, hparameters):
        self.visualizer = Visual(network.width, network.height, network.depth, network.sensors, network.base_pos)
        self.network = network
        self.hparameters = hparameters
        self.evaluator = Evaluator(hparameters)
        self.sensor_energy_history = pd.DataFrame(
            columns=["round", *[f"sensor_{idx}" for idx in range(network.N)]]
        )

    def run(self, algorithm, verbose=True):
        residual_e = [self.network.init_energy] * self.network.N
        live_nodes = list(range(self.network.N))
        history = []
        sensor_energy_history = []

        for t in range(self.hparameters.T_max):
            round_start = perf_counter()
            root, consumption = algorithm.plan_round(live_nodes, residual_e)
            if root is None:
                if verbose:
                    print(f"[{algorithm.name}] round {t}: no feasible routing found, stopping")
                break

            if consumption:
                total = sum(consumption.values())
            else:
                consumption, total = self.evaluator.energy_consumption(
                    root, self.network.dist_matrix, self.network.base_dists
                )

            if total <= 0:
                self.visualizer.clear_routes()
                self.visualizer.route(root)
                self.visualizer.save(f"error_{algorithm.name}_round{t}.png")
                self.visualizer.show()
                assert False, f"Total energy consumption is non-positive: {total}"

            for idx, e in consumption.items():
                residual_e[idx] = max(0.0, residual_e[idx] - e)

            live_nodes = [i for i in live_nodes if residual_e[i] > 0]

            sensor_energy_history.append({
                "round": t,
                **{
                    f"sensor_{idx}": consumption.get(idx, 0.0)
                    for idx in range(self.network.N)
                },
            })

            history.append({
                "round": t,
                "alive_nodes": len(live_nodes),
                "round_energy": total,
                "time": perf_counter() - round_start,
            })

            if verbose and t % 100 == 0:
                print(f"[{algorithm.name}] round {t}: {len(live_nodes)} alive, "
                      f"energy used this round {total:.6f}", flush=True)

            if not live_nodes:
                if verbose:
                    print(f"[{algorithm.name}] round {t}: network died")
                break

        self.sensor_energy_history = pd.DataFrame(
            sensor_energy_history,
            columns=["round", *[f"sensor_{idx}" for idx in range(self.network.N)]],
        )
        return pd.DataFrame(history, columns=["round", "alive_nodes", "round_energy", "time"])
