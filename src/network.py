"""
NetworkInstance: the static description of the deployed sensor field
(the "map"). It's shared read-only by every clustering/routing
algorithm, so several algorithms can be run and compared on the exact
same physical layout.

Mutable, per-run state (which nodes are still alive, residual energy,
etc.) does NOT live here -- Simulator.run gives each algorithm a fresh
copy of it, so running algorithm B never affects algorithm A's results.
"""
import pickle


class NetworkInstance:
    def __init__(self, sensors, base_pos, init_energy, width, height, depth, radius):
        self.sensors = sensors
        self.base_pos = base_pos
        self.init_energy = init_energy
        self.width = width
        self.height = height
        self.depth = depth
        self.radius = radius
        self.N = len(sensors)

        self.dist_matrix = self._build_dist_matrix()
        self.base_dists = [abs(base_pos - s) for s in sensors]

    def _build_dist_matrix(self):
        N = self.N
        m = [[0.0] * N for _ in range(N)]
        for i in range(N):
            for j in range(i):
                d = abs(self.sensors[i] - self.sensors[j])
                m[i][j] = m[j][i] = d
        return m

    @classmethod
    def from_pickle(cls, path="map.pkl"):
        with open(path, "rb") as f:
            raw = pickle.load(f)
        return cls(
            sensors=raw["sensors"],
            base_pos=raw["base_pos"],
            init_energy=raw["init_energy"],
            width=raw["width"],
            height=raw["height"],
            depth=raw["depth"],
            radius=raw["radius"],
        )
