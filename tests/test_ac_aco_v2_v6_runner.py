"""Production V2+V6 contracts without research scripts or optimizer data."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
import pickle
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import run
from algorithms.ac_aco import ACACO
from algorithms.ac_aco_v2_v6 import ACACO_V2_V6
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering.ac_aco.ac_aco import evaporation_rate
from algorithms.clustering.ac_aco.v2_v6 import (
    evaporation_only, marginal_log_quality, normalized_weights,
)
from hparameter import HyperParameters
from network import NetworkInstance


def signature(root):
    return None if root is None else (
        root.id, root.isCH, root.isRelay, tuple(signature(n) for n in root.nxts)
    )


def test_registered_preset_and_original_defaults_are_independent(monkeypatch):
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    monkeypatch.setattr(run, "SEED", 24)
    original = run.create_algorithm(ACACO, network, HyperParameters())
    variant = run.create_algorithm(ACACO_V2_V6, network, HyperParameters())
    assert ACACO_V2_V6 in run.ALGORITHMS
    assert original.params == ACACOParameters()
    assert original.name == "AC-ACO" and variant.name == "AC-ACO-V2-V6"
    assert original.seed == variant.seed == 24
    assert variant.params.load_weight == 0 and variant.params.num_ants == 40
    assert (variant.params.tau_min, variant.params.tau0, variant.params.tau_max) == (.01, 1, 20)
    assert pickle.loads(pickle.dumps(ACACO_V2_V6)) is ACACO_V2_V6


def test_seeded_trajectory_budget_and_pickle_resume():
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    left = ACACO_V2_V6(network, HyperParameters(), seed=24)
    right = ACACO_V2_V6(network, HyperParameters(), seed=24)
    live, residual = list(range(network.N)), [network.init_energy] * network.N
    evaluations = []
    evaluate = left.evaluator.energy_consumption

    def counted(*args):
        result = evaluate(*args)
        evaluations.append(result[1])
        return result

    left.evaluator.energy_consumption = counted
    for _ in range(3):
        start = len(evaluations)
        root, costs = left.plan_round(live, residual)
        other_root, other_costs = right.plan_round(live, residual)
        assert root is not None and signature(root) == signature(other_root)
        assert costs == other_costs and set(costs) == set(live)
        assert sum(costs.values()) == pytest.approx(min(evaluations[start:]))
        assert 0 < len(evaluations) - start <= left.params.num_ants
        assert left.clustering.rng.getstate() == right.clustering.rng.getstate()
        assert left.clustering.pheromone == right.clustering.pheromone
        for node, energy in costs.items():
            residual[node] = max(0.0, residual[node] - energy)
        live = [i for i in live if residual[i] > 0]
    restored = pickle.loads(pickle.dumps(right))
    assert restored.plan_round(live, residual)[1] == right.plan_round(live, residual)[1]


def test_spawn_runs_physical_round_and_writes_distinct_csvs(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    hp = HyperParameters()
    hp.T_max = 1
    prefix = "isolated-spawn-smoke"
    original_path = tmp_path / f"{prefix}_AC-ACO.csv"
    original_path.write_text("historical sentinel\n", encoding="utf-8")
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as pool:
        name, history = pool.submit(run.run_algorithm, ACACO_V2_V6, network, hp,
                                    24, tmp_path, prefix).result(timeout=60)
    assert name == "AC-ACO-V2-V6" and len(history) == 1
    assert history.iloc[0]["round"] == 0
    assert history.iloc[0]["alive_nodes"] == network.N
    assert history.iloc[0]["round_energy"] > 0
    assert original_path.read_text(encoding="utf-8") == "historical sentinel\n"
    written = pd.read_csv(tmp_path / f"{prefix}_{name}.csv")
    assert written.iloc[0]["round_energy"] == pytest.approx(history.iloc[0]["round_energy"])
    sensors = pd.read_csv(tmp_path / f"{prefix}_{name}_sensor-energy.csv")
    assert len(sensors) == network.N and list(sensors.columns) == ["sensor", "total_energy"]
    assert sensors.total_energy.sum() == pytest.approx(history.round_energy.sum())


@pytest.mark.parametrize("horizon", [1, 3500])
@pytest.mark.parametrize("kappa", [0, .5])
def test_evaporation_schedule_endpoint_accepts_roundoff(horizon, kappa):
    rho = evaporation_rate(horizon, horizon, .1, .6)
    assert evaporation_only(rho, .8, kappa, .1, .6) == .1


@pytest.mark.parametrize("rho", [.099, .601])
def test_evaporation_rejects_genuine_out_of_bounds(rho):
    with pytest.raises(ValueError):
        evaporation_only(rho, .8, .5, .1, .6)


@pytest.mark.parametrize("values", [[], [0], [-np.inf] * 3, [1e300, -1e300, np.nan]])
def test_stable_distributions(values):
    probabilities = normalized_weights(values)
    assert len(probabilities) == len(values)
    assert np.isfinite(probabilities).all() and all(v >= 0 for v in probabilities)
    assert not probabilities or sum(probabilities) == pytest.approx(1)


def test_marginal_quality_monotonic_scale_invariant_and_invalid_controls():
    deltas = [-3., -1., 0., 2., 7.]
    logs = marginal_log_quality(deltas, 2.)
    assert np.isfinite(np.exp(logs)).all() and (np.diff(logs) < 0).all()
    np.testing.assert_allclose(logs, marginal_log_quality(np.array(deltas) * 1e-20, 2e-20))
    np.testing.assert_array_equal(marginal_log_quality([0., 0.], 1), [0., 0.])
    with pytest.raises(ValueError):
        marginal_log_quality([1], 0)
    with pytest.raises(ValueError):
        evaporation_only(.5, .5, 2, .1, .6)
