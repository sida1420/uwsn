"""Partial clustering proxy: no router calls, no final tree evaluations."""
import numpy as np


class MarginalEnergyProxy:
    def __init__(self, network, evaluator, live):
        self.live = np.asarray(live, dtype=int)
        self.positions = {int(node): i for i, node in enumerate(self.live)}
        self.radius = network.radius
        full_distances = np.asarray(network.dist_matrix).reshape(network.N, network.N)
        self.distances = full_distances[np.ix_(self.live, self.live)]
        self.tx = np.asarray([[evaluator.E_tx(float(d)) for d in row]
                              for row in self.distances])
        self.rx_da = evaluator.E_rx() + evaluator.E_da()
        bases = np.asarray(network.base_dists)[self.live]
        self.energy_scale = max(evaluator.E_tx(network.radius) + self.rx_da, 1e-30)
        # Finite disconnected penalty permits partial solutions; not a feasibility certificate.
        fallback = (len(live) + 1) * self.energy_scale
        paths = np.full(len(live), np.inf)
        for i in np.argsort(bases, kind="stable"):
            if bases[i] <= self.radius:
                paths[i] = evaluator.E_tx(float(bases[i]))
            closer = (bases < bases[i]) & (self.distances[i] <= self.radius)
            if closer.any():
                paths[i] = min(paths[i], float(np.min(
                    self.tx[i, closer] + evaluator.E_rx() + paths[closer])))
        self.unreachable = ~np.isfinite(paths)
        self.paths = np.where(self.unreachable, fallback, paths)
        self.operations = 0  # estimated N*K proxy cell comparisons, not tree evaluations

    def components(self, selected):
        positions = [self.positions[i] for i in selected]
        n = len(self.live)
        if not positions:
            return self.paths.copy(), 0.0
        distances = self.distances[:, positions]
        nearest = np.argmin(distances, axis=1)
        ch = np.asarray(positions)[nearest]
        covered = distances[np.arange(n), nearest] <= self.radius
        members = np.where(covered, self.tx[np.arange(n), ch] + self.rx_da, self.paths)
        members[positions] = 0.0
        return members, float(2 * self.paths[positions].sum())

    def energy(self, selected):
        members, backbone = self.components(selected)
        return float(members.sum() + backbone)

    def additions(self, selected, available):
        """Vectorized nearest-CH updates; O(N*|A|), no full route/evaluator calls."""
        members, _ = self.components(selected)
        indices = np.asarray([self.positions[j] for j in available], dtype=int)
        if not indices.size:
            return np.empty(0)
        # Nearest distance assignment must match builder, not cheapest total surrogate.
        positions = [self.positions[j] for j in selected]
        current_nearest = (self.distances[:, positions].min(axis=1)
                           if positions else np.full(len(self.live), np.inf))
        added_dist = self.distances[:, indices]
        replace = (added_dist < current_nearest[:, None]) & (added_dist <= self.radius)
        new_members = np.where(replace, self.tx[:, indices] + self.rx_da, members[:, None])
        if positions:
            new_members[positions, :] = 0.0
        new_members[indices, np.arange(len(indices))] = 0.0
        deltas = new_members.sum(axis=0) - members.sum() + 2 * self.paths[indices]
        self.operations += int(new_members.size)
        return deltas
