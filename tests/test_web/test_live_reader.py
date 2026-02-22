"""Tests for the LiveReader service."""

import json
import os
import pytest

from tradingagents.web.services.live_reader import LiveReader


def _approx(a, b, tol=1e-6):
    """Compare floats without pytest.approx (numpy conflict workaround)."""
    assert abs(a - b) < tol, f"{a} != {b} (tol={tol})"


def _write_state(path, data):
    """Write a state dict as JSON to the given path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


@pytest.fixture
def state_path(tmp_path):
    """Return a path inside a temp dir for state.json."""
    return str(tmp_path / "state.json")


@pytest.fixture
def sample_state():
    """A realistic portfolio state fixture."""
    return {
        "initial_capital": 1000.0,
        "cash": 500.0,
        "last_portfolio_value": 1050.0,
        "positions": {
            "NVDA": {
                "shares": 2,
                "avg_entry_price": 120.0,
                "current_price": 150.0,
            },
            "AAPL": {
                "shares": 1,
                "avg_entry_price": 180.0,
                "current_price": 170.0,
            },
        },
        "trades": [
            {"date": "2024-06-03", "ticker": "NVDA", "action": "BUY", "price": 120.0, "shares": 2, "commission": 1.0},
            {"date": "2024-06-04", "ticker": "AAPL", "action": "BUY", "price": 180.0, "shares": 1, "commission": 1.0},
            {"date": "2024-06-05", "ticker": "NVDA", "action": "HOLD", "price": 150.0, "shares": 0, "commission": 0.0},
        ],
        "run_history": [
            {"date": "2024-06-03", "portfolio_value": 1000.0},
            {"date": "2024-06-04", "portfolio_value": 1030.0},
            {"date": "2024-06-05", "portfolio_value": 1070.0},
        ],
        "last_updated": "2024-06-05T16:00:00",
    }


# ---------------------------------------------------------------------------
# _load_state
# ---------------------------------------------------------------------------


class TestLoadState:
    """Tests for LiveReader._load_state."""

    def test_missing_file_returns_none(self, state_path):
        reader = LiveReader(state_path=state_path)
        assert reader._load_state() is None

    def test_valid_json(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        loaded = reader._load_state()
        assert loaded is not None
        assert loaded["initial_capital"] == 1000.0

    def test_corrupt_json_returns_none(self, state_path):
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w") as f:
            f.write("{invalid json!!!}")
        reader = LiveReader(state_path=state_path)
        assert reader._load_state() is None

    def test_empty_file_returns_none(self, state_path):
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w") as f:
            f.write("")
        reader = LiveReader(state_path=state_path)
        assert reader._load_state() is None


# ---------------------------------------------------------------------------
# get_portfolio
# ---------------------------------------------------------------------------


class TestGetPortfolio:
    """Tests for LiveReader.get_portfolio."""

    def test_no_state_file_returns_none(self, state_path):
        reader = LiveReader(state_path=state_path)
        assert reader.get_portfolio() is None

    def test_portfolio_values(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        assert p is not None
        assert p["initial_capital"] == 1000.0
        assert p["cash"] == 500.0
        # NVDA: 2*150=300, AAPL: 1*170=170, total_pos=470
        _approx(p["total_value"], 500.0 + 300.0 + 170.0)

    def test_position_unrealized_pnl(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        nvda = next(pos for pos in p["positions"] if pos["ticker"] == "NVDA")
        _approx(nvda["market_value"], 300.0)
        _approx(nvda["unrealized_pnl"], 60.0)  # 300 - 240
        _approx(nvda["unrealized_pnl_pct"], 0.25)  # 60/240

        aapl = next(pos for pos in p["positions"] if pos["ticker"] == "AAPL")
        _approx(aapl["unrealized_pnl"], -10.0)  # 170 - 180

    def test_position_weights_sum_to_non_cash_fraction(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        weight_sum = sum(pos["weight"] for pos in p["positions"])
        expected = (300.0 + 170.0) / 970.0
        _approx(weight_sum, expected)

    def test_total_return(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        expected_total_return = (970.0 - 1000.0) / 1000.0
        _approx(p["total_return"], expected_total_return)

    def test_daily_return(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        expected_daily = (970.0 - 1050.0) / 1050.0
        _approx(p["daily_return"], expected_daily)

    def test_zero_capital_no_division_error(self, state_path):
        state = {"initial_capital": 0, "cash": 0, "positions": {}, "last_portfolio_value": 0}
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        assert p is not None
        assert p["total_return"] == 0.0
        assert p["daily_return"] == 0.0

    def test_empty_positions(self, state_path):
        state = {
            "initial_capital": 200.0,
            "cash": 200.0,
            "positions": {},
            "last_portfolio_value": 200.0,
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        assert p["positions"] == []
        assert p["total_value"] == 200.0

    def test_position_missing_current_price_falls_back_to_avg(self, state_path):
        state = {
            "initial_capital": 100.0,
            "cash": 0.0,
            "positions": {
                "XYZ": {"shares": 5, "avg_entry_price": 20.0}
            },
            "last_portfolio_value": 100.0,
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        p = reader.get_portfolio()

        pos = p["positions"][0]
        assert pos["current_price"] == 20.0
        assert pos["market_value"] == 100.0
        assert pos["unrealized_pnl"] == 0.0


# ---------------------------------------------------------------------------
# get_trades
# ---------------------------------------------------------------------------


class TestGetTrades:
    """Tests for LiveReader.get_trades."""

    def test_no_state_returns_empty(self, state_path):
        reader = LiveReader(state_path=state_path)
        assert reader.get_trades() == []

    def test_trades_returned_newest_first(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        trades = reader.get_trades()

        assert len(trades) == 3
        assert trades[0]["date"] == "2024-06-05"
        assert trades[-1]["date"] == "2024-06-03"

    def test_trades_limit(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        trades = reader.get_trades(limit=2)

        assert len(trades) == 2
        assert trades[0]["date"] == "2024-06-05"

    def test_empty_trades_list(self, state_path):
        state = {"trades": []}
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        assert reader.get_trades() == []


# ---------------------------------------------------------------------------
# get_run_history
# ---------------------------------------------------------------------------


class TestGetRunHistory:
    """Tests for LiveReader.get_run_history."""

    def test_no_state_returns_empty(self, state_path):
        reader = LiveReader(state_path=state_path)
        assert reader.get_run_history() == []

    def test_returns_snapshots(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        history = reader.get_run_history()

        assert len(history) == 3
        assert history[0]["date"] == "2024-06-03"

    def test_missing_run_history_key(self, state_path):
        _write_state(state_path, {"cash": 100})
        reader = LiveReader(state_path=state_path)
        assert reader.get_run_history() == []


# ---------------------------------------------------------------------------
# get_performance
# ---------------------------------------------------------------------------


class TestGetPerformance:
    """Tests for LiveReader.get_performance."""

    def test_no_state_returns_none(self, state_path):
        reader = LiveReader(state_path=state_path)
        assert reader.get_performance() is None

    def test_total_return(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        expected = (1050.0 - 1000.0) / 1000.0
        _approx(perf["total_return"], expected)

    def test_trading_days(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert perf["trading_days"] == 3

    def test_daily_return_from_last_two_snapshots(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        expected = (1050.0 - 1030.0) / 1030.0
        _approx(perf["daily_return"], expected)

    def test_sharpe_ratio_computed(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert isinstance(perf["sharpe_ratio"], float)
        assert perf["sharpe_ratio"] != 0.0

    def test_max_drawdown(self, state_path):
        state = {
            "initial_capital": 1000.0,
            "last_portfolio_value": 900.0,
            "run_history": [
                {"portfolio_value": 1000.0},
                {"portfolio_value": 1100.0},
                {"portfolio_value": 900.0},
                {"portfolio_value": 950.0},
            ],
            "trades": [],
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        expected_dd = (1100.0 - 900.0) / 1100.0
        _approx(perf["max_drawdown"], expected_dd)

    def test_win_rate_only_buy_sell(self, state_path, sample_state):
        _write_state(state_path, sample_state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert perf["total_trades"] == 2  # 2 BUY, 0 SELL, excludes HOLD
        assert perf["win_rate"] == 0.0  # no SELL trades -> 0% win rate

    def test_win_rate_with_sells(self, state_path):
        state = {
            "initial_capital": 1000.0,
            "last_portfolio_value": 1000.0,
            "run_history": [],
            "trades": [
                {"date": "2024-06-01", "ticker": "NVDA", "action": "BUY", "price": 100.0, "shares": 5, "commission": 1.0},
                {"date": "2024-06-02", "ticker": "NVDA", "action": "SELL", "price": 120.0, "shares": 5, "commission": 1.0},
                {"date": "2024-06-03", "ticker": "AAPL", "action": "BUY", "price": 150.0, "shares": 3, "commission": 1.0},
                {"date": "2024-06-04", "ticker": "AAPL", "action": "SELL", "price": 140.0, "shares": 3, "commission": 1.0},
            ],
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert perf["total_trades"] == 4
        _approx(perf["win_rate"], 0.5)  # NVDA sold at profit, AAPL at loss

    def test_no_history_gives_zero_annualized(self, state_path):
        state = {
            "initial_capital": 100.0,
            "last_portfolio_value": 100.0,
            "run_history": [],
            "trades": [],
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert perf["annualized_return"] == 0.0
        assert perf["sharpe_ratio"] == 0.0

    def test_single_history_entry_no_daily_return(self, state_path):
        state = {
            "initial_capital": 100.0,
            "last_portfolio_value": 110.0,
            "run_history": [{"portfolio_value": 110.0}],
            "trades": [],
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert perf["daily_return"] == 0.0
        assert perf["sharpe_ratio"] == 0.0

    def test_zero_initial_capital(self, state_path):
        state = {
            "initial_capital": 0,
            "last_portfolio_value": 0,
            "run_history": [],
            "trades": [],
        }
        _write_state(state_path, state)
        reader = LiveReader(state_path=state_path)
        perf = reader.get_performance()

        assert perf["total_return"] == 0.0
