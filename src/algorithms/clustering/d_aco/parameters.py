class DACOParameters:
    """Hyperparameters for density-aware node-based ACO."""

    def __init__(self):
        self.num_ants = 20  # ants per iteration
        self.iterations_per_round = 4  # iterations per round (40 x 10 = 400 ants per round)
        self.CH_proportion = 0.2  # target fraction of live nodes made CH
        self.alpha = 1.0  # node-pheromone importance
        self.beta = 1  # residual-energy importance
        self.gamma = 0.05  # density importance
        self.energy_weight = 120.0  # total-energy weight in deposit fitness
        self.load_weight = 1.0  # load-imbalance weight in deposit fitness
        self.hopping_factor = 0.4  # energy-versus-distance relay preference
        self.rho_min = 0.1  # final node-pheromone evaporation rate (applied every iteration)
        self.rho_max = 0.2  # initial node-pheromone evaporation rate (applied every iteration)
        self.Q = 60  # pheromone deposit strength
        self.theta = 3  # additional best-configuration contribution
        self.tau0 = 0.5  # initial node-pheromone level
        self.tau_min = 0.5
        self.tau_max = 20
        self.max_clustering_attempts = 5

        self.coverage_strength = 0.3
        self.debug_every = 100  # print the D-ACO debug line on round 0 and every N rounds