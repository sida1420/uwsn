from math import exp


def logistic_step(value, r):
    return r * value * (1.0 - value)


def evaporation_rate(iteration, total_iterations, rho_min, rho_max):
    """Equation (13), with the first optimizer iteration numbered one."""
    progress = min(max(iteration / max(total_iterations, 1), 0.0), 1.0)
    return rho_max - progress * (rho_max - rho_min)


def heuristic_weight(iteration, total_iterations, beta_min, beta_max, slope):
    """Equation (14), evaluated safely for large sigmoid exponents."""
    exponent = slope * (iteration - total_iterations / 2.0)
    if exponent >= 0:
        sigmoid = 1.0 / (1.0 + exp(-exponent))
    else:
        value = exp(exponent)
        sigmoid = value / (1.0 + value)
    return beta_min + (beta_max - beta_min) * sigmoid


def chaos_strength(total_energy, lower_energy, upper_energy, low, high):
    """Equation (15) with an explicit, bounded UWSN cost window."""
    if (
        total_energy is None
        or lower_energy is None
        or upper_energy is None
        or upper_energy <= lower_energy
    ):
        return low
    ratio = (total_energy - lower_energy) / (upper_energy - lower_energy)
    return low + (high - low) * min(max(ratio, 0.0), 1.0)
