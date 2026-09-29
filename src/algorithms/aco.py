from algorithms.base.base import Algorithm
from algorithms.clustering.aco.aco import ACOClustering, ACOParameters
from algorithms.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator


class SimpleACO(Algorithm):
    """
    ACO cluster-head selection (ACOClustering) paired with multi-hop
    routing (dropping_member_multi_hop_routing, stateless so it stays a
    plain function): sensors -> nearest CH -> relay CHs -> base station.

    Each round:
      1. `num_ants` ants each start from a distinct random live node and
         walk out a CH path, edge by edge.
      2. Every candidate CH path is turned into a routing tree and
         scored by Evaluator.energy_consumption.
      3. The best tree found this round is returned, and pheromone is
         deposited along the edges of its CH path.
    """

    name = "SimpleACO"

    def __init__(self, network, hparameters, aco_params: ACOParameters = None):
        self._aco_params = aco_params
        super().__init__(network, hparameters)

    def init_params(self):
        self.params = self._aco_params or ACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = ACOClustering(self.network, self.hparameters, self.params)

    def plan_round(self, live_sensors, residual_e):
        best_root, best_CHs, best_cost, best_consumption = None, None, float("inf"), {}

        starts = self.clustering.pre_round(live_sensors, residual_e)

        for start in starts:

            root = None
            CHs = None
            for _ in range(self.params.max_clustering_attempts):
                clusters = self.clustering.create_clusters(live_sensors, residual_e, start)
                self.total_clustering_attempts += 1

                if clusters is None:
                    self.failed_clustering_attempts += 1
                    break

                CH_nodes, nodes, outliers = clusters
                if CH_nodes is None:
                    self.failed_clustering_attempts += 1
                    continue
                CHs = list(CH_nodes)  # insertion order == ant's CH path order

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
                if root is not None:
                    break

            if root is None:
                self.failed_routing_attempts += 1
                continue

            consumption, cost = self.evaluator.energy_consumption(
                root, self.network.dist_matrix, self.network.base_dists
            )

            if cost < best_cost:
                best_root, best_CHs, best_cost, best_consumption = root, CHs, cost, consumption

        if best_root is None:
            return None, {}

        self.clustering.post_round(live_sensors, residual_e, best_consumption, best_CHs)
        return best_root, best_consumption
