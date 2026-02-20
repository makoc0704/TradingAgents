"""Tests for tradingagents.live.models — data models."""

import pytest
from datetime import datetime

from tradingagents.live.models import LiveConfig, LiveRunResult, PortfolioSnapshot
from tradingagents.live.broker.interface import OrderResult
from tradingagents.risk.models import TradeSignal, PositionSize


class TestLiveConfig:
    def test_default_values(self):
        """LiveConfig has sensible defaults."""
        config = LiveConfig(tickers=["AAPL"])
        
        assert config.mode == "paper"
        assert config.broker_type == "dummy"
        assert config.initial_capital == 200.0
        assert config.commission_rate == 0.001
        assert config.slippage_rate == 0.0005
    
    def test_custom_values(self):
        """LiveConfig accepts custom values."""
        config = LiveConfig(
            tickers=["NVDA", "MSFT"],
            mode="dry_run",
            broker_type="dummy",
            state_path="custom/path.json",
            initial_capital=5000.0,
            commission_rate=0.002,
            slippage_rate=0.001,
        )
        
        assert config.tickers == ["NVDA", "MSFT"]
        assert config.mode == "dry_run"
        assert config.initial_capital == 5000.0
        assert config.commission_rate == 0.002
    
    def test_to_dict(self):
        """to_dict() serializes config."""
        config = LiveConfig(tickers=["AAPL"], initial_capital=1000.0)
        d = config.to_dict()
        
        assert d["tickers"] == ["AAPL"]
        assert d["initial_capital"] == 1000.0
        assert d["mode"] == "paper"


class TestPortfolioSnapshot:
    def test_creation(self):
        """PortfolioSnapshot can be created."""
        snapshot = PortfolioSnapshot(
            date="2024-06-01",
            cash=500.0,
            positions={"AAPL": {"shares": 10, "avg_entry_price": 150.0}},
            total_value=2000.0,
            daily_return=0.05,
            cumulative_return=0.10,
        )
        
        assert snapshot.date == "2024-06-01"
        assert snapshot.cash == 500.0
        assert snapshot.total_value == 2000.0
        assert snapshot.daily_return == 0.05
    
    def test_to_dict(self):
        """to_dict() serializes snapshot."""
        snapshot = PortfolioSnapshot(
            date="2024-06-01",
            cash=500.0,
            positions={},
            total_value=500.0,
            daily_return=0.0,
            cumulative_return=0.0,
        )
        d = snapshot.to_dict()
        
        assert d["date"] == "2024-06-01"
        assert d["cash"] == 500.0


class TestLiveRunResult:
    def test_creation(self):
        """LiveRunResult can be created."""
        signal = TradeSignal(
            action="BUY",
            confidence=0.8,
            position_size=PositionSize(
                method="fixed_fraction",
                fraction=0.10,
                max_loss_percent=0.05,
                stop_loss_price=145.0,
            ),
            risk_metrics=None,
            reasoning="Test",
        )
        
        snapshot = PortfolioSnapshot(
            date="2024-06-01",
            cash=900.0,
            positions={},
            total_value=1000.0,
            daily_return=0.0,
            cumulative_return=0.0,
        )
        
        result = LiveRunResult(
            date="2024-06-01",
            signals={"AAPL": signal},
            executed_orders=[],
            portfolio_snapshot=snapshot,
            daily_return=0.0,
            cumulative_return=0.0,
            performance_metrics={},
        )
        
        assert result.date == "2024-06-01"
        assert len(result.signals) == 1
        assert result.signals["AAPL"].action == "BUY"
    
    def test_to_dict_serializes_signals(self):
        """to_dict() converts TradeSignal objects to dicts."""
        signal = TradeSignal(
            action="BUY",
            confidence=0.8,
            position_size=None,
            risk_metrics=None,
            reasoning="Test",
        )
        
        snapshot = PortfolioSnapshot(
            date="2024-06-01",
            cash=1000.0,
            positions={},
            total_value=1000.0,
            daily_return=0.0,
            cumulative_return=0.0,
        )
        
        result = LiveRunResult(
            date="2024-06-01",
            signals={"AAPL": signal},
            executed_orders=[],
            portfolio_snapshot=snapshot,
            daily_return=0.0,
            cumulative_return=0.0,
            performance_metrics={},
        )
        
        d = result.to_dict()
        assert isinstance(d["signals"]["AAPL"], dict)
        assert d["signals"]["AAPL"]["action"] == "BUY"
        assert d["signals"]["AAPL"]["confidence"] == 0.8
    
    def test_to_dict_with_real_order_results(self):
        """to_dict() serializes real OrderResult dataclass objects."""
        order = OrderResult(
            success=True,
            order_id="buy-2024-06-01-AAPL",
            ticker="AAPL",
            action="BUY",
            shares=5,
            execution_price=150.075,
            commission=0.75,
            message="Bought 5 shares",
            timestamp="2024-06-01T10:00:00",
        )
        signal = TradeSignal(
            action="BUY", confidence=0.8, position_size=None,
            risk_metrics=None, reasoning="Test",
        )
        snapshot = PortfolioSnapshot(
            date="2024-06-01", cash=250.0, positions={},
            total_value=1000.0, daily_return=0.0, cumulative_return=0.0,
        )
        
        result = LiveRunResult(
            date="2024-06-01",
            signals={"AAPL": signal},
            executed_orders=[order],
            portfolio_snapshot=snapshot,
            daily_return=0.0,
            cumulative_return=0.0,
            performance_metrics={},
        )
        
        d = result.to_dict()
        assert isinstance(d["executed_orders"][0], dict)
        assert d["executed_orders"][0]["ticker"] == "AAPL"
        assert d["executed_orders"][0]["shares"] == 5
        assert d["executed_orders"][0]["success"] is True
