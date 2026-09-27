class PSOParameters:
    """Hyperparameters for particle-swarm cluster-head selection."""

    def __init__(self):
        self.swarm_size = 15
        self.iterations = 10
        self.early_stopping_patience = 3
        # Fraction of the worst particles discarded after each simulation
        # round. Their slots are filled by random particles next round.
        self.particle_delete_percentage = 0.2
        self.CH_proportion = 0.05
        self.inertia = 0.7
        self.cognitive = 1.5
        self.social = 1.5
        self.velocity_max = 4.0
        self.infeasible_penalty = 1_000_000.0
        self.hopping_factor = 0.4  # energy-versus-distance relay preference

