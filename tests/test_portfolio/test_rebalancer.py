"""Tests for tradingagents.portfolio.rebalancer."""

import pytest
from tradingagents.portfolio.rebalancer import Rebalancer
from tradingagents.portfolio.models import Position


def _pos(ticker, shares, price, target_w, actual_w):
    return Position(
        ticker=ticker, shares=shares, avg_entry_price=price,
        current_price=price, target_weight=target_w, actual_weight=actual_w,
    )


class TestCheckDrift:
    def test_no_drift(self):
        r = Rebalancer(threshold=0.05)
        # 100 shares @ 150 = 15,000 position + 15,000 cash = 30,000 total
        # actual weight = 15,000 / 30,000 = 0.50 => matches target
        positions = {
            "AAPL": _pos("AAPL", 100, 150.0, 0.50, 0.50),
        }
        assert r.check_drift(
            positions, {"AAPL": 0.50}, cash=15_000, prices={"AAPL": 150.0},
        ) is False

    def test_drift_detected(self):
        r = Rebalancer(threshold=0.05)
        positions = {
            "AAPL": _pos("AAPL", 100, 150.0, 0.50, 0.70),
        }
        assert r.check_drift(
            positions, {"AAPL": 0.50}, cash=10_000, prices={"AAPL": 150.0},
        ) is True

    def test_new_ticker_with_weight_triggers(self):
        r = Rebalancer(threshold=0.05)
        assert r.check_drift(
            {}, {"NVDA": 0.50}, cash=100_000, prices={"NVDA": 120.0},
        ) is True


class TestGenerateOrders:
    def test_overweight_generates_sell(self):
        r = Rebalancer(threshold=0.05, min_trade_value=100)
        positions = {
            "AAPL": _pos("AAPL", 100, 150.0, 0.30, 0.60),
        }
        orders = r.generate_orders(
            positions, {"AAPL": 0.30}, {"AAPL": 150.0},
            cash=10_000, total_value=25_000,
        )
        sell_orders = [o for o in orders if o.action == "SELL"]
        assert len(sell_orders) >= 1
        assert sell_orders[0].ticker == "AAPL"

    def test_underweight_generates_buy(self):
        r = Rebalancer(threshold=0.05, min_trade_value=100)
        orders = r.generate_orders(
            {}, {"NVDA": 0.50}, {"NVDA": 120.0},
            cash=100_000, total_value=100_000,
        )
        buy_orders = [o for o in orders if o.action == "BUY"]
        assert len(buy_orders) >= 1
        assert buy_orders[0].ticker == "NVDA"

    def test_sells_before_buys(self):
        r = Rebalancer(threshold=0.05, min_trade_value=100)
        # AAPL: 500 shares @ 150 = 75,000 in a 100k portfolio => 75% actual, target 20% => SELL
        # NVDA: 0 shares, target 40% => BUY
        positions = {
            "AAPL": _pos("AAPL", 500, 150.0, 0.20, 0.75),
        }
        orders = r.generate_orders(
            positions, {"AAPL": 0.20, "NVDA": 0.40}, {"AAPL": 150.0, "NVDA": 120.0},
            cash=25_000, total_value=100_000,
        )
        assert len(orders) >= 2
        sell_idx = next(i for i, o in enumerate(orders) if o.action == "SELL")
        buy_idx = next(i for i, o in enumerate(orders) if o.action == "BUY")
        assert sell_idx < buy_idx

    def test_no_orders_within_threshold(self):
        r = Rebalancer(threshold=0.10, min_trade_value=100)
        # 300 shares @ 150 = 45,000 in a 100k portfolio => 45% actual, target 50%
        # drift = |0.45 - 0.50| = 0.05 < threshold 0.10 => no orders
        positions = {
            "AAPL": _pos("AAPL", 300, 150.0, 0.50, 0.45),
        }
        orders = r.generate_orders(
            positions, {"AAPL": 0.50}, {"AAPL": 150.0},
            cash=55_000, total_value=100_000,
        )
        assert len(orders) == 0


class TestShouldRebalanceToday:
    def test_daily_always(self):
        r = Rebalancer()
        dates = ["2024-06-03", "2024-06-04", "2024-06-05"]
        assert r.should_rebalance_today(1, "daily", dates) is True

    def test_weekly_new_week(self):
        r = Rebalancer()
        dates = ["2024-06-07", "2024-06-10"]  # Fri -> Mon
        assert r.should_rebalance_today(1, "weekly", dates) is True

    def test_weekly_same_week(self):
        r = Rebalancer()
        dates = ["2024-06-03", "2024-06-04"]  # Mon -> Tue
        assert r.should_rebalance_today(1, "weekly", dates) is False

    def test_monthly_new_month(self):
        r = Rebalancer()
        dates = ["2024-05-31", "2024-06-03"]
        assert r.should_rebalance_today(1, "monthly", dates) is True

    def test_first_day_always(self):
        r = Rebalancer()
        dates = ["2024-06-03"]
        assert r.should_rebalance_today(0, "weekly", dates) is True
