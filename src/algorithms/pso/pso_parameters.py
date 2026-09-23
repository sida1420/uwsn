class PSOParameters:
    """Hyperparameters for particle-swarm cluster-head selection."""

    def __init__(self):
        self.swarm_size = 30
        self.iterations = 50
        self.CH_proportion = 0.05
        self.inertia = 0.7
        self.cognitive = 1.5
        self.social = 1.5
        self.velocity_max = 4.0
        self.infeasible_penalty = 1_000_000.0

