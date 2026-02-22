"""LiveReader — reads live trading portfolio state from disk (read-only)."""

import json
import logging
import os
import statistics
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LiveReader:
    """Reads LivePortfolioState JSON from disk without modifying it.

    Args:
        state_path: Path to the live portfolio state JSON file.
    """

    def __init__(self, state_path: str = "./live_portfolio/state.json"):
        self.state_path = state_path

    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Load the state file from disk."""
        if not os.path.isfile(self.state_path):
            return None
        try:
            with open(self.state_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read live state from %s: %s", self.state_path, exc)
            return None

    def get_portfolio(self) -> Optional[Dict[str, Any]]:
        """Get the current portfolio state for the frontend.

        Returns a dict with: total_value, cash, initial_capital,
        positions (list), total_return, daily_return, last_updated.
        """
        state = self._load_state()
        if state is None:
            return None

        initial_capital = state.get("initial_capital", 0)
        cash = state.get("cash", 0)
        positions_raw = state.get("positions", {})
        last_portfolio_value = state.get("last_portfolio_value", initial_capital)

        positions = []
        total_position_value = 0.0
        for ticker, pos in positions_raw.items():
            shares = pos.get("shares", 0)
            avg_entry = pos.get("avg_entry_price", 0)
            current_price = pos.get("current_price", avg_entry)
            market_value = shares * current_price
            total_position_value += market_value
            cost_basis = shares * avg_entry
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis) if cost_basis > 0 else 0.0
            positions.append({
                "ticker": ticker,
                "shares": shares,
                "avg_entry_price": avg_entry,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "weight": 0.0,
            })

        total_value = cash + total_position_value
        for p in positions:
            p["weight"] = (p["market_value"] / total_value) if total_value > 0 else 0.0

        total_return = ((total_value - initial_capital) / initial_capital) if initial_capital > 0 else 0.0
        daily_return = ((total_value - last_portfolio_value) / last_portfolio_value) if last_portfolio_value > 0 else 0.0

        return {
            "total_value": total_value,
            "cash": cash,
            "initial_capital": initial_capital,
            "positions": positions,
            "total_return": total_return,
            "daily_return": daily_return,
            "last_updated": state.get("last_updated", ""),
        }

    def get_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent trades from state."""
        state = self._load_state()
        if state is None:
            return []
        trades = state.get("trades", [])
        return list(reversed(trades[-limit:]))

    def get_run_history(self) -> List[Dict[str, Any]]:
        """Get run snapshots for equity curve."""
        state = self._load_state()
        if state is None:
            return []
        return state.get("run_history", [])

    def get_performance(self) -> Optional[Dict[str, Any]]:
        """Compute aggregate performance metrics from run history."""
        state = self._load_state()
        if state is None:
            return None

        initial_capital = state.get("initial_capital", 0)
        last_value = state.get("last_portfolio_value", initial_capital)
        history = state.get("run_history", [])
        trades = state.get("trades", [])

        total_return = ((last_value - initial_capital) / initial_capital) if initial_capital > 0 else 0.0
        daily_return = 0.0
        if len(history) >= 2:
            prev = history[-2].get("portfolio_value", last_value)
            daily_return = ((last_value - prev) / prev) if prev > 0 else 0.0

        trading_days = len(history)
        annualized = total_return * (252 / trading_days) if trading_days > 0 else 0.0

        daily_returns = []
        for i in range(1, len(history)):
            prev_val = history[i - 1].get("portfolio_value", 0)
            cur_val = history[i].get("portfolio_value", 0)
            if prev_val > 0:
                daily_returns.append((cur_val - prev_val) / prev_val)

        sharpe = 0.0
        if daily_returns:
            mean_r = statistics.mean(daily_returns)
            std_r = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 1.0
            sharpe = (mean_r / std_r * (252 ** 0.5)) if std_r > 0 else 0.0

        max_dd = 0.0
        peak = initial_capital
        for snap in history:
            val = snap.get("portfolio_value", 0)
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        sell_trades = [t for t in trades if t.get("action", "").upper() == "SELL"]
        buy_trades = [t for t in trades if t.get("action", "").upper() == "BUY"]
        last_buy_price: Dict[str, float] = {}
        for bt in buy_trades:
            last_buy_price[bt.get("ticker", "")] = bt.get("price", 0)

        wins = 0
        for st in sell_trades:
            entry = last_buy_price.get(st.get("ticker", ""), 0)
            if entry > 0 and st.get("price", 0) > entry:
                wins += 1
        total_closed = len(sell_trades)
        win_rate = (wins / total_closed) if total_closed > 0 else 0.0

        return {
            "total_return": total_return,
            "daily_return": daily_return,
            "annualized_return": annualized,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "total_trades": len(buy_trades) + len(sell_trades),
            "trading_days": trading_days,
        }
