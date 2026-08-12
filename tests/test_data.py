"""Data quality tests: alignment, calendar, friendly errors (all offline)."""
from __future__ import annotations

import pandas as pd
import pytest

from factor_risk_model.data.data_fetcher import fetch_app_data
from factor_risk_model.utils.helpers import normalize_tickers, validate_dates


# ----------------------------------------------------------------------
# Alignment
# ----------------------------------------------------------------------
def test_aligned_dataset_shares_one_index(app_data):
    ds = app_data.ds
    assert (ds.returns.index == ds.factors.index).all()
    assert (ds.rf.index == ds.factors.index).all()
    assert ds.excess.shape == ds.returns.shape


def test_default_window_has_59_months(app_data):
    assert len(app_data.ds.returns) == 59  # 2015-01 .. 2019-12


def test_benchmark_always_present(app_data):
    assert "SPY" in app_data.ds.returns.columns
    # SPY is intentionally absent from the sector map: the engine's
    # exposure_heatmap groups any unmapped ticker under 'Benchmark'.
    assert "SPY" not in app_data.sector_map


def test_requested_tickers_resolved(app_data):
    assert set(app_data.tickers) == {"AAPL", "MSFT", "JPM", "XOM", "JNJ",
                                     "PG", "AMZN", "META", "CAT", "BA"}


def test_custom_ticker_gets_other_sector(app_data):
    assert app_data.sector_map["AAPL"] == "Technology"


# ----------------------------------------------------------------------
# Input validation (no network needed)
# ----------------------------------------------------------------------
def test_unknown_ticker_raises_friendly_error(monkeypatch):
    """A ticker with no price data must raise ValueError, not vanish."""
    import factor_risk_model.data.data_fetcher as df_mod

    def fake_fetch(tickers, start, end, **kw):
        # pretend Yahoo returned only SPY for a bogus ticker
        idx = pd.date_range(start, end, freq="B")
        return pd.DataFrame({"SPY": 100.0}, index=idx)

    monkeypatch.setattr(df_mod, "fetch_daily_prices", fake_fetch)
    # Patch the name in data_fetcher's OWN namespace (it imported
    # fetch_fama_french via `from src.data import ...`), so the test is
    # genuinely network-free and never relies on the on-disk cache.
    monkeypatch.setattr(df_mod, "fetch_fama_french",
                        lambda **kw: _tiny_ff())
    with pytest.raises(ValueError, match="No usable price data"):
        fetch_app_data(["ZZZZ"], "2015-01-01", "2019-12-31")


def test_empty_tickers_raise():
    with pytest.raises(ValueError, match="Select at least one stock"):
        fetch_app_data([], "2015-01-01", "2019-12-31")


def test_short_window_raises():
    with pytest.raises(ValueError, match="shorter than ~4 months"):
        fetch_app_data(["AAPL"], "2019-10-01", "2019-12-31")


def test_reversed_dates_raise():
    with pytest.raises(ValueError, match="must be before"):
        validate_dates("2019-12-31", "2015-01-01")


# ----------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------
def test_normalize_tickers():
    assert normalize_tickers("aapl, MSFT googl;TSLA") == \
        ["AAPL", "MSFT", "GOOGL", "TSLA"]
    assert normalize_tickers(["XOM", "xom", "CVX"]) == ["XOM", "CVX"]
    assert normalize_tickers("") == []


def _tiny_ff():
    """Stand-in factor frame so the fake-fetch test never touches network."""
    idx = pd.date_range("2015-01-31", "2019-12-31", freq="ME")
    cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    return pd.DataFrame(0.0, index=idx, columns=cols)
