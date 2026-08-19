"""
Step 4 - Factor-targeting portfolio optimization
==================================================
Run:  python scripts/step4_optimization.py

Builds a long-only (and a limited-shorts) portfolio that minimizes
variance subject to a target factor profile, prints the resulting
weights, achieved-vs-target exposures, and a risk decomposition.
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

# scipy's trust-constr emits benign warnings when constraint gradients are
# linearly dependent (our sum=1 and exposure constraints share the same
# columns); they don't affect the solution.
warnings.filterwarnings("ignore", category=UserWarning, module="scipy")

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
from src.analysis import plot_weights
from src.optimization import summarize, target_factor_portfolio


def main():
    print("=" * 92)
    print("STEP 4 - FACTOR-TARGETING PORTFOLIO OPTIMIZATION")
    print(f"window {START_DATE} -> {END_DATE} | "
          f"{len(UNIVERSE)} stocks | 5-factor model | SLSQP")
    print("=" * 92)

    tickers = list(UNIVERSE) + [BENCHMARK]
    prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
    ff5 = fetch_fama_french("5", START_DATE, END_DATE)
    monthly = to_monthly_returns(prices)
    ds = build_analysis_dataset(monthly, ff5)
    t5 = exposure_table(ds.excess, ds.factors, MODEL_5F)

    betas = t5[[f"beta_{k}" for k in MODEL_5F]].copy()
    betas.columns = MODEL_5F
    cov_f = ds.factors.cov()                         # factor covariance (Step 3)
    idio_var = t5["resid_sd"] ** 2                   # idiosyncratic variance

    TARGETS = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0, "RMW": 0.0, "CMA": 0.0}
    TOL = 0.10
    print("\nMANDATE (target factor profile, tolerance +/- %.2f):" % TOL)
    print(pd.Series(TARGETS).to_string())

    n = len(betas)
    ew = np.full(n, 1.0 / n)
    ew_sum = summarize(ew, betas, cov_f, idio_var)
    print("\nEQUAL-WEIGHT PORTFOLIO (the naive starting point):")
    print(ew_sum["exposures"].round(3).to_string())
    print(f"  total vol (ann.) = {ew_sum['total_vol_ann']:.2f}%  "
          f"(factor {ew_sum['factor_vol_ann']:.2f}% + idio {ew_sum['idio_vol_ann']:.2f}%)")

    print("\n" + "-" * 92)
    print("SCENARIO 1 - LONG-ONLY (w >= 0), minimize variance vs mandate")
    lo = target_factor_portfolio(betas, cov_f, idio_var, TARGETS, tolerance=TOL)
    print(f"  solver: {lo['method']}  success={lo['success']}  feasible={lo['feasible']}  "
          f"(iterations={lo['iterations']})")
    if not lo["feasible"]:
        print(f"  !! mandate NOT fully satisfiable long-only: "
              f"worst exposure gap {lo['max_gap']:.3f} > tol {TOL:.2f}")
    print("\n  TOP HOLDINGS:")
    top = lo["weights"].sort_values(ascending=False).head(10)
    for t, w in top.items():
        print(f"    {t:5s} {w * 100:6.2f}%")
    print(f"    ... remaining {n - len(top)} names share "
          f"{lo['weights'].sort_values(ascending=False).tail(n - len(top)).sum() * 100:.2f}%")

    print("\n  ACHIEVED vs TARGET EXPOSURES:")
    cmp = pd.DataFrame({"target": TARGETS,
                        "long-only": lo["exposures"],
                        "|gap|": (lo["exposures"] - pd.Series(TARGETS)).abs()})
    print(cmp.round(3).to_string())

    print(f"\n  portfolio vol (ann.) = {lo['total_vol_ann']:.2f}%   "
          f"factor {lo['factor_vol_ann']:.2f}% + idio {lo['idio_vol_ann']:.2f}%   "
          f"(factor share {lo['factor_share'] * 100:.1f}%)")

    print("\n" + "-" * 92)
    print("SCENARIO 2 - LIMITED SHORTS (w >= -0.10), same mandate")
    ls = target_factor_portfolio(betas, cov_f, idio_var, TARGETS,
                                 tolerance=TOL, allow_shorts=True)
    print(f"  solver: {ls['method']}  success={ls['success']}  feasible={ls['feasible']}  "
          f"(iterations={ls['iterations']})")
    print("\n  ACHIEVED vs TARGET EXPOSURES:")
    cmp2 = pd.DataFrame({"target": TARGETS,
                         "long-only": lo["exposures"],
                         "shorts": ls["exposures"]})
    print(cmp2.round(3).to_string())
    print(f"\n  portfolio vol (ann.) = {ls['total_vol_ann']:.2f}%   "
          f"(long-only was {lo['total_vol_ann']:.2f}%)")

    # Chart the FEASIBLE solution (limited shorts) - the one that meets the
    # mandate; the long-only effort is discussed in the text output.
    plot_weights(ls["weights"], FIGURES_DIR / "portfolio_weights.png",
                 title="Optimal weights - limited shorts (floor -10%) - value + size tilt")
    lo["weights"].to_csv(DATA_DIR / "portfolio_weights_longonly.csv")
    ls["weights"].to_csv(DATA_DIR / "portfolio_weights_shorts.csv")
    pd.DataFrame({"target": TARGETS,
                  "long_only": lo["exposures"],
                  "limited_shorts": ls["exposures"]}).to_csv(
        DATA_DIR / "optimization_summary.csv")
    print("\n[done] weights + summary saved under data/; "
          "portfolio_weights.png under figures/")


if __name__ == "__main__":
    main()
