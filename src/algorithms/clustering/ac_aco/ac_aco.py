"""
AC-ACO (Adaptive Chaotic Ant Colony Optimization) cluster-head selection.

Adapts Zhou, Chen and Cao (2025), DOI 10.32604/cmc.2025.065561, to the 3D
underwater simulator. This module holds the parameters and the stateful
clustering part (pheromone, chaos, schedules). The per-round orchestration
(ants, routing, best-tree selection) lives in algorithms/ac_aco.py.
"""

from dataclasses import dataclass
from math import exp
import random

import numpy as np

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering import build_clusters
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from evaluate import Evaluator




# --------------------------------------------------------------------------
# Adaptive schedules (paper Eq. 13-15) and logistic chaos
# --------------------------------------------------------------------------

def logistic_step(value, r):
    return r * value * (1.0 - value)


def evaporation_rate(iteration, total_iterations, rho_min, rho_max):
    """Equation (13), with the first iteration numbered one."""
    progress = min(max(iteration / max(total_iterations, 1), 0.0), 1.0)
    return rho_max - progress * (rho_max - rho_min)


def heuristic_weight(iteration, total_iterations, beta_min, beta_max, slope):
    """Equation (14), evaluated safely for large sigmoid exponents."""
    exponent = slope * (iteration - total_iterations / 2.0)
    if exponent >= 0:
        sigmoid = 1.0 / (1.0 + exp(-exponent))
    else:
        value = exp(exponent)
        sigmoid = value / (1.0 + value)
    return beta_min + (beta_max - beta_min) * sigmoid


def chaos_strength(total_energy, lower_energy, upper_energy, low, high):
    """Equation (15) with an explicit, bounded UWSN cost window."""
    if (
        total_energy is None
        or lower_energy is None
        or upper_energy is None
        or upper_energy <= lower_energy
    ):
        return low
    ratio = (total_energy - lower_energy) / (upper_energy - lower_energy)
    return low + (high - low) * min(max(ratio, 0.0), 1.0)


# --------------------------------------------------------------------------
# Clustering
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RoundState:
    """Per-round values computed once in pre_round and shared by every ant."""

    live: tuple
    target: int  # number of CHs each ant selects
    rho: float
    beta: float
    strength: float


