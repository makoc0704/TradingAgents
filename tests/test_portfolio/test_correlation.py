"""Tests for tradingagents.portfolio.correlation."""

import math
import pytest
import numpy as np
import pandas as pd

from tradingagents.portfolio.correlation import (
    calculate_correlation_matrix,
    calculate_covariance_matrix,
    calculate_portfolio_volatility,
    calculate_portfolio_var,
    diversification_ratio,
    get_individual_volatilities,
)


def _make_price_series(n=60, base=100.0, seed=42):
    """Create synthetic price series for testing."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    returns = rng.normal(0.001, 0.02, n)
    prices = base * np.cumprod(1 + returns)
    return pd.Series(prices, index=dates)


class TestCorrelationMatrix:
    def test_self_correlation_is_one(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        corr = calculate_correlation_matrix({"A": s1, "B": s2})
        assert abs(corr.loc["A", "A"] - 1.0) < 1e-10
        assert abs(corr.loc["B", "B"] - 1.0) < 1e-10

    def test_symmetric(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        corr = calculate_correlation_matrix({"A": s1, "B": s2})
        assert abs(corr.loc["A", "B"] - corr.loc["B", "A"]) < 1e-10

    def test_perfect_correlation(self):
        s = _make_price_series(seed=1)
        corr = calculate_correlation_matrix({"A": s, "B": s * 2})
        assert abs(corr.loc["A", "B"] - 1.0) < 1e-10

    def test_too_few_tickers(self):
        s = _make_price_series()
        with pytest.raises(ValueError, match="at least 2"):
            calculate_correlation_matrix({"A": s})

    def test_insufficient_overlap(self):
        s1 = _make_price_series(n=5, seed=1)
        s2 = _make_price_series(n=5, seed=2)
        with pytest.raises(ValueError, match="at least 10"):
            calculate_correlation_matrix({"A": s1, "B": s2})


class TestCovarianceMatrix:
    def test_annualized(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        cov_ann = calculate_covariance_matrix({"A": s1, "B": s2}, annualize=True)
        cov_raw = calculate_covariance_matrix({"A": s1, "B": s2}, annualize=False)
        assert cov_ann.loc["A", "A"] == pytest.approx(cov_raw.loc["A", "A"] * 252, rel=1e-10)


class TestPortfolioVolatility:
    def test_single_asset(self):
        s = _make_price_series(seed=1)
        cov = calculate_covariance_matrix({"A": s, "B": _make_price_series(seed=2)})
        vol = calculate_portfolio_volatility({"A": 1.0, "B": 0.0}, cov)
        assert vol > 0

    def test_equal_weight_less_than_max_individual(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        cov = calculate_covariance_matrix({"A": s1, "B": s2})
        port_vol = calculate_portfolio_volatility({"A": 0.5, "B": 0.5}, cov)
        vol_a = math.sqrt(cov.loc["A", "A"])
        vol_b = math.sqrt(cov.loc["B", "B"])
        assert port_vol <= max(vol_a, vol_b) + 1e-10


class TestPortfolioVar:
    def test_negative_value(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        cov = calculate_covariance_matrix({"A": s1, "B": s2})
        var = calculate_portfolio_var({"A": 0.5, "B": 0.5}, cov, confidence=0.95)
        assert var < 0


class TestDiversificationRatio:
    def test_perfect_correlation_is_one(self):
        ratio = diversification_ratio(
            weights={"A": 0.5, "B": 0.5},
            volatilities={"A": 0.20, "B": 0.20},
            portfolio_volatility=0.20,
        )
        assert ratio == 1.0

    def test_diversification_greater_than_one(self):
        ratio = diversification_ratio(
            weights={"A": 0.5, "B": 0.5},
            volatilities={"A": 0.20, "B": 0.20},
            portfolio_volatility=0.15,
        )
        assert ratio > 1.0

    def test_zero_portfolio_vol(self):
        ratio = diversification_ratio(
            weights={"A": 0.5}, volatilities={"A": 0.2}, portfolio_volatility=0.0,
        )
        assert ratio == 1.0


class TestIndividualVolatilities:
    def test_returns_positive(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        vols = get_individual_volatilities({"A": s1, "B": s2})
        assert vols["A"] > 0
        assert vols["B"] > 0

    def test_insufficient_data(self):
        s = pd.Series([100.0])
        vols = get_individual_volatilities({"A": s})
        assert vols["A"] == 0.0
