from math import exp


def logistic_step(value, r):
    """One logistic-map step: x[n+1] = r*x[n]*(1-x[n])."""
    return r * value * (1.0 - value)


def evaporation_rate(progress, rho_min, rho_max):
    """Linearly reduce evaporation from exploration to exploitation."""
    progress = min(max(progress, 0.0), 1.0)
    return rho_max - progress * (rho_max - rho_min)


def heuristic_weight(progress, beta_min, beta_max, slope):
    """Sigmoid schedule from the AC-ACO presentation."""
    progress = min(max(progress, 0.0), 1.0)
    value = slope * (progress - 0.5)
    if value >= 0:
        sigmoid = 1.0 / (1.0 + exp(-value))
    else:
        exp_value = exp(value)
        sigmoid = exp_value / (1.0 + exp_value)
    return beta_min + (beta_max - beta_min) * sigmoid


def chaos_weight(energy_ratio, chaos_min, chaos_max):
    """Increase exploration as network residual energy decreases."""
    energy_ratio = min(max(energy_ratio, 0.0), 1.0)
    return chaos_min + (chaos_max - chaos_min) * (1.0 - energy_ratio)
