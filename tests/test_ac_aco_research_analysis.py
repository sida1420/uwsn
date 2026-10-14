"""Statistical pairing must use physical topology fingerprints, never labels."""
import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).resolve().parents[1] / "plans" /
          "261014-1051-acaco-candidates" / "analysis" / "analyze-results.py")
SPEC = importlib.util.spec_from_file_location("acaco_research_analysis", SCRIPT)
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def row(variant="B0", fingerprint="map-a", label="scenario", seed=24, energy=10.):
    candidate = dict(positive_finite=True, conservation_valid=True,
                     topology_valid=True, radius_valid=True, all_live_present=True,
                     energy=energy, stage="search")
    return dict(variant=variant, map_sha=fingerprint, scenario=label,
                algorithm_seed=seed, physical_round=0,
                params={"num_ants": 2}, options={}, invalid_probability_count=0,
                candidate_records=[candidate], feasible_count=2,
                energy={"min": energy, "mean": energy, "p10": energy},
                evaluation_count=2, feasibility_rate=1., algorithm_seconds=.01,
                setup_seconds=.001, attempt_count=2, calibration_attempt_count=0,
                jaccard_diversity=.5, outliers={"mean": 0}, coverage={"mean": 1.},
                transition_entropy={"mean": .5}, effective_lambda={"mean": .1},
                pheromone_after={"concentration_cv": .2}, best_so_far=[energy, energy])


def result(rows, variant="V2", **kwargs):
    return next(item for item in analysis.analyze(rows, **kwargs)
                if item["variant"] == variant)


def test_condition_ignores_labels_and_uses_map_hash_and_algorithm_seed():
    assert analysis.condition(row()) == ("map-a", 24)
    assert analysis.condition(row(label="alias")) == analysis.condition(row())
    assert analysis.condition(row(fingerprint="map-b")) != analysis.condition(row())
    assert analysis.condition(row(seed=25)) != analysis.condition(row())


def test_duplicate_condition_rejected_even_with_alias_label():
    with pytest.raises(ValueError, match="duplicate condition"):
        analysis.validate_rows([row(), row(label="alias")])
    analysis.validate_rows([row(), row(fingerprint="map-b"), row(seed=25)])
    later = row()
    later["physical_round"] = 1
    analysis.validate_rows([row(), later])


@pytest.mark.parametrize("flag", ["positive_finite", "conservation_valid",
    "topology_valid", "radius_valid", "all_live_present", "invalid_probability_count"])
def test_invalid_search_evidence_rejected(flag):
    invalid = row()
    if flag == "invalid_probability_count":
        invalid[flag] = 1
    else:
        invalid["candidate_records"][0][flag] = False
    with pytest.raises(ValueError, match="invalid probability/tree"):
        analysis.validate_rows([invalid])


@pytest.mark.parametrize("field", ["params", "options"])
def test_configuration_drift_rejected_within_variant(field):
    changed = row(seed=25)
    changed[field]["changed_control"] = .5
    with pytest.raises(ValueError, match="different effective parameters/options"):
        analysis.validate_rows([row(), changed])
    changed["variant"] = "V2"
    analysis.validate_rows([row(), changed])


def test_pairing_does_not_cross_map_or_seed_and_groups_aliases_by_fingerprint():
    rows = [row(seed=24, energy=10), row(seed=25, label="alias", energy=20),
            row(fingerprint="map-b", energy=10),
            row("V2", seed=24, label="variant-alias", energy=8),
            row("V2", seed=25, energy=10), row("V2", fingerprint="map-b", energy=9),
            row("V2", fingerprint="map-c", energy=1), row("V2", seed=26, energy=1)]
    analysis.validate_rows(rows)
    actual = result(rows, independent=True)
    assert actual["paired_runs"] == 3 and actual["valid_topologies"] == 2
    assert actual["topology_effects"] == pytest.approx({"map-a": 35., "map-b": 10.})
    assert actual["improvement_pct"] == pytest.approx(22.5)
    assert actual["paired_difference_J"] == pytest.approx(3.5)
    assert actual["ci95_low"] < actual["improvement_pct"] < actual["ci95_high"]
    assert result(rows)["ci95_low"] is None
    assert result([row(), row("V2", fingerprint="map-other")])["paired_runs"] == 0


def test_equal_budget_pairing_and_incomplete_pool_exclusion():
    baseline, variant = row(), row("V2", energy=8)
    variant["params"]["num_ants"] = variant["feasible_count"] = 1
    assert result([baseline, variant])["paired_runs"] == 0
    assert result([baseline, variant], total_budget=True)["paired_runs"] == 1
    variant["evaluation_count"] = 3
    assert result([baseline, variant], total_budget=True)["paired_runs"] == 0
    incomplete = deepcopy(baseline)
    incomplete["variant"], incomplete["feasible_count"] = "V2", 1
    assert result([baseline, incomplete])["paired_runs"] == 0
