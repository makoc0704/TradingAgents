"""Tests for tradingagents.live.performance — performance metrics calculation."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from tradingagents.live.performance import calculate_live_performance
from tradingagents.live.models import LiveRunResult, PortfolioSnapshot
from tradingagents.risk.models import TradeSignal


@pytest.fixture
def sample_run_results():
    """Create sample LiveRunResult list for testing."""
    results = []
    
    # Day 1: Buy AAPL
    results.append(LiveRunResult(
        date="2024-06-01",
        signals={"AAPL": TradeSignal(action="BUY", confidence=0.8, position_size=None, risk_metrics=None, reasoning="")},
        executed_orders=[MagicMock(action="BUY", shares=10, commission=1.5, success=True)],
        portfolio_snapshot=PortfolioSnapshot(
            date="2024-06-01",
            cash=850.0,
            positions={"AAPL": {"shares": 10, "avg_entry_price": 150.0}},
            total_value=1000.0,
            daily_return=0.0,
            cumulative_return=0.0,
        ),
        daily_return=0.0,
        cumulative_return=0.0,
        performance_metrics={},
    ))
    
    # Day 2: Hold, price goes up
    results.append(LiveRunResult(
        date="2024-06-02",
        signals={"AAPL": TradeSignal(action="HOLD", confidence=0.7, position_size=None, risk_metrics=None, reasoning="")},
        executed_orders=[MagicMock(action="HOLD", shares=0, commission=0.0, success=True)],
        portfolio_snapshot=PortfolioSnapshot(
            date="2024-06-02",
            cash=850.0,
            positions={"AAPL": {"shares": 10, "avg_entry_price": 150.0}},
            total_value=1100.0,  # Price went up
            daily_return=0.10,
            cumulative_return=0.10,
        ),
        daily_return=0.10,
        cumulative_return=0.10,
        performance_metrics={},
    ))
    
    # Day 3: Sell AAPL
    results.append(LiveRunResult(
        date="2024-06-03",
        signals={"AAPL": TradeSignal(action="SELL", confidence=0.9, position_size=None, risk_metrics=None, reasoning="")},
        executed_orders=[MagicMock(action="SELL", shares=10, commission=1.6, success=True)],
        portfolio_snapshot=PortfolioSnapshot(
            date="2024-06-03",
            cash=1098.4,  # Sold at 110, minus commission
            positions={},
            total_value=1098.4,
            daily_return=-0.0015,
            cumulative_return=0.0984,
        ),
        daily_return=-0.0015,
        cumulative_return=0.0984,
        performance_metrics={},
    ))
    
    return results


class TestCalculateLivePerformance:
    def test_empty_history_returns_empty_metrics(self):
        """calculate_live_performance() returns empty metrics for empty history."""
        metrics = calculate_live_performance([], 1000.0)
        
        assert metrics["total_return"] == 0.0
        assert metrics["total_trades"] == 0
        assert metrics["trading_days"] == 0
    
    def test_calculates_total_return(self, sample_run_results):
        """calculate_live_performance() calculates total return correctly."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        # Final value: 1098.4, Initial: 1000.0
        expected_return = (1098.4 - 1000.0) / 1000.0
        assert metrics["total_return"] == pytest.approx(expected_return, rel=0.01)
    
    def test_calculates_annualized_return(self, sample_run_results):
        """calculate_live_performance() calculates annualized return."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        assert "annualized_return" in metrics
        assert metrics["annualized_return"] > 0  # Positive return
    
    def test_counts_trades(self, sample_run_results):
        """calculate_live_performance() counts trades correctly."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        assert metrics["total_trades"] == 2  # 1 BUY + 1 SELL
        assert metrics["buy_trades"] == 1
        assert metrics["sell_trades"] == 1
    
    def test_calculates_total_commission(self, sample_run_results):
        """calculate_live_performance() sums commissions."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        # 1.5 + 1.6 = 3.1
        assert metrics["total_commission"] == pytest.approx(3.1, rel=0.01)
    
    def test_calculates_exposure_time(self, sample_run_results):
        """calculate_live_performance() calculates exposure time."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        # 2 out of 3 days had positions
        assert metrics["exposure_time"] == pytest.approx(2/3, rel=0.01)
    
    def test_calculates_sharpe_ratio(self, sample_run_results):
        """calculate_live_performance() calculates Sharpe ratio."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        assert "sharpe_ratio" in metrics
        # Sharpe can be positive or negative depending on returns
    
    def test_calculates_max_drawdown(self, sample_run_results):
        """calculate_live_performance() calculates max drawdown."""
        metrics = calculate_live_performance(sample_run_results, 1000.0)
        
        assert "max_drawdown" in metrics
        assert metrics["max_drawdown"] <= 0  # Drawdown is negative or zero
    
    def test_handles_single_run(self):
        """calculate_live_performance() handles single run."""
        single_result = LiveRunResult(
            date="2024-06-01",
            signals={},
            executed_orders=[],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-01",
                cash=1000.0,
                positions={},
                total_value=1000.0,
                daily_return=0.0,
                cumulative_return=0.0,
            ),
            daily_return=0.0,
            cumulative_return=0.0,
            performance_metrics={},
        )
        
        metrics = calculate_live_performance([single_result], 1000.0)
        
        assert metrics["total_return"] == 0.0
        assert metrics["trading_days"] == 1


class TestProfitFactor:
    def test_profit_factor_infinite_when_all_wins(self):
        """profit_factor is inf when there are no losing trades."""
        results = []
        results.append(LiveRunResult(
            date="2024-06-01",
            signals={},
            executed_orders=[MagicMock(action="BUY", shares=1, commission=1.0, success=True)],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-01", cash=0.0, positions={},
                total_value=1000.0, daily_return=0.0, cumulative_return=0.0,
            ),
            daily_return=0.0, cumulative_return=0.0, performance_metrics={},
        ))
        results.append(LiveRunResult(
            date="2024-06-02",
            signals={},
            executed_orders=[MagicMock(action="SELL", shares=1, commission=1.0, success=True)],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-02", cash=1100.0, positions={},
                total_value=1100.0, daily_return=0.10, cumulative_return=0.10,
            ),
            daily_return=0.10, cumulative_return=0.10, performance_metrics={},
        ))
        
        metrics = calculate_live_performance(results, 1000.0)
        assert metrics["profit_factor"] == float("inf")
        assert metrics["win_rate"] == 1.0


class TestWinRateCalculation:
    def test_calculates_win_rate(self):
        """calculate_live_performance() calculates win rate from round trips."""
        # Create results with winning and losing trades
        results = []
        
        # Win: Buy at 1000, sell at 1100
        results.append(LiveRunResult(
            date="2024-06-01",
            signals={},
            executed_orders=[MagicMock(action="BUY", shares=1, commission=1.0, success=True)],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-01",
                cash=0.0,
                positions={},
                total_value=1000.0,
                daily_return=0.0,
                cumulative_return=0.0,
            ),
            daily_return=0.0,
            cumulative_return=0.0,
            performance_metrics={},
        ))
        results.append(LiveRunResult(
            date="2024-06-02",
            signals={},
            executed_orders=[MagicMock(action="SELL", shares=1, commission=1.1, success=True)],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-02",
                cash=1098.9,
                positions={},
                total_value=1100.0,  # Higher than buy
                daily_return=0.10,
                cumulative_return=0.10,
            ),
            daily_return=0.10,
            cumulative_return=0.10,
            performance_metrics={},
        ))
        
        # Loss: Buy at 1000, sell at 900
        results.append(LiveRunResult(
            date="2024-06-03",
            signals={},
            executed_orders=[MagicMock(action="BUY", shares=1, commission=1.0, success=True)],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-03",
                cash=98.9,
                positions={},
                total_value=1000.0,
                daily_return=0.0,
                cumulative_return=0.0,
            ),
            daily_return=0.0,
            cumulative_return=0.0,
            performance_metrics={},
        ))
        results.append(LiveRunResult(
            date="2024-06-04",
            signals={},
            executed_orders=[MagicMock(action="SELL", shares=1, commission=0.9, success=True)],
            portfolio_snapshot=PortfolioSnapshot(
                date="2024-06-04",
                cash=998.0,
                positions={},
                total_value=900.0,  # Lower than buy
                daily_return=-0.10,
                cumulative_return=-0.10,
            ),
            daily_return=-0.10,
            cumulative_return=-0.10,
            performance_metrics={},
        ))
        
        metrics = calculate_live_performance(results, 1000.0)
        
        # 1 win, 1 loss = 50% win rate
        assert metrics["win_rate"] == pytest.approx(0.5, rel=0.01)
