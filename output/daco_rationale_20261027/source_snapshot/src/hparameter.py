class HyperParameters:
    """
    Network / energy-model constants shared by every algorithm. This is
    deliberately algorithm-agnostic -- algorithm-specific knobs (e.g. the
    ACO pheromone parameters) live in their own hyperparameter classes
    instead, see aco_parameters.py.
    """

    def __init__(self):
        self.T_max = 3500  # max number of simulation rounds (network lifetime)
        self.P_0 = 0.1  # control bit sent to check communication first
        self.E_elec = 5 * 1e-8
        self.E_integrate = 5 * 1e-9
        self.freq = 30000  # Hz
        self.spreadking_factor = 1.5
        self.packet_size = 200
        self.trasmission_rate = 10000  # bps

        # Thorp's absorption formula expects frequency in kHz, hence /1000 here.
        # (Feeding it 30000 directly, as Hz, previously made attenuation_coeff
        # overflow to inf -- every E_tx() call would have raised or returned inf.)
        freq_khz = self.freq / 1000
        self.absorption_factor = (
            (0.11 * freq_khz**2) / (1 + freq_khz**2)
            + 44 * freq_khz**2 / (4100 + freq_khz**2)
            + 2.75 * freq_khz**2 / 10000
            + 0.003
        )
        self.attenuation_coeff = 10 ** (self.absorption_factor / 10)
