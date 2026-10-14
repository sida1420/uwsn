from dataclasses import asdict
from math import isfinite
import numpy as np
from algorithms.d_aco import DACO
from algorithms.aco import SimpleACO
from algorithms.pso import PSO
from algorithms.ac_aco import ACACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering.aco.parameters import ACOParameters
from algorithms.clustering.pso.parameters import PSOParameters
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from optimizer.search_space import SPACE
from algorithms.research_acaco import ResearchACACO, ResearchOptions

REGISTRY = {}
def register(adapter):
    if adapter.name in REGISTRY: raise ValueError('Duplicate adapter')
    REGISTRY[adapter.name] = adapter
def get(name): return REGISTRY[name]

class BaseAdapter:
    adapter_version = '2-local-seed'
    parameter_space_version = 'native-v1'
    time_dependency_version = 'native-clock-v1'
    state_schema_version = 'pickle-rng-v1'
    evaluation_budget_policy = 'native search effort; fixed in primary campaign'
    space = {}
    def diagnostics(self, a):
        return dict(native_iterations=getattr(a,'last_iterations',1),
                    attempted=getattr(a,'last_evaluation_requests',None),
                    unique=getattr(a,'last_unique_evaluations',None))
    def effective_config(self, cfg):
        self.validate_config(cfg);return {**self.baseline_config(), **cfg}
    def suggest(self, trial):
        values={k:trial.suggest_float(k,lo,hi,log=log) for k,(lo,hi,log) in self.space.items()}
        return self.effective_config(values)

class DACOAdapter(BaseAdapter):
    name='daco';native_fitness_id='energy-plus-calibrated-power-density-v1'
    parameter_space_version='ten-coordinates-parabolic-v1';space=SPACE
    def baseline_config(self): return asdict(DACOParameters())
    def validate_config(self,cfg):
        p=DACOParameters(**cfg)
        if p.rho_min>=p.rho_max: raise ValueError('Require rho_min < rho_max')
    def make_algorithm(self,n,h,cfg,seed): return DACO(n,h,DACOParameters(**self.effective_config(cfg)),seed=seed)
    def diagnostics(self,a):
        tau=np.asarray(a.clustering.pheromone)
        refs=a.references
        return dict(rho=a.clustering.rho,pheromone_saturation=float(np.mean(tau>=a.params.tau_max)),
                    score_reference=refs.energy if refs else None,theta=a.params.theta,
                    n_ants=a.params.num_ants,n_sensors=a.network.N)

class SimpleAdapter(BaseAdapter):
    name='simple';native_fitness_id='physical-energy-v1'
    def baseline_config(self):
        p=ACOParameters();p.beta=p.gamma=0.;return vars(p)
    def validate_config(self,cfg):
        if set(cfg)-set(self.baseline_config()): raise ValueError('Unknown SimpleACO fields')
    def make_algorithm(self,n,h,cfg,seed):
        p=ACOParameters();vars(p).update(self.effective_config(cfg));return SimpleACO(n,h,p,seed=seed)

class PSOAdapter(BaseAdapter):
    name='pso';native_fitness_id='energy-plus-max-relative-depletion-v1'
    def baseline_config(self): return vars(PSOParameters())
    def validate_config(self,cfg):
        if set(cfg)-set(self.baseline_config()): raise ValueError('Unknown PSO fields')
        c={**self.baseline_config(),**cfg}
        if any(not isfinite(v) for v in c.values()): raise ValueError('Nonfinite PSO field')
        for k in ('swarm_size','iterations'):
            if type(c[k]) is not int or c[k]<1: raise ValueError(k)
        if not 0<=c['mutation_probability']<=1 or c['velocity_max']<=0: raise ValueError('Invalid PSO controls')
    def make_algorithm(self,n,h,cfg,seed):
        a=PSO(n,h,seed=seed);vars(a.params).update(self.effective_config(cfg));return a

class ACACOAdapter(BaseAdapter):
    name='acaco';native_fitness_id='native-energy-load-cv-v1'
    def baseline_config(self): return asdict(ACACOParameters())
    def validate_config(self,cfg): ACACOParameters(**cfg)
    def make_algorithm(self,n,h,cfg,seed): return ACACO(n,h,ACACOParameters(**self.effective_config(cfg)),seed=seed)

class ACACOV2V6Adapter(BaseAdapter):
    """Fixed V2+V6 operators, with five opt-in smoke parameter coordinates."""
    name = 'acaco_v2_v6'
    native_fitness_id = 'physical-energy-marginal-evaporation-only-v1'
    parameter_space_version = 'five-coordinates-smoke-v1'
    space = dict(pheromone_exponent=(.5, 2., False), beta_min=(.5, 2., False),
                 Q=(.003, .03, True), rho_max=(.3, .7, False), elite_weight=(0., .2, False))

    def baseline_config(self):
        from dataclasses import replace
        return asdict(replace(ACACOParameters(), num_ants=40, load_weight=0.,
                              tau_min=.01, tau0=1., tau_max=20.))

    def validate_config(self, cfg):
        baseline = self.baseline_config()
        if set(cfg) - set(baseline):
            raise ValueError('Unknown V2+V6 parameter')
        values = {**baseline, **cfg}
        ACACOParameters(**values)
        for name, value in values.items():
            if name not in self.space and value != baseline[name]:
                raise ValueError(f'V2+V6 smoke fixes {name}={baseline[name]}')
        for name, (low, high, _) in self.space.items():
            if not low <= values[name] <= high:
                raise ValueError(f'{name} outside declared smoke search space')

    def make_algorithm(self, network, hp, cfg, seed):
        algorithm = ResearchACACO(network, hp,
            params=ACACOParameters(**self.effective_config(cfg)), seed=seed,
            options=ResearchOptions(heuristic='marginal', chaos_policy='evaporation',
                                    evaporation_kappa=.5))
        algorithm.name = 'AC-ACO-V2-V6-parameter-trial'
        return algorithm

    def diagnostics(self, algorithm):
        c = algorithm.clustering
        tau = np.asarray(c.pheromone)
        return dict(chaos_policy='evaporation', selection_chaos=c.last_exploration,
            evaporation_kappa=.5, effective_rho_mean=float(np.mean(c.effective_rhos))
                if c.effective_rhos else None,
            pheromone_floor=float(np.mean(tau <= c.params.tau_min)),
            pheromone_ceiling=float(np.mean(tau >= c.params.tau_max)),
            proxy_cell_operations=c.proxy.operations if c.proxy else 0,
            proxy_seconds=c.proxy_seconds, n_ants=c.params.num_ants)


for adapter in (DACOAdapter(),SimpleAdapter(),PSOAdapter(),ACACOAdapter(),ACACOV2V6Adapter()): register(adapter)
