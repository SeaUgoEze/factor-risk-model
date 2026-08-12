"""RiskAnalyzer - performance, tail risk, attribution and stress tests.

Wraps the engine's Step-5 risk functions (``src.risk``) and adds the
stress-test engine that is new in the interactive version.

How the stress test works
-------------------------
A scenario is a one-month *shock to the five factors* (e.g. a crash
month where Mkt-RF = -15%).  A portfolio with factor loadings beta has
expected one-month excess return:

    r_p - rf  ~  alpha + sum_k beta_k * shock_k

so the scenario impact follows directly from the estimated exposures -
no simulation needed, just the factor model itself.  SPY's impact is the
same formula with its own loadings (beta ~ 1 on the market, ~ 0
elsewhere), which makes the comparison clean.

The shocks below are *stylized* reconstructions of real episodes for
teaching - they are illustrative magnitudes, not backtested values.
"""
from __future__ import annotations

import pandas as pd

from src.config import BENCHMARK
from src.risk import (drawdown_series, expected_shortfall,
                      factor_attribution, historical_var, max_drawdown,
                      normal_var, performance_summary)

from factor_risk_model.data.data_fetcher import AppData
from factor_risk_model.models.factor_model import FactorModel
from factor_risk_model.models.optimizer import PortfolioOptimizer
from factor_risk_model.utils.helpers import equal_weight_returns, portfolio_returns

# Stylized one-month factor shocks (fractions) per historical episode.
#      Mkt-RF    SMB    HML    RMW    CMA
SCENARIOS: dict[str, dict[str, float]] = {
    "COVID crash (Mar-2020 style)": {
        "Mkt-RF": -0.15, "SMB": 0.02, "HML": 0.04,
        "RMW": 0.01, "CMA": 0.03,
    },
    "GFC crisis (2008 style)": {
        "Mkt-RF": -0.17, "SMB": -0.02, "HML": 0.06,
        "RMW": -0.03, "CMA": 0.04,
    },
    "Rate-shock selloff (2022 style)": {
        "Mkt-RF": -0.08, "SMB": -0.05, "HML": 0.08,
        "RMW": 0.02, "CMA": 0.05,
    },
    "Tech-bubble pop (2000 style)": {
        "Mkt-RF": -0.10, "SMB": 0.04, "HML": -0.06,
        "RMW": 0.01, "CMA": -0.02,
    },
}


