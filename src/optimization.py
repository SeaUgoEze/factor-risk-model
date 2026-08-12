"""
Step 4 - Factor-targeting portfolio optimization
==================================================
Given the Step-2 beta matrix B (stocks x factors) and the Step-3 factor
covariance matrix V_f, build a portfolio whose *weighted* betas hit a
target factor profile while minimizing risk:

    min_w    w' (B V_f B' + D) w          (portfolio variance)
    s.t.     sum(w) = 1                   (fully invested)
             |(B'w)_k - target_k| <= tol  (factor exposure targets)
             w >= 0  (long-only)   or   w >= short_floor (limited shorts)

where D = diag(idiosyncratic variances) comes from the Step-2 regressions.

Why the factor structure matters: the full stock covariance is 26x26 and
would be dominated by estimation noise with only 59 months of data.  The
factor covariance is 5x5 - easy to estimate - and B V_f B' + D rebuilds
the stock covariance with ~100x fewer parameters.  That is the core trick
of factor investing: the factors are the *data compression*.

We solve with scipy.optimize.minimize(method="SLSQP") - sequential
quadratic programming.  SLSQP is a *local* solver, so we start it from the
equal-weight portfolio (a sensible, feasible initial point).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def portfolio_exposures(weights, betas):
    """Portfolio factor loadings = w' B."""
    return pd.Series(betas.values.T @ weights, index=betas.columns)


def summarize(weights, betas, factor_cov, idio_var):
    """Risk/exposure summary for a weight vector (used for all portfolios).

    Full variance = w'(B V_f B')w + w'Dw  (factor risk + idiosyncratic risk).
    """
    B = betas.values
    V = factor_cov.values
    d = np.asarray(idio_var.reindex(betas.index))

    factor_var = float(weights @ B @ V @ B.T @ weights)
    # idiosyncratic part: sum_i w_i^2 * sigma_i^2  (d is 1-D, so square w)
    idio_var_p = float((weights ** 2) @ d)
    total_var = factor_var + idio_var_p

    return {
        "weights": pd.Series(weights, index=betas.index),
        "exposures": portfolio_exposures(weights, betas),
        "factor_vol_ann": np.sqrt(factor_var) * np.sqrt(12) * 100,
        "idio_vol_ann": np.sqrt(idio_var_p) * np.sqrt(12) * 100,
        "total_vol_ann": np.sqrt(total_var) * np.sqrt(12) * 100,
        "factor_share": factor_var / total_var,
    }


def target_factor_portfolio(betas, factor_cov, idio_var, targets,
                            tolerance=0.10, allow_shorts=False,
                            short_floor=-0.10, initial=None):
    """Minimize variance subject to factor-exposure targets.

    Tries SLSQP first, then falls back to trust-constr (both local solvers
    with the same API) and returns the best *feasible* result - or the
    lowest-variance result if the mandate cannot be satisfied at all
    (which itself is an important, honest finding: long-only universes
    often cannot hit aggressive multi-factor targets).

    Parameters
    ----------
    betas        : DataFrame (stocks x factors) of loadings (Step 2)
    factor_cov   : DataFrame (factors x factors) covariance (Step 3)
    idio_var     : Series of idiosyncratic variances per stock (Step 2)
    targets      : dict {factor: target loading}
    tolerance    : absolute |achieved - target| allowance per factor
    allow_shorts : if True, weights may go down to short_floor
    initial      : starting weights (default: equal weight)

    Returns
    -------
    dict with weights, exposures, vol decomposition, feasibility flags.
    """
    n = len(betas)
    B = betas.values
    V = factor_cov.values
    # Hoist the 26x26 covariance and the idiosyncratic vector out of the
    # objective (they are constant across all candidate weight vectors).
    M = B @ V @ B.T          # factor covariance mapped to stock space
    d = np.asarray(idio_var.reindex(betas.index))
    factor_names = list(betas.columns)
    target_vec = np.array([targets.get(k, 0.0) for k in factor_names])
    # Align the target series to ALL factors (missing -> 0.0), exactly like
    # the constraint vector, so the feasibility check never sees NaN gaps
    # for factors the mandate simply does not mention.
    target_series = pd.Series(target_vec, index=factor_names)

    def objective(w):
        factor_part = float(w @ M @ w)
        idio_part = float((w ** 2) @ d)
        return factor_part + idio_part

    # sum(w) = 1  (equality constraint)
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    # |(B'w)_k - target_k| <= tol  ->  two linear inequality constraints per
    # factor (avoids the non-smooth absolute value in the constraint list).
    for i in range(len(factor_names)):
        constraints.append(
            {"type": "ineq", "fun": lambda w, i=i: tolerance - (B.T @ w - target_vec)[i]})
        constraints.append(
            {"type": "ineq", "fun": lambda w, i=i: tolerance + (B.T @ w - target_vec)[i]})

    lower = short_floor if allow_shorts else 0.0
    bounds = [(lower, 1.0)] * n
    w0 = initial if initial is not None else np.full(n, 1.0 / n)

    solver_options = {
        "SLSQP": {"maxiter": 2000, "ftol": 1e-12, "disp": False},
        "trust-constr": {"maxiter": 500, "verbose": 0},
    }

    candidates = []
    for method in ("SLSQP", "trust-constr"):
        try:
            result = minimize(objective, w0, method=method, bounds=bounds,
                              constraints=constraints,
                              options=solver_options[method])
        except Exception:
            continue
        s = summarize(result.x, betas, factor_cov, idio_var)
        s["method"] = method
        s["success"] = bool(result.success)
        s["message"] = str(result.message)
        s["iterations"] = int(getattr(result, "nit", -1))
        gaps = (s["exposures"] - target_series).abs()
        s["max_gap"] = float(gaps.max())
        s["feasible"] = bool((gaps <= tolerance).all())
        candidates.append(s)

    if not candidates:
        raise RuntimeError(
            "Portfolio optimization failed: both SLSQP and trust-constr "
            "raised without producing a candidate solution.")

    # trust-constr can silently drift off the equality constraint on
    # degenerate problems (e.g. a single stock), so only accept weights
    # that actually sum to one.  A candidate that breaks sum(w)=1 is not
    # a portfolio.
    valid = [c for c in candidates if abs(c["weights"].sum() - 1.0) < 1e-4]
    if not valid:
        raise RuntimeError(
            "Portfolio optimization failed: neither solver returned a "
            "fully-invested weight vector (sum(w)=1).")

    # Prefer a feasible solution; otherwise keep the lowest-variance one.
    feasible = [c for c in valid if c["feasible"]]
    best = min(feasible or valid, key=lambda c: c["total_vol_ann"])
    return best
