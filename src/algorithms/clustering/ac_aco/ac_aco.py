"""
AC-ACO (Adaptive Chaotic Ant Colony Optimization) cluster-head selection.

Adapts Zhou, Chen and Cao (2025), DOI 10.32604/cmc.2025.065561, to the 3D
underwater simulator. This module holds the parameters and the stateful
clustering part (pheromone, chaos, schedules). The per-round orchestration
(ants, routing, best-tree selection) lives in algorithms/ac_aco.py.
"""

from dataclasses import dataclass
from math import exp, isfinite, log
import random

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering import build_clusters
from evaluate import Evaluator


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ACACOParameters:
    """AC-ACO controls; names separate pheromone and chaos weights."""

    num_ants: int = 40
    max_clustering_attempts: int = 10  # attempts per ant to build a feasible tree

    ch_proportion: float = 0.20
    pheromone_exponent: float = 1.0  # "alpha" on tau
    energy_cost_exponent: float = 1.0  # "gamma" on 1 / E_m
    beta_min: float = 1.0
    beta_max: float = 5.0
    beta_slope: float = 5.0
    rho_min: float = 0.10
    rho_max: float = 0.90
    chaos_min: float = 0.05
    chaos_max: float = 0.30
    chaos_r: float = 3.61
    chaos_seed: float = 0.37
    Q: float = 100.0
    tau0: float = 1.0
    tau_min: float = 0.10
    tau_max: float = 10.0
    hopping_factor: float = 0.40

    def __post_init__(self):
        self._positive_integer("num_ants", self.num_ants)
        self._positive_integer("max_clustering_attempts", self.max_clustering_attempts)
        if not 0 < self.ch_proportion <= 1:
            raise ValueError("ch_proportion must be in (0, 1]")
        self._bounds("rho", self.rho_min, self.rho_max, strict_low=True, upper=1)
        self._bounds("beta", self.beta_min, self.beta_max)
        self._bounds("chaos", self.chaos_min, self.chaos_max)
        self._bounds("tau", self.tau_min, self.tau_max, strict_low=True)
        if not 3.57 < self.chaos_r < 4:
            raise ValueError("chaos_r must be in (3.57, 4)")
        if not 0 < self.chaos_seed < 1:
            raise ValueError("chaos_seed must be in (0, 1)")
        if not 0 <= self.hopping_factor <= 1:
            raise ValueError("hopping_factor must be in [0, 1]")
        for name in ("pheromone_exponent", "energy_cost_exponent", "beta_slope"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if not isfinite(self.Q) or self.Q <= 0:
            raise ValueError("Q must be finite and > 0")
        if not self.tau_min <= self.tau0 <= self.tau_max:
            raise ValueError("tau0 must be in [tau_min, tau_max]")

    @staticmethod
    def _positive_integer(name, value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be an integer >= 1")

    @staticmethod
    def _bounds(name, low, high, strict_low=False, upper=None):
        low_ok = low > 0 if strict_low else low >= 0
        if (
            not isfinite(low)
            or not isfinite(high)
            or not low_ok
            or low > high
            or (upper is not None and high >= upper)
        ):
            bound = f" and < {upper}" if upper is not None else ""
            operator = "0 <" if strict_low else "0 <="
            raise ValueError(f"{name} bounds must satisfy {operator} min <= max{bound}")


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
        CHs = self._construct_candidate(state, residual_e)
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
        log_weights = []

        for target in available:
            distance = max(self.network.dist_matrix[source][target], 1e-12)
            eta = max(residual_e[target], 0.0) / distance
            energy = self.evaluator.E_m(distance)
            tau = self.pheromone[source][target]

            if tau <= 0 or eta <= 0 or energy <= 0 or not isfinite(energy):
                log_weights.append(float("-inf"))
                continue

            log_weights.append(
                self.params.pheromone_exponent * log(tau)
                + beta * log(eta)
                - self.params.energy_cost_exponent * log(energy)
            )

        greatest = max(log_weights)
        if not isfinite(greatest):
            return [1.0 / len(available)] * len(available)

        weights = [exp(w - greatest) if isfinite(w) else 0.0 for w in log_weights]
        total = sum(weights)
        if total <= 0:
            return [1.0 / len(available)] * len(available)

        probabilities = [w / total for w in weights]

        # Chaotic disturbance.
        chaos = strength * self.chaos[source]
        weights = [p + chaos for p in probabilities]
        total = sum(weights)
        return [w / total for w in weights]

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
