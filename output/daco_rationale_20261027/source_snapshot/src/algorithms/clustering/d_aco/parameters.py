"""D-ACO controls: live pheromone and one combined fitness."""
from dataclasses import dataclass, fields
from math import isfinite


@dataclass
class DACOParameters:
    num_ants: int = 40
    max_clustering_attempts: int = 10
    CH_proportion: float = 0.2
    alpha: float = 1.8
    beta: float = 0.04
    gamma: float = 0.6
    density_decay: str = 'parabolic'
    load_power: float = 2.6
    load_density_weight: float = 0.84
    reference_memory: float = 0.8
    calibration_ants: int = 40
    density_epsilon: float = 1e-12
    hopping_factor: float = 0.4
    rho_min: float = 0.36
    rho_max: float = 0.52
    Q: float = 9.5  # deposit scale for fitness / energy reference
    theta: float = 0.84
    tau0: float = 1.0
    tau_min: float = 1.0
    tau_max: float = 25

    def __post_init__(self):
        self.validate()

    def validate(self):
        unknown = set(vars(self)) - {f.name for f in fields(self)}
        if unknown:
            raise ValueError(f'Unknown or obsolete D-ACO parameters: {sorted(unknown)}')
        for name in ('num_ants','max_clustering_attempts','calibration_ants'):
            value = getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,int) or value<1:
                raise ValueError(f'{name} must be a positive integer')
        for name in ('alpha','beta','gamma','load_density_weight','theta'):
            if not isfinite(getattr(self,name)) or getattr(self,name)<0:
                raise ValueError(f'{name} must be finite and nonnegative')
        if not isfinite(self.load_power) or self.load_power<1:
            raise ValueError('load_power must be finite and at least 1')
        if not 0<=self.reference_memory<1:
            raise ValueError('reference_memory must be in [0,1)')
        if not 0<self.CH_proportion<=1 or not 0<=self.hopping_factor<=1:
            raise ValueError('Invalid CH proportion or hopping factor')
        if not 0<self.rho_min<=self.rho_max<1:
            raise ValueError('Require 0 < rho_min <= rho_max < 1')
        for name in ('Q','density_epsilon','tau_min','tau0','tau_max'):
            if not isfinite(getattr(self,name)) or getattr(self,name)<=0:
                raise ValueError(f'{name} must be finite and positive')
        if not self.tau_min<=self.tau0<=self.tau_max or self.tau_min==self.tau_max:
            raise ValueError('Invalid pheromone bounds or initial value')
        if self.density_decay not in ('none','linear','quadratic','parabolic'):
            raise ValueError('Invalid grid density_decay')
