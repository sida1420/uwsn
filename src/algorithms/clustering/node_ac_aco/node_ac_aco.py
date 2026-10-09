"""Node pheromone and NodeACO heuristics with adaptive chaotic control."""

from math import isfinite

import numpy as np

from algorithms.clustering.ac_aco.ac_aco import ACACOClustering, logistic_step
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters


class NodeACACOClustering(ACACOClustering):
    name = "NodeACACOClustering"

    def __init__(self, network, hparameters, params: NodeACACOParameters = None, seed=None):
        if params is not None and not isinstance(params, NodeACACOParameters):
            raise TypeError("params must be NodeACACOParameters or None")
        super().__init__(network, hparameters, params or NodeACACOParameters(), seed)
        self.pheromone = [self.params.tau0] * network.N

    def _transition_probabilities(self, source, available, residual_e, beta, strength):
        """Use tau[j]^alpha * residual[j]^beta / E_m(i,j)^gamma.

        As in NodeACO, later ants see earlier successful ants' node deposits.
        ACACO's normalized source-chaos disturbance follows the log weights.
        """
        targets = np.asarray(available, dtype=np.intp)
        tau = np.asarray(self.pheromone, dtype=float)[targets]
        residual = np.asarray(residual_e, dtype=float)[targets]
        log_energy = self._log_edge_costs[source, targets]
        valid = (tau > 0) & np.isfinite(tau) & (residual > 0)
        valid &= np.isfinite(residual) & np.isfinite(log_energy)
        log_weights = np.full(len(available), -np.inf)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            log_weights[valid] = (
                self.params.pheromone_exponent * np.log(tau[valid])
                + beta * np.log(residual[valid])
                - self.params.energy_cost_exponent * log_energy[valid]
            )
        greatest = np.max(log_weights)
        if not np.isfinite(greatest):
            return [1.0 / len(available)] * len(available)
        weights = np.exp(log_weights - greatest)
        probabilities = weights / weights.sum()
        disturbed = probabilities + strength * self.chaos[source]
        return (disturbed / disturbed.sum()).tolist()

    def deposit(self, CH_list, fitness, per_ant=True):
        """Reinforce every CH by the same dimensionless fitness used to rank."""
        if not CH_list or fitness is None or not isfinite(fitness) or fitness < 0:
            return
        p = self.params
        amount = p.Q / max(fitness, p.fitness_eps)
        amount = amount / p.num_ants if per_ant else amount * p.theta
        for node in CH_list:
            self.pheromone[node] = min(max(self.pheromone[node] + amount, p.tau_min), p.tau_max)

    def _update_pheromone(self, state):
        """Evaporate and disturb each live node once, then advance its chaos."""
        p = self.params
        for node in state.live:
            value = (1.0 - state.rho) * self.pheromone[node] + state.strength * self.chaos[node]
            self.pheromone[node] = min(max(value, p.tau_min), p.tau_max)
            self.chaos[node] = logistic_step(self.chaos[node], p.chaos_r)

    def post_round(self, live_sensors, residual_e, consumption, state=None,
                   candidate_costs=(), CH_list=None, best_fitness=None):
        """Keep chaos's joule window; winner reinforcement uses fitness."""
        best_cost = sum(consumption.values()) if CH_list is not None else None
        if candidate_costs:
            round_low, round_high = min(candidate_costs), max(candidate_costs)
            self.lower_cost = round_low if self.lower_cost is None else min(self.lower_cost, round_low)
            self.upper_cost = round_high if self.upper_cost is None else max(self.upper_cost, round_high)
        self.previous_cost = best_cost
        self._update_pheromone(state)
        if CH_list is not None:
            self.deposit(CH_list, best_fitness, per_ant=False)
        if self.iteration == 1 or self.iteration % 100 == 0 or best_cost is None:
            values = [self.pheromone[node] for node in state.live]
            print(
                f"[NodeACACO DEBUG] iter={self.iteration} beta={state.beta:.6g} "
                f"rho={state.rho:.6g} chaos={state.strength:.6g} "
                f"feasible={len(candidate_costs)} best_energy={best_cost} fitness={best_fitness} "
                f"tau_min={min(values):.6g} tau_max={max(values):.6g} "
                f"tau_mean={sum(values) / len(values):.6g}"
            )
