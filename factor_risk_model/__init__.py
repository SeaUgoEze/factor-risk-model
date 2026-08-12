"""
factor_risk_model - interactive application layer for the Factor-Based
Risk & Optimization Model.

This package turns the tested, headless engine in ``src/`` into a tool a
portfolio manager can actually drive: pick tickers, set a factor mandate,
run the full pipeline, and export reports - without touching code.

Layers (each built as its own step of this project):

    config/           UI defaults; imports engine constants from src.config
    data/             fetching + alignment (wraps src.data)          [Step 2]
    models/           FactorModel, PortfolioOptimizer classes         [Step 3]
    analytics/        RiskAnalyzer, windowed anomaly detection        [Step 4]
    visualization/    consistent themed charts for the app            [Step 5]
    interface/        interactive dashboard + argparse CLI              [Step 6]

The engine (already built and tested) lives in ``src/``: data, regressions,
analysis, optimization, risk, anomaly. Rule of thumb: the *engine* owns the
math; this package owns the *experience*.
"""

__version__ = "0.2.0"  # 0.1.x = static engine; 0.2.x = interactive application
