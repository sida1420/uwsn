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

        self.rng = random.Random(parameters.random_seed)

        self.pheromone = [[parameters.tau0] * network.N for _ in range(network.N)]

        self.chaos = initial_chaos(
            network.N,
            parameters.chaos_seed,
            parameters.chaos_r,
        )

    def optimize(self, live_nodes, residual_e):
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

        best_global = None

        # Lưu các cost hợp lệ đã tìm thấy.
        seen_costs = []

        # Cost tốt nhất của iteration ngay trước.
        previous_cost = None

        for iteration in range(
            1,
            self.parameters.num_iterations + 1,
        ):
            rho = evaporation_rate(
                iteration,
                self.parameters.num_iterations,
                self.parameters.rho_min,
                self.parameters.rho_max,
            )

            beta = heuristic_weight(
                iteration,
                self.parameters.num_iterations,
                self.parameters.beta_min,
                self.parameters.beta_max,
                self.parameters.beta_slope,
            )

            strength = chaos_strength(
                previous_cost,
                min(seen_costs, default=None),
                max(seen_costs, default=None),
                self.parameters.chaos_min,
                self.parameters.chaos_max,
            )

            candidates = []

            # Mỗi ant tạo một candidate solution.
            for _ in range(self.parameters.num_ants):
                cluster_heads = self._construct_candidate(
                    live,
                    residual_e,
                    target,
                    beta,
                    strength,
                )

                solution = self._evaluate(
                    cluster_heads,
                    live,
                    residual_e,
                    target,
                )

                if solution is not None:
                    candidates.append(solution)

            # Best solution của iteration hiện tại.
            best_iteration = min(
                candidates,
                key=lambda item: (
                    item.cost,
                    item.cluster_heads,
                ),
                default=None,
            )

            # Lưu tất cả candidate cost hợp lệ.
            seen_costs.extend(solution.cost for solution in candidates)

            # Update global best.
            if best_iteration is not None:
                if best_global is None or (
                    best_iteration.cost,
                    best_iteration.cluster_heads,
                ) < (
                    best_global.cost,
                    best_global.cluster_heads,
                ):
                    best_global = best_iteration

            # Quan trọng:
            # Nếu iteration này không tìm được solution,
            # iteration sau phải nhận previous_cost = None.
            previous_cost = best_iteration.cost if best_iteration is not None else None

            # Update pheromone một lần sau mỗi iteration.
            update_pheromone(
                self.pheromone,
                self.chaos,
                live,
                self.parameters,
                rho,
                strength,
                best_iteration,
            )

        return best_global

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

        if not self._valid_tree(root, live):
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

    def _valid_tree(self, root, live):
        if root is None or root.id != -1:
            return False

        expected = set(live)

        found = set()
        visiting = set()

        def visit(node):
            if node.id != -1:
                if node.id not in expected or node.id in found or node.id in visiting:
                    return False

                found.add(node.id)

                parent = node.prev

                # Tránh AttributeError nếu routing tạo node
                # chưa có parent.
                if parent is None:
                    return False

                if parent.id == -1:
                    distance = self.network.base_dists[node.id]
                else:
                    distance = self.network.dist_matrix[node.id][parent.id]

                if distance > self.network.radius:
                    return False

            visiting.add(node.id)

            for child in node.nxts:
                if child.prev is not node:
                    visiting.remove(node.id)
                    return False

                if not visit(child):
                    visiting.remove(node.id)
                    return False

            visiting.remove(node.id)

            return True

        return visit(root) and found == expected
