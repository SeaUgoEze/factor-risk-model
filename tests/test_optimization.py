"""Optimization tests: every constraint the spec demands, verified."""
from __future__ import annotations

import numpy as np
import pandas as pd

TOL = 1e-9


def _sum1(w) -> bool:
    return abs(float(w.sum()) - 1.0) < 1e-6


def test_long_only_weights_are_nonnegative(full_optimizer):
    targets = {"Mkt-RF": 1.0}
    r = full_optimizer.optimize(targets, allow_shorts=False)
    w = r["weights"]
    assert _sum1(w)
    assert (w >= -TOL).all(), "long-only violated"
    assert r["feasible"]


def test_shorts_respect_floor(full_optimizer):
    targets = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0}
    r = full_optimizer.optimize(targets, allow_shorts=True, short_floor=-0.10)
    w = r["weights"]
    assert _sum1(w)
    assert (w >= -0.10 - 1e-6).all(), "short floor violated"
    assert r["feasible"], "full universe with shorts should hit the mandate"


def test_long_only_infeasible_for_aggressive_value(full_optimizer):
    """The honest engine finding: HML ~1.0 is out of reach long-only."""
    targets = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0}
    r = full_optimizer.optimize(targets, allow_shorts=False)
    assert not r["feasible"]


def test_feasible_mandate_gaps_within_tolerance(full_optimizer):
    targets = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0}
    r = full_optimizer.optimize(targets, tolerance=0.10, allow_shorts=True)
    t = pd.Series(targets)
    gaps = (r["exposures"].reindex(t.index) - t).abs()
    assert (gaps <= 0.10 + 1e-6).all()


def test_exposure_decomposition_sums(full_optimizer):
    targets = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0}
    r = full_optimizer.optimize(targets, allow_shorts=True)
    total, factor, idio = (r["total_vol_ann"], r["factor_vol_ann"],
                           r["idio_vol_ann"])
    # factor_vol^2 + idio_vol^2 ~ total_vol^2 (variance adds)
    assert abs((factor ** 2 + idio ** 2) - total ** 2) < 1.0


def test_single_stock_portfolio():
    """One stock -> weights must be [1.0] and sum to 1."""
    from factor_risk_model.pipeline import run_pipeline
    res = run_pipeline(["JPM"], "2015-01-01", "2019-12-31")
    w = res.weights
    assert _sum1(w)
    assert abs(w["JPM"] - 1.0) < 1e-6
    assert len(w) == 1
