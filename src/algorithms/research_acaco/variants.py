"""Independent opt-in AC-ACO construction policies; inherited objective unchanged."""
from dataclasses import dataclass
from math import isfinite
import numpy as np
from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.ac_aco import ACACOClustering, ACACOParameters, logistic_step
from evaluate import Evaluator
from .operators import (ProgressFeedback, evaporation_only, marginal_log_quality,
                        normalized_weights, uniform_mix)
from .surrogate import MarginalEnergyProxy


@dataclass(frozen=True)
class ResearchOptions:
    heuristic: str = "baseline"
    chaos_policy: str = "baseline"
    distinct_starts: bool = False
    random_sets: bool = False
    fixed_scale: float = .1
    exploration_max: float = .25
    evaporation_kappa: float = .5

    def __post_init__(self):
        if self.heuristic not in ("baseline", "marginal"):
            raise ValueError("unknown heuristic")
        if self.chaos_policy not in ("baseline", "reduced", "normalized", "adaptive", "evaporation"):
            raise ValueError("unknown chaos policy")
        for name in ("fixed_scale", "exploration_max", "evaporation_kappa"):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite in [0,1]")
        if self.chaos_policy == "adaptive" and self.exploration_max < .02:
            raise ValueError("adaptive maximum must be >=.02")


class ResearchClustering(ACACOClustering):
    def __init__(self, network, hp, params, seed, options):
        super().__init__(network, hp, params, seed)
        self.options = options
        self.feedback = ProgressFeedback(maximum=max(.02, options.exploration_max))
        self.proxy = None
        self.proxy_seconds = 0.0
        self.last_exploration = 0.0
        self.effective_rhos = []

    def pre_round(self, live_sensors, residual_e):
        from time import perf_counter
        state = super().pre_round(live_sensors, residual_e)
        if state is None:
            return None
        self.feedback = ProgressFeedback(maximum=max(.02, self.options.exploration_max))
        self.ant_index = self.attempt_in_ant = 0
        self.starts = (self.rng.sample(list(state.live), len(state.live))
                       if self.options.distinct_starts else [])
        if self.options.heuristic == "marginal":
            started = perf_counter()
            self.proxy = MarginalEnergyProxy(self.network, self.evaluator, state.live)
            self.proxy_seconds = perf_counter() - started
        return state

    def _construct_candidate(self, state, residual_e):
        if self.options.random_sets:
            return tuple(self.rng.sample(list(state.live), state.target))
        available = list(state.live)
        if self.options.distinct_starts:
            if self.attempt_in_ant == self.params.max_clustering_attempts:
                self.ant_index += 1
                self.attempt_in_ant = 0
            first = self.starts[self.ant_index % len(self.starts)]
            self.attempt_in_ant += 1
        else:
            first = self.rng.choice(available)
        selected = [first]
        available.remove(first)
        while available and len(selected) < state.target:
            self.partial = tuple(selected)
            p = self._transition_probabilities(selected[-1], available, residual_e,
                                               state.beta, state.strength)
            chosen = self.rng.choices(available, weights=p, k=1)[0]
            selected.append(chosen)
            available.remove(chosen)
        return tuple(selected)

    def _transition_probabilities(self, source, available, residual_e, beta, strength):
        if not available:
            return []
        o = self.options
        if o.heuristic == "marginal":
            from time import perf_counter
            started = perf_counter()
            deltas = self.proxy.additions(self.partial, available)
            quality = marginal_log_quality(deltas, self.proxy.energy_scale)
            tau = np.asarray(self.pheromone[source])[available]
            logs = self.params.pheromone_exponent * np.log(tau) + beta * quality
            base = normalized_weights(logs)
            self.proxy_seconds += perf_counter() - started
        else:
            base = super()._transition_probabilities(source, available, residual_e, beta, 0.0)
        signal = self.chaos[source]
        if o.chaos_policy in ("baseline", "reduced"):
            c = strength * signal * (o.fixed_scale if o.chaos_policy == "reduced" else 1)
            disturbed = np.asarray(base) + c
            self.last_exploration = len(available) * c / (1 + len(available) * c)
            return (disturbed / disturbed.sum()).tolist()
        coefficient = 0.0
        if o.chaos_policy == "normalized":
            coefficient = min(1.0, strength * signal)
        elif o.chaos_policy == "adaptive":
            coefficient = self.feedback.coefficient() * signal
        self.last_exploration = coefficient
        return uniform_mix(base, coefficient)

    def deposit(self, CH_list, cost, per_ant=True):
        if per_ant:
            self.feedback.observe(cost)
            if self.options.distinct_starts:
                self.ant_index += 1
                self.attempt_in_ant = 0
        if not self.options.random_sets:
            super().deposit(CH_list, cost, per_ant)

    def _update_pheromone(self, state):
        if self.options.chaos_policy != "evaporation":
            return super()._update_pheromone(state)
        p = self.params
        self.effective_rhos = []
        for source in state.live:
            rho = evaporation_only(state.rho, self.chaos[source],
                                   self.options.evaporation_kappa, p.rho_min, p.rho_max)
            self.effective_rhos.append(rho)
            for target in state.live:
                if source != target:
                    self.pheromone[source][target] = min(p.tau_max, max(
                        p.tau_min, (1 - rho) * self.pheromone[source][target]))
            self.chaos[source] = logistic_step(self.chaos[source], p.chaos_r)


class ResearchACACO(ACACO):
    """Default options delegate exactly to current baseline, including its RNG."""
    name = "AC-ACO research"

    def __init__(self, network, hparameters, params=None, seed=None, options=None):
        self.options = options or ResearchOptions()
        super().__init__(network, hparameters, params, seed)

    def init_params(self):
        if self.options == ResearchOptions():
            return super().init_params()
        self.params = self._params or ACACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = ResearchClustering(self.network, self.hparameters,
            self.params, self._seed, self.options)
