"""
Step 5 - Performance & risk analysis
=====================================
Run:  python scripts/step5_performance.py

Loads the Step-4 optimal portfolio (limited-shorts solution), builds its
monthly return stream from the aligned dataset, and benchmarks it against
SPY and the equal-weight universe:

  * performance summary (return / vol / Sharpe / max drawdown / VaR / CVaR)
  * cumulative growth + drawdown charts
  * factor attribution of the portfolio's returns
  * correlation heatmap of the largest holdings

Saves figures under figures/ and tables under outputs/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 80)

from src.config import (START_DATE, END_DATE, UNIVERSE, BENCHMARK,
                        DATA_DIR, FIGURES_DIR, OUTPUTS_DIR)
from src.data import (build_analysis_dataset, fetch_daily_prices,
                      fetch_fama_french, to_monthly_returns)
from src.regressions import MODEL_5F, exposure_table
from src.risk import (annualized_return, expected_shortfall, factor_attribution,
                      historical_var, normal_var, performance_summary,
                      plot_attribution, plot_cumulative_returns, plot_drawdowns,
                      plot_holdings_corr)


def main():
    print("=" * 92)
    print("STEP 5 - PERFORMANCE & RISK ANALYSIS")
    print(f"window {START_DATE} -> {END_DATE} | "
          f"{len(UNIVERSE)} stocks | optimal portfolio from Step 4")
    print("=" * 92)

    tickers = list(UNIVERSE) + [BENCHMARK]
    prices = fetch_daily_prices(tickers, START_DATE, END_DATE)
    ff5 = fetch_fama_french("5", START_DATE, END_DATE)
    monthly = to_monthly_returns(prices)
    ds = build_analysis_dataset(monthly, ff5)

    weights_path = DATA_DIR / "portfolio_weights_shorts.csv"
    if not weights_path.exists():
        raise SystemExit(f"[step5] missing {weights_path} - run step4 first.")
    stocks = [c for c in ds.returns.columns if c in UNIVERSE]
    # Optimal: w' R  (weights are per-stock; a missing ticker would be 0)
    w_opt = pd.read_csv(weights_path, index_col=0).iloc[:, 0]
    w_opt = w_opt.reindex(stocks).fillna(0.0)
    r_opt = ds.returns[stocks].dot(w_opt)

    # Equal weight: 1/n across the whole universe (the "no optimization" state)
    w_ew = pd.Series(1.0 / len(stocks), index=stocks)
    r_ew = ds.returns[stocks].dot(w_ew)

    # Benchmark: raw SPY column
    r_spy = ds.returns[BENCHMARK]

    perf = pd.DataFrame({
        "Optimal": r_opt,
        "SPY": r_spy,
        "Equal weight": r_ew,
    })
    rf = ds.rf

    print("\n1) PERFORMANCE SUMMARY (monthly, 2015-2019):")
    table = performance_summary(perf, rf)
    print(table.round(2).to_string())

    print("\n2) TAIL RISK - OPTIMAL PORTFOLIO (monthly, 95% confidence):")
    print(f"  historical VaR = {historical_var(r_opt) * 100:.2f}%   "
          f"(worst month expected 5% of the time)")
    print(f"  normal VaR     = {normal_var(r_opt) * 100:.2f}%   "
          f"(parametric, assumes Gaussian)")
    print(f"  CVaR / ES      = {expected_shortfall(r_opt) * 100:.2f}%   "
          f"(average loss once VaR is breached)")
    print(f"  worst month    = {r_opt.min() * 100:.2f}% "
          f"({r_opt.idxmin():%b %Y})")
    print("  The empirical distribution is not Gaussian: historical VaR sits")
    print("  below the normal-VaR boundary, while CVaR (the average loss once")
    print("  VaR is breached) captures the severity of the tail beyond it.")

    print("\n3) FACTOR ATTRIBUTION (what drives the optimal portfolio's returns):")
    attr = factor_attribution(r_opt - rf, ds.factors)
    contrib = attr["contributions"] * 100
    print(f"  model R2 = {attr['R2']:.3f}  (share of portfolio variance "
          f"explained by factors)")
    print("\n  annualized contributions (%):")
    items = contrib.copy()
    items["alpha"] = attr["alpha_ann"] * 100
    print(items.round(2).to_string())
    total = items.sum()
    # Attribution identity: sum(factor contributions) + alpha + unexplained
    # = annualized *arithmetic* mean excess return (mean of (r - rf) * 12).
    # The geometric (compounded) number is lower when returns are volatile.
    ann_arith = float((r_opt - rf).mean()) * 12 * 100
    ann_geom = (annualized_return(r_opt) - float(rf.mean()) * 12) * 100
    print(f"\n  sum of contributions + alpha = {total:.2f}%")
    print(f"  annualized excess return: arithmetic = {ann_arith:.2f}%  "
          f"|  geometric (compounded) = {ann_geom:.2f}%")

    top = w_opt.reindex(stocks).abs().sort_values(ascending=False).head(12)
    hold_corr = ds.returns[top.index].corr()
    print(f"\n4) HOLDINGS CORRELATION: {len(top)} largest weights by |w|")

    growth = (1.0 + perf).cumprod()
    plot_cumulative_returns(growth, FIGURES_DIR / "cumulative_returns.png",
                            title="Cumulative growth - optimal vs benchmark "
                                  "(2015-2019, monthly)")
    plot_drawdowns(perf, FIGURES_DIR / "drawdowns.png",
                   title="Drawdowns - optimal vs benchmark (2015-2019)")
    plot_attribution(attr["contributions"], attr["alpha_ann"],
                     FIGURES_DIR / "factor_attribution.png")
    plot_holdings_corr(hold_corr, FIGURES_DIR / "holdings_correlation.png")

    table.round(4).to_csv(OUTPUTS_DIR / "performance_summary.csv")
    contrib_out = attr["contributions"].round(4).to_frame("ann_contribution")
    contrib_out.loc["alpha"] = round(attr["alpha_ann"], 4)
    contrib_out.to_csv(OUTPUTS_DIR / "factor_contributions.csv")
    r_opt.round(6).to_csv(OUTPUTS_DIR / "optimal_portfolio_returns.csv")
    print("\n[done] figures under figures/ ; tables under outputs/")


if __name__ == "__main__":
    main()
