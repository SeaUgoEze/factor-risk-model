"""
Step 2 - Factor exposure regressions
=====================================
Run:  python scripts/step2_regressions.py

Estimates the Fama-French 3- and 5-factor models for every security,
prints the exposure tables with significance stars, and saves the full
statistics to CSV for Steps 3-6.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 60)

from src.config import START_DATE, END_DATE, UNIVERSE, BENCHMARK, DATA_DIR
from src.data import (
    build_analysis_dataset,
    fetch_daily_prices,
    fetch_fama_french,
    to_monthly_returns,
)
from src.regressions import (
    MODEL_3F,
    MODEL_5F,
    exposure_table,
    pretty_beta_table,
    top_bottom,
)


def main():
    print("=" * 92)
    print("STEP 2 - FACTOR EXPOSURES (OLS BETA ESTIMATION)")
    print(f"window {START_DATE} -> {END_DATE} | "
          f"{len(UNIVERSE)} stocks + {BENCHMARK} | monthly observations")
    print("=" * 92)

    # ---- rebuild the aligned dataset (Step 1 caches make this instant) ----
    tickers = list(UNIVERSE) + [BENCHMARK]
    prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
    ff5 = fetch_fama_french("5", START_DATE, END_DATE)
    monthly = to_monthly_returns(prices)
    ds = build_analysis_dataset(monthly, ff5)

    # ---- 3-factor model -----------------------------------------------
    print("\n" + "-" * 92)
    print("FAMA-FRENCH 3-FACTOR EXPOSURES   (r - rf = a + b1*Mkt + b2*SMB + b3*HML + e)")
    print("significance stars:  * p<.10  ** p<.05  *** p<.01")
    t3 = exposure_table(ds.excess, ds.factors, MODEL_3F)
    print(pretty_beta_table(t3, MODEL_3F).to_string())

    # ---- 5-factor model ------------------------------------------------
    print("\n" + "-" * 92)
    print("FAMA-FRENCH 5-FACTOR EXPOSURES   (adds RMW = profitability, CMA = investment)")
    t5 = exposure_table(ds.excess, ds.factors, MODEL_5F)
    print(pretty_beta_table(t5, MODEL_5F).to_string())

    # ---- SPY sanity check ----------------------------------------------
    spy = t5.loc[BENCHMARK]
    print("\nSPY sanity check (the benchmark should load ~1.0 on the market factor):")
    print(f"  beta_mkt = {spy['beta_Mkt-RF']:+.3f}   "
          f"alpha = {spy['alpha'] * 12 * 100:+.2f}%/yr   "
          f"R2 = {spy['R2']:.3f}")

    # ---- strongest exposures --------------------------------------------
    print("\nSTRONGEST EXPOSURES (5-factor model, lowest / highest 3):")
    for k in MODEL_5F:
        tb = top_bottom(t5, k)
        low = "  ".join(f"{ix} {v:+.2f}" for ix, v in tb.head(3).items())
        high = "  ".join(f"{ix} {v:+.2f}" for ix, v in tb.tail(3).items())
        print(f"  {k:6s} low : {low}")
        print(f"  {'':6s} high: {high}")

    # ---- does the 5-factor model add explanatory power? ------------------
    delta = t5["adj_R2"] - t3["adj_R2"]
    print("\nADJUSTED R2 GAIN FROM ADDING RMW + CMA (5F minus 3F, sorted):")
    print(delta.sort_values(ascending=False).round(4).to_string())

    # ---- persist ---------------------------------------------------------
    t3.to_csv(DATA_DIR / "exposures_3f.csv")
    t5.to_csv(DATA_DIR / "exposures_5f.csv")
    print("\n[done] exposure tables saved -> "
          "data/exposures_3f.csv, data/exposures_5f.csv (full t/p stats included)")


if __name__ == "__main__":
    main()
