class NodeACOParameters:
    """
    Hyperparameters specific to node-based ACO.

    NodeACO keeps pheromone on candidate cluster-head nodes, so these
    parameters are intentionally independent from edge-based ACO settings.
    """

    def __init__(self):
        self.num_ants = 160 # ants per round
        self.CH_proportion = 0.2  # target fraction of live nodes made CH
        self.alpha = 1  # node-pheromone importance
        self.beta = 0.6  # residual-energy importance
        self.gamma = 0.05  # transmission-energy heuristic importance
        self.rho = 0.1  # node-pheromone evaporation rate
        self.Q = 0.03  # pheromone deposit strength
        
        self.theta = 0.1 # additional contribution of best configuration

        self.tau0 = 1.0  # initial node-pheromone level
        self.tau_min = 1
        self.tau_max = 8.0
        self.hopping_factor = 0.4  # energy-versus-distance relay preference

        self.max_clustering_attempts = 5

        self.assignment_distance_weight=0.6
        self.assignment_load_weight=0.25
        self.assignment_energy_weight=0.15
