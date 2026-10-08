class ACOParameters:
    """
    Hyperparameters specific to the simple ACO clustering algorithm.
    Kept separate from HyperParameters so each algorithm can own its own
    parameter set without polluting the shared network/energy model.
    """

    def __init__(self):
        self.num_ants = 40  # ants per round
        self.CH_proportion = 0.2  # target fraction of live nodes made CH
        self.alpha = 1.0  # pheromone importance
        self.beta = 0.5  # residual energy / distance importance
        self.gamma = 1.0  # transmission-energy heuristic importance
        self.rho = 0.1  # pheromone evaporation rate
        self.Q = 0.07  # pheromone deposit strength
        self.tau0 = 1.0  # initial pheromone level
        self.tau_min = 0.1
        self.tau_max = 10.0
        self.hopping_factor = 0.4  # energy-versus-distance relay preference

        self.max_clustering_attempts = 10  # max attempts to build a feasible clustering tree
