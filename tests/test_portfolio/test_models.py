"""Tests for tradingagents.portfolio.models."""

import pytest
from tradingagents.portfolio.models import (
    PortfolioConfig,
    Position,
    AllocationResult,
    RebalanceOrder,
    PortfolioSnapshot,
    PortfolioResult,
)


class TestPortfolioConfig:
    def test_default_values(self):
        cfg = PortfolioConfig(tickers=["AAPL"], start_date="2024-01-01", end_date="2024-06-01")
        assert cfg.initial_capital == 100_000.0
        assert cfg.weighting_strategy == "equal"
        assert cfg.max_position_fraction == 0.30

    def test_to_dict_excludes_config(self):
        cfg = PortfolioConfig(
            tickers=["AAPL", "NVDA"],
            start_date="2024-01-01",
            end_date="2024-06-01",
            config={"llm_provider": "openai"},
        )
        d = cfg.to_dict()
        assert "config" not in d
        assert d["tickers"] == ["AAPL", "NVDA"]


class TestPosition:
    def test_market_value(self):
        pos = Position(
            ticker="AAPL", shares=10, avg_entry_price=150.0,
            current_price=160.0, target_weight=0.25, actual_weight=0.20,
        )
        assert pos.market_value == 1600.0

    def test_to_dict_includes_market_value(self):
        pos = Position(
            ticker="NVDA", shares=5, avg_entry_price=100.0,
            current_price=120.0, target_weight=0.30, actual_weight=0.28,
        )
        d = pos.to_dict()
        assert d["market_value"] == 600.0


class TestAllocationResult:
    def test_to_dict(self):
        ar = AllocationResult(
            weights={"AAPL": 0.5, "NVDA": 0.5},
            method="equal",
        )
        d = ar.to_dict()
        assert d["method"] == "equal"
        assert d["weights"]["AAPL"] == 0.5


class TestRebalanceOrder:
    def test_to_dict(self):
        order = RebalanceOrder(
            ticker="AAPL", action="BUY", target_shares=10,
            estimated_value=1500.0, reason="Underweight",
        )
        d = order.to_dict()
        assert d["action"] == "BUY"
        assert d["estimated_value"] == 1500.0


class TestPortfolioSnapshot:
    def test_to_dict(self):
        pos = Position(
            ticker="AAPL", shares=10, avg_entry_price=150.0,
            current_price=160.0, target_weight=0.5, actual_weight=0.5,
        )
        snap = PortfolioSnapshot(
            date="2024-06-01",
            total_value=101000.0,
            cash=99400.0,
            positions={"AAPL": pos},
            allocation=None,
            daily_return=0.01,
            cumulative_return=0.01,
            actions={"AAPL": "BUY"},
        )
        d = snap.to_dict()
        assert d["date"] == "2024-06-01"
        assert "AAPL" in d["positions"]
        assert d["positions"]["AAPL"]["market_value"] == 1600.0
