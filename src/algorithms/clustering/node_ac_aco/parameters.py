"""NodeACO controls combined with ACACO's adaptive schedules and chaos."""

from dataclasses import dataclass
from math import isclose, isfinite

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
    w_energy: float = 1.0
    w_load: float = 0.0
    # Fixed joule reference, shared by all ants and rounds. 1 J preserves the
    # original energy-only score/deposit scale without changing Q or bounds.
    energy_reference: float = 1.0
    fitness_eps: float = 1e-12

    def __post_init__(self):
        super().__post_init__()
        if not isfinite(self.theta) or self.theta < 0:
            raise ValueError("theta must be finite and >= 0")
        if any(not isfinite(w) or w < 0 or w > 1 for w in (self.w_energy, self.w_load)):
            raise ValueError("fitness weights must be finite and in [0, 1]")
        if not isclose(self.w_energy + self.w_load, 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("fitness weights must sum to 1")
        for name in ("energy_reference", "fitness_eps"):
            if not isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be finite and > 0")
