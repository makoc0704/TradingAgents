"""Tests for tradingagents.portfolio.optimizer."""

import pytest
import numpy as np
import pandas as pd

from tradingagents.portfolio.optimizer import PortfolioOptimizer
from tradingagents.risk.models import RiskMetrics, TradeSignal, PositionSize


def _make_price_series(n=60, base=100.0, seed=42):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    returns = rng.normal(0.001, 0.02, n)
    prices = base * np.cumprod(1 + returns)
    return pd.Series(prices, index=dates)


def _make_risk_metrics(ticker, vol=0.20):
    return RiskMetrics(
        ticker=ticker, date="2024-06-01",
        daily_volatility=vol / (252 ** 0.5), annualized_volatility=vol,
        atr=2.0, atr_percent=0.02, max_drawdown=-0.05, current_drawdown=-0.01,
        var_95=-0.03, var_99=-0.05, cvar_95=-0.04,
        beta=1.0, sharpe_ratio=1.0, sortino_ratio=1.5,
        current_price=150.0, sma_50=148.0, sma_200=145.0, rsi=55.0,
    )


class TestEqualWeight:
    def test_two_tickers(self):
        opt = PortfolioOptimizer(max_position=0.60, min_position=0.01)
        result = opt.optimize("equal", ["AAPL", "NVDA"])
        assert result.method == "equal"
        assert len(result.weights) == 2
        assert result.weights["AAPL"] == pytest.approx(0.5, abs=0.01)
        assert result.weights["NVDA"] == pytest.approx(0.5, abs=0.01)

    def test_empty_tickers(self):
        opt = PortfolioOptimizer()
        result = opt.optimize("equal", [])
        assert result.weights == {}

    def test_weights_clamped_to_max(self):
        opt = PortfolioOptimizer(max_position=0.30, min_position=0.01)
        result = opt.optimize("equal", ["A", "B"])
        for w in result.weights.values():
            assert w <= 0.30 + 1e-10


class TestRiskParity:
    def test_higher_vol_gets_lower_weight(self):
        opt = PortfolioOptimizer(max_position=0.80, min_position=0.01)
        rm_low = _make_risk_metrics("LOW_VOL", vol=0.10)
        rm_high = _make_risk_metrics("HIGH_VOL", vol=0.40)
        result = opt.optimize(
            "risk_parity",
            ["LOW_VOL", "HIGH_VOL"],
            risk_metrics={"LOW_VOL": rm_low, "HIGH_VOL": rm_high},
        )
        assert result.weights["LOW_VOL"] > result.weights["HIGH_VOL"]

    def test_with_price_series(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        opt = PortfolioOptimizer(max_position=0.80, min_position=0.01)
        result = opt.optimize(
            "risk_parity", ["A", "B"], price_series={"A": s1, "B": s2},
        )
        assert sum(result.weights.values()) <= 1.0 + 1e-10


class TestMinVariance:
    def test_returns_valid_weights(self):
        s1 = _make_price_series(seed=1)
        s2 = _make_price_series(seed=2)
        s3 = _make_price_series(seed=3)
        opt = PortfolioOptimizer(max_position=0.60, min_position=0.05)
        result = opt.optimize(
            "min_variance",
            ["A", "B", "C"],
            price_series={"A": s1, "B": s2, "C": s3},
        )
        assert result.method == "min_variance"
        assert sum(result.weights.values()) <= 1.0 + 1e-10
        for w in result.weights.values():
            assert w >= 0.0

    def test_fallback_to_equal_without_data(self):
        opt = PortfolioOptimizer()
        result = opt.optimize("min_variance", ["A", "B"])
        assert result.method == "equal"


class TestSignalWeighted:
    def test_buy_gets_more_than_hold(self):
        buy_sig = TradeSignal(
            action="BUY", confidence=0.9, position_size=None,
            risk_metrics=None, reasoning="Strong buy",
        )
        hold_sig = TradeSignal(
            action="HOLD", confidence=0.5, position_size=None,
            risk_metrics=None, reasoning="Neutral",
        )
        opt = PortfolioOptimizer(max_position=0.80, min_position=0.01)
        result = opt.optimize(
            "signal_weighted", ["BUYER", "HOLDER"],
            signals={"BUYER": buy_sig, "HOLDER": hold_sig},
        )
        assert result.weights["BUYER"] > result.weights["HOLDER"]

    def test_sell_gets_zero(self):
        sell_sig = TradeSignal(
            action="SELL", confidence=0.8, position_size=None,
            risk_metrics=None, reasoning="Sell",
        )
        buy_sig = TradeSignal(
            action="BUY", confidence=0.8, position_size=None,
            risk_metrics=None, reasoning="Buy",
        )
        opt = PortfolioOptimizer(max_position=0.80, min_position=0.01)
        result = opt.optimize(
            "signal_weighted", ["SELLER", "BUYER"],
            signals={"SELLER": sell_sig, "BUYER": buy_sig},
        )
        assert result.weights.get("SELLER", 0.0) == 0.0

    def test_fallback_without_signals(self):
        opt = PortfolioOptimizer()
        result = opt.optimize("signal_weighted", ["A", "B"])
        assert result.method == "equal"


class TestUnknownStrategy:
    def test_raises_value_error(self):
        opt = PortfolioOptimizer()
        with pytest.raises(ValueError, match="Unknown weighting strategy"):
            opt.optimize("magic_oracle", ["A", "B"])
