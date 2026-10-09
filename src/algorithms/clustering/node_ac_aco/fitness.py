"""Read-only, complete-service fitness using the unchanged shared energy model."""

from dataclasses import dataclass
from math import isfinite
from numbers import Integral

import numpy as np

from node import Node


@dataclass(frozen=True)
class Candidate:
    fitness: float
    total_energy: float
    energy_load: float
    consumption: dict
    heads: tuple
    root: Node


def valid_live_sensors(live_sensors, residual_e, size):
    """Do not silently omit invalid or depleted IDs from the service cohort."""
    try:
        return (
            len(residual_e) == size and len(live_sensors) > 0
            and len(set(live_sensors)) == len(live_sensors)
            and all(isinstance(i, Integral) and not isinstance(i, bool)
                    and 0 <= i < size and isfinite(residual_e[i])
                    and residual_e[i] > 0 for i in live_sensors)
        )
    except (TypeError, ValueError, IndexError):
        return False


def energy_load(consumption, residual_e, live_sensors):
    """Normalized concentration of relative depletion for ALL live sensors.

    Everyone generates a reading, including members, CHs, outliers and relays.
    Missing sensors must not appear to save energy; require complete coverage.
    Zero total depletion and N=1 have zero imbalance. Log scaling avoids
    overflow/underflow in the squared ratios, including tiny valid energies.
    Invalid or unaffordable per-node costs raise ValueError.
    """
    live = tuple(live_sensors)
    if not valid_live_sensors(live, residual_e, len(residual_e)):
        raise ValueError("live sensors must have unique valid IDs and positive finite energy")
    if set(consumption) != set(live):
        raise ValueError("consumption must include every live sensor exactly once")
    delta = np.asarray([consumption[i] for i in live], dtype=float)
    residual = np.asarray([residual_e[i] for i in live], dtype=float)
    if not np.all(np.isfinite(delta) & (delta >= 0) & (delta <= residual)):
        raise ValueError("consumption must be finite, nonnegative and affordable")
    positive = delta > 0
    n = len(live)
    if n == 1 or not positive.any():
        return 0.0
    log_ratios = np.log(delta[positive]) - np.log(residual[positive])
    scaled = np.exp(log_ratios - log_ratios.max())
    penalty = (n * float(scaled @ scaled) / float(scaled.sum()) ** 2 - 1) / (n - 1)
    return min(1.0, max(0.0, penalty))


def _valid_tree(root, live, network, heads):
    """Validate before recursive evaluation, preventing cycles/duplicate packets."""
    if not isfinite(network.radius) or network.radius < 0:
        return False
    if not isinstance(root, Node) or root.id != -1 or root.prev is not None:
        return False
    if root.isCH or root.isRelay:
        return False
    seen, actual_heads, pending = set(), set(), [root]
    while pending:
        parent = pending.pop()
        if not isinstance(parent.nxts, list):
            return False
        # A non-CH relay must forward every incoming packet. Ordinary leaves
        # send their own only; an ordinary interior node would lose data.
        if parent.id != -1 and parent.nxts and not (parent.isCH or parent.isRelay):
            return False
        for child in parent.nxts:
            if not isinstance(child, Node):
                return False
            i = child.id
            if (not isinstance(i, Integral) or isinstance(i, bool)
                    or i not in live or i in seen or child.prev is not parent):
                return False
            seen.add(i)
            if child.isCH:
                actual_heads.add(i)
            distance = (network.base_dists[i] if parent.id == -1
                        else network.dist_matrix[parent.id][i])
            if not isfinite(distance) or distance < 0 or distance > network.radius:
                return False
            pending.append(child)
    return seen == live and len(heads) == len(set(heads)) and set(heads) == actual_heads


def score_candidate(root, live_sensors, residual_e, network, evaluator, params, heads=()):
    """Return a Candidate or None; never debit residual/network energy.

    energy_reference is a fixed, configured positive value in joules, not a
    candidate minimum/maximum. Chaos still uses physical joules separately.
    CHs can also be relays: the shared model's CH aggregation takes precedence.
    """
    if not valid_live_sensors(live_sensors, residual_e, network.N):
        return None
    try:
        heads = tuple(heads)
        if not heads or any(not isinstance(i, Integral) or isinstance(i, bool)
                            or i not in live_sensors for i in heads):
            return None
        if not _valid_tree(root, set(live_sensors), network, heads):
            return None
        consumption, _ = evaluator.energy_consumption(
            root, network.dist_matrix, network.base_dists
        )
        load = energy_load(consumption, residual_e, live_sensors)
        # Match Evaluator and Simulator's summation order for the energy-only
        # control; normalization must not alter physical energy accounting.
        total = sum(consumption.values())
        fitness = params.w_energy * (total / params.energy_reference) + params.w_load * load
        if not isfinite(total) or total <= 0 or not isfinite(fitness) or fitness < 0:
            return None
    except (TypeError, KeyError, ValueError, OverflowError, RecursionError, ZeroDivisionError):
        return None
    return Candidate(fitness, total, load, consumption, tuple(heads), root)
