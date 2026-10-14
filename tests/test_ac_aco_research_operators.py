"""Numerical contracts for positive marginal quality and bounded exploration."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from algorithms.research_acaco.operators import (ProgressFeedback, evaporation_only,
    marginal_log_quality, normalized_weights, uniform_mix)
from algorithms.research_acaco.variants import ResearchOptions


@pytest.mark.parametrize("values", [[], [0], [-np.inf] * 3, [1e300, -1e300, np.nan]])
def test_stable_distributions(values):
    p = uniform_mix(normalized_weights(values), .25)
    assert len(p) == len(values)
    assert np.isfinite(p).all() and all(v >= 0 for v in p)
    assert not p or sum(p) == pytest.approx(1)


def test_marginal_quality_monotonic_scale_invariant_and_invalid_controls():
    deltas = [-3., -1., 0., 2., 7.]
    logs = marginal_log_quality(deltas, 2.)
    assert np.isfinite(np.exp(logs)).all() and (np.exp(logs) > 0).all()
    assert (np.diff(logs) < 0).all()
    np.testing.assert_allclose(logs, marginal_log_quality(np.array(deltas) * 1e-20, 2e-20))
    np.testing.assert_array_equal(marginal_log_quality([0., 0.], 1), [0., 0.])
    for invalid in (-1., 2., np.nan, np.inf):
        with pytest.raises(ValueError):
            uniform_mix([.3, .7], invalid)
        with pytest.raises(ValueError):
            ResearchOptions(fixed_scale=invalid)
    with pytest.raises(ValueError):
        marginal_log_quality([1], 0)
    with pytest.raises(ValueError):
        uniform_mix([-.1, 1.1], .1)
    with pytest.raises(ValueError):
        evaporation_only(.5, .5, 2, .1, .6)


def test_feedback_observed_only_bounded_cyclic_deterministic():
    left, right = ProgressFeedback(), ProgressFeedback()
    for cost in [10, 9] + [9] * 24 + [8]:
        before = left.coefficient()
        assert left.coefficient() == before
        left.observe(cost)
        right.observe(cost)
        assert left == right and .02 <= left.coefficient() <= .25
    feedback = ProgressFeedback()
    feedback.observe(10)
    values = []
    for _ in range(16):
        feedback.observe(10)
        values.append(feedback.coefficient())
    assert min(values) == .02 and max(values) == .25
