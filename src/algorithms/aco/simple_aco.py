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
    and alpha/beta/gamma/CH-proportion stay fixed for the whole run.

    CH selection is a *path*, not an independent pick per node: each ant
    starts at a random live node and walks node-to-node, picking the
    next CH based on the pheromone on that edge, a (residual energy /
    distance) heuristic, and how cheap that edge is to relay a packet
    across -- the same three factors as the old AC-ACO's make_path,
    just without the chaos term.

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
        super().__init__(network, hparameters)
        self.params = aco_params or ACOParameters()
        self.evaluator = Evaluator(hparameters)

        # pheromone[i][j] = pheromone on the directed edge i -> j
        self.pheromone = [[self.params.tau0] * network.N for _ in range(network.N)]

        # Precomputed "cheap to relay through" heuristic: how little
        # energy it costs to forward one packet across edge i -> j.
        # Static for the whole run -- only depends on distance, not on
        # who's still alive -- so it's computed once here rather than
        # every round.
        self.E_m_heuristic = [[0.0] * network.N for _ in range(network.N)]
        for i in range(network.N):
            for j in range(network.N):
                if i != j:
                    cost = self.evaluator.E_m(self.network.dist_matrix[i][j])
                    self.E_m_heuristic[i][j] = (1 / cost) ** self.params.beta

    def plan_round(self, live_sensors, residual_e):
        best_root, best_CHs, best_cost = None, None, float("inf")

        starts = random.sample(live_sensors, min(self.params.num_ants, len(live_sensors)))

        for start in starts:

            root = None
            CHs= None
            for _ in range(self.params.max_clustering_attempts):
            # for _ in range(10):  # temp fix
                CHs = self._make_path(live_sensors, residual_e, start)

                if CHs is None:
                    break

                CH_nodes, nodes, outliers = build_clusters(CHs, live_sensors, self.network.dist_matrix, self.network.radius)
                if CH_nodes is None:
                    print("Failed to build clusters")
                    continue
                root = multi_hop_routing(
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

    def _make_path(self, live_nodes, residual_e, start_node):
        """
        Walk out a CH path edge by edge: from the current node, pick the
        next CH biased by pheromone on that edge, (residual energy /
        distance) at the candidate, and how cheap it is to relay a
        packet across that edge -- i.e. make_path.
        """
        num_CHs = max(1, round(self.params.CH_proportion * len(live_nodes)))

        curr = start_node
        CH_list = [curr]
        CH_set = {curr}

        while len(CH_list) < num_CHs:
            allowed = [i for i in live_nodes if i not in CH_set]
            if not allowed:
                return None

            weights = [
                self.pheromone[curr][i] ** self.params.alpha
                * (residual_e[i] / max(self.network.dist_matrix[curr][i], 1e-9)) ** self.params.gamma
                * self.E_m_heuristic[curr][i]
                for i in allowed
            ]
            if sum(weights) <= 0:
                return None

            curr = random.choices(allowed, weights=weights, k=1)[0]
            CH_list.append(curr)
            CH_set.add(curr)

        

        return CH_list

    def _update_pheromone(self, CH_list, cost):
        rho = self.params.rho
        deposit = self.params.Q / cost if cost > 0 else 0.0

        for i in range(self.network.N):
            for j in range(self.network.N):
                self.pheromone[i][j] *= (1 - rho)

        for a, b in zip(CH_list, CH_list[1:]):
            self.pheromone[a][b] += deposit

        lo, hi = self.params.tau_min, self.params.tau_max
        for i in range(self.network.N):
            self.pheromone[i] = [min(max(p, lo), hi) for p in self.pheromone[i]]
