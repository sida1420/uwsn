"""Energy plus calibrated powered relative load, without a density term."""
import numpy as np

from algorithms.clustering.d_aco.fitness import FitnessReferences


def power_load_penalty(consumption, nodes, residual, power):
    """Mean powered fraction of pre-round energy spent by every live sensor."""
    loads = np.asarray([consumption[i] for i in nodes], dtype=float)
    depletion = loads / np.maximum(residual, 1e-12)
    return float(np.mean(depletion ** power))


def fitness(total_energy, load_penalty, references, weight):
    """Score in joules; references remain fixed throughout an ant batch."""
    if weight == 0:
        return total_energy
    return total_energy + weight * references.energy * (load_penalty / references.penalty)
