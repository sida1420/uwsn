
from hparameter import HyperParameters
import pickle
class Run:
    def __init__(self):
        self.hparameters = HyperParameters()
        self.load_map()

        self.dist_matrix = [[0.0 for _ in range(self.N)] for _ in range(self.N)]

        for i in range(self.N):
            for j in range(i):
                self.dist_matrix[i][j]=self.dist_matrix[j][i]=abs(self.sensors[i]-self.sensors[j])

        self.base_dists=[abs(self.base_pos-node) for node in self.sensors]
        self.residual_e=[self.init_energy]*self.N
        
    def load_map(self):
        with open("map.pkl",'rb') as file:
            _map=pickle.load(file)
        self.width, self.height, self.base_pos, self.sensors, self.init_energy, self.radius=_map.values()
        self.N=len(self.sensors)