"""
Step 1 - Data acquisition and preparation
==========================================
Two independent data sources:

  1. Yahoo Finance (via `yfinance`)
     -> daily *adjusted* close prices for our stock universe and SPY.
        Adjusted close re-states history as if all dividends were
        reinvested and all splits already happened, so simple returns
        computed from it are total returns.

  2. Kenneth French Data Library (via `pandas_datareader`, with a
     direct-download fallback)
     -> monthly factor returns, published in percent:
          Mkt-RF : value-weighted US market return minus T-bill rate
          SMB    : Small Minus Big  (size factor)
          HML    : High Minus Low   (value factor)
          RMW    : Robust Minus Weak (profitability factor)
          CMA    : Conservative Minus Aggressive (investment factor)
          RF     : one-month T-bill rate

The factors are monthly, so we convert daily prices to monthly returns
and align on the same month-end calendar.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from src.config import DATA_DIR


# ----------------------------------------------------------------------
# Yahoo Finance daily prices
# ----------------------------------------------------------------------
def fetch_daily_prices(tickers, start, end, cache=True, force_refresh=False):
    """Fetch daily adjusted close prices for `tickers` between start/end.

    Caches to CSV so re-runs are instant and we don't hammer the free API.
    Includes retry logic because Yahoo rate-limits rapid requests.
    """
    cache_path = DATA_DIR / f"daily_prices_{start}_{end}.csv"

    if cache and cache_path.exists() and not force_refresh:
        prices = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        print(f"[data] loaded cached prices ({prices.shape[0]} rows x {prices.shape[1]} cols)")
        return prices

    print(f"[data] downloading {len(tickers)} tickers from Yahoo Finance ...")
    close = pd.DataFrame()
    remaining = list(tickers)

    for attempt in range(1, 4):                      # up to 3 rounds
        if not remaining:
            break
        try:
            batch = _download_batch(remaining, start, end, threads=(attempt == 1))
        except Exception as exc:                     # network / rate-limit errors
            print(f"[data] round {attempt} failed ({type(exc).__name__}): {exc}")
            time.sleep(2 * attempt)
            continue

        new = batch[[t for t in remaining if t in batch.columns]]
        close = pd.concat([close, new], axis=1)
        remaining = [t for t in remaining if t not in close.columns]
        if remaining:
            print(f"[data] retrying missing tickers: {remaining}")

    if close.empty:
        raise RuntimeError("Yahoo Finance download failed after 3 attempts.")

    # Drop tickers that returned (almost) no data; warn about the rest.
    good = [c for c in close.columns if close[c].notna().sum() >= 0.5 * len(close)]
    dropped = [c for c in close.columns if c not in good]
    if dropped:
        print(f"[data] WARNING: dropped tickers with insufficient data: {dropped}")
    close = close[good].sort_index()

    if cache:
        close.to_csv(cache_path)
        print(f"[data] saved daily prices -> {cache_path.name}")
    return close


def _download_batch(tickers, start, end, threads=True):
    """Single yfinance call -> wide DataFrame of adjusted Close prices.

    threads=True is fast but can hit yfinance's sqlite-cache lock;
    the retry loop in fetch_daily_prices re-runs stragglers serially.
    """
    import yfinance as yf

    data = yf.download(
        list(tickers),
        start=start, end=end,
        auto_adjust=True,       # dividends + splits already applied
        progress=False,
        threads=threads,
    )
    # With several tickers yfinance returns MultiIndex columns
    # (price field, ticker); grab the Close layer.
    close = data["Close"].copy() if isinstance(data.columns, pd.MultiIndex) else data
    if isinstance(close, pd.Series):                 # single-ticker edge case
        close = close.to_frame()
    return close


# ----------------------------------------------------------------------
# Kenneth French factor data
# ----------------------------------------------------------------------
def fetch_fama_french(model="5", start=None, end=None, cache=True, force_refresh=False):
    """Fetch monthly Fama-French factor returns.

    model="3" -> Mkt-RF, SMB, HML, RF
    model="5" -> Mkt-RF, SMB, HML, RMW, CMA, RF

    Returns are converted from Ken French's *percent* units to decimal
    fractions (0.55 -> 0.0055), matching how we store stock returns.
    """
    dataset = ("F-F_Research_Data_5_Factors_2x3" if model == "5"
               else "F-F_Research_Data_Factors")
    cache_path = DATA_DIR / f"fama_french_{model}f_monthly.csv"

    if cache and cache_path.exists() and not force_refresh:
        ff = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        print(f"[data] loaded cached Fama-French {model}-factor data")
    else:
        try:
            from pandas_datareader.famafrench import FamaFrenchReader
            # Quirk: pandas-datareader anchors the END year at January and
            # returns only recent history when no range is given.  Buffer the
            # years by +/-1 and do the precise slicing ourselves below.
            lo = None if start is None else int(str(start)[:4]) - 1
            hi = None if end is None else int(str(end)[:4]) + 1
            ff = FamaFrenchReader(dataset, start=lo, end=hi).read()[0]
            print(f"[data] Fama-French {model}-factor via pandas-datareader")
        except Exception as exc:
            print(f"[data] pandas-datareader failed ({type(exc).__name__}: {exc})")
            print("[data] falling back to direct download from Ken French's site")
            ff = _download_fama_french_direct(dataset)

        # pandas-datareader can return a PeriodIndex (period[M]); convert it
        # to a clean month-end DatetimeIndex at midnight so it joins exactly
        # onto the month-end stock returns (23:59:59.999999 would not match).
        if isinstance(ff.index, pd.PeriodIndex):
            ff.index = ff.index.to_timestamp(how="end").normalize()
        else:
            ff.index = pd.DatetimeIndex(ff.index).normalize()

        ff = ff.sort_index() / 100.0                   # percent -> fraction
        if cache:
            ff.to_csv(cache_path)

    # Slice to the analysis window (factor history runs from 1926).
    if start is not None:
        ff = ff.loc[ff.index >= pd.Timestamp(start)]
    if end is not None:
        ff = ff.loc[ff.index <= pd.Timestamp(end)]
    return ff


def _download_fama_french_direct(dataset):
    """Fallback: unzip the CSV straight from Ken French's public FTP.

    The archive's format is slightly messy (a header block, then monthly
    rows 'YYYYMM, ...', then a separate annual block), so we parse only
    rows whose first token is a 6-digit year-month.
    """
    import requests

    url = f"https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{dataset}_CSV.zip"
    print(f"[data] downloading {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    with ZipFile(BytesIO(resp.content)) as zf:
        raw = zf.read(zf.namelist()[0]).decode("latin-1")

    rows = []
    for line in raw.splitlines():
        toks = [t.strip() for t in line.split(",")]
        if toks and len(toks[0]) == 6 and toks[0].isdigit():
            rows.append(toks)                          # only YYYYMM rows

    df = pd.DataFrame(rows)
    df[0] = pd.to_datetime(df[0], format="%Y%m") + pd.offsets.MonthEnd(0)
    df = df.set_index(0).apply(pd.to_numeric)

    # Rename columns from the CSV header line (", Mkt-RF, SMB, ...").
    for line in raw.splitlines():
        toks = [t.strip() for t in line.split(",")]
        if any("Mkt-RF" in t for t in toks):
            names = [t for t in toks if t]
            df.columns = [c for c in names]            # len == n_cols - 1
            break
    return df


# ----------------------------------------------------------------------
# Price -> monthly return conversion
# ----------------------------------------------------------------------
def to_monthly_returns(daily_prices):
    """Convert daily prices to month-end simple returns.

    resample("ME") = Month End: keep the LAST trading price of each month,
    then pct_change() gives the return over that month.
    """
    monthly_prices = daily_prices.resample("ME").last()
    returns = monthly_prices.pct_change().dropna(how="all")
    print(f"[data] monthly returns: {returns.shape[0]} months x {returns.shape[1]} securities")
    return returns


# ----------------------------------------------------------------------
# Alignment
# ----------------------------------------------------------------------
@dataclass
class AnalysisData:
    """Aligned, ready-to-regress monthly dataset (Steps 2-6 input)."""
    returns: pd.DataFrame   # raw stock monthly returns (fractions)
    factors: pd.DataFrame   # Fama-French factor returns (fractions)
    rf: pd.Series           # monthly risk-free rate (fractions)
    excess: pd.DataFrame    # stock returns minus the risk-free rate


def build_analysis_dataset(monthly_returns, ff_factors):
    """Align stock returns and factor returns on the same month-end index.

    Excess return = stock return - RF.  In asset pricing, excess returns
    are explained by factor returns.
    """
    factor_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    factor_cols = [c for c in factor_cols if c in ff_factors.columns]
    factors = ff_factors[factor_cols]

    # inner join: keep only months present in BOTH datasets
    stock = monthly_returns
    aligned = stock.join(factors, how="inner").dropna()

    returns = aligned[stock.columns]
    factors = aligned[factor_cols].drop(columns=["RF"])
    rf = aligned["RF"]
    excess = returns.subtract(rf, axis=0)

    print(f"[data] aligned dataset: {returns.shape[0]} months x {returns.shape[1]} stocks")
    return AnalysisData(returns=returns, factors=factors, rf=rf, excess=excess)
