import random
from math import log

import numpy as np

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering import build_clusters
from algorithms.clustering.node_aco.parameters import NodeACOParameters
from evaluate import Evaluator


class NodeACOClustering(ClusteringAlgorithm):
    """ACO clustering with pheromone attached to candidate CH nodes."""

    name = "NodeACOClustering"

    def __init__(self, network, hparameters, aco_params: NodeACOParameters = None):
        super().__init__(network, hparameters)
        self.params = aco_params or NodeACOParameters()
        self.evaluator = Evaluator(hparameters)
        self.pheromone = [self.params.tau0] * network.N
        self.round_number = 0

        distances = np.asarray(network.dist_matrix, dtype=float)
        log_energy = np.zeros_like(distances)
        for source in range(network.N):
            for target in range(network.N):
                if source != target:
                    log_energy[source, target] = log(
                        self.evaluator.E_m(max(distances[source, target], 1e-9))
                    )
        self._log_energy = self.params.gamma * log_energy
    def pre_round(self, live_sensors, residual_e):
        residual = np.asarray(residual_e, dtype=float)
        self._log_residual = self.params.beta * np.log(
            np.maximum(residual, np.finfo(float).tiny)
        )
        return random.sample(live_sensors, min(self.params.num_ants, len(live_sensors)))

    def create_clusters(self, live_sensors, residual_e, start):
        CHs = self._make_path(live_sensors, residual_e, start)
        if CHs is None:
            return None
        return build_clusters(CHs, live_sensors, self.network.dist_matrix, self.network.radius)

    def post_round(self, live_sensors, residual_e, consumption, CH_list):
        self._update_pheromone()
        self.deposit(CH_list, sum(consumption.values()), per_ant=False)
        self.round_number += 1
        # if self.round_number == 1 or self.round_number % 100 == 0:
            # self._log_heuristic_dominance(live_sensors, residual_e)

    def _log_heuristic_dominance(self, live_nodes, residual_e):
        """Log average per-source spreads of the weighted path contributions."""
        source_spreads = []
        pheromone_values = [self.pheromone[node] for node in live_nodes]

        for source in live_nodes:
            contributions = {
                "tau": [],
                "residual": [],
                "energy_cost": [],
            }
            for target in live_nodes:
                if source == target:
                    continue

                distance = max(self.network.dist_matrix[source][target], 1e-9)
                residual = residual_e[target]
                energy = self.evaluator.E_m(distance)
                tau = self.pheromone[target]

                if (
                    tau > 0
                    and residual > 0
                    and energy > 0
                    and isfinite(energy)
                ):
                    contributions["tau"].append(self.params.alpha * log(tau))
                    contributions["residual"].append(
                        self.params.beta * log(residual)
                    )
                    contributions["energy_cost"].append(
                        -self.params.gamma * log(energy)
                    )

            if all(contributions.values()):
                source_spreads.append(
                    {
                        name: max(values) - min(values)
                        for name, values in contributions.items()
                    }
                )

        spreads = {
            name: (
                sum(source[name] for source in source_spreads)
                / len(source_spreads)
                if source_spreads
                else 0.0
            )
            for name in ("tau", "residual", "energy_cost")
        }
        dominant = max(spreads, key=spreads.get) if spreads else "none"
        ranges = " ".join(
            f"{name}={spreads.get(name, 0.0):.4g}"
            for name in ("tau", "residual", "energy_cost")
        )
        tau_min = min(pheromone_values) if pheromone_values else 0.0
        tau_max = max(pheromone_values) if pheromone_values else 0.0
        tau_mean = (
            sum(pheromone_values) / len(pheromone_values)
            if pheromone_values
            else 0.0
        )
        bound_tolerance = 1e-9
        at_tau_min = sum(
            abs(value - self.params.tau_min) <= bound_tolerance
            for value in pheromone_values
        )
        at_tau_max = sum(
            abs(value - self.params.tau_max) <= bound_tolerance
            for value in pheromone_values
        )
        print(
            f"[NodeACO HEURISTIC] round={self.round_number} "
            f"{ranges} dominant={dominant} "
            f"tau_min={tau_min:.4g} tau_max={tau_max:.4g} "
            f"tau_mean={tau_mean:.4g} "
            f"number_at_tau_min={at_tau_min} "
            f"number_at_tau_max={at_tau_max}"
        )

    def deposit(self, CH_list, cost, per_ant=True):
        """Deposit pheromone for a successful route."""
        if not CH_list or cost is None or cost <= 0:
            return

        amount = self.params.Q / cost
        if per_ant:
            amount /= self.params.num_ants
        else:
            amount *= self.params.theta

        for node in CH_list:
            self.pheromone[node] = min(
                self.pheromone[node] + amount,
                self.params.tau_max,
            )

    def _make_path(self, live_nodes, residual_e, start_node):
        num_CHs = max(1, round(self.params.CH_proportion * len(live_nodes)))
        current = start_node
        CH_list = [current]
        allowed = list(live_nodes)
        allowed.remove(current)

        while len(CH_list) < num_CHs:
            if not allowed:
                return None
            targets = np.asarray(allowed, dtype=np.intp)
            log_weights = (
                self.params.alpha * np.log(np.asarray(self.pheromone)[targets])
                + self._log_residual[targets]
                - self._log_energy[current, targets]
            )
            greatest = np.max(log_weights)
            weights = np.exp(log_weights - greatest)

            current = random.choices(allowed, weights=weights, k=1)[0]
            CH_list.append(current)
            allowed.remove(current)
        return CH_list

    def _update_pheromone(self):
        """Evaporate pheromone without adding any new deposit."""
        rho = self.params.rho
        self.pheromone = [pheromone * (1 - rho) for pheromone in self.pheromone]

        lo, hi = self.params.tau_min, self.params.tau_max
        self.pheromone = [min(max(value, lo), hi) for value in self.pheromone]
