"""Tests for tradingagents.backtesting.portfolio — paper trade execution."""

import pytest

from tradingagents.backtesting.portfolio import Portfolio
from tradingagents.backtesting.models import TradeRecord, DailySnapshot
from tradingagents.risk.models import TradeSignal, PositionSize


@pytest.fixture
def portfolio():
    """Standard portfolio with 100k capital."""
    return Portfolio(
        initial_capital=100_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )


@pytest.fixture
def sample_signal():
    """BUY signal with 10% position size."""
    return TradeSignal(
        action="BUY",
        confidence=0.8,
        position_size=PositionSize(
            method="volatility_adjusted",
            fraction=0.10,
            max_loss_percent=0.04,
            stop_loss_price=145.0,
        ),
        risk_metrics=None,
        reasoning="Test signal",
    )


class TestPortfolioInit:
    def test_initial_state(self, portfolio):
        assert portfolio.cash == 100_000.0
        assert portfolio.shares == 0
        assert portfolio.get_value(100.0) == 100_000.0

    def test_custom_capital(self):
        p = Portfolio(initial_capital=50_000.0)
        assert p.cash == 50_000.0


class TestExecuteBuy:
    def test_basic_buy(self, portfolio):
        trade = portfolio.execute_buy("AAPL", 150.0, 0.10, "2024-06-01")
        assert trade.action == "BUY"
        assert trade.ticker == "AAPL"
        assert trade.shares > 0
        assert trade.commission > 0
        assert portfolio.shares == trade.shares
        assert portfolio.cash < 100_000.0

    def test_buy_respects_fraction(self, portfolio):
        trade = portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        # 20% of 100k = 20k, at ~$100.05 (slipped) = ~199 shares
        expected_max_shares = int(20_000 / (100.0 * 1.0005))
        assert abs(trade.shares - expected_max_shares) <= 1

    def test_buy_slippage_increases_price(self, portfolio):
        trade = portfolio.execute_buy("AAPL", 100.0, 0.10, "2024-06-01")
        assert trade.price > 100.0  # Slipped up

    def test_buy_commission_deducted(self, portfolio):
        trade = portfolio.execute_buy("AAPL", 100.0, 0.10, "2024-06-01")
        expected_trade_value = trade.shares * trade.price
        expected_commission = expected_trade_value * 0.001
        assert trade.commission == pytest.approx(expected_commission, rel=1e-4)

    def test_buy_insufficient_funds(self):
        p = Portfolio(initial_capital=10.0)
        trade = p.execute_buy("AAPL", 150.0, 0.10, "2024-06-01")
        # Can't afford even 1 share at $150
        assert trade.action == "HOLD"
        assert trade.shares == 0

    def test_multiple_buys_accumulate(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.10, "2024-06-01")
        first_shares = portfolio.shares
        portfolio.execute_buy("AAPL", 100.0, 0.10, "2024-06-02")
        assert portfolio.shares > first_shares

    def test_no_negative_cash(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.50, "2024-06-01")
        portfolio.execute_buy("AAPL", 100.0, 0.50, "2024-06-02")
        assert portfolio.cash >= 0


class TestExecuteSell:
    def test_basic_sell(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        shares_before = portfolio.shares
        trade = portfolio.execute_sell("AAPL", 110.0, "2024-06-02")
        assert trade.action == "SELL"
        assert trade.shares == shares_before
        assert portfolio.shares == 0
        assert portfolio.cash > 0

    def test_sell_slippage_decreases_price(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        trade = portfolio.execute_sell("AAPL", 100.0, "2024-06-02")
        assert trade.price < 100.0  # Slipped down

    def test_sell_no_position(self, portfolio):
        trade = portfolio.execute_sell("AAPL", 100.0, "2024-06-01")
        assert trade.action == "HOLD"
        assert trade.shares == 0

    def test_profitable_roundtrip(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        cash_after_buy = portfolio.cash
        portfolio.execute_sell("AAPL", 120.0, "2024-06-15")
        # Sold at $120 (minus slippage), should have more cash now
        assert portfolio.cash > cash_after_buy

    def test_losing_roundtrip(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        cash_after_buy = portfolio.cash
        portfolio.execute_sell("AAPL", 80.0, "2024-06-15")
        # Sold at loss, but still have some cash back
        assert portfolio.cash > cash_after_buy
        # Portfolio value should be less than initial
        assert portfolio.get_value(80.0) < 100_000.0


class TestHold:
    def test_hold_no_changes(self, portfolio):
        trade = portfolio.hold("AAPL", 100.0, "2024-06-01")
        assert trade.action == "HOLD"
        assert trade.shares == 0
        assert trade.commission == 0.0
        assert portfolio.cash == 100_000.0

    def test_hold_with_position(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        shares = portfolio.shares
        cash = portfolio.cash
        trade = portfolio.hold("AAPL", 105.0, "2024-06-02")
        assert portfolio.shares == shares
        assert portfolio.cash == cash
        assert trade.portfolio_value == pytest.approx(cash + shares * 105.0)


class TestExecuteSignal:
    def test_dispatch_buy(self, portfolio, sample_signal):
        trade = portfolio.execute_signal(sample_signal, "AAPL", 150.0, "2024-06-01")
        assert trade.action == "BUY"

    def test_dispatch_sell(self, portfolio):
        portfolio.execute_buy("AAPL", 150.0, 0.10, "2024-06-01")
        sell_signal = TradeSignal(
            action="SELL", confidence=0.7,
            position_size=None, risk_metrics=None,
            reasoning="Sell test",
        )
        trade = portfolio.execute_signal(sell_signal, "AAPL", 155.0, "2024-06-02")
        assert trade.action == "SELL"

    def test_dispatch_hold(self, portfolio):
        hold_signal = TradeSignal(
            action="HOLD", confidence=0.5,
            position_size=None, risk_metrics=None,
            reasoning="Hold test",
        )
        trade = portfolio.execute_signal(hold_signal, "AAPL", 150.0, "2024-06-01")
        assert trade.action == "HOLD"

    def test_plain_string_signal(self, portfolio):
        trade = portfolio.execute_signal("BUY", "AAPL", 150.0, "2024-06-01")
        assert trade.action == "BUY"

    def test_uses_position_size_fraction(self, portfolio, sample_signal):
        trade = portfolio.execute_signal(sample_signal, "AAPL", 100.0, "2024-06-01")
        # 10% of 100k = 10k, at ~$100.05 = ~99 shares
        assert 90 <= trade.shares <= 110


class TestDailySnapshot:
    def test_snapshot_initial(self, portfolio):
        snap = portfolio.get_daily_snapshot("2024-06-01", 100.0, "HOLD")
        assert isinstance(snap, DailySnapshot)
        assert snap.portfolio_value == 100_000.0
        assert snap.daily_return == 0.0
        assert snap.cumulative_return == 0.0

    def test_snapshot_after_price_change(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.50, "2024-06-01")
        portfolio.get_daily_snapshot("2024-06-01", 100.0, "BUY")
        snap = portfolio.get_daily_snapshot("2024-06-02", 110.0, "HOLD")
        assert snap.daily_return > 0
        assert snap.cumulative_return > 0

    def test_snapshot_tracks_position(self, portfolio):
        portfolio.execute_buy("AAPL", 100.0, 0.20, "2024-06-01")
        snap = portfolio.get_daily_snapshot("2024-06-01", 100.0, "BUY")
        assert snap.position_shares == portfolio.shares
        assert snap.position_shares > 0
