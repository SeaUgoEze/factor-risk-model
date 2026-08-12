"""Shared pytest fixtures.

All tests run OFFLINE: they reuse the on-disk cache in ``data/`` (built
by the step scripts for the 2015-2019 window).  A fresh clone needs to
run ``scripts/step1_fetch.py`` once before ``pytest`` so the cache exists.
"""
from __future__ import annotations

import pytest

from factor_risk_model.data.data_fetcher import CURATED, fetch_app_data
from factor_risk_model.models.factor_model import FactorModel
from factor_risk_model.models.optimizer import PortfolioOptimizer

WINDOW = ("2015-01-01", "2019-12-31")
SUBSET = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "PG", "AMZN", "META",
          "CAT", "BA"]


@pytest.fixture(scope="session")
def app_data():
    """Cached dataset for a 10-stock, sector-diverse subset (offline)."""
    return fetch_app_data(SUBSET, *WINDOW)


@pytest.fixture(scope="session")
def full_app_data():
    """Cached dataset for the full 26-stock universe."""
    return fetch_app_data(CURATED, *WINDOW)


@pytest.fixture(scope="session")
def model(app_data):
    return FactorModel(app_data, "5-factor")


@pytest.fixture(scope="session")
def optimizer(model):
    return PortfolioOptimizer(model)


@pytest.fixture(scope="session")
def full_optimizer(full_app_data):
    return PortfolioOptimizer(FactorModel(full_app_data, "5-factor"))
