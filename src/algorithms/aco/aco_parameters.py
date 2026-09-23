class ACOParameters:
    """
    Hyperparameters specific to the simple ACO clustering algorithm.
    Kept separate from HyperParameters so each algorithm can own its own
    parameter set without polluting the shared network/energy model.
    """

    def __init__(self):
        self.num_ants = 20  # ants per round
        self.CH_proportion = 0.05  # target fraction of live nodes made CH
        self.alpha = 1.0  # pheromone importance
        self.beta = 3.0  # heuristic (energy/distance) importance
        self.rho = 0.1  # pheromone evaporation rate
        self.Q = 100.0  # pheromone deposit strength
        self.tau0 = 1.0  # initial pheromone level
        self.tau_min = 0.1
        self.tau_max = 10.0
