from math import isfinite

from algorithms.base.base import Algorithm
from algorithms.clustering.ac_aco.ac_aco import ACACOClustering, ACACOParameters
from algorithms.routing.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator


class ACACO(Algorithm):
    """
    AC-ACO cluster-head selection (ACACOClustering) paired with multi-hop
    routing (dropping_member_multi_hop_routing).

    Each simulator round:
      1. pre_round computes this round's rho / beta / chaos strength.
      2. `num_ants` ants each build an ordered CH path (up to
         `max_clustering_attempts` tries until routing is feasible).
      3. Every feasible tree is scored by Evaluator.energy_consumption;
         the cheapest one is returned.
      4. post_round updates the cost window and pheromone once, even if
         every ant failed.
    """

    name = "AC-ACO"

    def __init__(self, network, hparameters, params: ACACOParameters = None, seed=None):
        self._params = params
        self._seed = seed
        super().__init__(network, hparameters)

    def init_params(self):
        self.params = self._params or ACACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = ACACOClustering(
            self.network, self.hparameters, self.params, seed=self._seed
        )

    def plan_round(self, live_sensors, residual_e):
        state = self.clustering.pre_round(live_sensors, residual_e)
        if state is None:
            return None, {}

        candidates = []  # (cost, CHs, root, consumption)
        for _ in range(self.params.num_ants):
            for _attempt in range(self.params.max_clustering_attempts):
                self.total_clustering_attempts += 1
                clusters = self.clustering.create_clusters(live_sensors, residual_e, state)
                if clusters is None:
                    self.failed_clustering_attempts += 1
                    continue

                CH_nodes, nodes, outliers = clusters
                CHs = tuple(CH_nodes)  # insertion order == ant's CH path order

                self.total_routing_attempts += 1
                root = dropping_member_multi_hop_routing(
                    CH_nodes,
                    nodes,
                    state.live,
                    outliers,
                    self.network.dist_matrix,
                    self.network.base_dists,
                    residual_e,
                    self.network.radius,
                    self.params.hopping_factor,
                )
                if root is None:
                    self.failed_routing_attempts += 1
                    continue

                consumption, cost = self.evaluator.energy_consumption(
                    root, self.network.dist_matrix, self.network.base_dists
                )
                if not isfinite(cost) or cost <= 0:
                    self.failed_routing_attempts += 1
                    continue

                self.clustering.deposit(CHs, cost)
                candidates.append((cost, CHs, root, consumption))
                break

        best = min(candidates, key=lambda c: (c[0], c[1]), default=None)

        self.clustering.post_round(
            live_sensors,
            residual_e,
            best[3] if best else {},
            state=state,
            candidate_costs=[c[0] for c in candidates],
            CH_list=best[1] if best else None,
        )

        if best is None:
            return None, {}
        return best[2], best[3]
