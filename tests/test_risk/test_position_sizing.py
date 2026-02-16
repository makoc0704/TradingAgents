"""Tests for tradingagents.risk.position_sizing — position sizing algorithms."""

import pytest

from tradingagents.risk.position_sizing import (
    kelly_criterion,
    fixed_fraction,
    volatility_adjusted,
)
from tradingagents.risk.models import PositionSize


class TestKellyCriterion:
    def test_basic_calculation(self):
        ps = kelly_criterion(
            win_rate=0.6,
            avg_win=0.05,
            avg_loss=0.03,
            current_price=150.0,
            atr=3.0,
        )
        assert isinstance(ps, PositionSize)
        assert ps.method == "kelly"
        assert 0.0 <= ps.fraction <= 0.25
        assert ps.stop_loss_price > 0
        assert ps.stop_loss_price < 150.0

    def test_losing_strategy_zero_fraction(self):
        ps = kelly_criterion(
            win_rate=0.3,
            avg_win=0.02,
            avg_loss=0.05,
            current_price=100.0,
            atr=2.0,
        )
        assert ps.fraction == 0.0

    def test_invalid_avg_loss(self):
        ps = kelly_criterion(
            win_rate=0.5,
            avg_win=0.03,
            avg_loss=0.0,
            current_price=100.0,
            atr=2.0,
        )
        assert ps.fraction == 0.0

    def test_max_fraction_clamped(self):
        ps = kelly_criterion(
            win_rate=0.9,
            avg_win=0.10,
            avg_loss=0.01,
            current_price=100.0,
            atr=1.0,
            max_fraction=0.15,
        )
        assert ps.fraction <= 0.15


class TestFixedFraction:
    def test_basic_calculation(self):
        ps = fixed_fraction(
            risk_per_trade=0.02,
            current_price=200.0,
            atr=4.0,
        )
        assert isinstance(ps, PositionSize)
        assert ps.method == "fixed_fraction"
        assert 0.0 < ps.fraction <= 0.25
        assert ps.stop_loss_price < 200.0

    def test_zero_atr(self):
        ps = fixed_fraction(
            risk_per_trade=0.02,
            current_price=100.0,
            atr=0.0,
        )
        assert ps.fraction == 0.0

    def test_high_risk_clamped(self):
        ps = fixed_fraction(
            risk_per_trade=0.50,
            current_price=100.0,
            atr=1.0,
            max_fraction=0.20,
        )
        assert ps.fraction <= 0.20


class TestVolatilityAdjusted:
    def test_basic_calculation(self):
        ps = volatility_adjusted(
            annualized_volatility=0.30,
            target_volatility=0.15,
            current_price=100.0,
            atr=2.0,
        )
        assert isinstance(ps, PositionSize)
        assert ps.method == "volatility_adjusted"
        # 0.15 / 0.30 = 0.50, clamped to max 0.25
        assert ps.fraction == pytest.approx(0.25)

    def test_low_volatility_high_allocation(self):
        ps = volatility_adjusted(
            annualized_volatility=0.10,
            target_volatility=0.15,
            current_price=100.0,
            atr=1.5,
            max_fraction=0.25,
        )
        # 0.15 / 0.10 = 1.5, clamped to 0.25
        assert ps.fraction == 0.25

    def test_high_volatility_low_allocation(self):
        ps = volatility_adjusted(
            annualized_volatility=0.60,
            target_volatility=0.15,
            current_price=100.0,
            atr=3.0,
        )
        # 0.15 / 0.60 = 0.25
        assert ps.fraction == pytest.approx(0.25)

    def test_zero_volatility(self):
        ps = volatility_adjusted(
            annualized_volatility=0.0,
            target_volatility=0.15,
            current_price=100.0,
            atr=2.0,
        )
        assert ps.fraction == 0.0


class TestPositionSizeModel:
    def test_to_dict(self):
        ps = PositionSize(
            method="test",
            fraction=0.10,
            max_loss_percent=0.04,
            stop_loss_price=96.0,
        )
        d = ps.to_dict()
        assert d["method"] == "test"
        assert d["fraction"] == 0.10

    def test_format_for_prompt(self):
        ps = PositionSize(
            method="kelly",
            fraction=0.12,
            max_loss_percent=0.04,
            stop_loss_price=144.0,
        )
        text = ps.format_for_prompt()
        assert "kelly" in text
        assert "12.0%" in text
        assert "$144.00" in text
