import random

from algorithms.base import ClusteringAlgorithm
from algorithms.aco.aco_parameters import ACOParameters
from algorithms.routing import multi_hop_routing
from algorithms.clustering import build_clusters
from evaluate import Evaluator


class SimpleACO(ClusteringAlgorithm):
    """
    Plain Ant Colony Optimization for cluster-head selection, paired
    with multi-hop clustering: sensors -> nearest CH -> relay CHs -> base
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
        self.pheromone = [[self.params.tau0] * network.N for _ in range(network.N)]  # pheromone[i][j] = pheromone on edge i->j

    def plan_round(self, live_nodes, residual_e):
        best_root, best_CHs, best_cost = None, None, float("inf")

        for _ in range(self.params.num_ants):
            CHs = self._pick_CHs(live_nodes, residual_e)

            print(f"Selected CHs: {CHs}")
            if CHs is None:
                continue
            CH_nodes= None
            root = None

            # for _ in range(self.params.max_clusterting_attempts):
            for _ in range(10): #temp fix

                CH_nodes=build_clusters(CHs, live_nodes, self.network.dist_matrix, self.network.radius)
                if CH_nodes is None:
                    print("Failed to build clusters")
                    continue
                root = multi_hop_routing(
                    CH_nodes,
                    live_nodes,
                    self.network.dist_matrix,
                    self.network.base_dists,
                    residual_e,
                    self.network.radius,
                    self.params.hopping_factor,
                )
                if root is not None:
                    break
            
            if root is None:
                print("Failed to create routing tree")
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
        print(f"Picking {num_CHs} CHs from {len(live_nodes)} live nodes with proportion {self.params.CH_proportion}")
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
