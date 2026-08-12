"""PortfolioOptimizer - turns a factor mandate into weights.

Wraps the engine's ``target_factor_portfolio`` (minimize variance subject
to hitting target factor loadings) with an interface-friendly surface:

    opt = PortfolioOptimizer(betas, factor_cov, idio_var)
    result = opt.optimize(targets, allow_shorts=True, short_floor=-0.10)

One design note worth understanding: the optimizer *minimizes* variance
for a fixed mandate, so the achieved volatility is an **output**, not an
input.  A "target vol" above the minimum is automatically satisfied; a
target vol below it is mathematically impossible while still hitting the
mandate.  That is why the interface treats a vol budget as a *warning
threshold* (``check_vol_budget``) rather than a hard constraint -an honest way to frame it.
"""
from __future__ import annotations

import pandas as pd

from src.analysis import factor_covariance
from src.optimization import portfolio_exposures, target_factor_portfolio

from factor_risk_model.models.factor_model import FactorModel


class PortfolioOptimizer:
    """Minimum-variance portfolio that hits target factor exposures."""

    def __init__(self, model: FactorModel):
        self.model = model
        self.factor_cov, self.factor_corr, self.factor_vol = \
            factor_covariance(model.app_data.ds.factors)
        self.betas = model.betas()
        self.idio_var = model.idio_var()

    # ------------------------------------------------------------------
    def optimize(self, targets: dict, tolerance: float = 0.10,
                 allow_shorts: bool = True, short_floor: float = -0.10,
                 initial: pd.Series | None = None) -> dict:
        """Solve min-variance under factor-exposure targets.

        Returns the engine's result dict (weights, exposures, vol
        decomposition, feasibility flags) - see src.optimization.
        ``targets`` may omit factors (missing ones default to 0.0).
        """
        return target_factor_portfolio(
            self.betas, self.factor_cov, self.idio_var, targets,
            tolerance=tolerance, allow_shorts=allow_shorts,
            short_floor=short_floor,
            initial=None if initial is None else initial.reindex(self.betas.index).values,
        )

    def exposures_of(self, weights: pd.Series) -> pd.Series:
        """Portfolio factor loadings for an arbitrary weight vector.

        Weights are reindexed onto the beta matrix first so the matrix
        product can never silently use a misaligned ordering.
        """
        return portfolio_exposures(weights.reindex(self.betas.index).fillna(0.0),
                                   self.betas)

    def comparison(self, targets: dict, tolerance: float = 0.10,
                   allow_shorts: bool = True, short_floor: float = -0.10,
                   max_vol: float | None = None) -> dict:
        """Optimize + build the target-vs-achieved table and warnings.

        ``max_vol`` is a *warning threshold* (see the module docstring):
        the result reports whether the minimum achievable volatility is
        within the user's risk budget.
        """
        result = self.optimize(targets, tolerance=tolerance,
                               allow_shorts=allow_shorts,
                               short_floor=short_floor)

        t = pd.Series({k: targets.get(k, 0.0) for k in self.model.factor_cols})
        achieved = result["exposures"]
        cmp = pd.DataFrame({
            "target": t,
            "achieved": achieved.reindex(t.index),
            "gap": (achieved - t).reindex(t.index).abs(),
        }).round(4)

        warnings = []
        if not result["feasible"]:
            worst = (achieved.reindex(t.index) - t).abs().max()
            warnings.append(
                f"The mandate is NOT fully satisfiable: the closest feasible "
                f"portfolio still misses a target by {worst:.2f}. "
                "Relax the targets (or allow shorts) to tighten the fit.")
        if max_vol is not None and result["total_vol_ann"] > max_vol * 100:
            warnings.append(
                f"Achieved vol {result['total_vol_ann']:.1f}% exceeds your "
                f"budget of {max_vol * 100:.0f}%. Minimum variance under this "
                "mandate is already this high - only relaxing factor targets "
                "can bring risk down.")

        result["comparison"] = cmp
        result["warnings"] = warnings
        return result
