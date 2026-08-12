"""Regression tests: sane betas, R2 bounds, CI sanity, SPY validation."""
from __future__ import annotations

import numpy as np

from factor_risk_model.models.factor_model import FactorModel


def test_exposure_table_shape_and_ci_columns(model):
    t = model.exposures()
    assert "alpha" in t.columns
    for k in model.factor_cols:
        assert {f"beta_{k}", f"ci_lo_{k}", f"ci_hi_{k}"} <= set(t.columns)


def test_betas_within_sane_bounds(model):
    t = model.exposures()
    for k in model.factor_cols:
        b = t[f"beta_{k}"]
        assert (b.abs() < 5).all(), f"{k} betas out of bounds: {b.abs().max()}"


def test_r2_in_unit_interval(model):
    r2 = model.exposures()["R2"]
    assert (r2 >= 0).all() and (r2 <= 1).all()


def test_ci_contains_point_estimate(model):
    t = model.exposures()
    for k in model.factor_cols:
        assert (t[f"ci_lo_{k}"] <= t[f"beta_{k}"]).all()
        assert (t[f"ci_hi_{k}"] >= t[f"beta_{k}"]).all()


def test_spy_market_beta_near_one(model):
    row = model.exposures().loc["SPY"]
    assert 0.8 < row["beta_Mkt-RF"] < 1.2
    assert row["R2"] > 0.9


def test_three_factor_table_lacks_rmw_cma(app_data):
    m = FactorModel(app_data, "3-factor")
    t = m.exposures()
    assert "beta_RMW" not in t.columns and "beta_CMA" not in t.columns
    assert "beta_HML" in t.columns


def test_profiles_do_not_crash_in_3_factor_mode(app_data):
    m = FactorModel(app_data, "3-factor")
    profs = m.profiles()
    assert len(profs) == len(m.app_data.ds.excess.columns)


def test_betas_exclude_spy(model):
    assert "SPY" not in model.betas().index


def test_invalid_model_name_raises(app_data):
    try:
        FactorModel(app_data, "7-factor")
    except ValueError:
        return
    raise AssertionError("expected ValueError for bad model name")


def test_rolling_exposures_paths(model):
    paths = model.rolling_exposures(window=36, step=6)
    assert set(paths) == set(model.factor_cols)
    for k, frame in paths.items():
        assert len(frame) >= 2          # 59 months, window 36, step 6
        assert np.isfinite(frame.values).all()
