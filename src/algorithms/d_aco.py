"""D-ACO with live deposits and one energy + load^p/density fitness."""
from dataclasses import dataclass
from math import isfinite
import random
import numpy as np
from algorithms.base.base import Algorithm
from algorithms.clustering.d_aco.d_aco import DACOClustering
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering.d_aco.fitness import FitnessReferences, fitness, power_density_penalty
from algorithms.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator


@dataclass
class Candidate:
    root: object
    chs: tuple
    consumption: dict
    energy: float
    penalty: float
    fitness: float = 0.0


class DACO(Algorithm):
    name = 'D-ACO'

    def __init__(self, network, hparameters, aco_params=None):
        self._aco_params = aco_params
        super().__init__(network,hparameters)

    def init_params(self):
        self.params = self._aco_params or DACOParameters()
        self.params.validate()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = DACOClustering(self.network,self.hparameters,self.params)
        self.references = None
        self.calibration_attempts = 0
        self.calibration_routing_attempts = 0
        self.calibration_feasible = 0

    def _load_context(self, live_sensors, residual_e):
        return (list(live_sensors),np.asarray([residual_e[i] for i in live_sensors]),
                self.clustering.grid.get_base_density(live_sensors))

    def _run_ant(self, start, live_sensors, residual_e, context, calibration=False):
        for _ in range(self.params.max_clustering_attempts):
            clusters = self.clustering.create_clusters(live_sensors,residual_e,start)
            if calibration:
                self.calibration_attempts += 1
            else:
                self.total_clustering_attempts += 1
            if clusters is None:
                if not calibration:
                    self.failed_clustering_attempts += 1
                return None
            ch_nodes,nodes,outliers = clusters
            if ch_nodes is None:
                if not calibration:
                    self.failed_clustering_attempts += 1
                continue
            if calibration:
                self.calibration_routing_attempts += 1
            else:
                self.total_routing_attempts += 1
            root = dropping_member_multi_hop_routing(ch_nodes,nodes,live_sensors,outliers,
                self.network.dist_matrix,self.network.base_dists,residual_e,
                self.network.radius,self.params.hopping_factor)
            if root is None:
                continue
            consumption,cost = self.evaluator.energy_consumption(root,self.network.dist_matrix,self.network.base_dists)
            if not isfinite(cost) or cost<=0 or set(consumption)!=set(live_sensors):
                continue
            nodes,residual,density = context
            penalty = power_density_penalty(consumption,nodes,residual,density,self.params.load_power,self.params.density_epsilon)
            if not isfinite(penalty):
                continue
            return Candidate(root,tuple(ch_nodes),consumption,cost,penalty)
        if not calibration:
            self.failed_routing_attempts += 1
        return None

    def calibrate(self, live_sensors, residual_e):
        """Throwaway batch: no physical energy, deposits, or schedule advancement."""
        if self.references is not None:
            return True
        if not live_sensors:
            return False
        self.clustering.grid.compute_density(live_sensors,residual_e)
        context = self._load_context(live_sensors,residual_e)
        starts = random.sample(live_sensors,min(self.params.calibration_ants,len(live_sensors)))
        candidates = [self._run_ant(start,live_sensors,residual_e,context,True) for start in starts]
        candidates = [c for c in candidates if c is not None]
        self.calibration_feasible = len(candidates)
        if not candidates:
            return False
        self.references = FitnessReferences.from_observations([c.energy for c in candidates],[c.penalty for c in candidates])
        return True

    def plan_round(self, live_sensors, residual_e):
        if not live_sensors or not self.calibrate(live_sensors,residual_e):
            return None,{}
        starts = self.clustering.pre_round(live_sensors,residual_e)
        context = self._load_context(live_sensors,residual_e)
        references = self.references  # scales fixed for the round; pheromone remains live
        candidates = []
        for start in starts:
            candidate = self._run_ant(start,live_sensors,residual_e,context)
            if candidate is None:
                continue
            candidate.fitness = fitness(candidate.energy,candidate.penalty,references,self.params.load_density_weight)
            self.clustering.deposit(candidate.chs,candidate.fitness,references.energy)
            candidates.append(candidate)
        if not candidates:
            self.clustering.post_round(live_sensors,residual_e,{},None,None,references.energy)
            return None,{}
        best = min(candidates,key=lambda c:(c.fitness,c.energy,c.chs))
        self.clustering.post_round(live_sensors,residual_e,best.consumption,best.chs,best.fitness,references.energy)
        self.references = references.updated([c.energy for c in candidates],[c.penalty for c in candidates],self.params.reference_memory)
        return best.root,best.consumption
