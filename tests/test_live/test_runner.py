"""Tests for tradingagents.live.runner — LiveRunner orchestration.

These tests mock TradingAgentsGraph.propagate() to avoid LLM calls.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from tradingagents.live.runner import LiveRunner
from tradingagents.live.models import LiveConfig
from tradingagents.risk.models import TradeSignal, PositionSize, RiskMetrics


@pytest.fixture
def live_config():
    """Standard LiveConfig for testing."""
    return LiveConfig(
        tickers=["AAPL", "NVDA"],
        mode="paper",
        broker_type="dummy",
        state_path="test_state.json",
        initial_capital=1000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
        selected_analysts=["market"],
        backtest_profile="quick",
        config={
            "llm_provider": "openai",
            "quick_think_llm": "gpt-4o-mini",
            "deep_think_llm": "gpt-4o-mini",
        },
    )


@pytest.fixture
def mock_trade_signal():
    """Create a mock TradeSignal."""
    return TradeSignal(
        action="BUY",
        confidence=0.8,
        position_size=PositionSize(
            method="fixed_fraction",
            fraction=0.10,
            max_loss_percent=0.05,
            stop_loss_price=145.0,
        ),
        risk_metrics=RiskMetrics(
            ticker="AAPL",
            date="2024-06-01",
            daily_volatility=0.02,
            annualized_volatility=0.32,
            atr=3.0,
            atr_percent=0.02,
            max_drawdown=-0.05,
            current_drawdown=-0.02,
            var_95=-0.03,
            var_99=-0.05,
            cvar_95=-0.04,
            beta=1.2,
            sharpe_ratio=1.5,
            sortino_ratio=1.8,
            current_price=150.0,
            sma_50=148.0,
            sma_200=145.0,
            rsi=55.0,
        ),
        reasoning="Test signal",
    )


@pytest.fixture
def mock_graph_state(mock_trade_signal):
    """Create a mock AgentState from graph."""
    return {
        "company_of_interest": "AAPL",
        "trade_date": "2024-06-01",
        "final_trade_decision": "BUY",
        "risk_metrics": {
            "current_price": 150.0,
            "daily_volatility": 0.02,
        },
    }


class TestLiveRunnerInit:
    def test_initializes_with_config(self, live_config):
        """LiveRunner initializes with LiveConfig."""
        runner = LiveRunner(live_config)
        assert runner.config == live_config
        assert runner._graph is None  # Lazy initialization
        assert runner._broker is None
        assert runner._state is None


class TestLiveRunnerRun:
    @patch("tradingagents.live.runner.LiveRunner._fetch_current_prices")
    @patch("tradingagents.live.runner.get_current_date")
    @patch("tradingagents.live.runner.LivePortfolioState")
    @patch("tradingagents.live.runner.DummyBroker")
    @patch("tradingagents.graph.trading_graph.TradingAgentsGraph")
    def test_run_executes_for_all_tickers(
        self,
        mock_graph_class,
        mock_broker_class,
        mock_state_class,
        mock_get_date,
        mock_fetch_prices,
        live_config,
        mock_graph_state,
        mock_trade_signal,
    ):
        """run() executes propagation and execution for all tickers."""
        mock_get_date.return_value = "2024-06-01"
        mock_fetch_prices.return_value = {"AAPL": 150.0, "NVDA": 500.0}
        
        mock_graph = MagicMock()
        mock_graph.propagate.return_value = (mock_graph_state, mock_trade_signal)
        mock_graph_class.return_value = mock_graph
        
        mock_state = MagicMock()
        mock_state.get_initial_capital.return_value = 1000.0
        mock_state.get_cash.return_value = 1000.0
        mock_state.get_all_positions.return_value = []
        mock_state.get_last_portfolio_value.return_value = 1000.0
        mock_state.get_run_history.return_value = []
        mock_state_class.return_value = mock_state
        
        mock_broker = MagicMock()
        mock_broker.get_cash.return_value = 1000.0
        mock_broker.get_positions.return_value = []
        mock_broker.get_portfolio_value.return_value = 1000.0
        mock_broker.place_order.return_value = MagicMock(
            success=True,
            action="BUY",
            shares=1,
            execution_price=150.0,
            commission=0.15,
        )
        mock_broker_class.return_value = mock_broker
        
        runner = LiveRunner(live_config)
        result = runner.run()
        
        assert mock_graph.propagate.call_count == 2
        assert mock_graph.propagate.call_args_list[0][0][0] == "AAPL"
        assert mock_graph.propagate.call_args_list[1][0][0] == "NVDA"
        assert mock_broker.place_order.call_count == 2
        
        assert result.date == "2024-06-01"
        assert len(result.signals) == 2
        assert len(result.executed_orders) == 2
        mock_state.set_last_portfolio_value.assert_called_once()
        mock_state.append_run_snapshot.assert_called_once()
    
    @patch("tradingagents.live.runner.LiveRunner._fetch_current_prices")
    @patch("tradingagents.live.runner.get_current_date")
    @patch("tradingagents.live.runner.LivePortfolioState")
    @patch("tradingagents.live.runner.DummyBroker")
    @patch("tradingagents.graph.trading_graph.TradingAgentsGraph")
    def test_run_dry_run_mode_no_execution(
        self,
        mock_graph_class,
        mock_broker_class,
        mock_state_class,
        mock_get_date,
        mock_fetch_prices,
        live_config,
        mock_graph_state,
        mock_trade_signal,
    ):
        """run() in dry_run mode doesn't execute orders."""
        live_config.mode = "dry_run"
        mock_get_date.return_value = "2024-06-01"
        mock_fetch_prices.return_value = {"AAPL": 150.0, "NVDA": 500.0}
        
        mock_graph = MagicMock()
        mock_graph.propagate.return_value = (mock_graph_state, mock_trade_signal)
        mock_graph_class.return_value = mock_graph
        
        mock_state = MagicMock()
        mock_state.get_initial_capital.return_value = 1000.0
        mock_state.get_cash.return_value = 1000.0
        mock_state.get_all_positions.return_value = []
        mock_state.get_last_portfolio_value.return_value = 1000.0
        mock_state.get_run_history.return_value = []
        mock_state_class.return_value = mock_state
        
        mock_broker = MagicMock()
        mock_broker.get_cash.return_value = 1000.0
        mock_broker.get_positions.return_value = []
        mock_broker.get_portfolio_value.return_value = 1000.0
        mock_broker_class.return_value = mock_broker
        
        runner = LiveRunner(live_config)
        result = runner.run()
        
        mock_broker.place_order.assert_not_called()
        assert len(result.executed_orders) == 0
    
    @patch("tradingagents.live.runner.LiveRunner._fetch_current_prices")
    @patch("tradingagents.live.runner.get_current_date")
    @patch("tradingagents.live.runner.LivePortfolioState")
    @patch("tradingagents.live.runner.DummyBroker")
    @patch("tradingagents.graph.trading_graph.TradingAgentsGraph")
    def test_run_handles_propagation_failure(
        self,
        mock_graph_class,
        mock_broker_class,
        mock_state_class,
        mock_get_date,
        mock_fetch_prices,
        live_config,
    ):
        """run() handles propagate() failures gracefully."""
        mock_get_date.return_value = "2024-06-01"
        mock_fetch_prices.return_value = {"AAPL": 150.0, "NVDA": 500.0}
        
        mock_graph = MagicMock()
        mock_graph.propagate.side_effect = Exception("API error")
        mock_graph_class.return_value = mock_graph
        
        mock_state = MagicMock()
        mock_state.get_initial_capital.return_value = 1000.0
        mock_state.get_cash.return_value = 1000.0
        mock_state.get_all_positions.return_value = []
        mock_state.get_last_portfolio_value.return_value = 1000.0
        mock_state.get_run_history.return_value = []
        mock_state_class.return_value = mock_state
        
        mock_broker = MagicMock()
        mock_broker.get_cash.return_value = 1000.0
        mock_broker.get_positions.return_value = []
        mock_broker.get_portfolio_value.return_value = 1000.0
        mock_broker_class.return_value = mock_broker
        
        runner = LiveRunner(live_config)
        result = runner.run()
        
        assert len(result.signals) == 2
        for signal in result.signals.values():
            assert signal.action == "HOLD"
    
    @patch("tradingagents.live.runner.LiveRunner._fetch_current_prices")
    @patch("tradingagents.live.runner.get_current_date")
    @patch("tradingagents.live.runner.LivePortfolioState")
    @patch("tradingagents.live.runner.DummyBroker")
    @patch("tradingagents.graph.trading_graph.TradingAgentsGraph")
    def test_run_calculates_portfolio_value(
        self,
        mock_graph_class,
        mock_broker_class,
        mock_state_class,
        mock_get_date,
        mock_fetch_prices,
        live_config,
        mock_graph_state,
        mock_trade_signal,
    ):
        """run() calculates portfolio value correctly."""
        mock_get_date.return_value = "2024-06-01"
        mock_fetch_prices.return_value = {"AAPL": 150.0, "NVDA": 500.0}
        
        mock_graph = MagicMock()
        mock_graph.propagate.return_value = (mock_graph_state, mock_trade_signal)
        mock_graph_class.return_value = mock_graph
        
        mock_state = MagicMock()
        mock_state.get_initial_capital.return_value = 1000.0
        mock_state.get_cash.return_value = 1000.0
        mock_state.get_all_positions.return_value = []
        mock_state.get_last_portfolio_value.return_value = 1000.0
        mock_state.get_run_history.return_value = []
        mock_state_class.return_value = mock_state
        
        mock_broker = MagicMock()
        mock_broker.get_cash.return_value = 500.0
        mock_broker.get_positions.return_value = []
        mock_broker.get_portfolio_value.return_value = 1000.0
        mock_broker.place_order.return_value = MagicMock(
            success=True,
            action="BUY",
            shares=1,
            execution_price=150.0,
            commission=0.15,
        )
        mock_broker_class.return_value = mock_broker
        
        runner = LiveRunner(live_config)
        result = runner.run()
        
        assert result.portfolio_snapshot.cash == 500.0
        assert result.portfolio_snapshot.total_value > 0
        assert result.portfolio_snapshot.date == "2024-06-01"


