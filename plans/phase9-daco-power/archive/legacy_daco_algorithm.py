from algorithms.base.base import Algorithm
from legacy_daco_clustering import DACOClustering
from legacy_daco_parameters import DACOParameters
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
        if self.params.fitness_mode not in ("normalized", "absolute"):
            raise ValueError("fitness_mode must be normalized or absolute")
        if self.params.deposit_mode not in ("batch", "live"):
            raise ValueError("deposit_mode must be batch or live")
        if self.params.deposit_mode == "live" and self.params.fitness_mode != "absolute":
            raise ValueError("Live deposits require absolute fitness")
        for name in ("density_load_weight", "density_load_kappa"):
            value = getattr(self.params, name)
            if not numpy.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = DACOClustering(
            self.network,
            self.hparameters,
            self.params,
        )

    def plan_round(self, live_sensors, residual_e):
        candidates = []

        starts = self.clustering.pre_round(live_sensors, residual_e)
        density_context = None
        if self.params.density_load_weight > 0:
            density_context = self._density_load_context(live_sensors, residual_e)
        density_penalties = []

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
            penalty = (self._density_load_penalty(consumption, cost, density_context)
                       if density_context is not None else 0.0)
            density_penalties.append(penalty)
            if self.params.deposit_mode == "live":
                fitness = (self.params.energy_weight * cost + self.params.load_weight * load_cv
                           + self.params.density_load_weight * penalty)
                self.clustering.deposit(chs, fitness)

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
        if self.params.fitness_mode == "absolute":
            scored = [(energy_weight * c[2] + load_weight * c[4], c) for c in candidates]
        if density_context is not None:
            scored = [(fitness + self.params.density_load_weight * penalty, candidate)
                      for (fitness, candidate), penalty in zip(scored, density_penalties)]
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

    def _density_load_context(self, live_sensors, residual_e):
        density = self.clustering.grid.get_base_density(live_sensors)
        positive = density[density > 0]
        scale = float(numpy.median(positive)) if positive.size else 1.0
        scarcity = 1.0 + self.params.density_load_kappa / (1.0 + density / scale)
        return (list(live_sensors), numpy.asarray([residual_e[i] for i in live_sensors]),
                scarcity)

    @staticmethod
    def _density_load_penalty(consumption, cost, context):
        nodes, residual, scarcity = context
        depletion = numpy.asarray([consumption[i] for i in nodes]) / numpy.maximum(residual, 1e-12)
        # Divide by ideal equal relative depletion, keeping units compatible with CV.
        ideal = cost / max(float(residual.sum()), 1e-12)
        return float(numpy.max(depletion * scarcity) / max(ideal, 1e-12))
