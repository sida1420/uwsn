import random

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering.aco.parameters import ACOParameters
from algorithms.clustering import build_clusters
from evaluate import Evaluator


class ACOClustering(ClusteringAlgorithm):
    """
    Plain Ant Colony Optimization for cluster-head selection. Unlike the
    earlier AC-ACO version, there's no chaos term and no adaptive
    schedule -- pheromone evaporates at a constant rate and
    alpha/beta/gamma/CH-proportion stay fixed for the whole run.

    CH selection is a *path*, not an independent pick per node: each ant
    starts at a random live node and walks node-to-node, picking the
    next CH based on the pheromone on that edge, a (residual energy /
    distance) heuristic, and how cheap that edge is to relay a packet
    across -- the same three factors as the old AC-ACO's make_path,
    just without the chaos term.

    Round lifecycle (driven by the SimpleACO algorithm):
      pre_round      -> pick `num_ants` distinct random start nodes
      create_clusters-> one ant walk (CH path) + build_clusters
      post_round     -> evaporate pheromone, deposit along best CH path
    """

    name = "ACOClustering"

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

    def pre_round(self, live_sensors, residual_e):
        return random.sample(live_sensors, min(self.params.num_ants, len(live_sensors)))

    def create_clusters(self, live_sensors, residual_e, start):
        """
        One clustering attempt for one ant.

        Returns (CH_nodes, nodes, outliers), or None if the ant could not
        build a CH path. The CH path order is the key order of CH_nodes.
        """
        CHs = self._make_path(live_sensors, residual_e, start)
        if CHs is None:
            return None

        return build_clusters(CHs, live_sensors, self.network.dist_matrix, self.network.radius)

    def post_round(self, live_sensors, residual_e, consumption, CH_list):
        self._update_pheromone(CH_list, sum(consumption.values()))

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
