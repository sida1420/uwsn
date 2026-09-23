import pandas as pd

from evaluate import Evaluator


class Simulator:
    """
    Runs a ClusteringAlgorithm round by round on a NetworkInstance until
    either every node has died or hparameters.T_max rounds have passed,
    tracking residual energy and how many nodes stay alive.

    Each call to run() gives the algorithm a fresh copy of residual
    energy, so multiple algorithms can be compared fairly on the same
    network (see run.py).
    """

    def __init__(self, network, hparameters):
        self.network = network
        self.hparameters = hparameters
        self.evaluator = Evaluator(hparameters)

    def run(self, algorithm, verbose=True):
        residual_e = [self.network.init_energy] * self.network.N
        live_nodes = list(range(self.network.N))
        history = []

        for t in range(self.hparameters.T_max):
            root = algorithm.plan_round(live_nodes, residual_e)
            if root is None:
                if verbose:
                    print(f"[{algorithm.name}] round {t}: no feasible routing found, stopping")
                break

            consumption, total = self.evaluator.energy_consumption(
                root, self.network.dist_matrix, self.network.base_dists
            )
            for idx, e in consumption.items():
                residual_e[idx] = max(0.0, residual_e[idx] - e)

            live_nodes = [i for i in live_nodes if residual_e[i] > 0]

            history.append({
                "round": t,
                "alive_nodes": len(live_nodes),
                "round_energy": total,
            })

            if verbose and t % 100 == 0:
                print(f"[{algorithm.name}] round {t}: {len(live_nodes)} alive, "
                      f"energy used this round {total:.6f}")

            if not live_nodes:
                if verbose:
                    print(f"[{algorithm.name}] round {t}: network died")
                break

        return pd.DataFrame(history)
