from algorithms.base import ClusteringAlgorithm
from algorithms.ac_aco.cluster_tree import build_cluster_tree
from algorithms.ac_aco.optimizer import ACACOOptimizer
from algorithms.ac_aco.parameters import ACACOParameters


class ACACOClustering(ClusteringAlgorithm):
    """Adaptive Chaotic ACO for phase-1 cluster-head selection."""

    name = "AC-ACO"

    def __init__(self, network, hparameters, ac_aco_params=None):
        super().__init__(network, hparameters)
        self.params = ac_aco_params or ACACOParameters()
        self.optimizer = ACACOOptimizer(network, hparameters, self.params)
        self.last_solution = None

    def select_cluster_heads(self, live_nodes, residual_e, allowed_heads=None):
        """Run phase 1 and return the selected CH IDs for the current round."""
        self.last_solution = self.optimizer.optimize(
            live_nodes, residual_e, allowed_heads=allowed_heads
        )
        if self.last_solution is None:
            return None
        return list(self.last_solution.cluster_heads)

    def plan_round(self, live_nodes, residual_e):
        allowed_heads = None
        if self.params.enforce_sink_radius:
            alive = [node_id for node_id in live_nodes if residual_e[node_id] > 0]
            allowed_heads = [
                node_id
                for node_id in alive
                if self.network.base_dists[node_id] <= self.network.radius
            ]
            covered = {
                node_id
                for node_id in alive
                if any(
                    self.network.dist_matrix[node_id][ch] <= self.network.radius
                    for ch in allowed_heads
                )
            }
            if covered != set(alive):
                self.last_solution = None
                return None
        cluster_heads = self.select_cluster_heads(
            live_nodes, residual_e, allowed_heads=allowed_heads
        )
        if not cluster_heads:
            return None
        return build_cluster_tree(cluster_heads, self.last_solution.assignments)
