"""Tests for tradingagents.backtesting.runner — BacktestRunner logic.

These tests mock TradingAgentsGraph.propagate() to avoid LLM calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from tradingagents.backtesting.runner import BacktestRunner
from tradingagents.backtesting.models import BacktestConfig, BacktestResult
from tradingagents.risk.models import TradeSignal, PositionSize


@pytest.fixture
def minimal_config():
    """Minimal BacktestConfig for testing."""
    return BacktestConfig(
        ticker="AAPL",
        start_date="2024-06-03",
        end_date="2024-06-07",
        initial_capital=100_000.0,
        trading_frequency="daily",
        commission_rate=0.001,
        slippage_rate=0.0005,
        selected_analysts=["market"],
        backtest_profile="quick",
        reflection_mode="none",
        reflection_interval=20,
        use_data_cache=False,
        config={
            "llm_provider": "openai",
            "quick_think_llm": "gpt-4o-mini",
            "deep_think_llm": "gpt-4o-mini",
            "backend_url": "https://api.openai.com/v1",
        },
    )


class TestGenerateTradingDates:
    def test_daily_skips_weekends(self, minimal_config):
        runner = BacktestRunner(minimal_config)
        dates = runner._generate_trading_dates()
        # June 3-7, 2024: Mon-Fri = 5 weekdays
        assert len(dates) == 5
        for d in dates:
            dt = datetime.strptime(d, "%Y-%m-%d")
            assert dt.weekday() < 5

    def test_weekly_one_per_week(self, minimal_config):
        minimal_config.start_date = "2024-06-01"
        minimal_config.end_date = "2024-06-30"
        minimal_config.trading_frequency = "weekly"
        runner = BacktestRunner(minimal_config)
        dates = runner._generate_trading_dates()
        # June 2024 has ~4 weeks
        assert 4 <= len(dates) <= 5

    def test_monthly_one_per_month(self, minimal_config):
        minimal_config.start_date = "2024-01-01"
        minimal_config.end_date = "2024-06-30"
        minimal_config.trading_frequency = "monthly"
        runner = BacktestRunner(minimal_config)
        dates = runner._generate_trading_dates()
        assert len(dates) == 6

    def test_empty_range(self, minimal_config):
        minimal_config.start_date = "2024-06-08"  # Saturday
        minimal_config.end_date = "2024-06-09"    # Sunday
        runner = BacktestRunner(minimal_config)
        dates = runner._generate_trading_dates()
        assert len(dates) == 0


class TestReflectionLogic:
    def test_none_never_reflects(self, minimal_config):
        minimal_config.reflection_mode = "none"
        runner = BacktestRunner(minimal_config)
        assert runner._should_reflect(100, 50, 100) is False

    def test_end_only_never_during_loop(self, minimal_config):
        minimal_config.reflection_mode = "end_only"
        runner = BacktestRunner(minimal_config)
        assert runner._should_reflect(100, 50, 100) is False

    def test_periodic_triggers_at_interval(self, minimal_config):
        minimal_config.reflection_mode = "periodic"
        minimal_config.reflection_interval = 20
        runner = BacktestRunner(minimal_config)
        assert runner._should_reflect(19, 19, 100) is False
        assert runner._should_reflect(20, 20, 100) is True
        assert runner._should_reflect(25, 25, 100) is True


class TestBacktestProfiles:
    def test_quick_profile_config(self, minimal_config):
        minimal_config.backtest_profile = "quick"
        runner = BacktestRunner(minimal_config)
        config = runner._build_effective_config()
        assert config["max_debate_rounds"] == 1
        assert config["max_risk_discuss_rounds"] == 1

    def test_full_profile_preserves_defaults(self, minimal_config):
        minimal_config.backtest_profile = "full"
        minimal_config.config["max_debate_rounds"] = 3
        runner = BacktestRunner(minimal_config)
        config = runner._build_effective_config()
        # full profile doesn't override debate rounds
        assert config["max_debate_rounds"] == 3
