"""Tests for tradingagents.portfolio.multi_portfolio."""

import pytest
from tradingagents.portfolio.multi_portfolio import MultiAssetPortfolio


class TestInit:
    def test_initial_state(self):
        p = MultiAssetPortfolio(initial_capital=50_000)
        assert p.cash == 50_000
        assert p.get_total_value({}) == 50_000

    def test_no_positions(self):
        p = MultiAssetPortfolio()
        assert p.get_all_positions({}) == {}


class TestExecuteBuy:
    def test_basic_buy(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        tr = p.execute_order("AAPL", "BUY", 150.0, 0.10, "2024-06-01")
        assert tr.action == "BUY"
        assert tr.ticker == "AAPL"
        assert tr.shares > 0
        assert p.cash < 100_000

    def test_two_tickers(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        p.execute_order("AAPL", "BUY", 150.0, 0.30, "2024-06-01")
        p.execute_order("NVDA", "BUY", 120.0, 0.30, "2024-06-01")

        pos = p.get_all_positions({"AAPL": 150.0, "NVDA": 120.0})
        assert "AAPL" in pos
        assert "NVDA" in pos
        assert pos["AAPL"].shares > 0
        assert pos["NVDA"].shares > 0

    def test_insufficient_funds_becomes_hold(self):
        p = MultiAssetPortfolio(initial_capital=100, commission_rate=0, slippage_rate=0)
        tr = p.execute_order("AAPL", "BUY", 150.0, 0.10, "2024-06-01")
        assert tr.action == "HOLD"


class TestExecuteSell:
    def test_sell_whole_position(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        p.execute_order("AAPL", "BUY", 150.0, 0.50, "2024-06-01")
        tr = p.execute_order("AAPL", "SELL", 160.0, 0.0, "2024-06-02")
        assert tr.action == "SELL"
        assert tr.shares > 0

        pos = p.get_all_positions({"AAPL": 160.0})
        assert "AAPL" not in pos

    def test_sell_no_position_becomes_hold(self):
        p = MultiAssetPortfolio()
        tr = p.execute_order("AAPL", "SELL", 150.0, 0.0, "2024-06-01")
        assert tr.action == "HOLD"

    def test_sell_one_keep_other(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        p.execute_order("AAPL", "BUY", 150.0, 0.30, "2024-06-01")
        p.execute_order("NVDA", "BUY", 120.0, 0.30, "2024-06-01")
        p.execute_order("AAPL", "SELL", 155.0, 0.0, "2024-06-02")

        pos = p.get_all_positions({"AAPL": 155.0, "NVDA": 120.0})
        assert "AAPL" not in pos
        assert "NVDA" in pos


class TestHold:
    def test_hold_no_changes(self):
        p = MultiAssetPortfolio(initial_capital=100_000)
        tr = p.execute_order("AAPL", "HOLD", 150.0, 0.0, "2024-06-01")
        assert tr.action == "HOLD"
        assert tr.shares == 0
        assert p.cash == 100_000


class TestTotalValue:
    def test_cash_plus_positions(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        p.execute_order("AAPL", "BUY", 100.0, 0.50, "2024-06-01")
        value = p.get_total_value({"AAPL": 110.0})
        assert value > 100_000


class TestSnapshot:
    def test_snapshot_values(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        p.execute_order("AAPL", "BUY", 100.0, 0.50, "2024-06-01")

        snap = p.get_snapshot(
            date="2024-06-01",
            prices={"AAPL": 100.0},
            actions={"AAPL": "BUY"},
        )
        assert snap.date == "2024-06-01"
        assert snap.total_value == pytest.approx(100_000, rel=0.01)
        assert "AAPL" in snap.positions
        assert snap.actions["AAPL"] == "BUY"

    def test_snapshot_daily_return(self):
        p = MultiAssetPortfolio(initial_capital=100_000, commission_rate=0, slippage_rate=0)
        p.execute_order("AAPL", "BUY", 100.0, 0.50, "2024-06-01")
        p.get_snapshot("2024-06-01", {"AAPL": 100.0}, {"AAPL": "BUY"})

        snap2 = p.get_snapshot("2024-06-02", {"AAPL": 110.0}, {"AAPL": "HOLD"})
        assert snap2.daily_return > 0


class TestTargetWeights:
    def test_set_and_get_target(self):
        p = MultiAssetPortfolio()
        p.set_target_weights({"AAPL": 0.5, "NVDA": 0.3})
        pos = p.get_position("AAPL")
        assert pos is None  # No shares yet
