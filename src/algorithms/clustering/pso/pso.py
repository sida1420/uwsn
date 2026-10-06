import random
from math import ceil

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering.pso.parameters import PSOParameters
from node import Node


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
        fresh_count = max(0, self.params.swarm_size - len(self._warm_start))
        heuristic_count = round(
            fresh_count * self.params.heuristic_seed_percentage
        )
        heuristic_scores = self._heuristic_scores(candidates, residual_e)

        particles = []
        fresh_index = 0
        for index in range(self.params.swarm_size):
            previous = self._warm_start[index] if index < len(self._warm_start) else None
            use_heuristic = previous is None and fresh_index < heuristic_count
            particles.append(
                self._new_particle(
                    dimensions,
                    candidates,
                    previous,
                    heuristic_scores if use_heuristic else None,
                )
            )
            if previous is None:
                fresh_index += 1

        return particles

    def decode(self, position, live_sensors):
        candidates = list(live_sensors)

        alive_fraction = len(live_sensors) / max(self.network.N, 1)
        proportion = min(
            self.params.max_CH_proportion,
            self.params.CH_proportion / max(alive_fraction, 1e-12),
        )
        num_CHs = max(1, round(proportion * len(live_sensors)))
        num_CHs = min(num_CHs, len(candidates))

        ranked = sorted(
            range(len(position)),
            key=lambda index: position[index],
            reverse=True,
        )
        return [candidates[index] for index in ranked[:num_CHs]]

    def create_clusters(self, live_sensors, residual_e, CHs):
        """Assign members using distance, CH load and residual energy."""
        CH_set = set(CHs)
        CH_nodes = {ch: Node(ch, isCH=True) for ch in CHs}
        nodes = dict(CH_nodes)
        outliers = []
        member_ids = [node_id for node_id in live_sensors if node_id not in CH_set]
        target_load = max(1, ceil(len(member_ids) / max(len(CHs), 1)))
        max_energy = max((residual_e[node_id] for node_id in live_sensors), default=1.0)

        # Place difficult, far-away members first so easy assignments do not
        # consume all capacity on the only CHs that can cover them.
        member_ids.sort(
            key=lambda node_id: min(
                self.network.dist_matrix[node_id][ch] for ch in CHs
            ),
            reverse=True,
        )

        for node_id in member_ids:
            reachable = [
                ch
                for ch in CHs
                if self.network.dist_matrix[node_id][ch] <= self.network.radius
            ]
            if not reachable:
                outliers.append(node_id)
                continue

            def assignment_score(ch):
                distance = self.network.dist_matrix[node_id][ch] / max(
                    self.network.radius, 1e-12
                )
                load = len(CH_nodes[ch].nxts) / target_load
                energy_risk = 1.0 - residual_e[ch] / max(max_energy, 1e-12)
                return (
                    self.params.assignment_distance_weight * distance
                    + self.params.assignment_load_weight * load
                    + self.params.assignment_energy_weight * energy_risk
                )

            parent = CH_nodes[min(reachable, key=assignment_score)]
            member = Node(node_id, prev=parent)
            parent.add_next(member)
            nodes[node_id] = member

        return CH_nodes, nodes, outliers

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

    def move(self, particle, global_best_position, iteration=0, total_iterations=1):
        p = self.params
        personal_best = particle["best_position"]
        progress = iteration / max(total_iterations - 1, 1)
        inertia = p.inertia_start + (p.inertia_end - p.inertia_start) * progress

        for i in range(len(particle["position"])):
            cognitive = p.cognitive * random.random() * (
                personal_best[i] - particle["position"][i]
            )
            social = p.social * random.random() * (
                global_best_position[i] - particle["position"][i]
            )
            velocity = inertia * particle["velocity"][i] + cognitive + social
            velocity = max(-p.velocity_max, min(p.velocity_max, velocity))

            particle["velocity"][i] = velocity
            particle["position"][i] = min(
                1.0,
                max(0.0, particle["position"][i] + velocity),
            )

        # A rank swap is a natural mutation for top-k decoding and prevents
        # the bounded continuous swarm from freezing on one CH ordering.
        if len(particle["position"]) >= 2 and random.random() < p.mutation_probability:
            first, second = random.sample(range(len(particle["position"])), 2)
            particle["position"][first], particle["position"][second] = (
                particle["position"][second],
                particle["position"][first],
            )

    def _new_particle(
        self,
        dimensions,
        candidates=None,
        previous=None,
        heuristic_scores=None,
    ):
        positions = []
        velocities = []

        for index in range(dimensions):
            node_id = candidates[index] if candidates is not None else index
            if previous is not None and node_id in previous["position"]:
                positions.append(previous["position"][node_id])
                velocities.append(previous["velocity"][node_id])
            else:
                if heuristic_scores is None:
                    positions.append(random.random())
                else:
                    positions.append(min(1.0, max(
                        0.0,
                        heuristic_scores[node_id] + random.uniform(-0.05, 0.05),
                    )))
                velocities.append(
                    random.uniform(-self.params.velocity_max, self.params.velocity_max)
                )

        return {
            "position": positions,
            "velocity": velocities,
            "best_position": None,
            "best_score": float("inf"),
        }

    def _heuristic_scores(self, candidates, residual_e):
        if not candidates:
            return {}

        max_energy = max(residual_e[node_id] for node_id in candidates)
        max_base_distance = max(self.network.base_dists[node_id] for node_id in candidates)
        scores = {}
        for node_id in candidates:
            energy = residual_e[node_id] / max(max_energy, 1e-12)
            sink_proximity = 1.0 - self.network.base_dists[node_id] / max(
                max_base_distance, 1e-12
            )
            coverage = sum(
                self.network.dist_matrix[node_id][other] <= self.network.radius
                for other in candidates
            ) / len(candidates)
            scores[node_id] = 0.50 * energy + 0.25 * sink_proximity + 0.25 * coverage
        return scores

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
