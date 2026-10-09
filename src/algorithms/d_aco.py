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

    def _run_ant(self, start, live_sensors, residual_e):
        """Build one solution for one ant.

        Returns (root, chs, consumption, fitness), or None if the ant failed.
        """
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
            return None

        consumption, cost = self.evaluator.energy_consumption(
            root,
            self.network.dist_matrix,
            self.network.base_dists,
        )
        loads = numpy.asarray(list(consumption.values()), dtype=float)
        mean_load = loads.mean() if loads.size else 0.0
        load_cv = float(loads.std() / mean_load) if mean_load > 0 else 0.0

        # Absolute fitness, no normalization (lower = better).
        fitness = (
            self.params.energy_weight * cost
            + self.params.load_weight * load_cv
        )
        return root, chs, consumption, fitness

    def plan_round(self, live_sensors, residual_e):
        best_root, best_chs = None, None
        best_fitness, best_consumption = float("inf"), {}

        self.clustering.pre_round(live_sensors, residual_e)

        for _ in range(self.params.iterations_per_round):
            starts = self.clustering.pre_iteration(live_sensors)
            it_best_chs, it_best_fitness = None, float("inf")

            for start in starts:
                result = self._run_ant(start, live_sensors, residual_e)
                if result is None:
                    continue
                root, chs, consumption, fitness = result

                # Per-ant deposit, immediately after the ant finishes.
                self.clustering.deposit(chs, fitness)

                if fitness < it_best_fitness:
                    it_best_chs, it_best_fitness = chs, fitness
                if fitness < best_fitness:
                    best_root, best_chs, best_fitness, best_consumption = (
                        root, chs, fitness, consumption
                    )

            self.clustering.post_iteration(it_best_chs, it_best_fitness)

        if best_root is None:
            return None, {}

        self.clustering.post_round(
            live_sensors,
            residual_e,
            best_consumption,
            best_chs,
            best_fitness,
        )
        return best_root, best_consumption