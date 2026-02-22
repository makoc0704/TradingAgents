"""Tests for the FastAPI application."""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from tradingagents.web.app import create_app
from tradingagents.web.config import WebConfig
from tradingagents.web.routers.live import _get_live_reader
from tradingagents.web.services.live_reader import LiveReader


@pytest.fixture
def mock_live_reader():
    """Create a mocked LiveReader for live endpoints."""
    reader = MagicMock(spec=LiveReader)
    reader.get_portfolio.return_value = None
    reader.get_trades.return_value = []
    reader.get_run_history.return_value = []
    reader.get_performance.return_value = None
    return reader


@pytest.fixture
def client(tmp_path, mock_live_reader):
    """Create a test client with a temporary results directory."""
    config = WebConfig(
        results_dir=str(tmp_path),
        dev_mode=True,
        max_concurrent_tasks=1,
    )
    app = create_app(config)
    app.dependency_overrides[_get_live_reader] = lambda: mock_live_reader
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "tradingagents-dashboard"


class TestResultsEndpoints:
    """Tests for the results browsing endpoints."""

    def test_list_tickers_empty(self, client):
        resp = client.get("/api/results/tickers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_list_ticker_dates(self, client):
        resp = client.get("/api/results/tickers/NVDA/dates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_list_pipeline_jobs_empty(self, client):
        resp = client.get("/api/results/pipeline/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []


class TestPipelineEndpoints:
    """Tests for the pipeline endpoints."""

    def test_pipeline_status(self, client):
        resp = client.get("/api/pipeline/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "jobs" in data["data"]

    def test_job_history_not_found(self, client):
        resp = client.get("/api/pipeline/jobs/nonexistent/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False


class TestTaskEndpoints:
    """Tests for the task management endpoints."""

    def test_list_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data

    def test_analysis_status_not_found(self, client):
        resp = client.get("/api/analysis/status/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    def test_backtest_status_not_found(self, client):
        resp = client.get("/api/backtest/status/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    def test_backtest_result_not_available(self, client):
        resp = client.get("/api/backtest/result/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False


class TestLiveEndpointsRegistered:
    """Verify the live router is properly mounted in the app."""

    def test_live_portfolio_route_exists(self, client):
        resp = client.get("/api/live/portfolio")
        assert resp.status_code == 200

    def test_live_trades_route_exists(self, client):
        resp = client.get("/api/live/trades")
        assert resp.status_code == 200

    def test_live_performance_route_exists(self, client):
        resp = client.get("/api/live/performance")
        assert resp.status_code == 200

    def test_live_history_route_exists(self, client):
        resp = client.get("/api/live/history")
        assert resp.status_code == 200

    def test_live_run_now_route_exists(self, client):
        resp = client.post("/api/live/run-now")
        assert resp.status_code == 200
