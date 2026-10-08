
from dataclasses import dataclass
from math import exp, isfinite, log
# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ACACOParameters:
    """AC-ACO controls; names separate pheromone and chaos weights."""

    num_ants: int = 40
    max_clustering_attempts: int = 10  # attempts per ant to build a feasible tree

    ch_proportion: float = 0.20
    pheromone_exponent: float = 1.0  # "alpha" on tau
    energy_cost_exponent: float = 1.0  # "gamma" on 1 / E_m
    beta_min: float = 1.0
    beta_max: float = 5.0
    beta_slope: float = 5.0
    rho_min: float = 0.10
    rho_max: float = 0.90  # baseline evaporation decreases from ~90% to 10%
    chaos_min: float = 0.05
    chaos_max: float = 0.30
    chaos_r: float = 3.61
    chaos_seed: float = 0.37
    Q: float = 100.0
    tau0: float = 1.0
    tau_min: float = 0.10
    tau_max: float = 10.0
    hopping_factor: float = 0.40

    def __post_init__(self):
        self._positive_integer("num_ants", self.num_ants)
        self._positive_integer("max_clustering_attempts", self.max_clustering_attempts)
        if not 0 < self.ch_proportion <= 1:
            raise ValueError("ch_proportion must be in (0, 1]")
        self._bounds("rho", self.rho_min, self.rho_max, strict_low=True, upper=1)
        self._bounds("beta", self.beta_min, self.beta_max)
        self._bounds("chaos", self.chaos_min, self.chaos_max)
        self._bounds("tau", self.tau_min, self.tau_max, strict_low=True)
        if not 3.57 < self.chaos_r < 4:
            raise ValueError("chaos_r must be in (3.57, 4)")
        if not 0 < self.chaos_seed < 1:
            raise ValueError("chaos_seed must be in (0, 1)")
        if not 0 <= self.hopping_factor <= 1:
            raise ValueError("hopping_factor must be in [0, 1]")
        for name in ("pheromone_exponent", "energy_cost_exponent", "beta_slope"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if not isfinite(self.Q) or self.Q <= 0:
            raise ValueError("Q must be finite and > 0")
        if not self.tau_min <= self.tau0 <= self.tau_max:
            raise ValueError("tau0 must be in [tau_min, tau_max]")

    @staticmethod
    def _positive_integer(name, value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be an integer >= 1")

    @staticmethod
    def _bounds(name, low, high, strict_low=False, upper=None):
        low_ok = low > 0 if strict_low else low >= 0
        if (
            not isfinite(low)
            or not isfinite(high)
            or not low_ok
            or low > high
            or (upper is not None and high >= upper)
        ):
            bound = f" and < {upper}" if upper is not None else ""
            operator = "0 <" if strict_low else "0 <="
            raise ValueError(f"{name} bounds must satisfy {operator} min <= max{bound}")
