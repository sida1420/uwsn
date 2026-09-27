"""Simulator adapter for Adaptive Chaotic Ant Colony Optimization."""

from algorithms.ac_aco.optimizer import ACACOOptimizer
from algorithms.ac_aco.parameters import ACACOParameters
from algorithms.base import ClusteringAlgorithm


class ACACOClustering(ClusteringAlgorithm):
    name = "AC-ACO"

    def __init__(self, network, hparameters, ac_aco_params=None):
        super().__init__(network, hparameters)
        self.params = ac_aco_params or ACACOParameters()
        self.optimizer = ACACOOptimizer(network, hparameters, self.params)
        self.last_solution = None

    def select_cluster_heads(self, live_nodes, residual_e):
        self.last_solution = self.optimizer.optimize(live_nodes, residual_e)
        return list(self.last_solution.cluster_heads) if self.last_solution is not None else []

    def plan_round(self, live_nodes, residual_e):
        self.last_solution = self.optimizer.optimize(live_nodes, residual_e)
        return self.last_solution.root if self.last_solution is not None else None
