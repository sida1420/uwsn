from hparameter import HyperParameters


class Evaluator:
    """
    Energy-cost model for a single round of communication, given the
    routing tree built for that round (see clustering.direct_routing):
    base station (root) -> cluster heads -> member sensors.

    Cost model per node:
      - an ordinary member only transmits its own reading to its CH
      - a cluster head additionally receives + aggregates every
        member's data before forwarding the combined packet onward
    """

    def __init__(self, hparameter: HyperParameters):
        self.hparameter = hparameter

    def E_tx(self, dist):
        # `attenuation_coeff` is a per-kilometer absorption factor (Thorp's
        # formula), and the whole acoustic path-loss term A_d is defined in
        # km (typical for underwater ranges), while dist_matrix/base_dists
        # are in meters -- so dist must be converted to km here, or A_d
        # (and the exponent especially) blows up for any realistic
        # sensor-field distance.
        dist_km = dist / 1000
        A_d = dist_km**self.hparameter.spreadking_factor * self.hparameter.attenuation_coeff**dist_km
        return self.hparameter.P_0 * A_d * self.hparameter.packet_size / self.hparameter.trasmission_rate

    def E_rx(self):
        return self.hparameter.packet_size * self.hparameter.E_elec

    def E_da(self):
        return self.hparameter.packet_size * self.hparameter.E_integrate

    def E_m(self, dist):
        return self.E_tx(dist) + self.E_rx() + self.E_da()

    def energy_consumption(self, root, dist_matrix, base_dists):
        """
        Walk the routing tree and compute each node's energy cost for
        this round.

        Args:
            root: base-station Node (id == -1) returned by a
                clustering algorithm for this round
            dist_matrix: NxN sensor-to-sensor distances
            base_dists: sensor-to-base-station distances, indexed by id

        Returns:
            (consumption, total) where consumption is {node_id: energy}
            for every non-root node, and total is the sum of all of it.
        """
        consumption = {}

        def dist_to_parent(node):
            parent = node.prev
            if parent is None or parent.id == -1:
                return base_dists[node.id]
            return dist_matrix[node.id][parent.id]

        def visit(node):
            if node.id != -1:  # the base station itself doesn't "spend" energy
                dist = dist_to_parent(node)
                if node.isCH:
                    # cluster head: receive from + aggregate each member,
                    # then transmit the aggregated packet onward
                    energy = self.E_rx() * len(node.nxts) + self.E_da() + self.E_tx(dist)
                else:
                    # ordinary member: just send its own reading to its CH
                    energy = self.E_tx(dist)
                consumption[node.id] = energy

            for nxt in node.nxts:
                visit(nxt)

        visit(root)
        return consumption, sum(consumption.values())
