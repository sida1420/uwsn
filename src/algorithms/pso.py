"""
PSO: the Algorithm wrapper around PSOClustering.

Goes in `algorithms/pso.py`.

Division of labour (same pattern as SimpleACO / ACACO):
  * PSOClustering (algorithms/clustering/pso/) owns the swarm state and the
    clustering-side hooks: pre_round, decode, create_clusters, move,
    infeasible_score, post_round.
  * This class owns the per-round search loop, the routing step (a stateless
    function), the evaluation cache, the failure counters and the choice of
    the best feasible routing tree.

plan_round returns (root, consumption) on success and (None, {}) when no
feasible routing tree was found, as Simulator.run expects.
"""

from algorithms.base.base import Algorithm
from algorithms.clustering.pso.pso import PSOClustering, PSOParameters
from algorithms.routing import dropping_member_multi_hop_routing
from algorithms.clustering import build_clusters
from evaluate import Evaluator


class PSO(Algorithm):
    name = "PSO"

    def init_params(self):
        # Called automatically by Algorithm.__init__ (do NOT call it manually).
        # Relies on Algorithm.__init__ having already stored self.network and
        # self.hparameters before it calls init_params().
        self.params = PSOParameters()
        self.clustering = PSOClustering(self.network, self.hparameters, self.params)
        self.evaluator = Evaluator(self.hparameters)

        # Cumulative counters over the whole simulation.
        self.total_clustering_attempts = 0
        self.failed_clustering_attempts = 0
        self.total_routing_attempts = 0
        self.failed_routing_attempts = 0

        # Per-round diagnostics (overwritten every plan_round).
        self.last_evaluation_requests = 0
        self.last_unique_evaluations = 0
        self.last_iterations = 0

    # ------------------------------------------------------------------
    def plan_round(self, live_sensors, residual_e):
        if not live_sensors:
            return None, {}

        particles = self.clustering.pre_round(live_sensors, residual_e)

        global_best_position = None
        global_best_score = float("inf")

        best_root = None
        best_consumption = {}
        best_score = float("inf")

        evaluation_cache = {}
        iterations_without_improvement = 0
        self.last_evaluation_requests = 0
        self.last_unique_evaluations = 0
        self.last_iterations = 0

        for iteration in range(self.params.iterations):
            self.last_iterations = iteration + 1
            score_before_iteration = best_score

            for particle in particles:
                CHs = self.clustering.decode(particle["position"], live_sensors)
                cache_key = tuple(sorted(CHs))
                self.last_evaluation_requests += 1

                if cache_key in evaluation_cache:
                    root, consumption, score = evaluation_cache[cache_key]
                else:
                    root, consumption, score = self._evaluate(
                        CHs, live_sensors, residual_e
                    )
                    evaluation_cache[cache_key] = (root, consumption, score)
                    self.last_unique_evaluations += 1

                if score < particle["best_score"]:
                    particle["best_score"] = score
                    particle["best_position"] = particle["position"].copy()

                if score < global_best_score:
                    global_best_score = score
                    global_best_position = particle["position"].copy()

                if root is not None and score < best_score:
                    best_root = root
                    best_consumption = consumption
                    best_score = score

            # Early stopping: only counts once a feasible tree exists.
            if best_root is not None:
                if best_score < score_before_iteration:
                    iterations_without_improvement = 0
                else:
                    iterations_without_improvement += 1

                patience = self.params.early_stopping_patience
                if patience > 0 and iterations_without_improvement >= patience:
                    break

            if global_best_position is None:
                continue

            for particle in particles:
                self.clustering.move(
                    particle,
                    global_best_position,
                    iteration,
                    self.params.iterations,
                )

        # Always let the swarm retain its survivors, even if this round failed.
        self.clustering.post_round(
            live_sensors, residual_e, best_consumption, particles
        )

        # self.evaluator.visit_summary()
        if best_root is None:
            return None, {}
        return best_root, best_consumption

    # ------------------------------------------------------------------
    def _evaluate(self, CHs, live_sensors, residual_e):
        """
        Score one CH selection.

        Returns (root, consumption, score). For infeasible candidates root is
        None, consumption is {} and score is the clustering's penalty.
        """
        self.total_clustering_attempts += 1
        clusters = self.clustering.create_clusters(live_sensors, residual_e, CHs)

        if clusters is None:
            self.failed_clustering_attempts += 1
            return None, {}, self.clustering.infeasible_score(CHs, live_sensors)

        CH_nodes, nodes, outliers = clusters

        self.total_routing_attempts += 1
        root = dropping_member_multi_hop_routing(
            CH_nodes,
            nodes,
            live_sensors,
            outliers,
            self.network.dist_matrix,
            self.network.base_dists,
            residual_e,
            self.network.radius,
            self.params.hopping_factor,
        )

        if root is None:
            self.failed_routing_attempts += 1
            return None, {}, self.clustering.infeasible_score(CHs, live_sensors)

        consumption, cost = self.evaluator.energy_consumption(
            root,
            self.network.dist_matrix,
            self.network.base_dists,
            len(live_sensors)
        )
        return root, consumption, self._lifetime_score(cost, consumption, residual_e)

    def _lifetime_score(self, total_cost, consumption, residual_e):
        """Balance total energy against the most endangered sensor."""
        if not consumption:
            return float("inf")

        max_depletion = max(
            energy / max(residual_e[node_id], 1e-12)
            for node_id, energy in consumption.items()
        )
        return total_cost + self.params.depletion_weight * max_depletion