class ACACOClustering(ClusteringAlgorithm):
    """
    Stateful part of AC-ACO: pheromone matrix, chaos sequence and the
    round-indexed schedules.

    Round lifecycle (driven by ACACO in algorithms/ac_aco.py):
      pre_round        -> advance the round counter, compute rho / beta /
                          chaos strength, return a RoundState
      create_clusters  -> one ant walk (ordered CH path) + build_clusters
      post_round       -> update the cost window, evaporate/deposit/disturb
                          pheromone, print the debug line
    """

    name = "AC-ACO"

    def __init__(self, network, hparameters, params: ACACOParameters = None, seed=None):
        super().__init__(network, hparameters)
        self.params = params or ACACOParameters()
        self.evaluator = Evaluator(hparameters)
        self.total_iterations = hparameters.T_max
        self.rng = random.Random(seed)

        self.pheromone = [[self.params.tau0] * network.N for _ in range(network.N)]
        self._distances = np.maximum(np.asarray(network.dist_matrix, dtype=float), 1e-12)
        edge_costs = np.asarray(
            [[self.evaluator.E_m(distance) for distance in row] for row in self._distances],
            dtype=float,
        )
        self._log_edge_costs = np.full(edge_costs.shape, -np.inf)
        valid_costs = (edge_costs > 0) & np.isfinite(edge_costs)
        np.log(edge_costs, out=self._log_edge_costs, where=valid_costs)

        self.chaos = []
        value = self.params.chaos_seed
        for _ in range(network.N):
            value = logistic_step(value, self.params.chaos_r)
            self.chaos.append(value)

        # One-based round counter: iteration 1 == simulator round 0.
        self.iteration = 0
        self.previous_cost = None
        self.lower_cost = None
        self.upper_cost = None

    # ---- lifecycle hooks -------------------------------------------------

    def pre_round(self, live_sensors, residual_e):
        """Returns a RoundState, or None if no live node has energy left."""
        self.iteration += 1
        live = tuple(i for i in live_sensors if residual_e[i] > 0)
        if not live:
            return None
        # Reuse these round snapshots for every ant's probability calculation.
        self._residual_array = np.asarray(residual_e, dtype=float)
        self._pheromone_array = np.asarray(self.pheromone, dtype=float)

        p = self.params
        target = min(len(live), max(1, round(p.ch_proportion * len(live))))
        return RoundState(
            live=live,
            target=target,
            rho=evaporation_rate(self.iteration, self.total_iterations, p.rho_min, p.rho_max),
            beta=heuristic_weight(
                self.iteration, self.total_iterations, p.beta_min, p.beta_max, p.beta_slope
            ),
            strength=chaos_strength(
                self.previous_cost, self.lower_cost, self.upper_cost, p.chaos_min, p.chaos_max
            ),
        )

    def create_clusters(self, live_sensors, residual_e, state: RoundState):
        """
        One ant: build an ordered CH path, then build_clusters over the
        round's live nodes (state.live). The CH path order is the key order
        of the returned CH_nodes. Never returns None (kept for the base
        contract).
        """
        CHs = self._construct_candidate(state, self._residual_array)
        return build_clusters(CHs, state.live, self.network.dist_matrix, self.network.radius)

    def post_round(self, live_sensors, residual_e, consumption, state=None,
                   candidate_costs=(), CH_list=None):
        """
        Args:
            consumption: best tree's {sensor_id: energy} ({} if every ant failed)
            state: the RoundState from pre_round
            candidate_costs: total energy of every feasible candidate this round
            CH_list: ordered CH path of the best candidate (None if none)
        """
        best_cost = sum(consumption.values()) if CH_list is not None else None

        if candidate_costs:
            round_low, round_high = min(candidate_costs), max(candidate_costs)
            self.lower_cost = round_low if self.lower_cost is None else min(self.lower_cost, round_low)
            self.upper_cost = round_high if self.upper_cost is None else max(self.upper_cost, round_high)
        self.previous_cost = best_cost

        self._update_pheromone(state, CH_list, best_cost)

        if self.iteration == 1 or self.iteration % 100 == 0 or best_cost is None:
            live = state.live
            values = [
                self.pheromone[s][t] for s in live for t in live if s != t
            ] or [self.pheromone[live[0]][live[0]]]
            best_energy = f"{best_cost:.6g}" if best_cost is not None else "None"
            print(
                f"[AC-ACO DEBUG] iter={self.iteration} "
                f"alpha={self.params.pheromone_exponent:.6g} beta={state.beta:.6g} "
                f"gamma={self.params.energy_cost_exponent:.6g} rho={state.rho:.6g} "
                f"chaos={state.strength:.6g} ants={self.params.num_ants} ch={state.target} "
                f"feasible={len(candidate_costs)} best_energy={best_energy} "
                f"tau_min={min(values):.6g} tau_max={max(values):.6g} "
                f"tau_mean={sum(values) / len(values):.6g}"
            )

    # ---- ant walk --------------------------------------------------------

    def _construct_candidate(self, state, residual_e):
        available = list(state.live)
        selected = [self.rng.choice(available)]
        available.remove(selected[0])

        while available and len(selected) < state.target:
            probabilities = self._transition_probabilities(
                selected[-1], available, residual_e, state.beta, state.strength
            )
            next_head = self.rng.choices(available, weights=probabilities, k=1)[0]
            selected.append(next_head)
            available.remove(next_head)

        return tuple(selected)

    def _transition_probabilities(self, source, available, residual_e, beta, strength):
        """Eq. (20) probabilities, including explicit chaos normalization."""
        targets = np.asarray(available, dtype=np.intp)
        distance = self._distances[source, targets]
        eta = np.maximum(np.asarray(residual_e, dtype=float)[targets], 0.0) / distance
        tau = self._pheromone_array[source, targets]
        log_energy = self._log_edge_costs[source, targets]
        valid = (tau > 0) & (eta > 0) & np.isfinite(log_energy)

        log_weights = np.full(len(available), -np.inf)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            log_weights[valid] = (
                self.params.pheromone_exponent * np.log(tau[valid])
                + beta * np.log(eta[valid])
                - self.params.energy_cost_exponent * log_energy[valid]
            )

        greatest = np.max(log_weights)
        if not np.isfinite(greatest):
            return [1.0 / len(available)] * len(available)

        weights = np.exp(log_weights - greatest)
        total = weights.sum()
        if total <= 0:
            return [1.0 / len(available)] * len(available)

        probabilities = weights / total
        disturbed = probabilities + strength * self.chaos[source]
        return (disturbed / disturbed.sum()).tolist()

    # ---- pheromone -------------------------------------------------------

    def _update_pheromone(self, state, CH_list, cost):
        """Bounded Eq. (12): evaporation + Q/cost on the best CH path + chaos."""
        p = self.params
        if CH_list is None or cost is None or cost <= 0:
            deposit = 0.0
            reinforced = set()
        else:
            deposit = p.Q / max(cost, 1e-12)
            reinforced = set(zip(CH_list, CH_list[1:]))

        for source in state.live:
            disturbance = state.strength * self.chaos[source]
            for target in state.live:
                if source == target:
                    continue
                value = (
                    (1.0 - state.rho) * self.pheromone[source][target]
                    + (deposit if (source, target) in reinforced else 0.0)
                    + disturbance
                )
                self.pheromone[source][target] = min(max(value, p.tau_min), p.tau_max)
            self.chaos[source] = logistic_step(self.chaos[source], p.chaos_r)
