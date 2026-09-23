from dataclasses import dataclass
from math import exp, isfinite, log, sqrt
import random

from algorithms.ac_aco.adaptive import (
    heuristic_weight,
)
from algorithms.ac_aco.objective import phase1_cost
from algorithms.ac_aco.pheromone import initial_chaos, update_pheromone
from evaluate import Evaluator


@dataclass(frozen=True)
class ClusterSolution:
    aco_heads: tuple
    cluster_heads: tuple
    assignments: dict
    cost: float
    target_head_count: int


class ACACOOptimizer:
    """Edge-pheromone AC-ACO optimizer for an ordered CH construction path."""

    def __init__(self, network, hparameters, parameters):
        self.network = network
        self.parameters = parameters
        self.evaluator = Evaluator(hparameters)
        self.rng = random.Random(parameters.random_seed)
        self.diagonal = max(
            sqrt(network.width**2 + network.height**2 + network.depth**2),
            1e-12,
        )
        self.start_pheromone = [parameters.tau0] * network.N
        self.pheromone = [
            [parameters.tau0] * network.N for _ in range(network.N)
        ]
        self.chaos = initial_chaos(
            network.N, parameters.chaos_seed, parameters.chaos_r
        )
        self.coverage = [
            {j for j in range(network.N) if network.dist_matrix[i][j] <= network.radius}
            for i in range(network.N)
        ]

    def optimize(self, live_nodes, residual_e, allowed_heads=None):
        live = tuple(i for i in live_nodes if residual_e[i] > 0)
        if not live:
            return None
        candidate_pool = tuple(
            i for i in (allowed_heads if allowed_heads is not None else live)
            if i in live
        )
        if not candidate_pool:
            return None
        target = min(
            len(candidate_pool),
            max(1, round(self.parameters.ch_proportion * len(live))),
        )
        global_best = None

        for iteration in range(self.parameters.num_iterations):
            progress = iteration / max(self.parameters.num_iterations - 1, 1)
            beta = heuristic_weight(
                progress,
                self.parameters.beta_min,
                self.parameters.beta_max,
                self.parameters.beta_slope,
            )
            solutions = []
            for _ in range(self.parameters.num_ants):
                aco_heads = self._construct_candidate(
                    candidate_pool, residual_e, target, beta
                )
                heads = aco_heads
                if self.parameters.ensure_member_coverage:
                    heads = self._repair_coverage(
                        heads, live, candidate_pool, residual_e
                    )
                if heads is None:
                    continue
                assignments = self._assign_members(heads, live)
                if assignments is None:
                    continue
                cost = phase1_cost(
                    self.network,
                    self.evaluator,
                    self.parameters,
                    heads,
                    assignments,
                    live,
                    residual_e,
                    target,
                    self.diagonal,
                )
                candidate = ClusterSolution(
                    tuple(aco_heads), tuple(heads), assignments, cost, target
                )
                solutions.append(candidate)
                if global_best is None or cost < global_best.cost:
                    global_best = candidate
            if solutions:
                update_pheromone(
                    self.start_pheromone,
                    self.pheromone,
                    self.chaos,
                    solutions,
                    live,
                    residual_e,
                    self.network,
                    self.parameters,
                    progress,
                )
        return global_best

    def _construct_candidate(self, live, residual_e, target, beta):
        available = list(live)
        selected = []
        max_energy = max(residual_e[i] for i in live)
        while available and len(selected) < target:
            previous = selected[-1] if selected else None
            log_weights = [
                self._transition_log_weight(
                    previous, node, residual_e, max_energy, beta
                )
                for node in available
            ]
            max_log = max(log_weights)
            weights = [exp(value - max_log) for value in log_weights]
            pick = (
                self.rng.choices(available, weights=weights, k=1)[0]
                if sum(weights) > 0
                else self.rng.choice(available)
            )
            selected.append(pick)
            available.remove(pick)
        return selected

    def _transition_log_weight(self, previous, node_id, residual_e, max_energy, beta):
        if previous is None:
            trail = self.start_pheromone[node_id]
            distance = self.network.base_dists[node_id]
        else:
            trail = self.pheromone[previous][node_id]
            distance = self.network.dist_matrix[previous][node_id]
        energy_ratio = residual_e[node_id] / max(max_energy, 1e-12)
        distance_ratio = max(distance / self.diagonal, 1e-9)
        eta = max(energy_ratio / distance_ratio, 1e-12)
        energy_term = 1.0 / (1.0 + self.evaluator.E_tx(distance))
        value = (
            self.parameters.pheromone_weight * log(max(trail, 1e-300))
            + beta * log(eta)
            + self.parameters.energy_cost_weight * log(max(energy_term, 1e-300))
        )
        return value if isfinite(value) else -1e300

    def _repair_coverage(self, heads, live, candidate_pool, residual_e):
        selected = list(heads)
        selected_set = set(selected)
        live_set = set(live)
        covered = set().union(*(self.coverage[ch] & live_set for ch in selected))
        uncovered = live_set - covered
        while uncovered:
            candidates = set(candidate_pool) - selected_set
            if not candidates:
                return None
            pick = max(
                candidates,
                key=lambda node_id: (
                    len(self.coverage[node_id] & uncovered),
                    residual_e[node_id],
                    -self.network.base_dists[node_id],
                    -node_id,
                ),
            )
            selected.append(pick)
            selected_set.add(pick)
            uncovered -= self.coverage[pick]
        return selected

    def _assign_members(self, heads, live):
        assignments = {}
        for node_id in live:
            ch_id = min(heads, key=lambda ch: self.network.dist_matrix[node_id][ch])
            if (
                self.parameters.ensure_member_coverage
                and self.network.dist_matrix[node_id][ch_id] > self.network.radius
            ):
                return None
            assignments[node_id] = ch_id
        return assignments

