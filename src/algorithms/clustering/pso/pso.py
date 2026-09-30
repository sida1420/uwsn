import random

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering import build_clusters
from algorithms.clustering.pso.parameters import PSOParameters


class PSOClustering(ClusteringAlgorithm):
    """
    Particle Swarm Optimization for cluster-head selection.

    A particle contains one continuous score for every live node. The nodes
    with the highest scores are selected as cluster heads, keeping the number
    of cluster heads fixed during a round. Cluster heads may relay through
    other cluster heads toward the base. Feasible routing trees are ranked by
    energy use; infeasible candidates receive a connectivity penalty.

    Round lifecycle (driven by the PSO algorithm):
      pre_round       -> build the swarm (warm-started from last round)
      decode          -> particle position -> CH list
      create_clusters -> assign members to a CH list
      move            -> velocity/position update of one particle
      post_round      -> keep the best particles for the next round
    """

    name = "PSOClustering"

    def __init__(self, network, hparameters, pso_params: PSOParameters = None):
        super().__init__(network, hparameters)
        self.params = pso_params or PSOParameters()
        self._warm_start = []
        self.last_deleted_particles = 0

    def pre_round(self, live_sensors, residual_e):
        candidates = list(live_sensors)
        dimensions = len(candidates)

        particles = []
        for index in range(self.params.swarm_size):
            previous = self._warm_start[index] if index < len(self._warm_start) else None
            particles.append(self._new_particle(dimensions, candidates, previous))

        return particles

    def decode(self, position, live_sensors):
        candidates = list(live_sensors)

        num_CHs = max(1, round(self.params.CH_proportion * len(live_sensors)))
        num_CHs = min(num_CHs, len(candidates))

        ranked = sorted(
            range(len(position)),
            key=lambda index: position[index],
            reverse=True,
        )
        return [candidates[index] for index in ranked[:num_CHs]]

    def create_clusters(self, live_sensors, residual_e, CHs):
        """Assign members to the decoded CH list. Returns (CH_nodes, nodes, outliers)."""
        return build_clusters(
            CHs,
            live_sensors,
            self.network.dist_matrix,
            self.network.radius,
        )

    def post_round(self, live_sensors, residual_e, consumption, particles):
        self._retain_particles_for_next_round(particles, list(live_sensors))

    def infeasible_score(self, CHs, live_sensors):
        # Penalize both uncovered sensors and CHs that lack a shorter hop
        # toward the base. This gives the swarm useful direction even before
        # it discovers its first fully feasible tree.
        uncovered_distance = sum(
            max(
                0.0,
                min(self.network.dist_matrix[node_id][ch] for ch in CHs)
                - self.network.radius,
            )
            for node_id in live_sensors
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

        return self.params.infeasible_penalty + uncovered_distance + relay_distance

    def move(self, particle, global_best_position):
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

    def _retain_particles_for_next_round(self, particles, candidates):
        delete_percentage = self.params.particle_delete_percentage
        if not 0.0 <= delete_percentage <= 1.0:
            raise ValueError("particle_delete_percentage must be between 0.0 and 1.0")

        delete_count = int(len(particles) * delete_percentage)
        survivor_count = len(particles) - delete_count
        survivors = sorted(
            particles,
            key=lambda particle: particle["best_score"],
        )[:survivor_count]

        # Store coordinates by sensor id because the live-node candidate list
        # can shrink before the next simulation round. Fitness is not retained:
        # residual energy changes the objective every round.
        self._warm_start = [
            {
                "position": dict(zip(candidates, particle["position"])),
                "velocity": dict(zip(candidates, particle["velocity"])),
            }
            for particle in survivors
        ]
        self.last_deleted_particles = delete_count
