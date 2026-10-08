class PSOParameters:
    """Hyperparameters for particle-swarm cluster-head selection."""

    def __init__(self):
        self.swarm_size = 200
        self.iterations = 1
        self.early_stopping_patience = 5
        # Fraction of the worst particles discarded after each simulation
        # round. Their slots are filled by random particles next round.
        self.particle_delete_percentage = 1
        self.CH_proportion = 0.20
        self.max_CH_proportion = 0.30
        self.inertia_start = 0.9
        self.inertia_end = 0.4
        self.cognitive = 1.5
        self.social = 1.5
        self.velocity_max = 4.0
        self.mutation_probability = 0.10
        self.heuristic_seed_percentage = 0
        self.depletion_weight = 5.0
        self.assignment_distance_weight = 0.60
        self.assignment_load_weight = 0.25
        self.assignment_energy_weight = 0.15
        self.infeasible_penalty = 1_000_000.0
        self.hopping_factor = 0.4  # energy-versus-distance relay preference
