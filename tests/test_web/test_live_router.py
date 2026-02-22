"""Tests for the Live Trading router endpoints."""

import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from tradingagents.web.app import create_app
from tradingagents.web.config import WebConfig
from tradingagents.web.routers.live import _get_live_reader
from tradingagents.web.services.live_reader import LiveReader


@pytest.fixture
def mock_reader():
    """Create a mocked LiveReader."""
    return MagicMock(spec=LiveReader)


@pytest.fixture
def client(tmp_path, mock_reader):
    """Create a test client with mocked LiveReader dependency."""
    config = WebConfig(
        results_dir=str(tmp_path),
        dev_mode=True,
        max_concurrent_tasks=1,
    )
    app = create_app(config)
    app.dependency_overrides[_get_live_reader] = lambda: mock_reader
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/live/portfolio
# ---------------------------------------------------------------------------


class TestLivePortfolioEndpoint:
    """Tests for GET /api/live/portfolio."""

    def test_no_state_returns_error(self, client, mock_reader):
        mock_reader.get_portfolio.return_value = None
        resp = client.get("/api/live/portfolio")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "No live portfolio" in body["error"]

    def test_returns_portfolio_data(self, client, mock_reader):
        mock_reader.get_portfolio.return_value = {
            "total_value": 1050.0,
            "cash": 500.0,
            "initial_capital": 1000.0,
            "positions": [
                {
                    "ticker": "NVDA",
                    "shares": 2,
                    "avg_entry_price": 120.0,
                    "current_price": 150.0,
                    "market_value": 300.0,
                    "unrealized_pnl": 60.0,
                    "unrealized_pnl_pct": 0.25,
                    "weight": 0.286,
                },
            ],
            "total_return": 0.05,
            "daily_return": 0.01,
            "last_updated": "2024-06-05T16:00:00",
        }

        resp = client.get("/api/live/portfolio")
        body = resp.json()

        assert body["success"] is True
        assert body["data"]["total_value"] == 1050.0
        assert len(body["data"]["positions"]) == 1
        assert body["data"]["positions"][0]["ticker"] == "NVDA"
        mock_reader.get_portfolio.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/live/trades
# ---------------------------------------------------------------------------


class TestLiveTradesEndpoint:
    """Tests for GET /api/live/trades."""

    def test_no_state_returns_empty_list(self, client, mock_reader):
        mock_reader.get_trades.return_value = []
        resp = client.get("/api/live/trades")

        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []

    def test_returns_trades(self, client, mock_reader):
        mock_reader.get_trades.return_value = [
            {"date": "2024-06-05", "ticker": "NVDA", "action": "BUY", "price": 150.0, "shares": 2, "commission": 1.0},
        ]
        resp = client.get("/api/live/trades")
        body = resp.json()

        assert body["success"] is True
        assert len(body["data"]) == 1
        assert body["data"][0]["action"] == "BUY"

    def test_limit_parameter_forwarded(self, client, mock_reader):
        mock_reader.get_trades.return_value = []
        resp = client.get("/api/live/trades?limit=10")

        assert resp.status_code == 200
        mock_reader.get_trades.assert_called_once_with(limit=10)

    def test_default_limit_is_50(self, client, mock_reader):
        mock_reader.get_trades.return_value = []
        client.get("/api/live/trades")

        mock_reader.get_trades.assert_called_once_with(limit=50)


# ---------------------------------------------------------------------------
# GET /api/live/performance
# ---------------------------------------------------------------------------


class TestLivePerformanceEndpoint:
    """Tests for GET /api/live/performance."""

    def test_no_data_returns_error(self, client, mock_reader):
        mock_reader.get_performance.return_value = None
        resp = client.get("/api/live/performance")

        body = resp.json()
        assert body["success"] is False
        assert "No live performance" in body["error"]

    def test_returns_performance_metrics(self, client, mock_reader):
        mock_reader.get_performance.return_value = {
            "total_return": 0.05,
            "daily_return": 0.01,
            "annualized_return": 6.3,
            "sharpe_ratio": 1.2,
            "max_drawdown": 0.03,
            "win_rate": 0.6,
            "total_trades": 5,
            "trading_days": 10,
        }
        resp = client.get("/api/live/performance")
        body = resp.json()

        assert body["success"] is True
        assert body["data"]["sharpe_ratio"] == 1.2
        assert body["data"]["total_trades"] == 5


# ---------------------------------------------------------------------------
# GET /api/live/history
# ---------------------------------------------------------------------------


