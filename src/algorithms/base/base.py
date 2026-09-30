from abc import ABC, abstractmethod


class ClusteringAlgorithm(ABC):
    """
    Base class for algorithms that choose cluster heads (CH) and assign
    member sensors to them (e.g. ACOClustering, PSOClustering).

    Stateful algorithms (pheromone, particle swarm, ...) keep their memory
    on the instance and update it in pre_round / post_round. Stateless
    ones can simply be plain functions in algorithms/clustering.py.

    Round lifecycle (driven by the owning Algorithm's plan_round):
      pre_round        -> prepare per-round state, return it (e.g. ant
                          start nodes, particles)
      create_clusters  -> one clustering attempt (may be called many times
                          per round, once per ant / particle)
      post_round       -> update memory once the round is decided
    """

    name = "base_clustering"

    def __init__(self, network, hparameters):
        self.network = network
        self.hparameters = hparameters

    def pre_round(self, live_sensors, residual_e):
        """
        Hook called once before the round's create_clusters calls.
        Returns whatever per-round state the algorithm wants plan_round to
        iterate over (None by default). Optional.
        """
        return None

    @abstractmethod
    def create_clusters(self, live_sensors, residual_e, *args, **kwargs):
        """
        One clustering attempt. Extra algorithm-specific inputs (an ant's
        start node, a decoded CH list, ...) are passed through *args/**kwargs.

        Returns:
            (CH_nodes, nodes, outliers) as produced by build_clusters:
              CH_nodes: {ch_id: Node} with members attached as children
              nodes:    {sensor_id: Node} for every CH and assigned member
              outliers: ids of sensors that could not reach any CH
            or None if no clustering could be produced.
        """
        raise NotImplementedError

    def post_round(self, live_sensors, residual_e, consumption, **context):
        """
        Hook called once after the round is decided. `consumption` is the
        chosen tree's {sensor_id: energy} ({} if the round failed);
        `context` carries algorithm-specific extras (e.g. CH_list for ACO,
        particles for PSO). Optional.
        """


class RoutingAlgorithm(ABC):
    """
    Base class for algorithms that connect the CHs (and outliers) to the
    base station (e.g. ACORouting). Stateless routing (e.g. multi_hop_routing)
    stays a plain function in algorithms/routing.py.
    """

    name = "base_routing"

    def __init__(self, network, hparameters):
        self.network = network
        self.hparameters = hparameters

    def pre_round(self, live_sensors, residual_e):
        """Hook called once before create_routes. May return per-round state. Optional."""
        return None

    @abstractmethod
    def create_routes(self, live_sensors, residual_e, CH_nodes, nodes, outliers, *args, **kwargs):
        """
        Build the routing tree from the clusters.

        Returns:
            the base-station root Node (id=-1), or None if no feasible
            route exists.
        """
        raise NotImplementedError

    def post_round(self, live_sensors, residual_e, consumption, **context):
        """Hook called once after the round is decided. Optional."""


class Algorithm(ABC):
    """
    Common interface every general algorithm must implement, so Simulator
    (and run.py) can run and compare any of them the same way. An Algorithm
    composes a ClusteringAlgorithm and a RoutingAlgorithm (or is a joint
    method such as AC-ACO). To add a new algorithm: subclass this,
    implement init_params and plan_round, and add the class to ALGORITHMS
    in run.py.
    """

    name = "base"

    def __init__(self, network, hparameters):
        self.network = network
        self.hparameters = hparameters

        self.failed_clustering_attempts = 0
        self.failed_routing_attempts = 0
        self.total_clustering_attempts = 0
        self.total_routing_attempts = 0

        self.init_params()

    @abstractmethod
    def init_params(self):
        """Create algorithm-specific parameters and sub-algorithms."""
        raise NotImplementedError

    @abstractmethod
    def plan_round(self, live_sensors, residual_e):
        """
        Decide this round's routing tree.

        Args:
            live_sensors: list of ids of sensors still alive
            residual_e: list (indexed by sensor id) of remaining energy

        Returns:
            (root_node, energy_consumption):
              root_node: base-station root Node (id=-1) of this round's tree
              energy_consumption: {sensor_id: energy} for this round
            or (None, {}) if no feasible routing could be found.
        """
        raise NotImplementedError