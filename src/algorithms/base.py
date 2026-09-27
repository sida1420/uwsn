from abc import ABC, abstractmethod


class ClusteringAlgorithm(ABC):
    """
    Common interface every clustering/routing algorithm must implement,
    so Simulator (and run.py) can run and compare any of them the same
    way. To add a new algorithm to the project: subclass this, implement
    plan_round, and add the class to ALGORITHMS in run.py.
    """

    name = "base"

    def __init__(self, network, hparameters):
        self.network = network
        self.hparameters = hparameters

        self.failed_clustering_attempts=0
        self.failed_routing_attempts=0
        self.total_clustering_attempts=0
        self.total_routing_attempts=0

    @abstractmethod
    def plan_round(self, live_sensors, residual_e):
        """
        Decide this round's routing tree.

        Args:
            live_sensors: list of ids of sensors still alive
            residual_e: list (indexed by sensor id) of remaining energy

        Returns:
            the base-station root Node for this round's routing tree,
            or None if no feasible routing could be found.
        """
        raise NotImplementedError
