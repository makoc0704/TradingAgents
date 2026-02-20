"""Tests for tradingagents.live.state — persistent portfolio state."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from tradingagents.live.state import LivePortfolioState, TradeRecord
from tradingagents.live.broker.interface import Position


@pytest.fixture
def temp_state_file():
    """Provide a temporary file path that does NOT yet exist."""
    tmp_dir = tempfile.mkdtemp()
    temp_path = str(Path(tmp_dir) / "state.json")
    yield temp_path
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def fresh_state(temp_state_file):
    """Create a fresh LivePortfolioState with initial capital."""
    return LivePortfolioState(
        state_path=temp_state_file,
        initial_capital=1000.0,
    )


class TestLivePortfolioStateInit:
    def test_creates_fresh_state_if_not_exists(self, temp_state_file):
        """State file should be created if it doesn't exist."""
        state = LivePortfolioState(
            state_path=temp_state_file,
            initial_capital=500.0,
        )
        assert state.get_cash() == 500.0
        assert Path(temp_state_file).exists()
    
    def test_loads_existing_state(self, temp_state_file):
        """Should load existing state from file."""
        # Create state file manually
        initial_data = {
            "cash": 750.0,
            "positions": {
                "AAPL": {"shares": 5, "avg_entry_price": 150.0}
            },
            "trades": [],
            "initialized_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
        with open(temp_state_file, 'w') as f:
            json.dump(initial_data, f)
        
        state = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        assert state.get_cash() == 750.0
        assert len(state.get_all_positions()) == 1
    
    def test_handles_corrupted_state_file(self, temp_state_file):
        """Should initialize fresh state if file is corrupted."""
        # Write invalid JSON
        with open(temp_state_file, 'w') as f:
            f.write("invalid json{")
        
        state = LivePortfolioState(
            state_path=temp_state_file,
            initial_capital=200.0,
        )
        assert state.get_cash() == 200.0


class TestCashOperations:
    def test_get_cash_returns_initial(self, fresh_state):
        """get_cash() returns initial capital for fresh state."""
        assert fresh_state.get_cash() == 1000.0
    
    def test_add_cash(self, fresh_state):
        """add_cash() increases balance."""
        fresh_state.add_cash(100.0)
        assert fresh_state.get_cash() == 1100.0
    
    def test_subtract_cash(self, fresh_state):
        """subtract_cash() decreases balance."""
        fresh_state.subtract_cash(200.0)
        assert fresh_state.get_cash() == 800.0
    
    def test_subtract_cash_never_goes_negative(self, fresh_state):
        """subtract_cash() never allows negative balance."""
        fresh_state.subtract_cash(2000.0)
        assert fresh_state.get_cash() == 0.0
    
    def test_cash_persists(self, temp_state_file):
        """Cash changes persist to file."""
        state1 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        state1.add_cash(500.0)
        
        state2 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        assert state2.get_cash() == 1500.0


class TestPositionOperations:
    def test_get_position_none_if_empty(self, fresh_state):
        """get_position() returns None if no position exists."""
        assert fresh_state.get_position("AAPL") is None
    
    def test_add_position_creates_new(self, fresh_state):
        """add_position() creates new position."""
        fresh_state.add_position("AAPL", 10, 150.0)
        pos = fresh_state.get_position("AAPL")
        assert pos is not None
        assert pos.shares == 10
        assert pos.avg_entry_price == 150.0
    
    def test_add_position_updates_existing(self, fresh_state):
        """add_position() updates existing position with average price."""
        fresh_state.add_position("AAPL", 10, 150.0)
        fresh_state.add_position("AAPL", 5, 160.0)
        
        pos = fresh_state.get_position("AAPL")
        assert pos.shares == 15
        # Average: (10*150 + 5*160) / 15 = 153.33...
        assert pos.avg_entry_price == pytest.approx(153.33, rel=0.01)
    
    def test_remove_position(self, fresh_state):
        """remove_position() deletes position."""
        fresh_state.add_position("AAPL", 10, 150.0)
        fresh_state.remove_position("AAPL")
        assert fresh_state.get_position("AAPL") is None
    
    def test_get_all_positions(self, fresh_state):
        """get_all_positions() returns all positions."""
        fresh_state.add_position("AAPL", 10, 150.0)
        fresh_state.add_position("NVDA", 5, 500.0)
        
        positions = fresh_state.get_all_positions()
        assert len(positions) == 2
        tickers = {pos.ticker for pos in positions}
        assert tickers == {"AAPL", "NVDA"}
    
    def test_positions_persist(self, temp_state_file):
        """Position changes persist to file."""
        state1 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        state1.add_position("AAPL", 10, 150.0)
        
        state2 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        pos = state2.get_position("AAPL")
        assert pos is not None
        assert pos.shares == 10


class TestInitialCapitalPersistence:
    def test_initial_capital_persisted(self, temp_state_file):
        """initial_capital is stored in state JSON."""
        state1 = LivePortfolioState(state_path=temp_state_file, initial_capital=200.0)
        assert state1.get_initial_capital() == 200.0
        
        state2 = LivePortfolioState(state_path=temp_state_file, initial_capital=999.0)
        assert state2.get_initial_capital() == 200.0

    def test_last_portfolio_value_defaults_to_initial(self, fresh_state):
        """get_last_portfolio_value() returns initial_capital on fresh state."""
        assert fresh_state.get_last_portfolio_value() == 1000.0

    def test_set_and_get_last_portfolio_value(self, fresh_state):
        """set_last_portfolio_value() persists value for next read."""
        fresh_state.set_last_portfolio_value(1234.56)
        assert fresh_state.get_last_portfolio_value() == 1234.56


class TestRunHistory:
    def test_append_run_snapshot(self, fresh_state):
        """append_run_snapshot() adds snapshot to history."""
        fresh_state.append_run_snapshot({"date": "2024-06-01", "total_value": 1000.0})
        history = fresh_state.get_run_history()
        assert len(history) == 1
        assert history[0]["date"] == "2024-06-01"

    def test_run_history_bounded(self, fresh_state):
        """Run history is bounded to 252 entries."""
        for i in range(260):
            fresh_state.append_run_snapshot({"date": f"2024-{i}", "total_value": 1000.0 + i})
        assert len(fresh_state.get_run_history()) == 252

    def test_run_history_persists(self, temp_state_file):
        """Run history persists to file."""
        state1 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        state1.append_run_snapshot({"date": "2024-06-01", "total_value": 1050.0})
        
        state2 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        assert len(state2.get_run_history()) == 1


class TestTradeHistory:
    def test_record_trade(self, fresh_state):
        """record_trade() adds trade to history."""
        fresh_state.record_trade("2024-06-01", "AAPL", "BUY", 150.0, 10, 1.5)
        history = fresh_state.get_trade_history()
        assert len(history) == 1
        assert history[0]["ticker"] == "AAPL"
        assert history[0]["action"] == "BUY"
        assert history[0]["shares"] == 10
    
    def test_trade_history_bounded(self, fresh_state):
        """Trade history is bounded to last 1000 trades."""
        # Add 1001 trades
        for i in range(1001):
            fresh_state.record_trade(
                f"2024-06-{i:02d}",
                "AAPL",
                "BUY",
                150.0,
                1,
                0.15,
            )
        
        history = fresh_state.get_trade_history()
        assert len(history) == 1000
    
    def test_get_trade_history_with_limit(self, fresh_state):
        """get_trade_history(limit) returns only recent trades."""
        for i in range(10):
            fresh_state.record_trade(
                f"2024-06-{i:02d}",
                "AAPL",
                "BUY",
                150.0,
                1,
                0.15,
            )
        
        history = fresh_state.get_trade_history(limit=5)
        assert len(history) == 5
    
    def test_trades_persist(self, temp_state_file):
        """Trade history persists to file."""
        state1 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        state1.record_trade("2024-06-01", "AAPL", "BUY", 150.0, 10, 1.5)
        
        state2 = LivePortfolioState(state_path=temp_state_file, initial_capital=1000.0)
        history = state2.get_trade_history()
        assert len(history) == 1
