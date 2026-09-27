import random

from algorithms.base import ClusteringAlgorithm
from algorithms.clustering import build_clusters
from algorithms.routing import multi_hop_routing
from algorithms.pso.pso_parameters import PSOParameters
from evaluate import Evaluator


class PSOClustering(ClusteringAlgorithm):
    """
    Particle Swarm Optimization for cluster-head selection.

    A particle contains one continuous score for every live node. The nodes
    with the highest scores are selected as cluster heads, keeping the number
    of cluster heads fixed during a round. Cluster heads may relay through
    other cluster heads toward the base. Feasible routing trees are ranked by
    energy use; infeasible candidates receive a connectivity penalty.
    """

    name = "PSO"

    def __init__(self, network, hparameters, pso_params: PSOParameters = None):
        super().__init__(network, hparameters)
        self.params = pso_params or PSOParameters()
        self.evaluator = Evaluator(hparameters)
        self._warm_start = []
        self.last_evaluation_requests = 0
        self.last_unique_evaluations = 0
        self.last_iterations = 0

    def plan_round(self, live_nodes, residual_e):
        if not live_nodes:
            return None

        candidates = list(live_nodes)

        num_CHs = max(1, round(self.params.CH_proportion * len(live_nodes)))
        num_CHs = min(num_CHs, len(candidates))
        dimensions = len(candidates)

        particles = []
        for index in range(self.params.swarm_size):
            previous = self._warm_start[index] if index < len(self._warm_start) else None
            particles.append(self._new_particle(dimensions, candidates, previous))

        global_best_position = None
        global_best_score = float("inf")
        best_feasible_root = None
        best_feasible_score = float("inf")
        iterations_without_improvement = 0
        evaluation_cache = {}
        self.last_evaluation_requests = 0
        self.last_unique_evaluations = 0
        self.last_iterations = 0

        for iteration in range(self.params.iterations):
            self.last_iterations = iteration + 1
            score_before_iteration = best_feasible_score

            for particle in particles:
                CHs = self._decode(particle["position"], candidates, num_CHs)
                cache_key = tuple(sorted(CHs))
                self.last_evaluation_requests += 1

                if cache_key in evaluation_cache:
                    root, score = evaluation_cache[cache_key]
                else:
                    root, score = self._evaluate(CHs, live_nodes, residual_e)
                    evaluation_cache[cache_key] = (root, score)
                    self.last_unique_evaluations += 1

                if score < particle["best_score"]:
                    particle["best_score"] = score
                    particle["best_position"] = particle["position"].copy()

                if score < global_best_score:
                    global_best_score = score
                    global_best_position = particle["position"].copy()

                if root is not None and score < best_feasible_score:
                    best_feasible_root = root
                    best_feasible_score = score

            if best_feasible_root is not None:
                if best_feasible_score < score_before_iteration:
                    iterations_without_improvement = 0
                else:
                    iterations_without_improvement += 1

                patience = self.params.early_stopping_patience
                if patience > 0 and iterations_without_improvement >= patience:
                    break

            if global_best_position is None:
                continue

            for particle in particles:
                self._move(particle, global_best_position)

        # Reuse the swarm's positions and velocities next round. Values are
        # stored by sensor id because the candidate list shrinks as nodes die.
        # Personal/global fitness is deliberately reset: residual energy and
        # therefore the objective change between simulation rounds.
        self._warm_start = [
            {
                "position": dict(zip(candidates, particle["position"])),
                "velocity": dict(zip(candidates, particle["velocity"])),
            }
            for particle in particles
        ]

        return best_feasible_root

    def _new_particle(self, dimensions, candidates=None, previous=None):
        positions = []
        velocities = []

        for index in range(dimensions):
            node_id = candidates[index] if candidates is not None else index
            if previous is not None and node_id in previous["position"]:
                positions.append(previous["position"][node_id])
                velocities.append(previous["velocity"][node_id])
            else:
                positions.append(random.random())
                velocities.append(
                    random.uniform(-self.params.velocity_max, self.params.velocity_max)
                )

        return {
            "position": positions,
            "velocity": velocities,
            "best_position": None,
            "best_score": float("inf"),
        }

    @staticmethod
    def _decode(position, candidates, num_CHs):
        ranked = sorted(
            range(len(position)),
            key=lambda index: position[index],
            reverse=True,
        )
        return [candidates[index] for index in ranked[:num_CHs]]

    def _evaluate(self, CHs, live_nodes, residual_e):
        CH_nodes, nodes, outliers = build_clusters(
            CHs,
            live_nodes,
            self.network.dist_matrix,
            self.network.radius,
        )
        root = multi_hop_routing(
            CH_nodes,
            nodes,
            live_nodes,
            outliers,
            self.network.dist_matrix,
            self.network.base_dists,
            residual_e,
            self.network.radius,
            self.params.hopping_factor,
        )
        if root is not None:
            _, cost = self.evaluator.energy_consumption(
                root,
                self.network.dist_matrix,
                self.network.base_dists,
            )
            return root, cost

        # Penalize both uncovered sensors and CHs that lack a shorter hop
        # toward the base. This gives the swarm useful direction even before
        # it discovers its first fully feasible tree.
        uncovered_distance = sum(
            max(
                0.0,
                min(self.network.dist_matrix[node_id][ch] for ch in CHs)
                - self.network.radius,
            )
            for node_id in live_nodes
        )
        relay_distance = 0.0
        for ch in CHs:
            if self.network.base_dists[ch] <= self.network.radius:
                continue
            closer_CHs = [
                candidate
                for candidate in CHs
                if self.network.base_dists[candidate] < self.network.base_dists[ch]
            ]
            best_hop = min(
                [self.network.base_dists[ch]]
                + [self.network.dist_matrix[ch][candidate] for candidate in closer_CHs]
            )
            relay_distance += max(0.0, best_hop - self.network.radius)

        return (
            None,
            self.params.infeasible_penalty + uncovered_distance + relay_distance,
        )

    def _move(self, particle, global_best_position):
        p = self.params
        personal_best = particle["best_position"]

        for i in range(len(particle["position"])):
            cognitive = p.cognitive * random.random() * (
                personal_best[i] - particle["position"][i]
            )
            social = p.social * random.random() * (
                global_best_position[i] - particle["position"][i]
            )
            velocity = p.inertia * particle["velocity"][i] + cognitive + social
            velocity = max(-p.velocity_max, min(p.velocity_max, velocity))

            particle["velocity"][i] = velocity
            particle["position"][i] += velocity

