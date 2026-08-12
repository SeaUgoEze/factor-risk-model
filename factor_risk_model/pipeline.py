"""run_pipeline - the one function every interface calls.

The interactive app, the CLI and the tests all go through here, so the numbers can
never disagree between interfaces.  It runs the whole engine chain:

    fetch -> align -> regressions (+CIs) -> optimize -> risk -> stress
    -> anomaly

and hands back a PipelineResult: every table the UI shows, every figure
it displays, and the auto-generated plain-English interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.analysis import exposure_heatmap, plot_weights
from src.config import OUTPUTS_DIR
from src.risk import (plot_attribution, plot_cumulative_returns,
                      plot_drawdowns)

from factor_risk_model.analytics.anomaly_detection import (
    PortfolioAnomalyDetector)
from factor_risk_model.analytics.risk_metrics import RiskAnalyzer
from factor_risk_model.data.data_fetcher import fetch_app_data
from factor_risk_model.models.factor_model import FactorModel
from factor_risk_model.models.optimizer import PortfolioOptimizer
from factor_risk_model.utils.helpers import normalize_tickers, portfolio_returns
from factor_risk_model.visualization import plots

DEFAULT_FIGURES_DIR = OUTPUTS_DIR / "app_figures"


@dataclass
class PipelineResult:
    """Everything produced by one run - the contract between pipeline and UI."""

    tickers: list
    start: str
    end: str
    factor_model: str
    targets: dict

    # data
    prices: pd.DataFrame = None
    ds: object = None                      # src.data.AnalysisData

    # exposures
    exposures: pd.DataFrame = None         # full statistics table (t/p/CIs)
    exposures_pretty: pd.DataFrame = None  # 'beta [lo, hi]' + R2 for the UI
    factor_cov: pd.DataFrame = None
    factor_corr: pd.DataFrame = None
    factor_vol: pd.Series = None
    profiles: pd.Series = None

    # optimization
    weights: pd.Series = None
    optimizer: dict = None                 # engine result incl. vol breakdown
    optimization_warnings: list = field(default_factory=list)

    # performance & risk
    portfolio_returns: pd.Series = None
    risk_summary: pd.DataFrame = None
    tail: dict = None
    attribution: dict = None
    stress: pd.DataFrame = None

    # anomaly
    anomaly: object = None                 # AnomalyResult
    anomaly_interpretation: list = field(default_factory=list)

    # figures: name -> saved path
    figures: dict = field(default_factory=dict)
    _interpretation: list = field(default_factory=list, repr=False)

    def interpretation(self) -> list[str]:
        """Plain-English bullets for the UI, CLI summary and PDF."""
        return list(self._interpretation)

    @property
    def anomaly_flags(self):
        """Export-friendly view of the flagged anomaly windows."""
        return self.anomaly.flagged_windows if self.anomaly is not None else None


def run_pipeline(tickers, start: str, end: str,
                 factor_model: str = "5-factor",
                 targets: dict | None = None,
                 tolerance: float = 0.10,
                 allow_shorts: bool = True,
                 short_floor: float = -0.10,
                 max_vol: float | None = None,
                 figures_dir: Path | str = DEFAULT_FIGURES_DIR,
                 app_data=None,
                 chart_mode: str = "mono") -> PipelineResult:
    """Execute the full factor-model pipeline for one user configuration.

    Parameters
    ----------
    app_data : optional pre-fetched AppData.  The interactive app passes a
        cached dataset here so widget tweaks never re-hit the network;
        the CLI omits it and lets this function fetch.
    chart_mode : "mono" (grayscale, the default) or "semantic" (deep
        green / muted red hues for sign, benchmark and loss regions).

    Raises ValueError / RuntimeError with friendly messages (bad tickers,
    short window, network failure) - the interfaces catch and display
    these rather than letting a traceback reach the user.
    """
    tickers = normalize_tickers(tickers)
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. data -----------------------------------------------------
    if app_data is None:
        app_data = fetch_app_data(tickers, start, end, factor_model)
    model = FactorModel(app_data, factor_model)
    optimizer = PortfolioOptimizer(model)

    # ---- 2. exposures + optimization --------------------------------
    table = model.exposures()
    betas, idio_var = model.betas(), model.idio_var()
    mandate = dict(targets or {k: 1.0 if k == "Mkt-RF" else 0.0
                               for k in model.factor_cols})
    result = optimizer.comparison(mandate, tolerance=tolerance,
                                  allow_shorts=allow_shorts,
                                  short_floor=short_floor, max_vol=max_vol)
    weights = result["weights"]

    # ---- 3. risk -----------------------------------------------------
    analyzer = RiskAnalyzer(app_data, model, optimizer, weights,
                            tickers=app_data.tickers)
    summary = analyzer.summary()
    tail = analyzer.tail_risk()
    attr = analyzer.attribution()
    stress = analyzer.stress_scenarios()

    # ---- 4. anomaly (windowed autoencoder on daily returns) ----------
    daily_ret = app_data.daily_prices[tickers].pct_change().dropna(
        how="all").fillna(0.0)
    port_daily = portfolio_returns(daily_ret, weights)
    detector = PortfolioAnomalyDetector()
    detector.fit(port_daily)
    anomaly = detector.detect(port_daily)

    # ---- 5. figures --------------------------------------------------
    growth = pd.DataFrame({
        "Optimal": (1 + analyzer.portfolio).cumprod(),
        "SPY": (1 + analyzer.spy).cumprod() if analyzer.spy is not None else None,
        "Equal weight": (1 + analyzer.equal_w).cumprod(),
    }).dropna(axis=1)

    figures = {
        "exposures": exposure_heatmap(table, model.factor_cols,
                                      app_data.sector_map,
                                      figures_dir / "exposures_heatmap.png",
                                      mode=chart_mode),
        "weights": plot_weights(weights, figures_dir / "weights.png",
                                title="Optimal portfolio weights - "
                                      f"mandate {dict(mandate)}",
                                mode=chart_mode),
        "cumulative": plot_cumulative_returns(
            growth, figures_dir / "cumulative.png", mode=chart_mode),
        "drawdowns": plot_drawdowns(
            pd.DataFrame({"Optimal": analyzer.portfolio,
                          "SPY": analyzer.spy,
                          "Equal weight": analyzer.equal_w}).dropna(axis=1),
            figures_dir / "drawdowns.png", mode=chart_mode),
        "attribution": plot_attribution(attr["contributions"], attr["alpha_ann"],
                                        figures_dir / "attribution.png",
                                        mode=chart_mode),
        "stress": plots.plot_stress(stress, figures_dir / "stress.png",
                                    mode=chart_mode),
        "anomaly": plots.plot_windowed_anomaly(anomaly, port_daily,
                                               figures_dir / "anomaly.png"),
    }

    # CI + rolling charts for the first ticker (a taste of the new math)
    first = tickers[0]
    row = table.loc[first]
    figures["ci"] = plots.plot_exposure_ci(
        pd.Series({k: row[f"beta_{k}"] for k in model.factor_cols}),
        pd.Series({k: row[f"ci_lo_{k}"] for k in model.factor_cols}),
        pd.Series({k: row[f"ci_hi_{k}"] for k in model.factor_cols}),
        figures_dir / "ci.png", title=f"Factor exposures with 95% CI - {first}",
        mode=chart_mode)
    rolling = model.rolling_exposures()
    if rolling and first in rolling[model.factor_cols[0]].columns:
        figures["rolling"] = plots.plot_rolling_exposures(
            rolling, first, figures_dir / "rolling.png")

    # ---- 6. interpretation -------------------------------------------
    interpretation = analyzer.interpretation()
    anomaly_interpretation = detector.interpretation(anomaly, port_daily)
    interpretation += anomaly_interpretation

    return PipelineResult(
        tickers=app_data.tickers, start=start, end=end,
        factor_model=factor_model, targets=mandate,
        prices=app_data.daily_prices, ds=app_data.ds,
        exposures=table, exposures_pretty=model.summary_table(),
        factor_cov=optimizer.factor_cov,
        factor_corr=optimizer.factor_corr, factor_vol=optimizer.factor_vol,
        profiles=model.profiles(),
        weights=weights, optimizer=result,
        optimization_warnings=result["warnings"],
        portfolio_returns=analyzer.portfolio,
        risk_summary=summary, tail=tail, attribution=attr, stress=stress,
        anomaly=anomaly, anomaly_interpretation=anomaly_interpretation,
        figures=figures, _interpretation=interpretation,
    )