class TestLiveHistoryEndpoint:
    """Tests for GET /api/live/history."""

    def test_empty_history(self, client, mock_reader):
        mock_reader.get_run_history.return_value = []
        resp = client.get("/api/live/history")

        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []

    def test_returns_snapshots(self, client, mock_reader):
        mock_reader.get_run_history.return_value = [
            {"date": "2024-06-03", "portfolio_value": 1000.0},
            {"date": "2024-06-04", "portfolio_value": 1030.0},
        ]
        resp = client.get("/api/live/history")
        body = resp.json()

        assert body["success"] is True
        assert len(body["data"]) == 2


# ---------------------------------------------------------------------------
# POST /api/live/run-now
# ---------------------------------------------------------------------------


class TestLiveRunNowEndpoint:
    """Tests for POST /api/live/run-now."""

    def test_submits_task(self, client, mock_reader):
        resp = client.post("/api/live/run-now")
        body = resp.json()

        assert body["success"] is True
        assert "task_id" in body["data"]
        assert body["data"]["task_type"] == "live_trading"
        assert body["data"]["status"] in ("pending", "running")

    def test_task_type_is_live_trading(self, client, mock_reader):
        resp = client.post("/api/live/run-now")
        body = resp.json()

        assert body["data"]["task_type"] == "live_trading"

    def test_custom_config_accepted(self, client, mock_reader):
        resp = client.post(
            "/api/live/run-now",
            json={"tickers": ["AAPL", "MSFT"], "initial_capital": 500.0, "backtest_profile": "standard"},
        )
        body = resp.json()

        assert body["success"] is True
        assert body["data"]["task_type"] == "live_trading"


# ---------------------------------------------------------------------------
# _run_live_trading (unit test via mock)
# ---------------------------------------------------------------------------


class TestRunLiveTradingFunction:
    """Tests for the _run_live_trading background function.

    Since LiveRunner and LiveConfig are lazy-imported inside the function body,
    we inject mock modules into sys.modules before calling.
    """

    def _setup_mocks(self):
        """Create mock modules for lazy imports."""
        mock_runner_mod = MagicMock()
        mock_models_mod = MagicMock()
        self._MockRunner = mock_runner_mod.LiveRunner
        self._MockConfig = mock_models_mod.LiveConfig
        return {
            "tradingagents.live": MagicMock(),
            "tradingagents.live.runner": mock_runner_mod,
            "tradingagents.live.models": mock_models_mod,
        }

    def test_calls_runner_and_returns_dict(self):
        mods = self._setup_mocks()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"date": "2024-06-05", "signals": {}}
        self._MockRunner.return_value.run.return_value = mock_result

        with patch.dict("sys.modules", mods):
            from tradingagents.web.routers.live import _run_live_trading

            task_info = MagicMock()
            task_info.config = {"tickers": ["NVDA"], "initial_capital": 200.0}
            update_fn = MagicMock()

            result = _run_live_trading(task_info, update_fn)

        assert result == {"date": "2024-06-05", "signals": {}}
        self._MockRunner.assert_called_once()
        self._MockRunner.return_value.run.assert_called_once()
        assert update_fn.call_count >= 2

    def test_update_fn_called_with_progress(self):
        mods = self._setup_mocks()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {}
        self._MockRunner.return_value.run.return_value = mock_result

        with patch.dict("sys.modules", mods):
            from tradingagents.web.routers.live import _run_live_trading

            task_info = MagicMock()
            task_info.config = {"tickers": ["AAPL", "MSFT"], "initial_capital": 500.0}
            update_fn = MagicMock()

            _run_live_trading(task_info, update_fn)

        calls = update_fn.call_args_list
        assert calls[0].kwargs["progress"] == 5
        assert calls[-1].kwargs["progress"] == 100

    def test_default_tickers_when_not_in_config(self):
        mods = self._setup_mocks()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {}
        self._MockRunner.return_value.run.return_value = mock_result

        with patch.dict("sys.modules", mods):
            from tradingagents.web.routers.live import _run_live_trading

            task_info = MagicMock()
            task_info.config = {}
            update_fn = MagicMock()

            _run_live_trading(task_info, update_fn)

        config_call = self._MockConfig.call_args
        assert config_call.kwargs["tickers"] == ["NVDA"]
        assert config_call.kwargs["initial_capital"] == 200.0

    def test_runner_exception_propagates(self):
        mods = self._setup_mocks()
        self._MockRunner.return_value.run.side_effect = ValueError("ticker invalid")

        with patch.dict("sys.modules", mods):
            from tradingagents.web.routers.live import _run_live_trading

            task_info = MagicMock()
            task_info.config = {"tickers": [""], "initial_capital": 200.0}
            update_fn = MagicMock()

            with pytest.raises(ValueError, match="ticker invalid"):
                _run_live_trading(task_info, update_fn)
