"""Tests for the ResultReader service."""

import json
import os
import pytest
from tradingagents.web.services.result_reader import ResultReader


@pytest.fixture
def results_dir(tmp_path):
    """Create a temporary results directory with test data."""
    # Analysis result
    ticker_dir = tmp_path / "NVDA" / "TradingAgentsStrategy_logs"
    ticker_dir.mkdir(parents=True)
    state_log = {
        "2024-06-05": {
            "company_of_interest": "NVDA",
            "trade_date": "2024-06-05",
            "market_report": "# Market Report\nBullish trend.",
            "final_trade_decision": "FINAL TRANSACTION PROPOSAL: **SELL**\nCONFIDENCE: **HIGH**",
            "risk_metrics": {"ticker": "NVDA", "sharpe_ratio": 1.5},
        }
    }
    with open(ticker_dir / "full_states_log_2024-06-05.json", "w") as f:
        json.dump(state_log, f)

    # Pipeline result
    pipeline_dir = tmp_path / "pipeline" / "test_job"
    pipeline_dir.mkdir(parents=True)
    job_result = {
        "job_name": "test_job",
        "job_type": "single_analysis",
        "status": "success",
        "signal": "BUY",
        "started_at": "2024-06-05T09:00:00",
        "finished_at": "2024-06-05T09:05:00",
        "duration_seconds": 300.0,
    }
    with open(pipeline_dir / "2024-06-05_090500.json", "w") as f:
        json.dump(job_result, f)
    with open(pipeline_dir / "latest.json", "w") as f:
        json.dump(job_result, f)

    # Top-level JSON result
    with open(tmp_path / "backtest_result.json", "w") as f:
        json.dump({"performance": {"total_return": 0.15}}, f)

    return tmp_path


class TestResultReader:
    """Tests for ResultReader file-based result access."""

    def test_list_tickers(self, results_dir):
        reader = ResultReader(str(results_dir))
        tickers = reader.list_tickers()
        assert "NVDA" in tickers
        assert "pipeline" not in tickers

    def test_list_dates_for_ticker(self, results_dir):
        # Create a date subdirectory
        (results_dir / "NVDA" / "2024-06-05").mkdir()
        reader = ResultReader(str(results_dir))
        dates = reader.list_dates_for_ticker("NVDA")
        assert "2024-06-05" in dates

    def test_get_analysis_result(self, results_dir):
        reader = ResultReader(str(results_dir))
        result = reader.get_analysis_result("NVDA", "2024-06-05")
        assert result is not None
        assert "2024-06-05" in result

    def test_get_analysis_result_not_found(self, results_dir):
        reader = ResultReader(str(results_dir))
        result = reader.get_analysis_result("AAPL", "2024-01-01")
        assert result is None

    def test_list_pipeline_jobs(self, results_dir):
        reader = ResultReader(str(results_dir))
        jobs = reader.list_pipeline_jobs()
        assert "test_job" in jobs

    def test_get_pipeline_latest(self, results_dir):
        reader = ResultReader(str(results_dir))
        latest = reader.get_pipeline_latest("test_job")
        assert latest is not None
        assert latest["signal"] == "BUY"

    def test_get_pipeline_history(self, results_dir):
        reader = ResultReader(str(results_dir))
        history = reader.get_pipeline_history("test_job")
        assert len(history) == 1
        assert history[0]["status"] == "success"

    def test_list_result_files(self, results_dir):
        reader = ResultReader(str(results_dir))
        files = reader.list_result_files()
        assert any(f["filename"] == "backtest_result.json" for f in files)

    def test_empty_directory(self, tmp_path):
        reader = ResultReader(str(tmp_path / "nonexistent"))
        assert reader.list_tickers() == []
        assert reader.list_pipeline_jobs() == []
