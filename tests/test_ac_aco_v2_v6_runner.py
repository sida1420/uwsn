"""Verify the named runner preset and real Windows-spawn CSV execution."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from multiprocessing import get_context
from pathlib import Path
import pickle
import runpy
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import run
from algorithms.ac_aco import ACACO
from algorithms.ac_aco_v2_v6 import ACACO_V2_V6
from algorithms.d_aco import DACO
from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.clustering.ac_aco.ac_aco import evaporation_rate
from algorithms.research_acaco.operators import evaporation_only
from hparameter import HyperParameters
from network import NetworkInstance


def test_registered_preset_and_original_defaults_are_independent(monkeypatch):
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    monkeypatch.setattr(run, "SEED", 24)
    original = run.create_algorithm(ACACO, network, HyperParameters())
    variant = run.create_algorithm(ACACO_V2_V6, network, HyperParameters())
    comparator = run.create_algorithm(DACO, network, HyperParameters(), seed=25)
    assert ACACO_V2_V6 in run.ALGORITHMS
    assert [type(a) for a in (original, comparator, variant)] == [ACACO, DACO, ACACO_V2_V6]
    assert original.params == ACACOParameters()
    assert original.name == "AC-ACO" and variant.name == "AC-ACO-V2-V6"
    assert original.seed == variant.seed == 24 and comparator.seed == 25
    assert variant.params.load_weight == 0 and variant.params.num_ants == 40
    assert (variant.params.tau_min, variant.params.tau0, variant.params.tau_max) == (.01, 1, 20)
    assert variant.options.heuristic == "marginal"
    assert variant.options.chaos_policy == "evaporation"
    assert variant.options.evaporation_kappa == .5


def test_exact_research_preset_trajectory_and_pickle():
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    factory = runpy.run_path(str(ROOT / "plans/261014-1051-acaco-candidates/run-experiments.py"))["make_algorithm"]
    expected = factory("V2+V6", network, 24, 40)
    actual = run.create_algorithm(ACACO_V2_V6, network, HyperParameters(), seed=24)
    assert asdict(actual.params) == asdict(expected.params)
    assert asdict(actual.options) == asdict(expected.options)
    assert pickle.loads(pickle.dumps(ACACO_V2_V6)) is ACACO_V2_V6
    live, residual = list(range(network.N)), [network.init_energy] * network.N
    for _ in range(2):
        expected_root, expected_costs = expected.plan_round(live, residual)
        root, costs = actual.plan_round(live, residual)
        assert root is not None and expected_root is not None
        assert costs == expected_costs and set(costs) == set(live)
        assert actual.clustering.rng.getstate() == expected.clustering.rng.getstate()
        assert actual.clustering.pheromone == expected.clustering.pheromone
        assert actual.clustering.last_exploration == 0.0
        for node, energy in costs.items():
            residual[node] = max(0.0, residual[node] - energy)
        live = [i for i in live if residual[i] > 0]
    restored = pickle.loads(pickle.dumps(actual))
    assert restored.plan_round(live, residual)[1] == actual.plan_round(live, residual)[1]


def test_spawn_runs_physical_round_and_writes_distinct_csvs(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    hp = HyperParameters()
    hp.T_max = 1  # Test-only horizon: exercise the actual final-round production path.
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
    assert len(written) == 1
    assert written.iloc[0]["round_energy"] == pytest.approx(history.iloc[0]["round_energy"])
    sensors = pd.read_csv(tmp_path / f"{prefix}_{name}_sensor-energy.csv")
    assert len(sensors) == 1 and len(sensors.columns) == network.N + 1


@pytest.mark.parametrize("horizon", [1, 3500])
@pytest.mark.parametrize("kappa", [0, .5])
def test_evaporation_schedule_endpoint_accepts_roundoff(horizon, kappa):
    rho = evaporation_rate(horizon, horizon, .1, .6)
    assert evaporation_only(rho, .8, kappa, .1, .6) == .1


@pytest.mark.parametrize("rho", [.099, .601])
def test_evaporation_rejects_genuine_out_of_bounds(rho):
    with pytest.raises(ValueError):
        evaporation_only(rho, .8, .5, .1, .6)
