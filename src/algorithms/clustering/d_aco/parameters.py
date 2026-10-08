class DACOParameters:
    """Hyperparameters for density-aware node-based ACO."""

    def __init__(self):
        self.num_ants = 40  # ants per round
        self.CH_proportion = 0.2  # target fraction of live nodes made CH
        self.alpha = 1.0  # node-pheromone importance
        self.beta = 0.9  # residual-energy importance
        self.gamma = 0.4  # density importance
        self.energy_weight = 0.9  # total-energy weight in deposit fitness
        self.load_weight = 0.1  # load-imbalance weight in deposit fitness
        self.hopping_factor = 0.4  # energy-versus-distance relay preference
        self.rho_min = 0.1  # final node-pheromone evaporation rate
        self.rho_max = 0.6  # initial node-pheromone evaporation rate
        self.Q = 5  # pheromone deposit strength
        self.theta = 0.1  # additional best-configuration contribution
        self.tau0 = 1.0  # initial node-pheromone level
        self.tau_min = 1.0
        self.tau_max = 8.0
        self.max_clustering_attempts = 10
