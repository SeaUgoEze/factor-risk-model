"""Shared helpers for the interactive application.

Small, dependency-light utilities the data and interface layers lean on:
parsing user input, formatting numbers for display, and a couple of
portfolio-return shortcuts.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Sequence

import pandas as pd

# ----------------------------------------------------------------------
# Input parsing
# ----------------------------------------------------------------------
_TICKER_SPLIT = re.compile(r"[,\s;]+")


def normalize_tickers(raw: str | Sequence[str]) -> list[str]:
    """Parse free-form ticker input into a clean, de-duplicated list.

    Accepts \"AAPL, MSFT GOOGL;TSLA\" or an iterable of strings.  Returns
    upper-cased, unique tickers in input order.  Empty input -> [].
    """
    if isinstance(raw, str):
        parts = [p for p in _TICKER_SPLIT.split(raw.strip()) if p]
    else:
        parts = [str(p) for p in raw]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        p = p.strip().upper()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def validate_dates(start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Coerce user date strings; raise ValueError with a friendly message."""
    try:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
    except Exception:
        raise ValueError(f"Could not parse dates '{start}' / '{end}'. "
                         "Use YYYY-MM-DD.")
    if s >= e:
        raise ValueError(f"Start date {s.date()} must be before end date "
                         f"{e.date()}.")
    if (e - s).days < 120:
        raise ValueError("The window is shorter than ~4 months; factor "
                         "regressions need at least 24 monthly observations "
                         "to be meaningful.")
    return s, e


# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------
def fmt_pct(x: float, digits: int = 2) -> str:
    """0.1234 -> '+12.34%'  (sign always shown for deltas)."""
    return f"{x * 100:+.{digits}f}%"


def fmt_float(x: float, digits: int = 3) -> str:
    """0.9876 -> '0.988'."""
    return f"{x:.{digits}f}"


def report_stamp() -> str:
    """File-safe timestamp for report names: 2026-08-05_1430."""
    return datetime.now().strftime("%Y-%m-%d_%H%M")


# ----------------------------------------------------------------------
# Portfolio return shortcuts
# ----------------------------------------------------------------------
def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Monthly returns of a weighted portfolio: r_p = R @ w.

    ``weights`` is reindexed onto ``returns`` columns so ordering can
    never silently corrupt the multiplication (any missing name -> 0).
    """
    w = weights.reindex(returns.columns).fillna(0.0)
    return returns @ w


def equal_weight_returns(returns: pd.DataFrame) -> pd.Series:
    """Simple average of the selected names - the 'no optimization' state."""
    return returns.mean(axis=1)
