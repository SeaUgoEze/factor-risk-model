"""
Application-layer configuration for the interactive Factor Risk Model.

This module is the single source of truth for *user-interface* defaults:
which tickers the app pre-selects, the default factor mandate, and the
risk settings the widgets start from.

Engine constants (analysis window, full universe, data paths) already
live in ``src.config`` - we import them rather than copy them. Rule of
thumb: if a value describes the DATA or the ENGINE, it belongs in
``src.config``; if it describes the USER INTERFACE, it belongs here.
"""

from src.config import UNIVERSE, START_DATE, END_DATE, OUTPUTS_DIR

# ----------------------------------------------------------------------
# Default stock selection
# ----------------------------------------------------------------------
# A curated, sector-diverse starter set drawn from the engine's 26-stock
# universe. The interface lets the user type any ticker (Step 2 fetches
# it via yfinance); these are just what the app opens on.
DEFAULT_TICKERS = [
    "AAPL", "MSFT",          # Technology
    "JPM",                   # Financials
    "XOM",                   # Energy
    "JNJ",                   # Health Care
    "PG",                    # Consumer Staples
    "AMZN",                  # Consumer Discretionary
    "META",                  # Communication Services
    "CAT", "BA",             # Industrials
]

# Short display names for the ticker picker (ticker -> company).  Custom
# tickers typed into the "Extra tickers" box fall back to the bare symbol.
TICKER_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA",
    "INTC": "Intel", "CSCO": "Cisco",
    "JPM": "JPMorgan", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "WFC": "Wells Fargo",
    "XOM": "ExxonMobil", "CVX": "Chevron",
    "JNJ": "Johnson & Johnson", "PFE": "Pfizer", "UNH": "UnitedHealth",
    "MRK": "Merck",
    "PG": "Procter & Gamble", "KO": "Coca-Cola", "WMT": "Walmart",
    "MCD": "McDonald's",
    "NKE": "Nike", "AMZN": "Amazon",
    "META": "Meta", "DIS": "Disney",
    "CAT": "Caterpillar", "BA": "Boeing", "GE": "GE",
    "SPY": "S&P 500 (benchmark)",
}

# ----------------------------------------------------------------------
# Factor model selection
# ----------------------------------------------------------------------
FACTOR_MODELS = ["3-factor", "5-factor"]
DEFAULT_FACTOR_MODEL = "5-factor"

# ----------------------------------------------------------------------
# Default factor mandate (target exposures)
# ----------------------------------------------------------------------
# Mirrors the Step-4 mandate: market 1.0, a strong value tilt (HML 1.0),
# and a moderate size tilt (SMB 0.5). The optimizer must hit these within
# the engine's tolerance. In 3-factor mode the app simply uses the first
# three keys. The interface sliders move within EXPOSURE_LIMITS.
TARGET_DEFAULTS = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0, "RMW": 0.0, "CMA": 0.0}
EXPOSURE_LIMITS = {"min": -1.0, "max": 2.0, "step": 0.1}

# ----------------------------------------------------------------------
# Constraints / risk settings
# ----------------------------------------------------------------------
# The engine's honest finding (Step 4): a long-only book cannot reach the
# mandate (HML caps out around 0.70). The app therefore opens with
# *limited shorts* enabled; the user can switch to long-only to reproduce
# the infeasibility result live.
ALLOW_SHORTS_DEFAULT = True
SHORT_FLOOR = -0.10          # -10% per-name floor on shorts

RISK_TOLERANCE_DEFAULT = 0.20   # annualized volatility target
RISK_TOLERANCE_RANGE = (0.05, 0.40)

# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------
REPORT_DIR = OUTPUTS_DIR / "reports"   # exported CSV / Excel / PDF reports
