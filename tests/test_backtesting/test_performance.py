"""Tests for tradingagents.backtesting.performance — aggregate metrics."""

import pytest

from tradingagents.backtesting.performance import (
    calculate_backtest_performance,
    _count_wins_losses,
    _calculate_profit_loss,
)
from tradingagents.backtesting.models import DailySnapshot, TradeRecord


def _make_snapshot(date, value, daily_ret=0.0, cum_ret=0.0, shares=0, action="HOLD"):
    return DailySnapshot(
        date=date,
        portfolio_value=value,
        cash=value - shares * 100,
        position_shares=shares,
        position_value=shares * 100,
        daily_return=daily_ret,
        cumulative_return=cum_ret,
        action=action,
    )


def _make_trade(date, action, portfolio_value, shares=0, commission=0.0):
    return TradeRecord(
        date=date,
        ticker="TEST",
        action=action,
        signal=None,
        price=100.0,
        shares=shares,
        commission=commission,
        portfolio_value=portfolio_value,
        cash=portfolio_value,
        position_value=0.0,
    )


class TestBacktestPerformance:
    def test_empty_snapshots(self):
        result = calculate_backtest_performance([], [], 100_000)
        assert result["total_return"] == 0.0
        assert result["trading_days"] == 0

    def test_flat_performance(self):
        snapshots = [
            _make_snapshot("2024-01-01", 100_000),
            _make_snapshot("2024-01-02", 100_000),
            _make_snapshot("2024-01-03", 100_000),
        ]
        result = calculate_backtest_performance(snapshots, [], 100_000)
        assert result["total_return"] == pytest.approx(0.0)
        assert result["max_drawdown"] == pytest.approx(0.0)

    def test_positive_return(self):
        snapshots = [
            _make_snapshot("2024-01-01", 100_000, 0.0, 0.0),
            _make_snapshot("2024-01-02", 101_000, 0.01, 0.01),
            _make_snapshot("2024-01-03", 110_000, 0.089, 0.10),
        ]
        result = calculate_backtest_performance(snapshots, [], 100_000)
        assert result["total_return"] == pytest.approx(0.10)
        assert result["final_portfolio_value"] == 110_000

    def test_negative_return(self):
        snapshots = [
            _make_snapshot("2024-01-01", 100_000),
            _make_snapshot("2024-01-02", 95_000, -0.05, -0.05),
        ]
        result = calculate_backtest_performance(snapshots, [], 100_000)
        assert result["total_return"] == pytest.approx(-0.05)

    def test_exposure_time(self):
        snapshots = [
            _make_snapshot("2024-01-01", 100_000, shares=0),
            _make_snapshot("2024-01-02", 100_000, shares=100),
            _make_snapshot("2024-01-03", 100_000, shares=100),
            _make_snapshot("2024-01-04", 100_000, shares=0),
        ]
        result = calculate_backtest_performance(snapshots, [], 100_000)
        assert result["exposure_time"] == pytest.approx(0.5)

    def test_commission_tracking(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000, shares=100, commission=10.0),
            _make_trade("2024-01-05", "SELL", 102_000, shares=100, commission=10.2),
        ]
        snapshots = [
            _make_snapshot("2024-01-01", 100_000),
            _make_snapshot("2024-01-05", 102_000, 0.02, 0.02),
        ]
        result = calculate_backtest_performance(snapshots, trades, 100_000)
        assert result["total_commission"] == pytest.approx(20.2)
        assert result["total_trades"] == 2


class TestWinsLosses:
    def test_one_win(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000),
            _make_trade("2024-01-05", "SELL", 105_000),
        ]
        wins, losses = _count_wins_losses(trades)
        assert wins == 1
        assert losses == 0

    def test_one_loss(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000),
            _make_trade("2024-01-05", "SELL", 95_000),
        ]
        wins, losses = _count_wins_losses(trades)
        assert wins == 0
        assert losses == 1

    def test_mixed(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000),
            _make_trade("2024-01-05", "SELL", 105_000),
            _make_trade("2024-01-10", "BUY", 105_000),
            _make_trade("2024-01-15", "SELL", 100_000),
        ]
        wins, losses = _count_wins_losses(trades)
        assert wins == 1
        assert losses == 1

    def test_hold_ignored(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000),
            _make_trade("2024-01-02", "HOLD", 101_000),
            _make_trade("2024-01-03", "HOLD", 102_000),
            _make_trade("2024-01-05", "SELL", 105_000),
        ]
        wins, losses = _count_wins_losses(trades)
        assert wins == 1
        assert losses == 0


class TestProfitLoss:
    def test_profit(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000),
            _make_trade("2024-01-05", "SELL", 110_000),
        ]
        profit, loss = _calculate_profit_loss(trades)
        assert profit == 10_000
        assert loss == 0.0

    def test_loss(self):
        trades = [
            _make_trade("2024-01-01", "BUY", 100_000),
            _make_trade("2024-01-05", "SELL", 90_000),
        ]
        profit, loss = _calculate_profit_loss(trades)
        assert profit == 0.0
        assert loss == -10_000

    def test_empty(self):
        profit, loss = _calculate_profit_loss([])
        assert profit == 0.0
        assert loss == 0.0
