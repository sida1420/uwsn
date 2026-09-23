import random

from algorithms.base import ClusteringAlgorithm
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

    def plan_round(self, live_nodes, residual_e):
        if not live_nodes:
            return None

        candidates = list(live_nodes)

        num_CHs = max(1, round(self.params.CH_proportion * len(live_nodes)))
        num_CHs = min(num_CHs, len(candidates))
        dimensions = len(candidates)

        particles = [
            self._new_particle(dimensions)
            for _ in range(self.params.swarm_size)
        ]

        global_best_position = None
        global_best_score = float("inf")
        best_feasible_root = None
        best_feasible_score = float("inf")

        for _ in range(self.params.iterations):
            for particle in particles:
                CHs = self._decode(particle["position"], candidates, num_CHs)
                root, score = self._evaluate(CHs, live_nodes, residual_e)

                if score < particle["best_score"]:
                    particle["best_score"] = score
                    particle["best_position"] = particle["position"].copy()

                if score < global_best_score:
                    global_best_score = score
                    global_best_position = particle["position"].copy()

                if root is not None and score < best_feasible_score:
                    best_feasible_root = root
                    best_feasible_score = score

            if global_best_position is None:
                continue

            for particle in particles:
                self._move(particle, global_best_position)

        return best_feasible_root

    def _new_particle(self, dimensions):
        return {
            "position": [random.random() for _ in range(dimensions)],
            "velocity": [
                random.uniform(-self.params.velocity_max, self.params.velocity_max)
                for _ in range(dimensions)
            ],
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
        root = multi_hop_routing(
            CHs,
            live_nodes,
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

