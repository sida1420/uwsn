
import pickle

class Module:
    def __init__(self, name, dist_matrix, base_dists, residual_e, N, sensors, base_pos, init_energy, width, height, depth, radius):
        self.name = name
        self.dist_matrix = dist_matrix
        self.base_dists = base_dists
        self.residual_e = residual_e
        self.N = N
        self.sensors = sensors
        self.base_pos = base_pos
        self.init_energy = init_energy
        self.width = width
        self.height = height
        self.depth = depth
        self.radius = radius
        