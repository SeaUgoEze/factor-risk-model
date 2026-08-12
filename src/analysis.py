"""
Step 3 - Factor analysis & visualization
==========================================
Turns the Step-2 exposure table into understanding:

  1. A heatmap of every stock's five betas, rows grouped by sector,
     tickers colored by sector (Blue = positive loading, red = negative).
  2. The factor covariance & correlation matrices - the answer to
     "how do these five risk sources move together?"
  3. A plain-English "factor profile" for every stock.

Why the covariance matrix matters: a portfolio's factor-risk is

    Risk(portfolio) ~ w' * B' * V_f * B * w + idiosyncratic terms,

so the factor covariance V_f is the engine room of Step 4's optimizer.
Correlated factors (e.g. value vs. profitability) mean you cannot treat
each factor bet as an independent risk bet.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")          # headless-safe backend (no GUI needed)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

from src.config import FIGURES_DIR

# Grayscale diverging ramp for heatmaps - dark gray at the negative
# extreme, mid gray at zero, light gray at the positive extreme, so the
# whole chart family stays monochrome like the reference palette.  The
# three stops sit far apart in luminance (near-black / mid / near-white)
# so positive, neutral and negative loadings read as three distinct
# bands instead of one muddy gradient.  The mid stop is deliberately
# dark so the sign-coloured annotations keep contrast across the widest
# possible range of cell values.
GP_DIVERGING = LinearSegmentedColormap.from_list(
    "gp_diverging", ["#1E1E26", "#4E4E57", "#F1F1F1"])

# Semantic diverging ramp - muted red at the negative extreme, neutral
# gray at zero, muted deep green at the positive extreme.  The hues stay
# inside the app's family (the same red already reserved for downside);
# deliberately no blue anywhere.
GP_DIVERGING_SEMANTIC = LinearSegmentedColormap.from_list(
    "gp_diverging_semantic", ["#B23B3B", "#3A3A42", "#1F8A4C"])

# Monochrome palette (flat near-black canvas, gray ramp; red only for
# downside so losses stay readable in an otherwise grayscale system)
ACCENT = "#F8F8F8"
NEG = "#E5484D"
# Semantic palette - muted deep green for gains / positive loadings,
# muted amber for a third comparison series.  Both are dark-canvas safe
# and sit comfortably next to the existing downside red.
POS = "#2EA043"
AMBER = "#D29922"
# Red/blue sign annotation on the monochrome heatmaps: negative loadings
# print in red, positive in blue - the classic convention, and the one
# the module docstring has always promised.  Each sign gets a bright
# variant for dark cells and a deep variant for light cells, and a
# contrast floor keeps every number readable.  This blue is the single
# deliberate exception to the otherwise no-blue palette, added on request
# as a sign annotation for the heatmap only.
SIGN_RED = "#FF6A70"   # bright red - light enough to hold contrast on mid grays
SIGN_RED_DARK = "#A62F33"
SIGN_BLUE = "#86B7EA"
SIGN_BLUE_DARK = "#1E5FA8"
SECTOR_COLORS = [
    "#F8F8F8", "#B4B4B4", "#8A8A92", "#626262", "#4E4E56",
    "#C9C9CF", "#9A9AA2", "#71717A", "#3A3A42",
]


def _semantic(mode: str) -> bool:
    """True when charts should use the semantic colour treatment."""
    return mode == "semantic"


def apply_style():
    """Flat monochrome chart theme consistent with the dashboard."""
    plt.rcParams.update({
        "figure.facecolor": "#101018",
        "axes.facecolor": "#181820",
        "axes.edgecolor": "#282830",
        "axes.labelcolor": "#F8F8F8",
        "text.color": "#F8F8F8",
        "xtick.color": "#8A8A92",
        "ytick.color": "#8A8A92",
        "grid.color": "#282830",
        "grid.alpha": 0.5,
        "axes.grid": True,
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
    })


# ----------------------------------------------------------------------
# Covariance / correlation
# ----------------------------------------------------------------------
def factor_covariance(factors):
    """Monthly covariance & correlation matrices + annualized factor vol.

    Returns (cov, corr, vol_annualized_pct).
    """
    cov = factors.cov()                                   # monthly, decimal
    corr = factors.corr()
    vol_ann = factors.std() * np.sqrt(12) * 100           # % annualized
    return cov, corr, vol_ann


# ----------------------------------------------------------------------
# Heatmaps
# ----------------------------------------------------------------------
def _recolor_annotations(ax, values, cmap, norm):
    """Set per-cell annotation color from background luminance (readable on dark)."""
    values = np.asarray(values)
    # seaborn creates one text per cell in row-major data order; fail loudly
    # if that contract ever changes.
    assert len(ax.texts) == values.size, "annotation/data cell count mismatch"
    for txt, v in zip(ax.texts, values.ravel()):
        r, g, b, _ = cmap(norm(v))
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        txt.set_color("#0d0d0d" if lum > 0.5 else "#f2f2f2")


def _hex_lum(hex_color: str) -> float:
    """Luminance of a hex color, same raw 0-1 weights as the rest of this file."""
    raw = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return 0.299 * raw[0] + 0.587 * raw[1] + 0.114 * raw[2]


def _contrast(l1: float, l2: float) -> float:
    """WCAG-style contrast ratio between two luminance values."""
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _recolor_annotations_sign(ax, values, cmap, norm, threshold: float = 0.1):
    """Red/blue sign annotation for the monochrome heatmaps.

    Negative loadings print in red, positive in blue.  Each sign has a
    bright variant for dark cells and a deep variant for light cells;
    whichever reads better on the cell's background wins, and anything
    that would fall below a readable contrast floor (e.g. values hugging
    the neutral mid band, whose sign matters least) stays in the neutral
    luminance-aware shade instead.  Only used in monochrome mode -
    semantic mode already encodes sign in the cell fill.
    """
    values = np.asarray(values)
    assert len(ax.texts) == values.size, "annotation/data cell count mismatch"
    for txt, v in zip(ax.texts, values.ravel()):
        r, g, b, _ = cmap(norm(v))
        cell = 0.299 * r + 0.587 * g + 0.114 * b
        neutral = "#0d0d0d" if cell > 0.5 else "#f2f2f2"
        if abs(v) < threshold:
            txt.set_color(neutral)
            continue
        bright, deep = ((SIGN_RED, SIGN_RED_DARK) if v < 0
                        else (SIGN_BLUE, SIGN_BLUE_DARK))
        cb = _contrast(_hex_lum(bright), cell)
        cd = _contrast(_hex_lum(deep), cell)
        txt.set_color(bright if cb >= cd else deep)
        if max(cb, cd) < 1.2:
            txt.set_color(neutral)

def exposure_heatmap(exposures, factor_cols, sector_map, path=None,
                     mode: str = "mono"):
    """Heatmap of 5-factor betas, rows grouped by sector.

    Rows are tickers; tick labels are colored by sector; a legend maps
    the sector colors.  Symmetric diverging scale so a -1.8 and +1.8
    loading are visually comparable.  ``mode`` = "mono" (grayscale
    ramp) or "semantic" (red/green diverging ramp).
    """
    apply_style()
    tbl = exposures[[f"beta_{k}" for k in factor_cols]].copy()
    tbl.columns = factor_cols

    sectors = list(dict.fromkeys(sector_map.values()))
    if "Benchmark" not in sectors:   # SPY (absent from the map) groups here
        sectors.append("Benchmark")
    order = sorted(
        tbl.index,
        key=lambda t: (sectors.index(sector_map.get(t, "Benchmark")), t),
    )
    tbl = tbl.loc[order]

    # Cycle the palette so ANY number of sectors (e.g. the app's 'Other'
    # bucket for custom tickers) always gets a color - never truncate.
    colors = {s: SECTOR_COLORS[i % len(SECTOR_COLORS)]
              for i, s in enumerate(sectors)}
    label_colors = [colors[sector_map.get(t, "Benchmark")] for t in order]

    vmax = float(max(abs(tbl.values.min()), abs(tbl.values.max())))
    cmap = GP_DIVERGING_SEMANTIC if _semantic(mode) else GP_DIVERGING
    norm = plt.Normalize(-vmax, vmax)

    fig, ax = plt.subplots(figsize=(9.5, 11))
    sns.heatmap(
        tbl, annot=True, fmt=".2f", cmap=cmap, center=0,
        vmin=-vmax, vmax=vmax, linewidths=0.5, linecolor="#282830",
        cbar_kws={"label": "factor loading (beta)"}, ax=ax,
    )
    ax.set_yticklabels(list(tbl.index), rotation=0)
    for lab, col in zip(ax.get_yticklabels(), label_colors):
        lab.set_color(col)
    ax.set_title("Factor exposures - 5-factor model (2015-2019, monthly)")
    if _semantic(mode):
        _recolor_annotations(ax, tbl.values, cmap, norm)
    else:
        _recolor_annotations_sign(ax, tbl.values, cmap, norm)

    # Legend BELOW the plot (horizontal) so it never overlaps the heatmap
    # or the colorbar on the right.  In monochrome mode the sign legend
    # sits under the sector legend, keyed to the red/blue annotations.
    handles = [Patch(color=c, label=s) for s, c in colors.items()]
    leg = ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.05),
                    ncol=5, frameon=False, fontsize=8, title="sector",
                    title_fontsize=8, columnspacing=1.4)
    if not _semantic(mode):
        ax.add_artist(leg)
        ax.legend(
            handles=[Patch(color=SIGN_BLUE, label="positive loading"),
                     Patch(color=SIGN_RED, label="negative loading")],
            loc="upper center", bbox_to_anchor=(0.5, -0.125), ncol=2,
            frameon=False, fontsize=8, handlelength=0.9, columnspacing=1.2)

    if path is None:
        path = FIGURES_DIR / "factor_exposures_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[analysis] saved {path.name}")
    return path


def plot_weights(weights, path=None, title="Optimal portfolio weights",
                 mode: str = "mono"):
    """Horizontal bar chart of portfolio weights (top names + 'other' lump).

    Positive weights in the accent gray (deep green in semantic mode),
    shorts (if any) in the muted downside red.
    """
    apply_style()
    w = weights.sort_values(ascending=False)
    keep = w.abs().nlargest(12)
    rest = w.drop(keep.index)
    if len(rest):
        w2 = pd.concat([keep, pd.Series({"other (%d names)" % len(rest): rest.sum()})])
    else:
        w2 = keep
    w2 = w2.sort_values()

    colors = [NEG if v < 0 else (POS if _semantic(mode) else ACCENT)
              for v in w2.values]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.barh(w2.index, w2.values * 100, color=colors, height=0.6)
    ax.axvline(0, color="#3A3A42", lw=0.8)
    ax.set_xlabel("portfolio weight (%)")
    ax.set_title(title)
    fig.tight_layout()

    if path is None:
        path = FIGURES_DIR / "portfolio_weights.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[analysis] saved {path.name}")
    return path


def correlation_heatmap(corr, path=None, mode: str = "mono"):
    """Factor correlation matrix, annotated with luminance-aware text."""
    apply_style()
    cmap = GP_DIVERGING_SEMANTIC if _semantic(mode) else GP_DIVERGING
    norm = plt.Normalize(-1, 1)

    fig, ax = plt.subplots(figsize=(7.5, 6.4))
    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap=cmap, center=0,
        vmin=-1, vmax=1, linewidths=0.6, linecolor="#282830",
        cbar_kws={"label": "correlation"}, square=True, ax=ax,
    )
    ax.set_title("Fama-French factor correlations (2015-2019, monthly)")
    if _semantic(mode):
        _recolor_annotations(ax, corr.values, cmap, norm)
    else:
        _recolor_annotations_sign(ax, corr.values, cmap, norm)
        ax.legend(
            handles=[Patch(color=SIGN_BLUE, label="positive"),
                     Patch(color=SIGN_RED, label="negative")],
            loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2,
            frameon=False, fontsize=8, handlelength=0.9, columnspacing=1.2)

    if path is None:
        path = FIGURES_DIR / "factor_correlation_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[analysis] saved {path.name}")
    return path


# ----------------------------------------------------------------------
# Plain-English profiles
# ----------------------------------------------------------------------
def plain_english_profile(row):
    """One human-readable sentence describing a stock's factor fingerprint.

    Thresholds are deliberately simple (|beta| > 0.5 = meaningful);
    the idea is interpretability, not statistical exactness.
    """
    tags = []
    bm = row["beta_Mkt-RF"]
    tags.append("high market beta" if bm > 1.3
                else "defensive (low market beta)" if bm < 0.7
                else "market beta")
    if row["beta_SMB"] < -0.5:
        tags.append("mega-cap")
    elif row["beta_SMB"] > 0.3:
        tags.append("small-cap-like")
    if row["beta_HML"] > 0.5:
        tags.append("value")
    elif row["beta_HML"] < -0.5:
        tags.append("growth")
    if row["beta_RMW"] > 0.5:
        tags.append("profitability-driven")
    elif row["beta_RMW"] < -0.5:
        tags.append("margin-sensitive")
    if row["beta_CMA"] > 0.5:
        tags.append("conservative investor")
    elif row["beta_CMA"] < -0.5:
        tags.append("aggressive investor")
    return ", ".join(tags) if tags else "balanced"
