"""Powered load divided by density, with shared frozen references."""
from dataclasses import dataclass
from math import exp, log
import numpy as np

TINY = np.finfo(float).tiny


@dataclass(frozen=True)
class FitnessReferences:
    energy: float
    penalty: float

    @classmethod
    def from_observations(cls, energies, penalties):
        return cls(max(float(np.mean(energies)),TINY),max(float(np.mean(penalties)),TINY))

    def updated(self, energies, penalties, memory):
        observed = self.from_observations(energies,penalties)
        def smooth(previous,new):
            return exp(memory*log(previous)+(1.-memory)*log(new))
        return FitnessReferences(smooth(self.energy,observed.energy),smooth(self.penalty,observed.penalty))


def power_density_penalty(consumption, nodes, residual, density, power, epsilon):
    loads = np.asarray([consumption[i] for i in nodes],dtype=float)
    depletion = loads/np.maximum(residual,1e-12)
    return float(np.mean(depletion**power/np.maximum(density,epsilon)))


def fitness(total_energy, combined_penalty, references, weight):
    """Energy + calibrated load^power/density; result is in joules."""
    return total_energy + weight*references.energy*(combined_penalty/references.penalty)
