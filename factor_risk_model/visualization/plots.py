"""Charts for the interactive app - one consistent dark theme.

The engine already owns the heavyweight figures (exposure heatmap,
weights, cumulative returns, drawdowns, attribution, holdings
correlation - all in ``src.analysis`` / ``src.risk``); this module adds
the charts that are *new* in the interactive version:

* beta confidence-interval whiskers,
* rolling exposure paths,
* stress-scenario impact bars,
* the windowed anomaly two-panel.

Every function takes an explicit ``path`` and returns it, so the
interactive app can ``st.image(path)`` and the CLI/PDF can reuse the same
PNGs.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis import AMBER, POS, _semantic, apply_style

ACCENT = "#F8F8F8"
NEG = "#E5484D"
YELLOW = "#B4B4B4"
GRAY = "#8A8A92"

FACTOR_COLORS = {"Mkt-RF": ACCENT, "SMB": "#B4B4B4", "HML": "#8A8A92",
                 "RMW": "#626262", "CMA": "#4E4E56"}


def plot_exposure_ci(betas: pd.Series, ci_lo: pd.Series, ci_hi: pd.Series,
                     path: Path, title: str = "Factor exposure (95% CI)",
                     mode: str = "mono"):
    """Horizontal bars of a single ticker's betas with CI whiskers.

    A wide whisker means the 59-month sample cannot pin the loading down
    - the honest visual companion to the exposure table.
    """
    apply_style()
    idx = list(betas.index)
    vals = betas.values
    lo = (vals - ci_lo.values)          # whisker lengths (asymmetric OK)
    hi = (ci_hi.values - vals)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ypos = np.arange(len(idx))
    colors = [(POS if _semantic(mode) else ACCENT) if v >= 0 else NEG
              for v in vals]
    ax.barh(ypos, vals, height=0.55, color=colors, alpha=0.85)
    ax.errorbar(vals, ypos, xerr=[lo, hi], fmt="none", ecolor="#B4B4B4",
                elinewidth=1.2, capsize=3)
    ax.axvline(0, color="#3A3A42", lw=0.8)
    ax.set_yticks(ypos, idx)
    ax.set_xlabel("factor loading (beta)")
    ax.set_title(title)
    ax.grid(True, axis="x", alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_rolling_exposures(paths: dict[str, pd.DataFrame], ticker: str,
                           path: Path):
    """One line per factor: how the ticker's betas drifted over time."""
    apply_style()
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for k, frame in paths.items():
        if ticker not in frame.columns:
            continue
        ax.plot(frame.index, frame[ticker], marker="o", markersize=3,
                lw=1.6, color=FACTOR_COLORS.get(k, GRAY), label=k)
    ax.set_ylabel("beta")
    ax.set_title(f"Rolling factor exposures - {ticker} "
                 f"({len(next(iter(paths.values()))) if paths else 0} windows)")
    ax.legend(frameon=False, fontsize=9, ncol=len(paths))
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_stress(stress: pd.DataFrame, path: Path, mode: str = "mono"):
    """Horizontal bars: one-month portfolio impact per scenario vs SPY."""
    apply_style()
    df = stress.sort_values("portfolio_%")
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ypos = np.arange(len(df))
    colors = [NEG if v < 0 else (POS if _semantic(mode) else ACCENT)
              for v in df["portfolio_%"] ]
    ax.barh(ypos, df["portfolio_%"], height=0.55, color=colors, alpha=0.85)
    # SPY dots are amber in semantic mode (green bars encode portfolio
    # sign, so the benchmark keeps a hue of its own).
    spy_col = AMBER if _semantic(mode) else YELLOW
    ax.scatter(df["spy_%"], ypos, color=spy_col, s=26, zorder=3,
               label="SPY impact")
    ax.axvline(0, color="#3A3A42", lw=0.8)
    ax.set_yticks(ypos, df.index)
    ax.set_xlabel("one-month portfolio return under scenario (%)")
    ax.set_title("Stress test - stylized one-month factor shocks")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.grid(True, axis="x", alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_windowed_anomaly(result, portfolio_daily: pd.Series, path: Path):
    """Two panels: daily returns with flagged windows shaded, and the
    reconstruction-error series against the threshold."""
    apply_style()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1.4]})

    ax1.plot(portfolio_daily.index, portfolio_daily.values * 100,
             color=GRAY, lw=0.9)
    for d in result.window_end_dates[result.flags]:
        ax1.axvspan(d - pd.Timedelta(days=9), d, color=NEG, alpha=0.18,
                    lw=0)
    ax1.set_ylabel("daily return (%)")
    ax1.set_title("Portfolio daily returns - shaded windows are anomalous")

    ax2.plot(result.window_end_dates, result.errors, color=ACCENT, lw=1.0)
    ax2.axhline(result.threshold, color=NEG, lw=1.2, ls="--",
                label=f"threshold (p{95:.0f}) = {result.threshold:.3f}")
    ax2.set_ylabel("reconstruction error")
    ax2.legend(frameon=False, fontsize=9)
    ax2.set_xlabel("date")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
