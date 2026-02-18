"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from tradingagents.web.app import create_app
from tradingagents.web.config import WebConfig


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary results directory."""
    config = WebConfig(
        results_dir=str(tmp_path),
        dev_mode=True,
        max_concurrent_tasks=1,
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


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
