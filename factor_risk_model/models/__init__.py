"""Model layer of the interactive app - built in Step 3.

Object-oriented wrappers over the engine's regressions and optimizer:

    factor_model.py   FactorModel class - 3- and 5-factor exposures with
                      95% confidence intervals (new) and rolling betas (new).
    optimizer.py      PortfolioOptimizer class - factor mandate to weights
                      under long-only or limited-short constraints,
                      reusing src.optimization.target_factor_portfolio.
"""
