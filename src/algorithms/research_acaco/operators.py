"""Bounded mathematical operators, independent of physical simulation state."""
from dataclasses import dataclass
from math import cos, isfinite, pi, ulp
import numpy as np


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


def uniform_mix(probabilities, coefficient):
    """Cardinality-independent exploration. Empty distribution stays empty."""
    if not isfinite(coefficient) or not 0 <= coefficient <= 1:
        raise ValueError("exploration coefficient must be finite in [0,1]")
    values = np.asarray(probabilities, dtype=float)
    if not values.size:
        return []
    if not np.isfinite(values).all() or (values < 0).any() or values.sum() <= 0:
        raise ValueError("probabilities must be finite, nonnegative with positive mass")
    values = values / values.sum()
    return ((1 - coefficient) * values + coefficient / values.size).tolist()


def marginal_log_quality(deltas, energy_scale):
    """Positive H=exp(clip(-delta/s,-40,40)); s scales with observed costs."""
    values = np.asarray(deltas, dtype=float)
    if not values.size:
        return values
    if not np.isfinite(values).all() or not isfinite(energy_scale) or energy_scale <= 0:
        raise ValueError("finite deltas and positive energy scale required")
    scale = max(float(np.median(np.abs(values))), np.finfo(float).eps * energy_scale)
    return np.clip(-values / scale, -40, 40)


def evaporation_only(rho, chaos, kappa, low, high):
    values = (rho, chaos, kappa, low, high)
    if not all(isfinite(v) for v in values):
        raise ValueError("finite evaporation controls required")
    if not (0 <= low <= high < 1 and 0 <= chaos <= 1 and 0 <= kappa <= 1):
        raise ValueError("evaporation controls outside bounds")
    # The unchanged schedule can evaluate its endpoint as .09999999999999998.
    # Accept only floating-point roundoff, then enforce the intended closed interval.
    tolerance = 8 * ulp(max(abs(rho), abs(low), abs(high)))
    if rho < low - tolerance or rho > high + tolerance:
        raise ValueError("evaporation controls outside bounds")
    rho = min(high, max(low, rho))
    return min(high, max(low, rho * (1 - kappa * chaos)))


@dataclass
class ProgressFeedback:
    """Observe feasible candidates only; cyclic pulses prevent permanent maximum."""
    maximum: float = .25
    minimum: float = .02
    period: int = 8
    best: float = float("inf")
    stagnation: int = 0
    improvement_ema: float = 0.0

    def __post_init__(self):
        if not (isfinite(self.minimum) and isfinite(self.maximum)
                and 0 <= self.minimum <= self.maximum <= 1):
            raise ValueError("feedback bounds must be finite in [0,1]")
        if type(self.period) is not int or self.period < 2:
            raise ValueError("feedback period must be integer >=2")

    def observe(self, energy):
        if not isfinite(energy) or energy <= 0:
            raise ValueError("feedback requires positive finite energy")
        gain = 0.0
        if energy < self.best:
            if isfinite(self.best):
                gain = min(1.0, (self.best - energy) / self.best)
            self.best = energy
            self.stagnation = 0
        else:
            self.stagnation += 1
        self.improvement_ema = .8 * self.improvement_ema + .2 * gain

    def coefficient(self):
        pulse = (1 - cos(2 * pi * (self.stagnation % self.period) / self.period)) / 2
        return self.minimum + (self.maximum - self.minimum) * (1 - self.improvement_ema) * pulse
