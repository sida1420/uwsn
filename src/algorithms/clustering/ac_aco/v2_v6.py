"""Marginal-energy construction (V2) and evaporation-only chaos (V6)."""
from math import isfinite, ulp

import numpy as np

from algorithms.clustering.ac_aco.ac_aco import ACACOClustering, logistic_step
from algorithms.clustering.ac_aco.surrogate import MarginalEnergyProxy


def normalized_weights(log_weights):
    values = np.asarray(log_weights, dtype=float)
    if not values.size:
        return []
    valid = np.isfinite(values)
    if not valid.any():
        return np.full(values.size, 1 / values.size).tolist()
    weights = np.zeros(values.size)
    weights[valid] = np.exp(values[valid] - values[valid].max())
    return (weights / weights.sum()).tolist()


def marginal_log_quality(deltas, energy_scale):
    """Scale marginal energy differences into bounded log-quality weights."""
    values = np.asarray(deltas, dtype=float)
    if not values.size:
        return values
    if not np.isfinite(values).all() or not isfinite(energy_scale) or energy_scale <= 0:
        raise ValueError("finite deltas and positive energy scale required")
    scale = max(float(np.median(np.abs(values))), np.finfo(float).eps * energy_scale)
    return np.clip(-values / scale, -40, 40)


def evaporation_only(rho, chaos, kappa, low, high):
    if not all(isfinite(v) for v in (rho, chaos, kappa, low, high)):
        raise ValueError("finite evaporation controls required")
    if not (0 <= low <= high < 1 and 0 <= chaos <= 1 and 0 <= kappa <= 1):
        raise ValueError("evaporation controls outside bounds")
    # The schedule endpoint can be .09999999999999998 instead of .1.
    tolerance = 8 * ulp(max(abs(rho), abs(low), abs(high)))
    if rho < low - tolerance or rho > high + tolerance:
        raise ValueError("evaporation controls outside bounds")
    rho = min(high, max(low, rho))
    return min(high, max(low, rho * (1 - kappa * chaos)))


class ACACOV2V6Clustering(ACACOClustering):
    evaporation_kappa = 0.5

    def pre_round(self, live_sensors, residual_e):
        state = super().pre_round(live_sensors, residual_e)
        if state is not None:
            self.proxy = MarginalEnergyProxy(self.network, self.evaluator, state.live)
        return state

    def _construct_candidate(self, state, residual_e):
        available = list(state.live)
        selected = [self.rng.choice(available)]
        available.remove(selected[0])
        while available and len(selected) < state.target:
            self.partial = tuple(selected)
            probabilities = self._transition_probabilities(
                selected[-1], available, residual_e, state.beta, state.strength
            )
            chosen = self.rng.choices(available, weights=probabilities, k=1)[0]
            selected.append(chosen)
            available.remove(chosen)
        return tuple(selected)

    def _transition_probabilities(self, source, available, residual_e, beta, strength):
        if not available:
            return []
        deltas = self.proxy.additions(self.partial, available)
        quality = marginal_log_quality(deltas, self.proxy.energy_scale)
        tau = np.asarray(self.pheromone[source])[available]
        logs = self.params.pheromone_exponent * np.log(tau) + beta * quality
        # Preserve the research preset's normalization and seeded arithmetic.
        base = np.asarray(normalized_weights(logs), dtype=float)
        base = base / base.sum()
        return base.tolist()

    def _update_pheromone(self, state):
        p = self.params
        for source in state.live:
            rho = evaporation_only(state.rho, self.chaos[source],
                                   self.evaporation_kappa, p.rho_min, p.rho_max)
            for target in state.live:
                if source != target:
                    self.pheromone[source][target] = min(p.tau_max, max(
                        p.tau_min, (1 - rho) * self.pheromone[source][target]))
            self.chaos[source] = logistic_step(self.chaos[source], p.chaos_r)
