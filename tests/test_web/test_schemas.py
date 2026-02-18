"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError
from tradingagents.web.schemas.requests import (
    AnalysisRequest,
    BacktestRequest,
    PortfolioRequest,
)
from tradingagents.web.schemas.responses import (
    ApiResponse,
    TaskStatusResponse,
    RiskMetricsResponse,
)


class TestAnalysisRequest:
    """Tests for AnalysisRequest validation."""

    def test_valid_request(self):
        req = AnalysisRequest(ticker="NVDA", analysis_date="2024-06-05")
        assert req.ticker == "NVDA"
        assert req.selected_analysts == ["market", "fundamentals"]

    def test_custom_analysts(self):
        req = AnalysisRequest(
            ticker="AAPL",
            analysis_date="2024-06-05",
            selected_analysts=["market", "social", "news"],
        )
        assert len(req.selected_analysts) == 3

    def test_missing_ticker_raises(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(analysis_date="2024-06-05")


class TestBacktestRequest:
    """Tests for BacktestRequest validation."""

    def test_valid_request(self):
        req = BacktestRequest(
            ticker="NVDA",
            start_date="2024-06-03",
            end_date="2024-06-07",
        )
        assert req.initial_capital == 100_000
        assert req.backtest_profile == "quick"

    def test_capital_below_minimum(self):
        with pytest.raises(ValidationError):
            BacktestRequest(
                ticker="NVDA",
                start_date="2024-06-03",
                end_date="2024-06-07",
                initial_capital=500,
            )


class TestPortfolioRequest:
    """Tests for PortfolioRequest validation."""

    def test_valid_request(self):
        req = PortfolioRequest(
            tickers=["NVDA", "AAPL"],
            start_date="2024-06-03",
            end_date="2024-06-07",
        )
        assert req.weighting_strategy == "equal"

    def test_single_ticker_raises(self):
        with pytest.raises(ValidationError):
            PortfolioRequest(
                tickers=["NVDA"],
                start_date="2024-06-03",
                end_date="2024-06-07",
            )


class TestApiResponse:
    """Tests for ApiResponse envelope."""

    def test_success_response(self):
        resp = ApiResponse(success=True, data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}
        assert resp.error is None
        assert resp.timestamp  # auto-generated

    def test_error_response(self):
        resp = ApiResponse(success=False, error="Something went wrong")
        assert resp.success is False
        assert resp.data is None
        assert resp.error == "Something went wrong"


class TestTaskStatusResponse:
    """Tests for TaskStatusResponse."""

    def test_fields(self):
        status = TaskStatusResponse(
            task_id="abc123",
            task_type="backtest",
            status="running",
            progress_percent=50,
            message="Halfway there",
        )
        assert status.task_id == "abc123"
        assert status.progress_percent == 50


class TestRiskMetricsResponse:
    """Tests for RiskMetricsResponse."""

    def test_all_fields(self):
        metrics = RiskMetricsResponse(
            ticker="NVDA",
            date="2024-06-05",
            daily_volatility=0.02,
            annualized_volatility=0.32,
            atr=5.50,
            atr_percent=0.04,
            max_drawdown=-0.15,
            current_drawdown=-0.05,
            var_95=-0.03,
            var_99=-0.05,
            cvar_95=-0.04,
            beta=1.2,
            sharpe_ratio=1.8,
            sortino_ratio=2.1,
            current_price=130.0,
            sma_50=125.0,
            sma_200=110.0,
            rsi=65.0,
        )
        assert metrics.ticker == "NVDA"
        assert metrics.sharpe_ratio == 1.8
