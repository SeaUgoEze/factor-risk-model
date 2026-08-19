"""Data acquisition for the interactive app.

A thin, user-friendly wrapper over the engine's data pipeline
(``src.data``).  The engine already handles retries, caching and
alignment; this module adds the *interface contract*:

* the benchmark (SPY) is always fetched alongside the user's tickers,
* tickers that return no data raise a clear ValueError instead of
  silently vanishing from the universe,
* a sector map is returned so unknown/custom tickers still get a
  sensible label in the exposures heatmap.

Everything is cached on disk (``src.data`` writes CSVs under ``data/``),
so re-running with the same window is instant and offline-friendly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.config import BENCHMARK, UNIVERSE
from src.data import (AnalysisData, build_analysis_dataset,
                      fetch_daily_prices, fetch_fama_french,
                      to_monthly_returns)

from factor_risk_model.utils.helpers import validate_dates

# Curated tickers offered in the picker (the engine's 26-stock universe).
CURATED = sorted(UNIVERSE)


@dataclass
class AppData:
    """Everything the model layer needs, plus app-level conveniences."""

    ds: AnalysisData            # aligned monthly dataset (engine object)
    daily_prices: pd.DataFrame  # daily adjusted close (incl. SPY)
    tickers: list               # resolved tickers actually in the dataset
    sector_map: dict = field(default_factory=dict)

    @property
    def factors(self) -> pd.DataFrame:
        return self.ds.factors


def _sector_map_for(tickers: list[str]) -> dict:
    """    UNIVERSE sectors for known names, 'Other' for custom tickers.

    SPY is absent: the engine's exposure_heatmap falls back to its own
    'Benchmark' group for any ticker missing from the map.
    """
    return {t: UNIVERSE.get(t, "Other") for t in tickers
            if t != BENCHMARK}


def fetch_app_data(tickers: list[str], start: str, end: str,
                   factor_model: str = "5-factor",
                   cache: bool = True,
                   force_refresh: bool = False) -> AppData:
    """Fetch, align and clean the full monthly dataset for the app.

    Parameters
    ----------
    tickers      : requested stock tickers (parsed, upper-cased)
    start, end   : 'YYYY-MM-DD' strings
    factor_model : '3-factor' or '5-factor' (which FF data to load)
    cache        : reuse on-disk CSVs when the window matches
    force_refresh: ignore the disk cache and re-download

    Raises
    ------
    ValueError   : no tickers, unknown/empty tickers, or a too-short window
    RuntimeError : network/API failure after the engine's retries
    """
    if not tickers:
        raise ValueError("Select at least one stock.")
    s, e = validate_dates(start, end)

    ff_model = "3" if factor_model == "3-factor" else "5"
    to_fetch = list(dict.fromkeys([*tickers, BENCHMARK]))   # SPY always

    prices = fetch_daily_prices(to_fetch, s.date(), e.date(),
                                cache=cache, force_refresh=force_refresh)
    ff = fetch_fama_french(model=ff_model, start=s.date(), end=e.date(),
                           cache=cache, force_refresh=force_refresh)

    # Friendly failure for tickers that produced no usable data.
    missing = [t for t in tickers if t not in prices.columns
               or prices[t].notna().sum() < 2]
    if missing:
        raise ValueError(
            f"No usable price data for: {', '.join(missing)}. Check the "
            "tickers (US-listed symbols work best) or widen the date range.")

    monthly = to_monthly_returns(prices)
    ds = build_analysis_dataset(monthly, ff)
    if len(ds.returns) < 24:
        raise ValueError(
            f"Only {len(ds.returns)} aligned months in {start}..{end} - "
            "factor regressions need at least 24. Widen the window.")

    resolved = [t for t in tickers if t in ds.returns.columns]
    return AppData(ds=ds, daily_prices=prices, tickers=resolved,
                   sector_map=_sector_map_for(resolved + [BENCHMARK]))
