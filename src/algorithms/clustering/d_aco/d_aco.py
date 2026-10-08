import random
import math
import numpy

from algorithms.base.base import ClusteringAlgorithm
from algorithms.clustering.d_aco.parameters import DACOParameters
from algorithms.clustering import build_clusters
from network import NetworkInstance


class Grid:
    def __init__(self, network: NetworkInstance, params: DACOParameters = None):

        total_volume = network.width * network.height * network.depth

        self.network = network
        self.params = params or DACOParameters()

        target_cube_volume = total_volume / self.params.CH_proportion / len(network.sensors)
        self.cube_size = target_cube_volume ** (1 / 3)

        self.xs = math.ceil(network.width / self.cube_size)
        self.ys = math.ceil(network.height / self.cube_size)
        self.zs = math.ceil(network.depth / self.cube_size)

        self.cube_vol = self.cube_size ** 3
        self.sphere_vol = (4.0 / 3.0) * math.pi * network.radius ** 3
        self._cube_data = {}

        for ix in range(self.xs):
            x_min = ix * self.cube_size
            x_max = min(x_min + self.cube_size, network.width)
            for iy in range(self.ys):
                y_min = iy * self.cube_size
                y_max = min(y_min + self.cube_size, network.height)
                for iz in range(self.zs):
                    z_min = iz * self.cube_size
                    z_max = min(z_min + self.cube_size, network.depth)
                    cube_index = (ix, iy, iz)
                    cube_min = numpy.array([x_min, y_min, z_min])
                    cube_max = numpy.array([x_max, y_max, z_max])
                    self._cube_data[cube_index] = (cube_min, cube_max)

        cubes = list(self._cube_data.values())
        self._lo = numpy.array([cube[0] for cube in cubes])
        self._hi = numpy.array([cube[1] for cube in cubes])
        self._center = (self._lo + self._hi) / 2
        self._cell_radius = 0.5 * numpy.linalg.norm(
            self._hi - self._lo,
            axis=1,
        )
        self.density = numpy.zeros((self.xs, self.ys, self.zs))
        self.loss = numpy.zeros_like(self.density)
        self.F = None

    def compute_density(self, live_sensors, _residual_e=None):
        points = numpy.array(
            [[sensor.x, sensor.y, sensor.z] for sensor in self.network.sensors],
            dtype=float,
        )
        distance = numpy.linalg.norm(
            points[:, None, :] - self._center[None, :, :],
            axis=2,
        )
        reach = self.network.radius + self._cell_radius
        fraction = (
            min(1.0, self.sphere_vol / self.cube_vol)
            * numpy.maximum(1.0 - distance / reach, 0.0) ** 3
        )
        fraction = numpy.minimum(fraction, 1.0)
        fraction[distance + self._cell_radius <= self.network.radius] = 1.0
        fraction[distance >= reach] = 0.0

        live = numpy.zeros(len(points))
        live[live_sensors] = 1.0
        self.F = fraction
        self.density = (fraction.T @ live).reshape(self.density.shape)
        self.reset_loss()

        return self.density

    def reset_loss(self):
        self.loss.fill(0.0)

    def get_density(self, sensor_ids):
        """Return remaining cube coverage weighted by each sensor's coverage."""
        remaining = numpy.maximum(
            self.density.ravel() - self.loss.ravel(),
            0.0,
        )
        return (self.F @ remaining)[sensor_ids]

    def add_loss(self, sensor_id):
        self.loss += self.F[sensor_id].reshape(self.loss.shape)

