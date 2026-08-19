"""
Step 2 - Factor exposures via OLS
==================================
For every security in the universe we estimate the *factor model*:

    r_it - rf_t = alpha_i + b_i,M * (Mkt-RF)_t + b_i,S * SMB_t
                          + b_i,H * HML_t  (+ b_i,P * RMW_t + b_i,I * CMA_t)
                          + eps_it

Interpretation
--------------
- b_i,k : the security's *loading* on factor k -- the units of factor-k
          return the stock earns per unit of factor movement.  A value
          stock carries a positive HML beta; a growth stock a negative one.
- alpha : the return NOT explained by the factors.  In a well-specified
          factor model it should be statistically indistinguishable from 0
          (that is what "the factors price the asset" means).
- R^2   : the share of the stock's monthly return variance the factors
          explain.  For a single large-cap stock, 0.5-0.9 is typical.

The betas are exactly the inputs Step 4's optimizer needs: a portfolio with
weights w has portfolio factor exposures w' * B, which we can then target.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

MODEL_3F = ["Mkt-RF", "SMB", "HML"]
MODEL_5F = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]


def _stars(p_value: float) -> str:
    """Conventional significance markers for p-values."""
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.10:
        return "*"
    return ""


def exposure_table(excess_returns, factors, factor_cols):
    """Run one OLS per security; return a tidy statistics table.

    Parameters
    ----------
    excess_returns : DataFrame (months x securities) - returns minus RF
    factors        : DataFrame (months x factor returns)
    factor_cols    : list[str] of factor columns to use

    Returns
    -------
    DataFrame indexed by ticker, with columns:
        alpha, t_alpha, p_alpha,
        beta_<k>, t_<k>, p_<k>, ci_lo_<k>, ci_hi_<k> for each factor k,
        R2, adj_R2, resid_sd, n

    The ci_lo_<k> / ci_hi_<k> columns are the 95% confidence interval for
    each factor loading (beta +/- 1.96 * std error).
    """
    design = sm.add_constant(factors[factor_cols])   # intercept = alpha
    rows = {}

    for ticker in excess_returns.columns:
        # statsmodels works positionally (ignores pandas indexes), so align
        # y to the design matrix explicitly; missing="drop" drops NaN rows.
        y = excess_returns[ticker].reindex(design.index)
        fit = sm.OLS(y, design, missing="drop").fit()   # closed-form OLS
        ci = fit.conf_int()                     # 95% CI per coefficient
        row = {
            "alpha": fit.params["const"],
            "t_alpha": fit.tvalues["const"],
            "p_alpha": fit.pvalues["const"],
        }
        # statsmodels' conf_int() column labels vary by version (0.025/0.975
        # vs a positional RangeIndex), so take them positionally: row k of
        # the returned frame is (lower, upper) in that order.
        for k in factor_cols:
            row[f"beta_{k}"] = fit.params[k]
            row[f"t_{k}"] = fit.tvalues[k]
            row[f"p_{k}"] = fit.pvalues[k]
            row[f"ci_lo_{k}"] = float(ci.loc[k].iloc[0])
            row[f"ci_hi_{k}"] = float(ci.loc[k].iloc[1])
        row["R2"] = fit.rsquared
        row["adj_R2"] = fit.rsquared_adj
        row["resid_sd"] = float(np.sqrt(fit.mse_resid))  # monthly, decimal
        row["n"] = int(fit.nobs)
        rows[ticker] = row

    return pd.DataFrame(rows).T


def pretty_beta_table(table, factor_cols):
    """Print-ready table: coefficients with significance stars + fit stats.

    Columns: alpha, beta_<k> ('+0.312***'), R2, adjR2.
    Full t/p statistics live in the CSVs saved by the driver script.
    """
    cols = ["alpha"] + [f"beta_{k}" for k in factor_cols]
    pretty = pd.DataFrame(index=table.index)

    for c in cols:
        if c == "alpha":
            pretty[c] = [
                f"{v:+.3f}{_stars(table.loc[ix, 'p_alpha'])}"
                for ix, v in table[c].items()
            ]
        else:
            p_col = c.replace("beta_", "p_")
            pretty[c] = [
                f"{v:+.3f}{_stars(table.loc[ix, p_col])}"
                for ix, v in table[c].items()
            ]
    pretty["R2"] = [f"{v:.3f}" for v in table["R2"]]
    pretty["adjR2"] = [f"{v:.3f}" for v in table["adj_R2"]]
    return pretty


def top_bottom(exposure, factor_col, k=3):
    """Lowest- and highest-loading securities on one factor (for highlights)."""
    s = exposure[f"beta_{factor_col}"].sort_values()
    return pd.concat([s.head(k), s.tail(k)])
