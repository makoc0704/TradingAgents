"""Tests for tradingagents.live.broker.dummy — DummyBroker paper trading."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from tradingagents.live.broker.dummy import DummyBroker
from tradingagents.live.state import LivePortfolioState
from tradingagents.risk.models import TradeSignal, PositionSize


@pytest.fixture
def mock_state():
    """Create a mock LivePortfolioState."""
    state = MagicMock(spec=LivePortfolioState)
    state.get_cash.return_value = 1000.0
    state.get_all_positions.return_value = []
    state.get_position.return_value = None
    return state


@pytest.fixture
def dummy_broker(mock_state):
    """Create a DummyBroker with mocked state."""
    return DummyBroker(
        state=mock_state,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )


@pytest.fixture
def buy_signal():
    """Create a BUY signal."""
    return TradeSignal(
        action="BUY",
        confidence=0.8,
        position_size=PositionSize(
            method="fixed_fraction",
            fraction=0.10,
            max_loss_percent=0.05,
            stop_loss_price=145.0,
        ),
        risk_metrics=None,
        reasoning="Test buy signal",
    )


@pytest.fixture
def sell_signal():
    """Create a SELL signal."""
    return TradeSignal(
        action="SELL",
        confidence=0.9,
        position_size=None,
        risk_metrics=None,
        reasoning="Test sell signal",
    )


@pytest.fixture
def hold_signal():
    """Create a HOLD signal."""
    return TradeSignal(
        action="HOLD",
        confidence=0.5,
        position_size=None,
        risk_metrics=None,
        reasoning="Test hold signal",
    )


class TestDummyBrokerInit:
    def test_initializes_with_state(self, mock_state):
        """DummyBroker initializes with state."""
        broker = DummyBroker(mock_state, 0.001, 0.0005)
        assert broker.state == mock_state
        assert broker.commission_rate == 0.001
        assert broker.slippage_rate == 0.0005


class TestPlaceOrderBuy:
    def test_buy_executes_successfully(self, dummy_broker, mock_state, buy_signal):
        """BUY order executes and updates state."""
        mock_state.get_cash.return_value = 10000.0
        
        result = dummy_broker.place_order("AAPL", buy_signal, 150.0, "2024-06-01")
        
        assert result.success is True
        assert result.action == "BUY"
        assert result.shares > 0
        assert result.execution_price > 150.0  # Slippage increases price
        assert result.commission > 0
        mock_state.add_position.assert_called_once()
        mock_state.subtract_cash.assert_called_once()
        mock_state.record_trade.assert_called_once()
    
    def test_buy_respects_fraction(self, dummy_broker, mock_state, buy_signal):
        """BUY order respects position_size.fraction."""
        mock_state.get_cash.return_value = 10000.0
        
        result = dummy_broker.place_order("AAPL", buy_signal, 10.0, "2024-06-01")
        
        # 10% of $10000 = $1000, at ~$10.005 (slipped) → 99 shares
        assert result.success is True
        assert result.action == "BUY"
        assert result.shares == 99
    
    def test_buy_insufficient_funds(self, dummy_broker, mock_state, buy_signal):
        """BUY order returns HOLD if insufficient funds."""
        mock_state.get_cash.return_value = 5.0  # Very little cash
        
        result = dummy_broker.place_order("AAPL", buy_signal, 150.0, "2024-06-01")
        
        assert result.success is False
        assert result.action == "HOLD"
        assert result.shares == 0
        assert "Insufficient funds" in result.message
    
    def test_buy_invalid_price(self, dummy_broker, mock_state, buy_signal):
        """BUY order returns HOLD if price is invalid."""
        mock_state.get_cash.return_value = 10000.0
        
        result = dummy_broker.place_order("AAPL", buy_signal, 0.0, "2024-06-01")
        
        assert result.success is False
        assert result.action == "HOLD"
        assert "Invalid price" in result.message
    
    def test_buy_applies_slippage(self, dummy_broker, mock_state, buy_signal):
        """BUY order applies slippage (price goes up)."""
        mock_state.get_cash.return_value = 10000.0
        
        result = dummy_broker.place_order("AAPL", buy_signal, 100.0, "2024-06-01")
        
        assert result.success is True
        assert result.execution_price > 100.0
        expected_slipped = 100.0 * (1 + 0.0005)
        assert result.execution_price == pytest.approx(expected_slipped, rel=0.01)


    def test_buy_without_position_size_uses_default(self, dummy_broker, mock_state):
        """BUY without position_size uses default fraction of 0.10."""
        signal = TradeSignal(
            action="BUY",
            confidence=0.7,
            position_size=None,
            risk_metrics=None,
            reasoning="No position size",
        )
        mock_state.get_cash.return_value = 10000.0
        
        result = dummy_broker.place_order("AAPL", signal, 50.0, "2024-06-01")
        
        # Default fraction 0.10 of $10000 = $1000, at ~$50.025 = 19 shares
        assert result.success is True
        assert result.action == "BUY"
        assert result.shares == 19


class TestPlaceOrderSell:
    def test_sell_executes_successfully(self, dummy_broker, mock_state, sell_signal):
        """SELL order executes and updates state."""
        from tradingagents.live.broker.interface import Position
        
        # Setup: existing position
        mock_position = Position(
            ticker="AAPL",
            shares=10,
            avg_entry_price=150.0,
            current_price=160.0,
        )
        mock_state.get_position.return_value = mock_position
        mock_state.get_cash.return_value = 500.0
        
        result = dummy_broker.place_order("AAPL", sell_signal, 160.0, "2024-06-01")
        
        assert result.success is True
        assert result.action == "SELL"
        assert result.shares == 10
        assert result.execution_price < 160.0  # Slippage decreases price
        assert result.commission > 0
        # Verify state was updated
        mock_state.remove_position.assert_called_once_with("AAPL")
        mock_state.add_cash.assert_called_once()
        mock_state.record_trade.assert_called_once()
    
    def test_sell_no_position(self, dummy_broker, mock_state, sell_signal):
        """SELL order returns HOLD if no position exists."""
        mock_state.get_position.return_value = None
        
        result = dummy_broker.place_order("AAPL", sell_signal, 160.0, "2024-06-01")
        
        assert result.success is False
        assert result.action == "HOLD"
        assert "No position to sell" in result.message
    
    def test_sell_applies_slippage(self, dummy_broker, mock_state, sell_signal):
        """SELL order applies slippage (price goes down)."""
        from tradingagents.live.broker.interface import Position
        
        mock_position = Position(
            ticker="AAPL",
            shares=10,
            avg_entry_price=150.0,
            current_price=160.0,
        )
        mock_state.get_position.return_value = mock_position
        mock_state.get_cash.return_value = 500.0
        
        result = dummy_broker.place_order("AAPL", sell_signal, 160.0, "2024-06-01")
        
        if result.success:
            assert result.execution_price < 160.0
            expected_slipped = 160.0 * (1 - 0.0005)
            assert result.execution_price == pytest.approx(expected_slipped, rel=0.01)


class TestPlaceOrderSellEdgeCases:
    def test_sell_at_zero_price_refused(self, dummy_broker, mock_state, sell_signal):
        """SELL at price=0 returns failure instead of destroying value."""
        from tradingagents.live.broker.interface import Position

        mock_position = Position(
            ticker="AAPL", shares=10, avg_entry_price=150.0, current_price=0.0,
        )
        mock_state.get_position.return_value = mock_position

        result = dummy_broker.place_order("AAPL", sell_signal, 0.0, "2024-06-01")

        assert result.success is False
        assert result.action == "HOLD"
        assert "zero" in result.message.lower()

    def test_failed_order_records_hold_trade(self, dummy_broker, mock_state, buy_signal):
        """Failed BUY (insufficient funds) records a HOLD trade in history."""
        mock_state.get_cash.return_value = 1.0
        dummy_broker.place_order("AAPL", buy_signal, 150.0, "2024-06-01")
        mock_state.record_trade.assert_called_once_with(
            "2024-06-01", "AAPL", "HOLD", 150.0, 0, 0.0,
        )


class TestPlaceOrderHold:
    def test_hold_returns_success(self, dummy_broker, mock_state, hold_signal):
        """HOLD order returns success with no execution."""
        result = dummy_broker.place_order("AAPL", hold_signal, 150.0, "2024-06-01")
        
        assert result.success is True
        assert result.action == "HOLD"
        assert result.shares == 0
        assert result.commission == 0.0
        # State should not be modified
        mock_state.add_position.assert_not_called()
        mock_state.remove_position.assert_not_called()


class TestBrokerGetters:
    def test_get_positions(self, dummy_broker, mock_state):
        """get_positions() delegates to state."""
        from tradingagents.live.broker.interface import Position
        
        mock_positions = [
            Position("AAPL", 10, 150.0, 160.0),
            Position("NVDA", 5, 500.0, 520.0),
        ]
        mock_state.get_all_positions.return_value = mock_positions
        
        positions = dummy_broker.get_positions()
        assert positions == mock_positions
        mock_state.get_all_positions.assert_called_once()
    
    def test_get_cash(self, dummy_broker, mock_state):
        """get_cash() delegates to state."""
        mock_state.get_cash.return_value = 750.0
        assert dummy_broker.get_cash() == 750.0
        mock_state.get_cash.assert_called_once()
    
    def test_get_portfolio_value(self, dummy_broker, mock_state):
        """get_portfolio_value() calculates from cash and positions."""
        from tradingagents.live.broker.interface import Position
        
        mock_state.get_cash.return_value = 500.0
        mock_positions = [
            Position("AAPL", 10, 150.0, 150.0),
        ]
        mock_state.get_all_positions.return_value = mock_positions
        
        value = dummy_broker.get_portfolio_value()
        # Cash (500) + Position (10 * 150 = 1500) = 2000
        assert value == 2000.0
    
    def test_get_last_price(self, dummy_broker, mock_state):
        """get_last_price() returns avg_entry_price from position."""
        from tradingagents.live.broker.interface import Position
        
        mock_position = Position("AAPL", 10, 150.0, 150.0)
        mock_state.get_position.return_value = mock_position
        
        price = dummy_broker.get_last_price("AAPL")
        assert price == 150.0
    
    def test_get_last_price_no_position(self, dummy_broker, mock_state):
        """get_last_price() returns 0.0 if no position."""
        mock_state.get_position.return_value = None
        price = dummy_broker.get_last_price("AAPL")
        assert price == 0.0
