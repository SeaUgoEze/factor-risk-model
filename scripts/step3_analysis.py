"""
Step 3 - Factor analysis & interpretation
===========================================
Run:  python scripts/step3_analysis.py

Prints the factor covariance/correlation structure, saves the exposure
and correlation heatmaps, and writes a plain-English factor profile for
every stock.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 80)

from src.config import START_DATE, END_DATE, UNIVERSE, BENCHMARK, DATA_DIR, FIGURES_DIR
from src.data import (
    build_analysis_dataset,
    fetch_daily_prices,
    fetch_fama_french,
    to_monthly_returns,
)
from src.regressions import MODEL_5F, exposure_table
from src.analysis import (
    correlation_heatmap,
    exposure_heatmap,
    factor_covariance,
    plain_english_profile,
)


def main():
    print("=" * 92)
    print("STEP 3 - FACTOR ANALYSIS & INTERPRETATION")
    print(f"window {START_DATE} -> {END_DATE} | "
          f"{len(UNIVERSE)} stocks + {BENCHMARK} | 5-factor model")
    print("=" * 92)

    tickers = list(UNIVERSE) + [BENCHMARK]
    prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
    ff5 = fetch_fama_french("5", START_DATE, END_DATE)
    monthly = to_monthly_returns(prices)
    ds = build_analysis_dataset(monthly, ff5)
    t5 = exposure_table(ds.excess, ds.factors, MODEL_5F)

    cov, corr, vol_ann = factor_covariance(ds.factors)

    print("\nANNUALIZED FACTOR VOLATILITY (%):")
    print(vol_ann.round(2).to_string())

    print("\nMONTHLY FACTOR COVARIANCE MATRIX  (x100, i.e. %^2 per month):")
    print((cov * 100).round(3).to_string())

    print("\nFACTOR CORRELATION MATRIX:")
    print(corr.round(3).to_string())

    print()
    exposure_heatmap(t5, MODEL_5F, UNIVERSE, FIGURES_DIR / "factor_exposures_heatmap.png")
    correlation_heatmap(corr, FIGURES_DIR / "factor_correlation_heatmap.png")

    print("\nWHAT EACH STOCK'S BETAS SAY (plain English):")
    profiles = t5.apply(plain_english_profile, axis=1)
    for ticker, profile in profiles.items():
        marker = "  <-- benchmark" if ticker == BENCHMARK else ""
        print(f"  {ticker:5s}  {profile}{marker}")

    cov.to_csv(DATA_DIR / "factor_covariance.csv")
    corr.to_csv(DATA_DIR / "factor_correlation.csv")
    profiles.to_csv(DATA_DIR / "factor_profiles.csv", header=["profile"])
    print("\n[done] covariance/correlation/profiles saved under data/; "
          "figures saved under figures/")


if __name__ == "__main__":
    main()
