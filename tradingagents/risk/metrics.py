"""Pure mathematical risk metric calculations.

All functions operate on pandas Series/DataFrames and return floats.
No LLM calls, no side effects, no network access.
"""

import logging
import math
from typing import Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_volatility(
    prices: pd.Series,
    window: int = 30,
) -> Tuple[float, float]:
    """Calculate daily and annualized volatility from closing prices.

    Args:
        prices: Series of closing prices, indexed by date, sorted ascending.
        window: Number of recent trading days to use.

    Returns:
        Tuple of (daily_volatility, annualized_volatility).

    Raises:
        ValueError: If prices has fewer than 2 data points after windowing.
    """
    recent = prices.tail(window)
    if len(recent) < 2:
        raise ValueError(f"Need at least 2 price points, got {len(recent)}")

    returns = recent.pct_change().dropna()
    daily_vol = float(returns.std())
    annualized_vol = daily_vol * math.sqrt(252)
    return daily_vol, annualized_vol


def calculate_var(
    returns: pd.Series,
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """Calculate Value at Risk and Conditional VaR (Expected Shortfall).

    Uses historical simulation (percentile method).

    Args:
        returns: Series of daily returns (e.g. from pct_change).
        confidence: Confidence level (0.95 or 0.99 typically).

    Returns:
        Tuple of (var, cvar) as negative fractions (e.g. -0.02 = -2% loss).

    Raises:
        ValueError: If returns has fewer than 10 data points.
    """
    if len(returns) < 10:
        raise ValueError(f"Need at least 10 return observations, got {len(returns)}")

    alpha = 1 - confidence
    var = float(np.percentile(returns.dropna(), alpha * 100))
    cvar = float(returns[returns <= var].mean()) if (returns <= var).any() else var
    return var, cvar


def calculate_max_drawdown(
    prices: pd.Series,
) -> Tuple[float, float]:
    """Calculate maximum drawdown and current drawdown from a price series.

    Args:
        prices: Series of closing prices, sorted ascending by date.

    Returns:
        Tuple of (max_drawdown, current_drawdown) as negative fractions.
        E.g. -0.15 means a 15% drawdown from peak.

    Raises:
        ValueError: If prices is empty.
    """
    if len(prices) < 1:
        raise ValueError("Need at least 1 price point")

    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax

    max_dd = float(drawdown.min())
    current_dd = float(drawdown.iloc[-1])
    return max_dd, current_dd


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.05,
) -> float:
    """Calculate annualized Sharpe ratio.

    Args:
        returns: Series of daily returns.
        risk_free_rate: Annual risk-free rate (default 5%).

    Returns:
        Annualized Sharpe ratio.

    Raises:
        ValueError: If returns has fewer than 2 data points or zero volatility.
    """
    if len(returns) < 2:
        raise ValueError(f"Need at least 2 return observations, got {len(returns)}")

    daily_rf = risk_free_rate / 252
    excess_returns = returns - daily_rf
    std = excess_returns.std()

    if std < 1e-12 or np.isnan(std):
        return 0.0

    return float((excess_returns.mean() / std) * math.sqrt(252))


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.05,
) -> float:
    """Calculate annualized Sortino ratio (penalizes only downside volatility).

    Args:
        returns: Series of daily returns.
        risk_free_rate: Annual risk-free rate.

    Returns:
        Annualized Sortino ratio.

    Raises:
        ValueError: If returns has fewer than 2 data points.
    """
    if len(returns) < 2:
        raise ValueError(f"Need at least 2 return observations, got {len(returns)}")

    daily_rf = risk_free_rate / 252
    excess_returns = returns - daily_rf
    downside = excess_returns[excess_returns < 0]

    downside_std = float(downside.std()) if len(downside) > 1 else 0.0

    if downside_std < 1e-12:
        # No downside risk: if mean excess return is positive, ratio is
        # effectively infinite; cap at a large finite value.
        if excess_returns.mean() > 0:
            return 99.0
        return 0.0

    return float((excess_returns.mean() / downside_std) * math.sqrt(252))


def calculate_beta(
    stock_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Calculate beta of a stock relative to a benchmark.

    Args:
        stock_returns: Daily returns of the stock.
        benchmark_returns: Daily returns of the benchmark (e.g. SPY).

    Returns:
        Beta coefficient.

    Raises:
        ValueError: If series have fewer than 10 overlapping data points.
    """
    aligned = pd.concat(
        [stock_returns.rename("stock"), benchmark_returns.rename("bench")],
        axis=1,
    ).dropna()

    if len(aligned) < 10:
        raise ValueError(f"Need at least 10 overlapping observations, got {len(aligned)}")

    bench_var = aligned["bench"].var()
    if bench_var == 0:
        return 1.0

    covariance = aligned["stock"].cov(aligned["bench"])
    return float(covariance / bench_var)


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> float:
    """Calculate Average True Range.

    Args:
        high: Series of daily high prices.
        low: Series of daily low prices.
        close: Series of daily closing prices.
        window: ATR averaging window (default 14 days).

    Returns:
        ATR value (absolute dollar amount).

    Raises:
        ValueError: If any series has fewer data points than window + 1.
    """
    min_len = min(len(high), len(low), len(close))
    if min_len < window + 1:
        raise ValueError(f"Need at least {window + 1} data points, got {min_len}")

    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    return float(tr.tail(window).mean())


def calculate_rsi(
    prices: pd.Series,
    window: int = 14,
) -> float:
    """Calculate Relative Strength Index.

    Args:
        prices: Series of closing prices.
        window: RSI period (default 14).

    Returns:
        RSI value between 0 and 100.

    Raises:
        ValueError: If prices has fewer data points than window + 1.
    """
    if len(prices) < window + 1:
        raise ValueError(f"Need at least {window + 1} data points, got {len(prices)}")

    delta = prices.diff()
    gains = delta.clip(lower=0)
    losses = (-delta).clip(lower=0)

    avg_gain = gains.rolling(window=window, min_periods=window).mean().iloc[-1]
    avg_loss = losses.rolling(window=window, min_periods=window).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def calculate_sma(
    prices: pd.Series,
    window: int,
) -> float:
    """Calculate Simple Moving Average at the latest data point.

    Args:
        prices: Series of closing prices.
        window: SMA period.

    Returns:
        SMA value. If insufficient data, returns the mean of available prices.
    """
    if len(prices) >= window:
        return float(prices.tail(window).mean())
    return float(prices.mean())
