"""NodeACO controls combined with ACACO's adaptive schedules and chaos."""

from dataclasses import dataclass
from math import isfinite

from algorithms.clustering.ac_aco.parameters import ACACOParameters


@dataclass(frozen=True)
class NodeACACOParameters(ACACOParameters):
    energy_cost_exponent: float = 0.05
    beta_min: float = 1.0
    beta_max: float = 5.0
    Q: float = 0.03
    tau_min: float = 1.0
    tau_max: float = 8.0
    theta: float = 0.1

    def __post_init__(self):
        super().__post_init__()
        if not isfinite(self.theta) or self.theta < 0:
            raise ValueError("theta must be finite and >= 0")
