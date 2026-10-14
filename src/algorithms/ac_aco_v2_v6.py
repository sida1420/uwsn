"""Energy-only AC-ACO V2+V6 preset, independent of research and optimizer tools."""
from dataclasses import replace

from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering.ac_aco.v2_v6 import ACACOV2V6Clustering
from evaluate import Evaluator


class ACACO_V2_V6(ACACO):
    """Marginal construction and evaporation-only chaos, with audited bounds."""

    name = "AC-ACO-V2-V6"

    def __init__(self, network, hparameters, seed=None):
        params = replace(ACACOParameters(), num_ants=40, load_weight=0.0,
                         tau0=1.0, tau_min=0.01, tau_max=20.0)
        super().__init__(network, hparameters, params=params, seed=seed)

    def init_params(self):
        self.params = self._params
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = ACACOV2V6Clustering(
            self.network, self.hparameters, self.params, seed=self._seed
        )