class DACOClustering(ClusteringAlgorithm):

    name = "DACOClustering"

    def __init__(self, network: NetworkInstance, hparameters, aco_params: DACOParameters = None):
        super().__init__(network, hparameters)
        self.params = aco_params or DACOParameters()
        self.grid = Grid(network, self.params)

        # Pheromone is associated with candidate CH nodes, not transitions.
        self.pheromone = [self.params.tau0] * network.N
        self.iteration = 0
        self.rho = self.params.rho_max
        self._score_components = {
            "pheromone": [],
            "energy": [],
            "density": [],
        }
        self.last_deposit = 0.0

    

    def pre_round(self, live_sensors, residual_e):
        self.iteration += 1
        progress = min(
            self.iteration / max(getattr(self.hparameters, "T_max", 1), 1),
            1.0,
        )
        self.rho = self.params.rho_max - progress * (
            self.params.rho_max - self.params.rho_min
        )
        for values in self._score_components.values():
            values.clear()
        self.grid.compute_density(live_sensors, residual_e)
        return random.sample(live_sensors, min(self.params.num_ants, len(live_sensors)))

    def create_clusters(self, live_sensors, residual_e, start):
        """
        One clustering attempt for one ant.

        Returns (CH_nodes, nodes, outliers), or None if the ant could not
        build a CH path. The CH path order is the key order of CH_nodes.
        """
        CHs = self._make_path(live_sensors, residual_e, start)
        if CHs is None:
            return None

        return build_clusters(CHs, live_sensors, self.network.dist_matrix, self.network.radius)

    def post_round(self, live_sensors, residual_e, consumption, CH_list,
                   fitness=None, ant_candidates=()):
        self._update_pheromone()
        self.last_deposit = 0.0
        for ant_fitness, (_, ant_chs, _, _, _) in ant_candidates:
            self.deposit(ant_chs, ant_fitness, per_ant=True)
        self.deposit(CH_list, fitness, per_ant=False)
        if self.iteration == 1 or self.iteration % 100 == 0:
            self._log_heuristic_dominance(sum(consumption.values()), fitness)

    def _make_path(self, live_nodes, residual_e, start_node):

        params = self.params
        self.grid.reset_loss()
        max_num_CHs = max(1, round(params.CH_proportion * len(live_nodes)))

        live = numpy.asarray(live_nodes, dtype=numpy.intp)
        pheromone = numpy.asarray(self.pheromone)[live]
        energy = numpy.fromiter(
            (residual_e[node] for node in live_nodes),
            dtype=float,
            count=len(live_nodes),
        )
        chosen = numpy.zeros(len(live), dtype=bool)
        chosen[live == start_node] = True
        CH_list = [start_node]
        self.grid.add_loss(start_node)

        while len(CH_list) < max_num_CHs:
            positions = numpy.flatnonzero(~chosen)
            if positions.size == 0:
                return None

            density = self.grid.get_density(live)[positions]
            pheromone_score = params.alpha * numpy.log(
                numpy.maximum(pheromone[positions], 1e-12)
            )
            energy_score = params.beta * numpy.log(
                numpy.maximum(energy[positions], 1e-12)
            )
            density_score = params.gamma * numpy.log(
                numpy.maximum(density, 1e-12)
            )
            self._score_components["pheromone"].extend(pheromone_score.tolist())
            self._score_components["energy"].extend(energy_score.tolist())
            self._score_components["density"].extend(density_score.tolist())
            score = pheromone_score + energy_score + density_score
            weights = numpy.exp(score - score.max())
            if weights.sum() <= 0:
                return None

            selected = random.choices(
                positions.tolist(),
                weights=weights.tolist(),
                k=1,
            )[0]
            chosen[selected] = True
            node = int(live[selected])
            CH_list.append(node)
            self.grid.add_loss(node)

        return CH_list

    def deposit(self, CH_list, cost, per_ant=True):
        """Deposit pheromone on the nodes in a successful CH path."""
        if not CH_list or cost is None or cost <= 0:
            return

        amount = self.params.Q / cost
        if per_ant:
            amount /= self.params.num_ants
        else:
            amount *= self.params.theta
        self.last_deposit = amount

        for node in CH_list:
            self.pheromone[node] = min(
                self.pheromone[node] + amount,
                self.params.tau_max,
            )

    def _update_pheromone(self):
        """Evaporate pheromone without adding any new deposit."""
        self.pheromone = [
            pheromone * (1 - self.rho)
            for pheromone in self.pheromone
        ]

        lo, hi = self.params.tau_min, self.params.tau_max
        self.pheromone = [
            min(max(pheromone, lo), hi)
            for pheromone in self.pheromone
        ]

    def _log_heuristic_dominance(self, cost, fitness):
        spreads = {
            name: (
                max(values) - min(values)
                if values
                else 0.0
            )
            for name, values in self._score_components.items()
        }
        dominant = max(spreads, key=spreads.get)
        print(
            f"[D-ACO DEBUG] iter={self.iteration} "
            f"alpha={self.params.alpha:.6g} beta={self.params.beta:.6g} "
            f"gamma={self.params.gamma:.6g} rho={self.rho:.6g} "
            f"dominant={dominant} "
            f"spread_tau={spreads['pheromone']:.6g} "
            f"spread_energy={spreads['energy']:.6g} "
            f"spread_density={spreads['density']:.6g} "
            f"deposit={self.last_deposit:.6g} "
            f"cost={cost:.6g} "
            f"fitness={fitness:.6g} "
            f"tau_min={min(self.pheromone):.6g} "
            f"tau_max={max(self.pheromone):.6g} "
            f"tau_mean={sum(self.pheromone) / len(self.pheromone):.6g}"
        )
