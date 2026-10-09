"""NodeACACO with complete-service, affordable multi-objective tree scoring."""

from algorithms.ac_aco import ACACO
from algorithms.clustering.node_ac_aco.node_ac_aco import NodeACACOClustering
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters
from algorithms.clustering.node_ac_aco.fitness import score_candidate, valid_live_sensors
from algorithms.routing.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator


class NodeACACO(ACACO):
    name = "NodeACACO"

    def __init__(self, network, hparameters, params: NodeACACOParameters = None, seed=None):
        super().__init__(network, hparameters, params, seed)

    def init_params(self):
        self.params = self._params if self._params is not None else NodeACACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = NodeACACOClustering(
            self.network, self.hparameters, self.params, seed=self._seed
        )
        self.last_candidates = []
        self.last_best = None
        self.last_state = None
        self.last_convergence = []

    def plan_round(self, live_sensors, residual_e):
        """Rank and reinforce by fitness; return the actual per-node joules.

        All candidate evaluation is read-only. Keep the physical-energy window
        for adaptive chaos so fitness weights do not redefine that mechanism.
        """
        self.last_candidates, self.last_convergence = [], []
        self.last_best = self.last_state = None
        if not valid_live_sensors(live_sensors, residual_e, self.network.N):
            return None, {}
        state = self.clustering.pre_round(live_sensors, residual_e)
        self.last_state = state
        best = None
        for _ in range(self.params.num_ants):
            for _attempt in range(self.params.max_clustering_attempts):
                self.total_clustering_attempts += 1
                clusters = self.clustering.create_clusters(live_sensors, residual_e, state)
                if clusters is None:
                    self.failed_clustering_attempts += 1
                    continue
                CH_nodes, nodes, outliers = clusters
                heads = tuple(CH_nodes)
                self.total_routing_attempts += 1
                root = dropping_member_multi_hop_routing(
                    CH_nodes, nodes, state.live, outliers,
                    self.network.dist_matrix, self.network.base_dists, residual_e,
                    self.network.radius, self.params.hopping_factor,
                )
                candidate = score_candidate(
                    root, state.live, residual_e, self.network,
                    self.evaluator, self.params, heads,
                )
                if candidate is None:
                    self.failed_routing_attempts += 1
                    continue
                self.clustering.deposit(heads, candidate.fitness)
                self.last_candidates.append(candidate)
                if best is None or (candidate.fitness, heads) < (best.fitness, best.heads):
                    best = candidate
                break
            self.last_convergence.append(best.fitness if best else None)
        self.last_best = best
        self.clustering.post_round(
            live_sensors, residual_e, best.consumption if best else {}, state=state,
            candidate_costs=[c.total_energy for c in self.last_candidates],
            CH_list=best.heads if best else None,
            best_fitness=best.fitness if best else None,
        )
        return (best.root, best.consumption) if best else (None, {})
