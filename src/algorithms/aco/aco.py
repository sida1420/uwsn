import random

from algorithms.base import ClusteringAlgorithm
from algorithms.aco.aco_parameters import ACOParameters
from algorithms.clustering import direct_routing
from evaluate import Evaluator


class ACOClustering(ClusteringAlgorithm):
    """
    Plain Ant Colony Optimization for cluster-head selection, paired
    with single-hop ("direct") clustering: sensors -> nearest CH -> base
    station. Unlike the earlier AC-ACO version, there's no chaos term
    and no adaptive schedule -- pheromone evaporates at a constant rate
    and alpha/beta/CH-proportion stay fixed for the whole run.

    Each round:
      1. `num_ants` ants each probabilistically pick a CH set, biased by
         pheromone and a (residual energy / distance-to-base) heuristic.
      2. Every candidate CH set is turned into a routing tree and scored
         by Evaluator.energy_consumption.
      3. The best tree found this round is returned, and its CH set
         gets a pheromone deposit.
    """

    name = "SimpleACO"

    def __init__(self, network, hparameters, aco_params: ACOParameters = None):
        super().__init__(network, hparameters)
        self.params = aco_params or ACOParameters()
        self.evaluator = Evaluator(hparameters)
        self.pheromone = [self.params.tau0] * network.N

    def plan_round(self, live_nodes, residual_e):
        best_root, best_CHs, best_cost = None, None, float("inf")

        for _ in range(self.params.num_ants):
            CHs = self._pick_CHs(live_nodes, residual_e)
            if CHs is None:
                continue

            root = direct_routing(
                CHs, live_nodes, self.network.dist_matrix,
                self.network.base_dists, self.network.radius,
            )
            if root is None:
                continue

            _, cost = self.evaluator.energy_consumption(
                root, self.network.dist_matrix, self.network.base_dists
            )
            if cost < best_cost:
                best_root, best_CHs, best_cost = root, CHs, cost

        if best_root is None:
            return None

        self._update_pheromone(best_CHs, best_cost)
        return best_root

    def _pick_CHs(self, live_nodes, residual_e):
        num_CHs = max(1, round(self.params.CH_proportion * len(live_nodes)))
        candidates = list(live_nodes)
        chosen = []

        for _ in range(num_CHs):
            if not candidates:
                return None

            weights = [
                (self.pheromone[i] ** self.params.alpha)
                * ((residual_e[i] / max(self.network.base_dists[i], 1e-9)) ** self.params.beta)
                for i in candidates
            ]
            if sum(weights) <= 0:
                return None

            pick = random.choices(candidates, weights=weights, k=1)[0]
            chosen.append(pick)
            candidates.remove(pick)

        return chosen

    def _update_pheromone(self, CHs, cost):
        rho = self.params.rho
        deposit = self.params.Q / cost if cost > 0 else 0.0

        for i in range(self.network.N):
            self.pheromone[i] *= (1 - rho)
        for i in CHs:
            self.pheromone[i] += deposit

        lo, hi = self.params.tau_min, self.params.tau_max
        self.pheromone = [min(max(p, lo), hi) for p in self.pheromone]
