"""Energy-only AC-ACO V2+V6 preset, independent of research and optimizer tools."""
from dataclasses import replace

from algorithms.ac_aco import ACACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering.ac_aco.me_aco import MEACOClustering
from evaluate import Evaluator


class MEACO(ACACO):
    """Marginal construction and evaporation-only chaos, with audited bounds."""

    name = "ME-ACO"

    def __init__(self, network, hparameters, seed=None):
        params = replace(ACACOParameters(), num_ants=40, load_weight=0.0,
                         tau0=1.0, tau_min=0.01, tau_max=20.0)
        super().__init__(network, hparameters, params=params, seed=seed)

    def init_params(self):
        self.params = self._params
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = MEACOClustering(
            self.network, self.hparameters, self.params, seed=self._seed
        )
