"""Position sizing algorithms for risk-aware trade allocation.

All functions return a PositionSize dataclass. Fractions are clamped
to [0.0, max_fraction] to prevent over-allocation.
"""

import logging
import math

from .models import PositionSize

logger = logging.getLogger(__name__)


def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value to [min_val, max_val]."""
    return max(min_val, min(value, max_val))


def kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    current_price: float,
    atr: float,
    max_fraction: float = 0.25,
    atr_stop_multiplier: float = 2.0,
) -> PositionSize:
    """Calculate position size using the Kelly Criterion.

    The Kelly fraction is: f* = (win_rate / avg_loss_ratio) - ((1 - win_rate) / avg_win_ratio)
    Simplified: f* = win_rate - (1 - win_rate) / (avg_win / avg_loss)

    In practice, half-Kelly is often used to reduce variance.

    Args:
        win_rate: Historical win rate (0.0 to 1.0).
        avg_win: Average winning return (positive, e.g. 0.03 = 3%).
        avg_loss: Average losing return (positive, e.g. 0.02 = 2%).
        current_price: Current stock price for stop-loss calculation.
        atr: Average True Range for stop-loss placement.
        max_fraction: Maximum allowed portfolio fraction.
        atr_stop_multiplier: ATR multiplier for stop-loss distance.

    Returns:
        PositionSize with Kelly-based allocation.
    """
    if avg_loss <= 0 or avg_win <= 0:
        logger.warning("Invalid avg_win/avg_loss for Kelly, defaulting to zero position")
        return PositionSize(
            method="kelly",
            fraction=0.0,
            max_loss_percent=0.0,
            stop_loss_price=current_price,
        )

    win_loss_ratio = avg_win / avg_loss
    kelly_f = win_rate - (1 - win_rate) / win_loss_ratio

    # Use half-Kelly for safety
    half_kelly = kelly_f / 2.0
    fraction = _clamp(half_kelly, 0.0, max_fraction)

    stop_distance = atr * atr_stop_multiplier
    stop_loss = current_price - stop_distance
    max_loss = stop_distance / current_price if current_price > 0 else 0.0

    return PositionSize(
        method="kelly",
        fraction=fraction,
        max_loss_percent=max_loss,
        stop_loss_price=max(stop_loss, 0.0),
    )


def fixed_fraction(
    risk_per_trade: float,
    current_price: float,
    atr: float,
    max_fraction: float = 0.25,
    atr_stop_multiplier: float = 2.0,
) -> PositionSize:
    """Calculate position size using fixed fractional risk.

    Allocates so that the maximum loss (at stop-loss) equals a fixed
    fraction of the portfolio.

    Args:
        risk_per_trade: Maximum risk per trade as fraction (e.g. 0.02 = 2%).
        current_price: Current stock price.
        atr: Average True Range for stop-loss placement.
        max_fraction: Maximum allowed portfolio fraction.
        atr_stop_multiplier: ATR multiplier for stop-loss distance.

    Returns:
        PositionSize with fixed-fraction allocation.
    """
    stop_distance = atr * atr_stop_multiplier
    stop_loss = current_price - stop_distance

    if current_price <= 0 or stop_distance <= 0:
        return PositionSize(
            method="fixed_fraction",
            fraction=0.0,
            max_loss_percent=0.0,
            stop_loss_price=current_price,
        )

    risk_ratio = stop_distance / current_price
    # fraction = risk_per_trade / risk_ratio
    # If stop is 4% away and we want to risk 2%, we allocate 50%
    fraction = risk_per_trade / risk_ratio if risk_ratio > 0 else 0.0
    fraction = _clamp(fraction, 0.0, max_fraction)

    return PositionSize(
        method="fixed_fraction",
        fraction=fraction,
        max_loss_percent=risk_ratio,
        stop_loss_price=max(stop_loss, 0.0),
    )


def volatility_adjusted(
    annualized_volatility: float,
    target_volatility: float,
    current_price: float,
    atr: float,
    max_fraction: float = 0.25,
    atr_stop_multiplier: float = 2.0,
) -> PositionSize:
    """Calculate position size by targeting a portfolio volatility level.

    Scales position inversely with the stock's volatility, so higher-vol
    stocks get smaller positions.

    Args:
        annualized_volatility: Stock's annualized volatility.
        target_volatility: Desired portfolio volatility contribution (e.g. 0.15 = 15%).
        current_price: Current stock price.
        atr: Average True Range for stop-loss placement.
        max_fraction: Maximum allowed portfolio fraction.
        atr_stop_multiplier: ATR multiplier for stop-loss distance.

    Returns:
        PositionSize with volatility-adjusted allocation.
    """
    if annualized_volatility <= 0:
        logger.warning("Zero or negative volatility, defaulting to zero position")
        return PositionSize(
            method="volatility_adjusted",
            fraction=0.0,
            max_loss_percent=0.0,
            stop_loss_price=current_price,
        )

    fraction = target_volatility / annualized_volatility
    fraction = _clamp(fraction, 0.0, max_fraction)

    stop_distance = atr * atr_stop_multiplier
    stop_loss = current_price - stop_distance
    max_loss = stop_distance / current_price if current_price > 0 else 0.0

    return PositionSize(
        method="volatility_adjusted",
        fraction=fraction,
        max_loss_percent=max_loss,
        stop_loss_price=max(stop_loss, 0.0),
    )