class TestLiveRunnerHelpers:
    def test_build_effective_config(self, live_config):
        """_build_effective_config() merges with DEFAULT_CONFIG and profile."""
        runner = LiveRunner(live_config)
        config = runner._build_effective_config()
        
        assert "llm_provider" in config
        assert config["llm_provider"] == "openai"
        assert config["max_debate_rounds"] == 1
        assert config["max_risk_discuss_rounds"] == 1
    
    def test_empty_tickers_raises(self):
        """run() raises ValueError for empty tickers list."""
        config = LiveConfig(tickers=[], initial_capital=1000.0)
        runner = LiveRunner(config)
        with pytest.raises(ValueError, match="tickers is empty"):
            runner.run()
    
    @patch("tradingagents.live.runner.LivePortfolioState")
    def test_create_broker(self, mock_state_class, live_config):
        """_create_broker() creates DummyBroker for dummy type."""
        mock_state = MagicMock()
        mock_state_class.return_value = mock_state
        
        runner = LiveRunner(live_config)
        runner._state = mock_state
        broker = runner._create_broker()
        
        assert broker is not None
        from tradingagents.live.broker.dummy import DummyBroker
        assert isinstance(broker, DummyBroker)
    
    def test_create_broker_unknown_type(self, live_config):
        """_create_broker() raises ValueError for unknown type."""
        live_config.broker_type = "unknown"
        runner = LiveRunner(live_config)
        runner._state = MagicMock()
        
        with pytest.raises(ValueError, match="Unknown broker type"):
            runner._create_broker()
