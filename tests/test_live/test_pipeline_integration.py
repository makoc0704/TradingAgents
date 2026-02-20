"""Integration tests for live trading with pipeline."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from tradingagents.pipeline.job_runner import JobRunner
from tradingagents.pipeline.models import JobConfig, ScheduleConfig, NotificationConfig
from tradingagents.pipeline.result_store import ResultStore
from tradingagents.pipeline.notifier import Notifier


@pytest.fixture
def mock_result_store():
    """Create a mock ResultStore."""
    store = MagicMock(spec=ResultStore)
    store.save.return_value = "test/path/result.json"
    store.has_signal_changed.return_value = False
    return store


@pytest.fixture
def mock_notifier():
    """Create a mock Notifier."""
    return MagicMock(spec=Notifier)


@pytest.fixture
def live_trading_job_config():
    """Create a JobConfig for live trading."""
    return JobConfig(
        name="test_live_trading",
        job_type="live_trading",
        tickers=["AAPL"],
        analysis_date="today",
        schedule=ScheduleConfig(
            cron_expression="0 9 * * 1-5",
            timezone="UTC",
            enabled=True,
            max_retries=1,
            retry_delay_seconds=0,
        ),
        notification=NotificationConfig(enabled=False),
        config={
            "live_mode": "paper",
            "live_broker_type": "dummy",
            "live_initial_capital": 1000.0,
            "live_state_path": "test_state.json",
        },
    )


class TestPipelineIntegration:
    @patch("tradingagents.live.LiveRunner")
    @patch("tradingagents.live.LiveConfig")
    def test_job_runner_executes_live_trading(
        self,
        mock_live_config_class,
        mock_live_runner_class,
        live_trading_job_config,
        mock_result_store,
        mock_notifier,
    ):
        """JobRunner executes live_trading job type."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.signals = {"AAPL": MagicMock(action="BUY")}
        mock_result.performance_metrics = {"total_return": 0.05}
        mock_runner.run.return_value = mock_result
        mock_live_runner_class.return_value = mock_runner
        
        mock_config = MagicMock()
        mock_live_config_class.return_value = mock_config
        
        runner = JobRunner(mock_result_store, mock_notifier)
        result = runner.execute(live_trading_job_config)
        
        mock_live_runner_class.assert_called_once()
        mock_runner.run.assert_called_once()
        
        assert result.job_type == "live_trading"
        assert result.status == "success"
        assert result.signal is not None
        assert "AAPL" in result.signal
    
    @patch("tradingagents.pipeline.job_runner.time.sleep")
    @patch("tradingagents.live.LiveRunner")
    def test_job_runner_handles_live_trading_failure(
        self,
        mock_live_runner_class,
        mock_sleep,
        live_trading_job_config,
        mock_result_store,
        mock_notifier,
    ):
        """JobRunner handles live_trading failures gracefully."""
        mock_runner = MagicMock()
        mock_runner.run.side_effect = Exception("Broker error")
        mock_live_runner_class.return_value = mock_runner
        
        runner = JobRunner(mock_result_store, mock_notifier)
        result = runner.execute(live_trading_job_config)
        
        assert result.status == "failure"
        assert result.error is not None
        assert "Broker error" in result.error
