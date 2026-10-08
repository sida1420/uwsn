"""NodeACACO reuses ACACO's ant loop, tree scoring and multi-hop routing."""

from algorithms.ac_aco import ACACO
from algorithms.clustering.node_ac_aco.node_ac_aco import NodeACACOClustering
from algorithms.clustering.node_ac_aco.parameters import NodeACACOParameters
from evaluate import Evaluator


class NodeACACO(ACACO):
    name = "NodeACACO"

    def __init__(self, network, hparameters, params: NodeACACOParameters = None, seed=None):
        super().__init__(network, hparameters, params, seed)

    def init_params(self):
        self.params = self._params if self._params is not None else NodeACACOParameters()
        self.evaluator = Evaluator(self.hparameters)
        self.clustering = NodeACACOClustering(
            self.network, self.hparameters, self.params, seed=self._seed
        )
