from algorithms.base.base import Algorithm
from algorithms.clustering.node_aco import NodeACOClustering
from algorithms.clustering.node_aco.parameters import NodeACOParameters
from algorithms.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator


class NodeACO(Algorithm):
    """Simple ACO variant whose pheromone is associated with CH nodes."""

    name = "NodeACO"

    def __init__(self, network, hparameters, aco_params: NodeACOParameters = None):
        self._aco_params = aco_params
        super().__init__(network, hparameters)

    def init_params(self):
        self.params = self._aco_params or NodeACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = NodeACOClustering(self.network, self.hparameters, self.params)

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
                CHs = list(CH_nodes)
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
            self.clustering.deposit(CHs, cost)
            if cost < best_cost:
                best_root, best_CHs, best_cost, best_consumption = (
                    root, CHs, cost, consumption
                )

        if best_root is None:
            return None, {}

        self.clustering.post_round(
            live_sensors,
            residual_e,
            best_consumption,
            best_CHs,
        )
        return best_root, best_consumption
