from dataclasses import dataclass
from math import isfinite
from typing import Optional


@dataclass(frozen=True)
class ACACOParameters:
    """Configuration for phase-1 Adaptive Chaotic ACO clustering."""

    # Search budget. M=10 means ten candidate CH sets per network round.
    num_ants: int = 10
    num_iterations: int = 5
    ch_proportion: float = 0.10

    # Transition probability: tau^a * eta^beta * (1 / E_tx)^gamma.
    pheromone_weight: float = 1.0
    beta_min: float = 1.0
    beta_max: float = 5.0
    beta_slope: float = 5.0
    energy_cost_weight: float = 0.10

    # Adaptive evaporation and logistic chaos.
    rho_min: float = 0.10
    rho_max: float = 0.90
    chaos_min: float = 0.02
    chaos_max: float = 0.25
    chaos_r: float = 3.58
    chaos_seed: float = 0.37

    # Pheromone update.
    deposit_strength: float = 0.50
    tau0: float = 1.0
    tau_min: float = 0.10
    tau_max: float = 10.0

    # Normalized phase-1 objective (lower is better).
    energy_weight: float = 0.40
    distance_weight: float = 0.35
    load_balance_weight: float = 0.15
    extra_head_weight: float = 0.10

    # Phase-1 feasibility and reproducibility.
    ensure_member_coverage: bool = True
    enforce_sink_radius: bool = True
    random_seed: Optional[int] = 42

    def __post_init__(self):
        if isinstance(self.num_ants, bool) or not isinstance(self.num_ants, int):
            raise ValueError("num_ants must be an integer")
        if isinstance(self.num_iterations, bool) or not isinstance(self.num_iterations, int):
            raise ValueError("num_iterations must be an integer")
        if self.num_ants < 1:
            raise ValueError("num_ants must be >= 1")
        if self.num_iterations < 1:
            raise ValueError("num_iterations must be >= 1")
        if not 0 < self.ch_proportion <= 1:
            raise ValueError("ch_proportion must be in (0, 1]")
        if not 0 <= self.pheromone_weight:
            raise ValueError("pheromone_weight must be >= 0")
        if not 0 <= self.energy_cost_weight:
            raise ValueError("energy_cost_weight must be >= 0")
        self._validate_bounds("beta", self.beta_min, self.beta_max)
        self._validate_bounds("rho", self.rho_min, self.rho_max, upper=1.0)
        self._validate_bounds("chaos", self.chaos_min, self.chaos_max)
        self._validate_bounds("tau", self.tau_min, self.tau_max)
        if not 3.57 <= self.chaos_r <= 4.0:
            raise ValueError("chaos_r must be in [3.57, 4.0]")
        if not 0 < self.chaos_seed < 1:
            raise ValueError("chaos_seed must be in (0, 1)")
        if self.deposit_strength <= 0 or self.tau0 <= 0:
            raise ValueError("deposit_strength and tau0 must be > 0")
        if not self.tau_min <= self.tau0 <= self.tau_max:
            raise ValueError("tau0 must be in [tau_min, tau_max]")
        weights = (
            self.energy_weight,
            self.distance_weight,
            self.load_balance_weight,
            self.extra_head_weight,
        )
        numeric_values = (
            self.ch_proportion,
            self.pheromone_weight,
            self.beta_min,
            self.beta_max,
            self.beta_slope,
            self.energy_cost_weight,
            self.rho_min,
            self.rho_max,
            self.chaos_min,
            self.chaos_max,
            self.chaos_r,
            self.chaos_seed,
            self.deposit_strength,
            self.tau0,
            self.tau_min,
            self.tau_max,
            *weights,
        )
        if not all(isfinite(value) for value in numeric_values):
            raise ValueError("all numeric parameters must be finite")
        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("objective weights must be non-negative with a positive sum")

    @staticmethod
    def _validate_bounds(name, low, high, upper=None):
        if (
            not isfinite(low)
            or not isfinite(high)
            or low < 0
            or low > high
            or (upper is not None and high > upper)
        ):
            suffix = f" and <= {upper}" if upper is not None else ""
            raise ValueError(f"{name} bounds must satisfy 0 <= min <= max{suffix}")
