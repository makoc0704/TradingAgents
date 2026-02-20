"""Performance metrics calculation for live trading over time."""

import logging
from typing import List, Dict, Optional
from datetime import datetime

import pandas as pd

from tradingagents.risk.metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
)
from .models import LiveRunResult

logger = logging.getLogger(__name__)


def calculate_live_performance(
    run_history: List[LiveRunResult],
    initial_capital: float,
    risk_free_rate: float = 0.05,
) -> Dict[str, float]:
    """Calculate performance metrics from live trading run history.
    
    Similar to backtesting performance calculation, but works with
    LiveRunResult snapshots instead of DailySnapshot.
    
    Args:
        run_history: Ordered list of LiveRunResult (daily snapshots).
        initial_capital: Starting portfolio value.
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino.
        
    Returns:
        Dict of metric name to value.
    """
    if not run_history:
        return _empty_performance()
    
    # Build pandas series from snapshots
    dates = [r.date for r in run_history]
    values = pd.Series(
        [r.portfolio_snapshot.total_value for r in run_history],
        index=pd.to_datetime(dates),
    )
    
    # Calculate daily returns
    daily_returns = []
    for i, result in enumerate(run_history):
        if i == 0:
            daily_return = 0.0
        else:
            prev_value = run_history[i - 1].portfolio_snapshot.total_value
            curr_value = result.portfolio_snapshot.total_value
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
            else:
                daily_return = 0.0
        daily_returns.append(daily_return)
    
    returns_series = pd.Series(
        daily_returns,
        index=pd.to_datetime(dates),
    )
    
    # --- Core returns ---
    final_value = run_history[-1].portfolio_snapshot.total_value
    total_return = (final_value - initial_capital) / initial_capital
    n_days = len(run_history)
    annualized_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1
    
    # --- Drawdown (reuse from risk.metrics) ---
    try:
        max_dd, current_dd = calculate_max_drawdown(values)
    except ValueError:
        max_dd, current_dd = 0.0, 0.0
    
    # --- Sharpe & Sortino (reuse from risk.metrics) ---
    returns_clean = returns_series.dropna()
    try:
        sharpe = calculate_sharpe_ratio(returns_clean, risk_free_rate)
    except ValueError:
        sharpe = 0.0
    try:
        sortino = calculate_sortino_ratio(returns_clean, risk_free_rate)
    except ValueError:
        sortino = 0.0
    
    # --- Trade analysis ---
    all_orders = []
    for result in run_history:
        all_orders.extend(result.executed_orders)
    
    buy_orders = [o for o in all_orders if hasattr(o, "action") and o.action == "BUY"]
    sell_orders = [o for o in all_orders if hasattr(o, "action") and o.action == "SELL"]
    
    # Win rate: compare portfolio value after each sell vs before corresponding buy
    wins, losses = _count_wins_losses(run_history)
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    
    # Profit factor
    gross_profit, gross_loss = _calculate_profit_loss(run_history)
    profit_factor = (
        gross_profit / abs(gross_loss) if gross_loss != 0 else float("inf")
    )
    
    # Exposure time: fraction of days we held positions
    days_with_positions = sum(
        1 for r in run_history
        if len(r.portfolio_snapshot.positions) > 0
    )
    exposure_time = days_with_positions / max(n_days, 1)
    
    # Total commissions
    total_commission = sum(
        o.commission if hasattr(o, "commission") else 0.0
        for o in all_orders
    )
    
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_dd,
        "current_drawdown": current_dd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": len(buy_orders) + len(sell_orders),
        "buy_trades": len(buy_orders),
        "sell_trades": len(sell_orders),
        "exposure_time": exposure_time,
        "total_commission": total_commission,
        "final_portfolio_value": final_value,
        "trading_days": n_days,
    }


def _count_wins_losses(run_history: List[LiveRunResult]) -> tuple:
    """Count winning and losing round-trip trades.
    
    A round trip is a BUY followed by a SELL.
    Win if portfolio value at SELL > portfolio value at preceding BUY.
    """
    wins = 0
    losses = 0
    last_buy_value = None
    
    for result in run_history:
        for order in result.executed_orders:
            if hasattr(order, "action"):
                if order.action == "BUY":
                    last_buy_value = result.portfolio_snapshot.total_value
                elif order.action == "SELL" and last_buy_value is not None:
                    if result.portfolio_snapshot.total_value > last_buy_value:
                        wins += 1
                    else:
                        losses += 1
                    last_buy_value = None
    
    return wins, losses


def _calculate_profit_loss(run_history: List[LiveRunResult]) -> tuple:
    """Calculate gross profit and gross loss from round-trip trades.
    
    Returns:
        Tuple of (gross_profit, gross_loss). gross_loss is negative.
    """
    gross_profit = 0.0
    gross_loss = 0.0
    last_buy_value = None
    
    for result in run_history:
        for order in result.executed_orders:
            if hasattr(order, "action"):
                if order.action == "BUY":
                    last_buy_value = result.portfolio_snapshot.total_value
                elif order.action == "SELL" and last_buy_value is not None:
                    pnl = result.portfolio_snapshot.total_value - last_buy_value
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += pnl
                    last_buy_value = None
    
    return gross_profit, gross_loss


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
        "trading_days": 0,
    }
