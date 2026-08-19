"""
Application-layer configuration for the interactive Factor Risk Model.

User-interface defaults: pre-selected tickers, default factor mandate,
and widget start values.  Engine constants (window, universe, paths)
live in ``src.config`` and are imported rather than copied.
"""

from src.config import UNIVERSE, START_DATE, END_DATE, OUTPUTS_DIR

# ----------------------------------------------------------------------
# Default stock selection
# ----------------------------------------------------------------------
# Curated, sector-diverse starter set; users can add any ticker.
DEFAULT_TICKERS = [
    "AAPL", "MSFT",
    "JPM",
    "XOM",
    "JNJ",
    "PG",
    "AMZN",
    "META",
    "CAT", "BA",
]

# Display names for the ticker picker (ticker -> company).  Unknown
# tickers fall back to the bare symbol.
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
# Default mandate: market 1.0, HML 1.0, SMB 0.5.  3-factor mode uses the
# first three keys.  Sliders move within EXPOSURE_LIMITS.
TARGET_DEFAULTS = {"Mkt-RF": 1.0, "SMB": 0.5, "HML": 1.0, "RMW": 0.0, "CMA": 0.0}
EXPOSURE_LIMITS = {"min": -1.0, "max": 2.0, "step": 0.1}

# ----------------------------------------------------------------------
# Constraints / risk settings
# ----------------------------------------------------------------------
# A long-only book cannot reach the mandate (HML caps near 0.70), so the
# app opens with limited shorts enabled.
ALLOW_SHORTS_DEFAULT = True
SHORT_FLOOR = -0.10          # -10% per-name floor on shorts

RISK_TOLERANCE_DEFAULT = 0.20   # annualized volatility target
RISK_TOLERANCE_RANGE = (0.05, 0.40)

# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------
REPORT_DIR = OUTPUTS_DIR / "reports"   # exported CSV / Excel / PDF reports
