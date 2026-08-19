"""
Step 1 - Data acquisition & preparation
========================================
Run:  python scripts/step1_fetch.py

Downloads daily prices (Yahoo) and factor returns (Ken French),
converts to aligned monthly data, and saves the analysis dataset
for Steps 2-6.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 50)

from src.config import START_DATE, END_DATE, UNIVERSE, BENCHMARK, DATA_DIR
from src.data import (
    build_analysis_dataset,
    fetch_daily_prices,
    fetch_fama_french,
    to_monthly_returns,
)


def main():
    print("=" * 78)
    print("STEP 1 - DATA ACQUISITION & PREPARATION")
    print(f"window   : {START_DATE} -> {END_DATE}")
    print(f"universe : {len(UNIVERSE)} stocks across "
          f"{len(set(UNIVERSE.values()))} sectors + {BENCHMARK}")
    print("=" * 78)

    tickers = list(UNIVERSE) + [BENCHMARK]

    prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
    print(f"\ndaily prices: {prices.shape[0]} trading days x {prices.shape[1]} tickers")
    print(prices.head(3).round(2).to_string())

    ff3 = fetch_fama_french("3", START_DATE, END_DATE)
    ff5 = fetch_fama_french("5", START_DATE, END_DATE)
    print(f"\nFama-French 3-factor (monthly, {len(ff3)} months in window):")
    print(ff3.head(3).to_string())
    print(f"\nFama-French 5-factor (monthly, {len(ff5)} months in window):")
    print(ff5.head(3).to_string())

    monthly = to_monthly_returns(prices)
    print("\nmonthly returns, first 3 months:")
    print(monthly.head(3).round(4).to_string())

    ds = build_analysis_dataset(monthly, ff5)
    print("\nstock excess returns (r - rf), first 3 months:")
    print(ds.excess.head(3).round(4).to_string())

    print("\nsanity checks:")
    print(f"  months in dataset      : {ds.returns.shape[0]} "
          f"(59 = Feb 2015..Dec 2019, first month lost to pct_change)")
    print(f"  missing values         : {bool(ds.excess.isna().any().any())}")
    print(f"  mean RF (annualized)   : {ds.rf.mean() * 12 * 100:.2f}%")
    print(f"  mean mkt excess (ann.) : {ds.factors['Mkt-RF'].mean() * 12 * 100:.2f}%")

    ds.returns.to_csv(DATA_DIR / "monthly_returns.csv")
    ds.factors.to_csv(DATA_DIR / "factors_monthly.csv")
    ds.excess.to_csv(DATA_DIR / "excess_returns.csv")
    ds.rf.to_csv(DATA_DIR / "rf_monthly.csv")
    print("\n[done] analysis dataset saved under data/ for Steps 2-6.")


if __name__ == "__main__":
    main()
