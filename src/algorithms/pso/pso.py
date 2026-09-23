import random

from algorithms.base import ClusteringAlgorithm
from algorithms.clustering import direct_routing
from algorithms.pso.pso_parameters import PSOParameters
from evaluate import Evaluator


class PSOClustering(ClusteringAlgorithm):
    """
    Particle Swarm Optimization for cluster-head selection.

    A particle contains one continuous score for every live node that can
    communicate directly with the base station. The nodes with the highest
    scores are selected as cluster heads, keeping the number of cluster heads
    fixed during a round. Feasible routing trees are ranked by energy use;
    infeasible candidates receive a coverage penalty that guides the swarm
    toward nodes capable of covering the remaining sensors.
    """

    name = "PSO"

    def __init__(self, network, hparameters, pso_params: PSOParameters = None):
        super().__init__(network, hparameters)
        self.params = pso_params or PSOParameters()
        self.evaluator = Evaluator(hparameters)

    def plan_round(self, live_nodes, residual_e):
        if not live_nodes:
            return None

        candidates = [
            node_id
            for node_id in live_nodes
            if self.network.base_dists[node_id] <= self.network.radius
        ]
        if not candidates:
            return None

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
                root, score = self._evaluate(CHs, live_nodes)

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

    def _evaluate(self, CHs, live_nodes):
        root = direct_routing(
            CHs,
            live_nodes,
            self.network.dist_matrix,
            self.network.base_dists,
            self.network.radius,
        )
        if root is not None:
            _, cost = self.evaluator.energy_consumption(
                root,
                self.network.dist_matrix,
                self.network.base_dists,
            )
            return root, cost

        # All selected CHs are base-reachable, so infeasibility means at least
        # one live sensor is outside every selected CH's communication radius.
        # The excess-distance penalty gives PSO a useful ordering among such
        # candidates while remaining much larger than any feasible energy cost.
        uncovered_distance = sum(
            max(
                0.0,
                min(self.network.dist_matrix[node_id][ch] for ch in CHs)
                - self.network.radius,
            )
            for node_id in live_nodes
        )
        return None, self.params.infeasible_penalty + uncovered_distance

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

