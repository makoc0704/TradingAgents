"""Aggregate performance metrics for backtest results.

Reuses calculation functions from tradingagents.risk.metrics where possible.
All functions are pure — input list of DailySnapshot, output dict.
"""

import logging
from typing import List, Dict

import pandas as pd

from tradingagents.risk.metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
)
from .models import DailySnapshot, TradeRecord

logger = logging.getLogger(__name__)


def calculate_backtest_performance(
    snapshots: List[DailySnapshot],
    trades: List[TradeRecord],
    initial_capital: float,
    risk_free_rate: float = 0.05,
) -> Dict[str, float]:
    """Compute aggregate performance metrics from backtest data.

    Args:
        snapshots: Ordered list of daily portfolio snapshots.
        trades: Ordered list of trade records.
        initial_capital: Starting portfolio value.
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino.

    Returns:
        Dict of metric name to value.
    """
    if not snapshots:
        return _empty_performance()

    # Build pandas series from snapshots
    values = pd.Series(
        [s.portfolio_value for s in snapshots],
        index=pd.to_datetime([s.date for s in snapshots]),
    )
    daily_returns = pd.Series(
        [s.daily_return for s in snapshots],
        index=pd.to_datetime([s.date for s in snapshots]),
    )

    # --- Core returns ---
    final_value = snapshots[-1].portfolio_value
    total_return = (final_value - initial_capital) / initial_capital
    n_days = len(snapshots)
    annualized_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1

    # --- Drawdown (reuse from risk.metrics) ---
    try:
        max_dd, current_dd = calculate_max_drawdown(values)
    except ValueError:
        max_dd, current_dd = 0.0, 0.0

    # --- Sharpe & Sortino (reuse from risk.metrics) ---
    returns_clean = daily_returns.dropna()
    try:
        sharpe = calculate_sharpe_ratio(returns_clean, risk_free_rate)
    except ValueError:
        sharpe = 0.0
    try:
        sortino = calculate_sortino_ratio(returns_clean, risk_free_rate)
    except ValueError:
        sortino = 0.0

    # --- Trade analysis ---
    actual_trades = [t for t in trades if t.action in ("BUY", "SELL")]
    buy_trades = [t for t in trades if t.action == "BUY"]
    sell_trades = [t for t in trades if t.action == "SELL"]

    # Win rate: compare portfolio value after each sell vs before corresponding buy
    wins, losses = _count_wins_losses(trades)
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0

    # Profit factor
    gross_profit, gross_loss = _calculate_profit_loss(trades)
    profit_factor = (
        gross_profit / abs(gross_loss) if gross_loss != 0 else float("inf")
    )

    # Exposure time: fraction of days we held a position
    days_with_position = sum(1 for s in snapshots if s.position_shares > 0)
    exposure_time = days_with_position / max(n_days, 1)

    # Total commissions
    total_commission = sum(t.commission for t in trades)

    # Buy-and-hold comparison
    buy_and_hold_return = _calculate_buy_and_hold(snapshots, initial_capital)

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_dd,
        "current_drawdown": current_dd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": len(actual_trades),
        "buy_trades": len(buy_trades),
        "sell_trades": len(sell_trades),
        "exposure_time": exposure_time,
        "total_commission": total_commission,
        "final_portfolio_value": final_value,
        "buy_and_hold_return": buy_and_hold_return,
        "alpha": total_return - buy_and_hold_return,
        "trading_days": n_days,
    }


def _count_wins_losses(trades: List[TradeRecord]) -> tuple:
    """Count winning and losing round-trip trades.

    A round trip is a BUY followed by a SELL.
    Win if portfolio value at SELL > portfolio value at preceding BUY.
    """
    wins = 0
    losses = 0
    last_buy_value = None

    for t in trades:
        if t.action == "BUY":
            last_buy_value = t.portfolio_value
        elif t.action == "SELL" and last_buy_value is not None:
            if t.portfolio_value > last_buy_value:
                wins += 1
            else:
                losses += 1
            last_buy_value = None

    return wins, losses


def _calculate_profit_loss(trades: List[TradeRecord]) -> tuple:
    """Calculate gross profit and gross loss from round-trip trades.

    Returns:
        Tuple of (gross_profit, gross_loss). gross_loss is negative.
    """
    gross_profit = 0.0
    gross_loss = 0.0
    last_buy_value = None

    for t in trades:
        if t.action == "BUY":
            last_buy_value = t.portfolio_value
        elif t.action == "SELL" and last_buy_value is not None:
            pnl = t.portfolio_value - last_buy_value
            if pnl > 0:
                gross_profit += pnl
            else:
                gross_loss += pnl
            last_buy_value = None

    return gross_profit, gross_loss


def _calculate_buy_and_hold(
    snapshots: List[DailySnapshot],
    initial_capital: float,
) -> float:
    """Calculate what buy-and-hold would have returned over the same period.

    Assumes buying at first day's price and holding to the last day.
    Uses the risk_metrics current_price if available, otherwise infers from
    position_value / position_shares.
    """
    if len(snapshots) < 2:
        return 0.0

    first_price = _get_price_from_snapshot(snapshots[0])
    last_price = _get_price_from_snapshot(snapshots[-1])

    if first_price is None or last_price is None or first_price <= 0:
        return 0.0

    return (last_price - first_price) / first_price


def _get_price_from_snapshot(snapshot: DailySnapshot) -> float:
    """Extract a price from a snapshot, trying risk_metrics first."""
    if snapshot.risk_metrics and "current_price" in snapshot.risk_metrics:
        return float(snapshot.risk_metrics["current_price"])
    if snapshot.position_shares > 0 and snapshot.position_value > 0:
        return snapshot.position_value / snapshot.position_shares
    return 0.0


def _empty_performance() -> Dict[str, float]:
    """Return zeroed-out performance dict."""
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "max_drawdown": 0.0,
        "current_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "total_trades": 0,
        "buy_trades": 0,
        "sell_trades": 0,
        "exposure_time": 0.0,
        "total_commission": 0.0,
        "final_portfolio_value": 0.0,
        "buy_and_hold_return": 0.0,
        "alpha": 0.0,
        "trading_days": 0,
    }
