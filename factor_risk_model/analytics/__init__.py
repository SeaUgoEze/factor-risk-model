"""Analytics layer of the interactive app - built in Step 4.

    risk_metrics.py       RiskAnalyzer - Sharpe, VaR/CVaR, max drawdown,
                          attribution, plus new stress-test scenarios
                          (2020 shock, 2008-style) on the chosen portfolio.
    anomaly_detection.py  windowed autoencoder over the portfolio's own
                          returns (time-series cousin of the cross-sectional
                          lens in src.anomaly), with a 95th-percentile
                          threshold and anomaly timeline chart.
"""
