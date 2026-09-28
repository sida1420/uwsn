"""AC-ACO search using the repository's shared clustering and routing helpers."""

from dataclasses import dataclass
from math import exp, isfinite, log
import random

from algorithms.ac_aco.adaptive import (
    chaos_strength,
    evaporation_rate,
    heuristic_weight,
)
from algorithms.ac_aco.pheromone import initial_chaos, update_pheromone
from algorithms.clustering import build_clusters
from algorithms.routing import multi_hop_routing
from evaluate import Evaluator


@dataclass(frozen=True)
class ClusterSolution:
    cluster_heads: tuple
    root: object
    cost: float
    path_length: float
    target_head_count: int


class ACACOOptimizer:
    """Construct ordered CH paths and retain the lowest-energy feasible route."""

    def __init__(self, network, hparameters, parameters):
        self.network = network
        self.parameters = parameters
        self.evaluator = Evaluator(hparameters)
        self.total_iterations = hparameters.T_max

        self.rng = random.Random(parameters.random_seed)

        self.pheromone = [[parameters.tau0] * network.N for _ in range(network.N)]

        self.chaos = initial_chaos(
            network.N,
            parameters.chaos_seed,
            parameters.chaos_r,
        )

        # Simulator.run -> plan_round -> optimize occurs once per network round.
        # Keep one-based schedule state for this optimizer's simulation run.
        self.iteration = 0
        self.previous_cost = None
        self.lower_cost = None
        self.upper_cost = None

    def optimize(self, live_nodes, residual_e):
        self.iteration += 1
        live = tuple(node_id for node_id in live_nodes if residual_e[node_id] > 0)

        if not live:
            return None

        target = min(
            len(live),
            max(
                1,
                round(self.parameters.ch_proportion * len(live)),
            ),
        )

        rho = evaporation_rate(
            self.iteration,
            self.total_iterations,
            self.parameters.rho_min,
            self.parameters.rho_max,
        )
        beta = heuristic_weight(
            self.iteration,
            self.total_iterations,
            self.parameters.beta_min,
            self.parameters.beta_max,
            self.parameters.beta_slope,
        )
        strength = chaos_strength(
            self.previous_cost,
            self.lower_cost,
            self.upper_cost,
            self.parameters.chaos_min,
            self.parameters.chaos_max,
        )

        candidates = []
        for _ in range(self.parameters.num_ants):
            for _attempt in range(20):
                cluster_heads = self._construct_candidate(
                    live, residual_e, target, beta, strength,
                )
                solution = self._evaluate(cluster_heads, live, residual_e, target)
                if solution is None:
                    continue
                candidates.append(solution)
                break

        best_iteration = min(
            candidates,
            key=lambda item: (item.cost, item.cluster_heads),
            default=None,
        )
        if candidates:
            round_low = min(solution.cost for solution in candidates)
            round_high = max(solution.cost for solution in candidates)
            self.lower_cost = round_low if self.lower_cost is None else min(self.lower_cost, round_low)
            self.upper_cost = round_high if self.upper_cost is None else max(self.upper_cost, round_high)
        self.previous_cost = best_iteration.cost if best_iteration is not None else None

        update_pheromone(
            self.pheromone,
            self.chaos,
            live,
            self.parameters,
            rho,
            strength,
            best_iteration,
        )

        if self.iteration == 1 or self.iteration % 100 == 0 or best_iteration is None:
            values = [
                self.pheromone[source][target]
                for source in live for target in live if source != target
            ] or [self.pheromone[live[0]][live[0]]]
            best_energy = f"{best_iteration.cost:.6g}" if best_iteration is not None else "None"
            print(
                f"[AC-ACO DEBUG] iter={self.iteration} "
                f"alpha={self.parameters.pheromone_exponent:.6g} beta={beta:.6g} "
                f"gamma={self.parameters.energy_cost_exponent:.6g} rho={rho:.6g} "
                f"chaos={strength:.6g} ants={self.parameters.num_ants} ch={target} "
                f"feasible={len(candidates)} best_energy={best_energy} "
                f"tau_min={min(values):.6g} tau_max={max(values):.6g} "
                f"tau_mean={sum(values) / len(values):.6g}"
            )

        return best_iteration

    def _construct_candidate(
        self,
        live,
        residual_e,
        target,
        beta,
        strength,
    ):
        available = list(live)

        # Giữ nguyên cách chọn đang chạy ổn trong project.
        selected = [self.rng.choice(available)]

        available.remove(selected[0])

        while available and len(selected) < target:
            next_head = self._choose_next(
                selected[-1],
                available,
                residual_e,
                beta,
                strength,
            )

            selected.append(next_head)
            available.remove(next_head)

        return tuple(selected)

    def _choose_next(
        self,
        source,
        available,
        residual_e,
        beta,
        strength,
    ):
        probabilities = self._transition_probabilities(
            source,
            available,
            residual_e,
            beta,
            strength,
        )

        return self.rng.choices(
            available,
            weights=probabilities,
            k=1,
        )[0]

    def _transition_probabilities(
        self,
        source,
        available,
        residual_e,
        beta,
        strength,
    ):
        """
        Eq. (20) probabilities,
        including explicit chaos normalization.
        """

        log_weights = []

        for target in available:
            distance = max(
                self.network.dist_matrix[source][target],
                1e-12,
            )

            eta = max(residual_e[target], 0.0) / distance

            energy = self.evaluator.E_m(distance)

            tau = self.pheromone[source][target]

            if tau <= 0 or eta <= 0 or energy <= 0 or not isfinite(energy):
                log_weights.append(float("-inf"))
                continue

            log_weights.append(
                self.parameters.pheromone_exponent * log(tau)
                + beta * log(eta)
                - self.parameters.energy_cost_exponent * log(energy)
            )

        greatest = max(log_weights)

        if not isfinite(greatest):
            return [1.0 / len(available)] * len(available)

        weights = [
            exp(weight - greatest) if isfinite(weight) else 0.0
            for weight in log_weights
        ]

        total = sum(weights)

        if total <= 0:
            return [1.0 / len(available)] * len(available)

        probabilities = [weight / total for weight in weights]

        # Chaotic disturbance.
        chaos = strength * self.chaos[source]

        weights = [probability + chaos for probability in probabilities]

        total = sum(weights)

        return [weight / total for weight in weights]

    def _prepare_clusters_for_routing(self, ch_nodes, nodes, outliers, live, residual_e):
        """Release one blocked relay only when a routing node has no usable parent."""
        base_dists = self.network.base_dists
        # Match shared routing order; appended releases also need routing support.
        pending = list(ch_nodes) + list(outliers)
        for node_id in pending:
            distance_to_base = base_dists[node_id]
            if distance_to_base <= self.network.radius:
                continue

            blocked = []
            has_parent = False
            for candidate_id in live:
                if candidate_id == node_id:
                    continue
                if self.network.dist_matrix[node_id][candidate_id] > self.network.radius:
                    continue
                if base_dists[candidate_id] > distance_to_base:
                    continue
                if residual_e[candidate_id] <= 0:
                    continue

                # Outliers are absent here; shared routing creates their Nodes.
                candidate = nodes.get(candidate_id)
                if (
                    candidate is not None
                    and not candidate.isCH
                    and candidate.prev is not None
                    and candidate.prev.isCH
                    and distance_to_base <= base_dists[candidate.prev.id]
                ):
                    blocked.append(candidate_id)
                else:
                    has_parent = True
                    break

            if has_parent or not blocked:
                continue

            # All physically eligible parents are blocked members at this dead end.
            total_candidate_energy = sum(residual_e[i] for i in blocked)

            def relay_cost(candidate_id):
                energy_cost = total_candidate_energy / max(residual_e[candidate_id], 1e-12)
                distance_cost = (
                    self.network.dist_matrix[node_id][candidate_id] ** 2
                    + base_dists[candidate_id] ** 2
                ) / max(distance_to_base**2, 1e-12)
                factor = self.parameters.hopping_factor
                return factor * energy_cost + (1 - factor) * distance_cost

            member_id = min(blocked, key=relay_cost)
            member = nodes.pop(member_id)
            # set_previous does not remove the old parent's child link.
            member.prev.nxts.remove(member)
            member.set_previous(None)
            outliers.append(member_id)
            pending.append(member_id)

    def _evaluate(
        self,
        cluster_heads,
        live,
        residual_e,
        target,
    ):
        ch_nodes, nodes, outliers = build_clusters(
            cluster_heads,
            live,
            self.network.dist_matrix,
            self.network.radius,
        )

        self._prepare_clusters_for_routing(ch_nodes, nodes, outliers, live, residual_e)

        root = multi_hop_routing(
            ch_nodes,
            nodes,
            live,
            outliers,
            self.network.dist_matrix,
            self.network.base_dists,
            residual_e,
            self.network.radius,
            self.parameters.hopping_factor,
        )

        if root is None:
            return None

        _, cost = self.evaluator.energy_consumption(
            root,
            self.network.dist_matrix,
            self.network.base_dists,
        )

        if not isfinite(cost) or cost <= 0:
            return None

        path_length = max(
            sum(
                self.network.dist_matrix[left][right]
                for left, right in zip(
                    cluster_heads,
                    cluster_heads[1:],
                )
            ),
            1e-12,
        )

        return ClusterSolution(
            cluster_heads,
            root,
            cost,
            path_length,
            target,
        )
