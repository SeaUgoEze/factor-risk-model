"""
Factor-Based Risk & Optimization Model
--------------------------------------
A factor-based risk and optimization framework in the style used by
institutional asset managers and pension funds.

Pipeline:
  Step 1  src/data.py              Data acquisition & preparation
  Step 2  src/regressions.py       Factor exposures (OLS betas)
  Step 3  src/analysis.py          Factor analysis & visualization
  Step 4  src/optimization.py      Factor-targeting portfolio construction
  Step 5  src/risk.py              Performance & risk analysis
  Step 6  src/anomalies.py         Autoencoder anomaly detection (bonus)
  Step 7  README.md + notebooks/   Documentation & presentation
"""

__version__ = "0.1.0"
