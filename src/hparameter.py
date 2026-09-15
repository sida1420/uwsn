
class HyperParameters:
    def __init__(self):
        self.T_max=3500 # The maximum number of iterations used in simulation
        self.ctrl_bit=100 # control bit send to check communication first
        self.CHs_proportion=0.1
        self.bit_count=2000
        self.E_elec=50 * 1e-9            # 50 nJ/bit
        self.E_agg=5 * 1e-9              # 5 nJ/bit/signal
        self.free_space_coeff= 10 * 1e-12 # 10 pJ/bit/m^2
        self.multipath_coeff=0.0013 * 1e-12 # 0.0013 pJ/bit/m^4
        self.distance_threshold=(self.free_space_coeff/self.multipath_coeff)**0.5 