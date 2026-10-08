from algorithms.base.base import Algorithm
from algorithms.clustering.d_aco.d_aco import DACOClustering
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator
import numpy


class DACO(Algorithm):
    """Density-aware ACO clustering paired with dropping multi-hop routing."""

    name = "D-ACO"

    def __init__(self, network, hparameters, aco_params: DACOParameters = None):
        self._aco_params = aco_params
        super().__init__(network, hparameters)

    def init_params(self):
        self.params = self._aco_params or DACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = DACOClustering(
            self.network,
            self.hparameters,
            self.params,
        )

    def plan_round(self, live_sensors, residual_e):
        candidates = []

        starts = self.clustering.pre_round(live_sensors, residual_e)

        for start in starts:
            root = None
            chs = None

            for _ in range(self.params.max_clustering_attempts):
                clusters = self.clustering.create_clusters(
                    live_sensors,
                    residual_e,
                    start,
                )
                self.total_clustering_attempts += 1

                if clusters is None:
                    self.failed_clustering_attempts += 1
                    break

                ch_nodes, nodes, outliers = clusters
                if ch_nodes is None:
                    self.failed_clustering_attempts += 1
                    continue

                chs = list(ch_nodes)
                self.total_routing_attempts += 1
                root = dropping_member_multi_hop_routing(
                    ch_nodes,
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
                root,
                self.network.dist_matrix,
                self.network.base_dists,
            )
            loads = numpy.asarray(list(consumption.values()), dtype=float)
            mean_load = loads.mean() if loads.size else 0.0
            load_cv = (
                float(loads.std() / mean_load)
                if mean_load > 0
                else 0.0
            )
            candidates.append((root, chs, cost, consumption, load_cv))

        if not candidates:
            return None, {}

        mean_energy = sum(candidate[2] for candidate in candidates) / len(candidates)
        mean_cv = sum(candidate[4] for candidate in candidates) / len(candidates)
        energy_weight = self.params.energy_weight
        load_weight = self.params.load_weight

        scored = [
            (
                energy_weight * candidate[2] / max(mean_energy, 1e-12)
                + load_weight * candidate[4] / max(mean_cv, 1e-12)
                if mean_cv > 0
                else energy_weight * candidate[2] / max(mean_energy, 1e-12)
                + load_weight,
                candidate,
            )
            for candidate in candidates
        ]
        best_fitness, (best_root, best_chs, best_cost, best_consumption, _) = min(
            scored,
            key=lambda item: item[0],
        )
        self.clustering.post_round(
            live_sensors,
            residual_e,
            best_consumption,
            best_chs,
            best_fitness,
            scored,
        )
        return best_root, best_consumption
