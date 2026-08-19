"""
Step 5 - Performance & risk analysis
======================================
Takes the Step-4 optimal portfolio into performance and risk analysis.
Everything is computed on the same monthly window (2015-2019) used to
build the model, and compared against the two natural references:

  * SPY          - the market benchmark (what a passive investor earns)
  * equal weight - the naive 26-stock portfolio (no optimization)

Metrics produced:

  * annualized return, annualized volatility, Sharpe ratio
  * maximum drawdown and the full drawdown path
  * Value at Risk (historical + normal) and Expected Shortfall (CVaR)
  * factor attribution - a regression of portfolio returns on the five
    Fama-French factors

Two conventions worth knowing:

  * Annualization: monthly returns are raised to the 12th power
    geometrically (compound), volatility is scaled by sqrt(12).  This is
    the standard convention in performance reporting.
  * VaR sign: VaR is reported as a *positive* loss number.  A "95% VaR
    of 6.2%" means "with 95% confidence, the worst month loses no more
    than 6.2%"; the other 5% of months can be worse.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")          # headless-safe backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from matplotlib.patches import Patch

from src.analysis import (GP_DIVERGING, GP_DIVERGING_SEMANTIC,
                          _recolor_annotations, _recolor_annotations_sign,
                          SIGN_BLUE, SIGN_RED, AMBER, POS, _semantic,
                          apply_style)
from src.config import FIGURES_DIR
from src.regressions import MODEL_5F

# Monochrome palette: gray ramp, red reserved for downside.
ACCENT = "#F8F8F8"
NEG = "#E5484D"
YELLOW = "#B4B4B4"


# ----------------------------------------------------------------------
# Core performance metrics
# ----------------------------------------------------------------------
def annualized_return(monthly_returns):
    """Geometric annualized return: (prod(1+r))^(12/n) - 1.

    Geometric compounding respects the order of returns (a +50% then
    -33% pair nets zero, which arithmetic means would misreport).
    """
    growth = (1.0 + monthly_returns).prod()
    n = len(monthly_returns)
    return float(growth ** (12.0 / n) - 1.0)


def annualized_vol(monthly_returns):
    """Annualized volatility = monthly std * sqrt(12)."""
    return float(monthly_returns.std(ddof=1) * np.sqrt(12))


def sharpe_ratio(monthly_returns, rf_series):
    """Sharpe = (annualized return - annualized risk-free) / annualized vol.

    The risk-free series is monthly (from Ken French's data); we take its
    mean and annualize it the same way as the return.
    """
    rf_ann = float(rf_series.mean() * 12)
    vol = annualized_vol(monthly_returns)
    if vol == 0:
        return float("nan")
    return (annualized_return(monthly_returns) - rf_ann) / vol


def drawdown_series(monthly_returns):
    """Drawdown path: (cumulative wealth / running peak) - 1.

    A value of -0.15 at date t means the portfolio is 15% below its best
    prior level.  The minimum of this series is the max drawdown.
    """
    wealth = (1.0 + monthly_returns).cumprod()
    peak = wealth.cummax()
    return wealth / peak - 1.0


def max_drawdown(monthly_returns):
    """Deepest peak-to-trough decline, reported as a positive number."""
    return float(-drawdown_series(monthly_returns).min())


def historical_var(monthly_returns, alpha=0.05):
    """Historical Value at Risk at confidence (1 - alpha).

    The alpha-quantile of the return distribution is the worst month we
    would expect to see with probability alpha; reported as a loss.
    """
    return float(-np.quantile(monthly_returns, alpha))


def normal_var(monthly_returns, alpha=0.05):
    """Parametric VaR assuming normally distributed returns.

    VaR = -(mean + z_alpha * std).  Comparing it to the historical VaR
    shows how fat the left tail of the actual return distribution is.
    """
    from scipy import stats as sp_stats

    z = sp_stats.norm.ppf(alpha)
    mu = float(monthly_returns.mean())
    sigma = float(monthly_returns.std(ddof=1))
    return float(-(mu + z * sigma))


def expected_shortfall(monthly_returns, alpha=0.05):
    """Expected Shortfall / CVaR: average return in the worst alpha tail.

    Where VaR says "the worst month is at least X% bad", CVaR says "when
    it IS that bad, the average loss is Y%".  Captures tail severity,
    not just the boundary.
    """
    q = np.quantile(monthly_returns, alpha)
    tail = monthly_returns[monthly_returns <= q]
    return float(-tail.mean())


def performance_summary(returns, rf_series):
    """One row of headline metrics per return series (as a DataFrame).

    Parameters
    ----------
    returns  : DataFrame of monthly returns (one column per portfolio)
    rf_series: monthly risk-free rate aligned on the same index
    """
    rows = {}
    for col in returns.columns:
        r = returns[col].dropna()
        rows[col] = {
            "ann_return_%": annualized_return(r) * 100,
            "ann_vol_%": annualized_vol(r) * 100,
            "sharpe": sharpe_ratio(r, rf_series),
            "max_drawdown_%": max_drawdown(r) * 100,
            "var95_hist_%": historical_var(r) * 100,
            "cvar95_%": expected_shortfall(r) * 100,
        }
    return pd.DataFrame(rows).T


# ----------------------------------------------------------------------
# Factor attribution
# ----------------------------------------------------------------------
def factor_attribution(portfolio_excess, factors, factor_cols=None):
    """Decompose a portfolio's excess return into factor contributions.

    Step 1: regress portfolio excess returns on the five factors:
        r_p - rf  =  alpha + sum_k beta_k * F_k + eps

    Step 2: each factor's *annualized contribution* is
        beta_k * annualized mean of F_k
    and alpha's contribution is the (annualized) intercept.  The five
    contributions plus alpha sum to the portfolio's annualized excess
    return (up to rounding) - that is the attribution identity.

    Returns a dict with betas, alpha, R2 and a contributions Series.
    """
    factor_cols = factor_cols or MODEL_5F
    design = sm.add_constant(factors[factor_cols])
    fit = sm.OLS(portfolio_excess, design).fit()

    alpha_monthly = float(fit.params["const"])
    betas = fit.params[factor_cols]

    # Annualized factor premia observed in the window
    premium = factors[factor_cols].mean() * 12

    contributions = pd.Series(
        betas * premium, index=factor_cols, name="ann_contribution_%"
    )
    alpha_ann = alpha_monthly * 12
    resid = pd.Series(fit.resid, index=portfolio_excess.index)
    unexplained_ann = float(resid.mean()) * 12

    return {
        "betas": betas,
        "alpha_ann": alpha_ann,
        "R2": float(fit.rsquared),
        "resid_sd": float(np.sqrt(fit.mse_resid)),
        "contributions": contributions,
        "unexplained_ann": unexplained_ann,
        "fit": fit,
    }


# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------
def plot_cumulative_returns(growth, path=None,
                            title="Cumulative growth - optimal vs benchmark",
                            mode: str = "mono"):
    """Growth-of-a-dollar lines for each return series."""
    apply_style()
    if _semantic(mode):
        palette = {"Optimal": ACCENT, "SPY": POS, "Equal weight": AMBER}
    else:
        palette = {"Optimal": ACCENT, "SPY": YELLOW, "Equal weight": "#626262"}
    fig, ax = plt.subplots(figsize=(9, 5.4))
    for col in growth.columns:
        color = palette.get(col, "#626262")
        ax.plot(growth.index, growth[col], label=col, color=color, lw=2)
    ax.set_ylabel("growth of $1")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.grid(True, alpha=0.35)

    if path is None:
        path = FIGURES_DIR / "cumulative_returns.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[risk] saved {path.name}")
    return path


def plot_drawdowns(returns, path=None, title="Drawdowns - optimal vs benchmark",
                   mode: str = "mono"):
    """Drawdown paths: how deep underwater each strategy got.

    Accepts the returns frame and computes drawdowns internally via
    drawdown_series.  In semantic mode the optimal portfolio's underwater
    region is tinted with the downside red.
    """
    apply_style()
    if _semantic(mode):
        palette = {"Optimal": ACCENT, "SPY": POS, "Equal weight": AMBER}
    else:
        palette = {"Optimal": ACCENT, "SPY": YELLOW, "Equal weight": "#626262"}
    dd = returns.apply(drawdown_series)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for col in dd.columns:
        color = palette.get(col, "#626262")
        ax.plot(dd.index, dd[col] * 100, label=col, color=color, lw=1.8)
        if _semantic(mode) and col == "Optimal":
            ax.fill_between(dd.index, dd[col] * 100, 0, color=NEG, alpha=0.07)
    ax.set_ylabel("drawdown (%)")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.grid(True, alpha=0.35)

    if path is None:
        path = FIGURES_DIR / "drawdowns.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[risk] saved {path.name}")
    return path


def plot_attribution(contributions, alpha_ann, path=None,
                     title="Factor attribution - what drives portfolio returns",
                     mode: str = "mono"):
    """Horizontal bar of annualized contributions (factors + alpha)."""
    apply_style()
    items = contributions.copy()
    items["alpha"] = alpha_ann
    items = items.sort_values()

    colors = [NEG if v < 0 else (POS if _semantic(mode) else ACCENT)
              for v in items.values]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(items.index, items.values, color=colors, height=0.62)
    ax.axvline(0, color="#3A3A42", lw=0.8)
    ax.set_xlabel("annualized contribution to excess return (%)")
    ax.set_title(title)
    fig.tight_layout()

    if path is None:
        path = FIGURES_DIR / "factor_attribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[risk] saved {path.name}")
    return path


def plot_holdings_corr(corr, path=None,
                       title="Portfolio holdings - return correlations",
                       mode: str = "mono"):
    """Correlation heatmap of the largest holdings (luminance-aware text)."""
    apply_style()
    cmap = GP_DIVERGING_SEMANTIC if _semantic(mode) else GP_DIVERGING
    norm = plt.Normalize(-1, 1)

    fig, ax = plt.subplots(figsize=(9.5, 8))
    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap=cmap, center=0,
        vmin=-1, vmax=1, linewidths=0.5, linecolor="#282830",
        cbar_kws={"label": "correlation"}, square=True, ax=ax,
    )
    ax.set_title(title)
    if _semantic(mode):
        _recolor_annotations(ax, corr.values, cmap, norm)
    else:
        _recolor_annotations_sign(ax, corr.values, cmap, norm)
        ax.legend(
            handles=[Patch(color=SIGN_BLUE, label="positive"),
                     Patch(color=SIGN_RED, label="negative")],
            loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2,
            frameon=False, fontsize=8, handlelength=0.9, columnspacing=1.2)

    if path is None:
        path = FIGURES_DIR / "holdings_correlation.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[risk] saved {path.name}")
    return path
