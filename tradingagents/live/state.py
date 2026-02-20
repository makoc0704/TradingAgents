"""Persistent state management for live trading portfolio."""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from datetime import datetime

from .broker.interface import Position

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """A single trade record in history."""
    
    date: str
    ticker: str
    action: str  # BUY, SELL, HOLD
    price: float
    shares: int
    commission: float
    
    def to_dict(self) -> dict:
        """Convert to plain dict."""
        return asdict(self)


class LivePortfolioState:
    """Manages persistent portfolio state for live trading.
    
    State is stored as JSON in a file. Each run loads state,
    updates it, and saves it back.
    
    Args:
        state_path: Path to JSON file for state storage.
        initial_capital: Starting cash if state file doesn't exist.
    """
    
    def __init__(
        self,
        state_path: str,
        initial_capital: float = 100_000.0,
    ):
        self.state_path = Path(state_path)
        self.initial_capital = initial_capital
        self._state: Dict = {}
        self._load()
    
    def _load(self) -> None:
        """Load state from disk, or initialize if file doesn't exist."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    self._state = json.load(f)
                logger.info("Loaded live portfolio state from %s", self.state_path)
            except Exception as e:
                logger.error("Failed to load state: %s — initializing fresh state", e)
                self._state = self._initial_state()
                self._save()
        else:
            self._state = self._initial_state()
            self._save()
    
    def _save(self) -> None:
        """Save state to disk atomically."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file, then rename
        temp_path = self.state_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w") as f:
                json.dump(self._state, f, indent=2)
            temp_path.replace(self.state_path)
            logger.debug("Saved live portfolio state to %s", self.state_path)
        except Exception as e:
            logger.error("Failed to save state: %s", e)
            if temp_path.exists():
                temp_path.unlink()
    
    def _initial_state(self) -> Dict:
        """Create initial empty state."""
        return {
            "initial_capital": self.initial_capital,
            "cash": self.initial_capital,
            "positions": {},  # {ticker: {"shares": int, "avg_entry_price": float}}
            "trades": [],  # List of TradeRecord dicts
            "run_history": [],  # Lightweight snapshots for performance calc
            "last_portfolio_value": self.initial_capital,
            "initialized_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
    
    def get_cash(self) -> float:
        """Get current cash balance."""
        return self._state.get("cash", self.initial_capital)
    
    def add_cash(self, amount: float) -> None:
        """Add cash to balance."""
        self._state["cash"] = self.get_cash() + amount
        self._state["last_updated"] = datetime.now().isoformat()
        self._save()
    
    def subtract_cash(self, amount: float) -> None:
        """Subtract cash from balance."""
        self._state["cash"] = max(0.0, self.get_cash() - amount)
        self._state["last_updated"] = datetime.now().isoformat()
        self._save()
    
    def get_position(self, ticker: str) -> Optional[Position]:
        """Get position for a ticker."""
        pos_data = self._state["positions"].get(ticker)
        if pos_data and pos_data.get("shares", 0) > 0:
            return Position(
                ticker=ticker,
                shares=pos_data["shares"],
                avg_entry_price=pos_data["avg_entry_price"],
                current_price=pos_data.get("avg_entry_price", 0.0),  # Placeholder
            )
        return None
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions."""
        positions = []
        for ticker, pos_data in self._state["positions"].items():
            if pos_data.get("shares", 0) > 0:
                positions.append(Position(
                    ticker=ticker,
                    shares=pos_data["shares"],
                    avg_entry_price=pos_data["avg_entry_price"],
                    current_price=pos_data.get("avg_entry_price", 0.0),
                ))
        return positions
    
    def add_position(self, ticker: str, shares: int, price: float) -> None:
        """Add or update a position."""
        if ticker not in self._state["positions"]:
            self._state["positions"][ticker] = {
                "shares": 0,
                "avg_entry_price": 0.0,
            }
        
        pos = self._state["positions"][ticker]
        old_shares = pos["shares"]
        old_avg = pos["avg_entry_price"]
        
        # Calculate new average entry price
        total_shares = old_shares + shares
        if total_shares > 0:
            new_avg = (
                (old_avg * old_shares + price * shares) / total_shares
            )
        else:
            new_avg = price
        
        pos["shares"] = total_shares
        pos["avg_entry_price"] = new_avg
        self._state["last_updated"] = datetime.now().isoformat()
        self._save()
    
    def remove_position(self, ticker: str) -> None:
        """Remove a position (sell all shares)."""
        if ticker in self._state["positions"]:
            del self._state["positions"][ticker]
            self._state["last_updated"] = datetime.now().isoformat()
            self._save()
    
    def record_trade(
        self,
        date: str,
        ticker: str,
        action: str,
        price: float,
        shares: int,
        commission: float,
    ) -> None:
        """Record a trade in history."""
        trade = {
            "date": date,
            "ticker": ticker,
            "action": action,
            "price": price,
            "shares": shares,
            "commission": commission,
        }
        self._state["trades"].append(trade)
        # Keep only last 1000 trades to prevent file bloat
        if len(self._state["trades"]) > 1000:
            self._state["trades"] = self._state["trades"][-1000:]
        self._state["last_updated"] = datetime.now().isoformat()
        self._save()
    
    def get_trade_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get trade history.
        
        Args:
            limit: Maximum number of trades to return (most recent first).
            
        Returns:
            List of trade dicts.
        """
        trades = self._state.get("trades", [])
        if limit:
            return trades[-limit:]
        return trades
    
    def get_initial_capital(self) -> float:
        """Get the initial capital persisted when state was first created."""
        return self._state.get("initial_capital", self.initial_capital)

    def append_run_snapshot(self, snapshot_dict: Dict) -> None:
        """Append a lightweight run snapshot for aggregate performance.

        Keeps the last 252 entries (roughly one trading year).
        """
        history = self._state.setdefault("run_history", [])
        history.append(snapshot_dict)
        if len(history) > 252:
            self._state["run_history"] = history[-252:]
        self._state["last_updated"] = datetime.now().isoformat()
        self._save()

    def get_run_history(self) -> List[Dict]:
        """Return stored run snapshots (oldest first)."""
        return self._state.get("run_history", [])

    def get_last_portfolio_value(self) -> float:
        """Get portfolio value from the end of the previous run."""
        return self._state.get(
            "last_portfolio_value",
            self._state.get("initial_capital", self.initial_capital),
        )

    def set_last_portfolio_value(self, value: float) -> None:
        """Store current portfolio value for next run's daily-return calc."""
        self._state["last_portfolio_value"] = value
        self._state["last_updated"] = datetime.now().isoformat()
        self._save()
