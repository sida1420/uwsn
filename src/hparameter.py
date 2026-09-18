
class HyperParameters:
    def __init__(self):
        self.T_max=3500 # The maximum number of iterations used in simulation
        self.P_0=0.1 # control bit send to check communication first
        self.E_elec=5*1e-8
        self.E_integrate=5*1e-9
        self.freq= 30000
        self.spreadking_factor=1.5
        self.packet_size=200
        self.trasmission_rate=10000 #bps

        self.absorption_factor=(0.11*self.freq**2)/(1+self.freq**2)+44*self.freq**2/(4100+self.freq**2)+2.75*self.freq**2/10000+0.003
        self.attenuation_coeff=10**(self.absorption_factor/10)