"""
Central configuration: paths, analysis window and stock universe.
"""

from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"        # cached raw data (CSV)
FIGURES_DIR = ROOT / "figures"  # saved plots
OUTPUTS_DIR = ROOT / "outputs"  # result tables / reports

for _dir in (DATA_DIR, FIGURES_DIR, OUTPUTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# Analysis window
#
# 2015-2019: a "normal" regime with no crisis.  2020's COVID drawdown is
# excluded so the factor model is estimated on clean data first.
START_DATE = "2015-01-01"
END_DATE = "2019-12-31"

# Stock universe: 26 S&P 500 names across 8 sectors (ticker -> sector).
UNIVERSE = {
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "INTC": "Technology", "CSCO": "Technology",
    # Financials
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
    "WFC": "Financials",
    # Energy
    "XOM": "Energy", "CVX": "Energy",
    # Health Care
    "JNJ": "Health Care", "PFE": "Health Care", "UNH": "Health Care",
    "MRK": "Health Care",
    # Consumer Staples
    "PG": "Consumer Staples", "KO": "Consumer Staples",
    "WMT": "Consumer Staples", "MCD": "Consumer Staples",
    # Consumer Discretionary / Communication Services
    "NKE": "Consumer Discretionary", "AMZN": "Consumer Discretionary",
    "META": "Communication Services", "DIS": "Communication Services",
    # Industrials
    "CAT": "Industrials", "BA": "Industrials", "GE": "Industrials",
}

# Investable benchmark used for performance comparison (Step 5).
BENCHMARK = "SPY"
