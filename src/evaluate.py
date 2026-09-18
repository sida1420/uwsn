
from hparameter import HyperParameters
class Evaluator:
    def __init__(self, hparameter: HyperParameters):
        self.hparameter=hparameter


    def E_tx(self, dist):


        
        A_d=dist**self.hparameter.spreadking_factor*self.hparameter.attenuation_coeff**dist
        return self.hparameter.P_0*A_d*self.hparameter.packet_size/self.hparameter.trasmission_rate
    

    def E_rx(self):
        

        return self.hparameter.packet_size*self.hparameter.E_elec

    def E_da(self):
        return self.hparameter.packet_size*self.hparameter.E_integrate

    def E_m(self, dist):
        return self.E_tx(dist)+self.E_rx() +self.E_da()

    def energy_consumption(self, root):

        


    