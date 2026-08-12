"""FactorModel - the regression engine behind the app.

Wraps the engine's OLS machinery (``src.regressions.exposure_table``) in
an object the interface can ask simple questions of:

    model = FactorModel(app_data, "5-factor")
    model.exposures()      -> beta table incl. 95% confidence intervals
    model.betas()          -> clean (stocks x factors) matrix for the optimizer
    model.rolling(...)     -> how exposures drift over time (windowed OLS)

Why a class?  The interface needs one object that holds the dataset, the
chosen factor set, and all derived quantities.  A class makes the state
explicit and lets the dashboard/CLI layers stay thin.
"""
from __future__ import annotations

import pandas as pd

from src.regressions import MODEL_3F, MODEL_5F, exposure_table

from factor_risk_model.data.data_fetcher import AppData

FACTOR_MODELS = {"3-factor": MODEL_3F, "5-factor": MODEL_5F}


class FactorModel:
    """Fama-French 3- or 5-factor exposures for a chosen universe."""

    def __init__(self, app_data: AppData, factor_model: str = "5-factor"):
        if factor_model not in FACTOR_MODELS:
            raise ValueError(f"factor_model must be one of {list(FACTOR_MODELS)}")
        self.app_data = app_data
        self.name = factor_model
        self.factor_cols = FACTOR_MODELS[factor_model]

    # ------------------------------------------------------------------
    # Core outputs
    # ------------------------------------------------------------------
    def exposures(self) -> pd.DataFrame:
        """Full statistics table (betas, t/p, 95% CIs, R2) per ticker.

        Includes SPY, which doubles as a model sanity check: its market
        beta should come out near 1.0 with R2 near 1.
        """
        return exposure_table(self.app_data.ds.excess,
                              self.app_data.ds.factors,
                              self.factor_cols)

    def betas(self) -> pd.DataFrame:
        """Loading matrix for the optimizer - user tickers only (SPY must
        never become a portfolio holding)."""
        table = self.exposures().loc[self.app_data.tickers]
        b = table[[f"beta_{k}" for k in self.factor_cols]].copy()
        b.columns = self.factor_cols
        return b

    def idio_var(self) -> pd.Series:
        """Idiosyncratic variance per stock (residual sd squared)."""
        return (self.exposures().loc[self.app_data.tickers]["resid_sd"] ** 2
                ).rename("idio_var")

    def summary_table(self, digits: int = 3) -> pd.DataFrame:
        """Display-ready exposure table: beta ± CI per factor + fit stats.

        Columns like 'HML' show '0.83  [0.58, 1.08]' - the point estimate
        with its 95% confidence interval, so a user immediately sees how
        precisely (or imprecisely) an exposure is measured.
        """
        table = self.exposures()
        pretty = pd.DataFrame(index=table.index)
        for k in self.factor_cols:
            pretty[k] = [
                f"{b:+.{digits}f}  [{lo:.{digits}f}, {hi:.{digits}f}]"
                for b, lo, hi in zip(table[f"beta_{k}"],
                                     table[f"ci_lo_{k}"],
                                     table[f"ci_hi_{k}"])
            ]
        pretty["R2"] = table["R2"].round(digits)
        pretty["n"] = table["n"]
        return pretty

    # ------------------------------------------------------------------
    # Rolling exposures (new in the interactive version)
    # ------------------------------------------------------------------
    def rolling_exposures(self, window: int = 36, step: int = 3
                          ) -> dict[str, pd.DataFrame]:
        """Refit the OLS on a rolling window; return per-factor paths.

        Parameters
        ----------
        window : months per regression window (needs >= 24 to be sane)
        step   : months between re-estimations

        Returns
        -------
        {factor: DataFrame(date x ticker)} of beta paths - e.g. how AAPL's
        HML loading drifted as it became a growth stock.  With 59 months
        and window=36, you get ~8 windows - a coarse but honest look.
        """
        if window < 24:
            raise ValueError("Rolling window needs >= 24 months.")
        rets, facs = self.app_data.ds.excess, self.app_data.ds.factors
        idx = rets.index
        paths: dict[str, list[pd.Series]] = {k: [] for k in self.factor_cols}
        dates: list[pd.Timestamp] = []

        for i in range(0, len(idx) - window + 1, step):
            sub = rets.iloc[i:i + window]
            table = exposure_table(sub, facs, self.factor_cols)
            for k in self.factor_cols:
                paths[k].append(table[f"beta_{k}"])
            dates.append(idx[i + window - 1])

        return {k: pd.DataFrame(v, index=pd.DatetimeIndex(dates, name="window_end"))
                for k, v in paths.items()}

    # ------------------------------------------------------------------
    # Human-readable profile (reuses the engine's plain-English logic)
    # ------------------------------------------------------------------
    def profiles(self) -> pd.Series:
        """One sentence per ticker describing its factor fingerprint.

        The engine's profile logic expects the full 5-factor column set;
        in 3-factor mode the missing columns become NaN, and NaN
        comparisons are False, so no spurious RMW/CMA tags appear.
        """
        from src.analysis import plain_english_profile
        table = self.exposures()
        full = table.reindex(columns=[f"beta_{k}" for k in MODEL_5F])
        return full.apply(plain_english_profile, axis=1)