class RiskAnalyzer:
    """One object that answers every 'how did it do / what could hurt it'
    question for the optimized portfolio."""

    def __init__(self, app_data: AppData, model: FactorModel,
                 optimizer: PortfolioOptimizer, weights: pd.Series,
                 tickers: list[str] | None = None):
        self.app_data = app_data
        self.model = model
        self.optimizer = optimizer
        self.weights = weights
        self.returns = app_data.ds.returns
        self.tickers = tickers or list(weights.index)

        self.portfolio = portfolio_returns(self.returns, weights)
        # Equal weight is over the *selected* names only - never SPY.
        self.equal_w = equal_weight_returns(self.returns[self.tickers])
        self.spy = self.returns[BENCHMARK] if BENCHMARK in self.returns else None

    # ------------------------------------------------------------------
    # Headline metrics
    # ------------------------------------------------------------------
    def summary(self) -> pd.DataFrame:
        """Annualized return/vol/Sharpe/max-DD/VaR/CVaR for optimal vs refs."""
        frame = {"Optimal": self.portfolio}
        if self.spy is not None:
            frame["SPY"] = self.spy
        frame["Equal weight"] = self.equal_w
        return performance_summary(pd.DataFrame(frame),
                                   self.app_data.ds.rf)

    def tail_risk(self, alpha: float = 0.05) -> dict:
        """VaR (historical + normal) and CVaR for the optimal portfolio."""
        r = self.portfolio.dropna()
        return {
            "var_historical_%": historical_var(r, alpha) * 100,
            "var_normal_%": normal_var(r, alpha) * 100,
            "cvar_%": expected_shortfall(r, alpha) * 100,
        }

    def attribution(self) -> dict:
        """Factor attribution of the optimal portfolio's excess return."""
        return factor_attribution(self.portfolio - self.app_data.ds.rf,
                                  self.app_data.ds.factors,
                                  self.model.factor_cols)

    def drawdown(self) -> pd.Series:
        """Drawdown path of the optimal portfolio."""
        return drawdown_series(self.portfolio)

    # ------------------------------------------------------------------
    # Stress tests (new)
    # ------------------------------------------------------------------
    def stress_scenarios(self) -> pd.DataFrame:
        """One-month portfolio impact per scenario, vs SPY and equal weight.

        Impact = alpha_monthly + sum(beta_k * shock_k)  (excess), then the
        risk-free rate is added back for a raw return view.  Reported as
        the one-month return % under each scenario.
        """
        attr = self.attribution()
        betas = attr["betas"].reindex(self.model.factor_cols).fillna(0.0)
        alpha_m = attr["alpha_ann"] / 12
        rf_m = float(self.app_data.ds.rf.mean())

        spy_betas = pd.Series(0.0, index=self.model.factor_cols)
        spy_betas["Mkt-RF"] = 1.0
        ew_weights = pd.Series(1.0 / len(self.tickers), index=self.tickers)
        ew_betas = self.optimizer.exposures_of(ew_weights)

        rows = {}
        for name, shocks in SCENARIOS.items():
            shock = pd.Series({k: shocks.get(k, 0.0)
                               for k in self.model.factor_cols})
            rows[name] = {
                "portfolio_%": (alpha_m + betas.dot(shock) + rf_m) * 100,
                "spy_%": (rf_m + spy_betas.dot(shock)) * 100,
                "equal_weight_%": (alpha_m + ew_betas.dot(shock) + rf_m) * 100,
            }
        return pd.DataFrame(rows).T.round(2)

    # ------------------------------------------------------------------
    # Interpretation (plain English, drives the UI + PDF)
    # ------------------------------------------------------------------
    def interpretation(self) -> list[str]:
        """Auto-generated bullet summary of the whole risk picture."""
        s = self.summary()
        opt = s.loc["Optimal"]
        t = self.tail_risk()
        a = self.attribution()
        stress = self.stress_scenarios()
        bullets = [
            f"The optimized portfolio earned {opt['ann_return_%']:.1f}%/yr at "
            f"{opt['ann_vol_%']:.1f}% vol (Sharpe {opt['sharpe']:.2f}) vs "
            f"SPY's {s.loc['SPY', 'ann_return_%']:.1f}%/yr at "
            f"{s.loc['SPY', 'ann_vol_%']:.1f}% vol.",
            f"Worst peak-to-trough drawdown was {opt['max_drawdown_%']:.1f}% "
            f"(SPY {s.loc['SPY', 'max_drawdown_%']:.1f}%).",
            f"95% monthly VaR {t['var_historical_%']:.1f}%, CVaR "
            f"{t['cvar_%']:.1f}% - CVaR exceeds VaR because the tail is "
            f"worse than the boundary suggests.",
            f"Factors explain {a['R2'] * 100:.0f}% of portfolio variance; "
            "the largest contributions are "
            + self._top_contrib(a) + ".",
        ]
        worst = stress["portfolio_%"].idxmin()
        bullets.append(
            f"Worst stress scenario: '{worst}' would cost "
            f"{stress.loc[worst, 'portfolio_%']:.1f}% in one month "
            f"(vs {stress.loc[worst, 'spy_%']:.1f}% for SPY).")
        return bullets

    @staticmethod
    def _top_contrib(a: dict) -> str:
        c = a["contributions"].copy()
        c["alpha"] = a["alpha_ann"]
        top = c.sort_values(key=abs, ascending=False).head(2)
        return ", ".join(f"{k} {v * 100:+.1f}%/yr" for k, v in top.items())
