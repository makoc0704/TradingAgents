"""Correlation analysis and portfolio-level risk calculations.

Pure functions operating on price series — no LLM calls, no side effects.
"""

import logging
import math
from typing import Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_correlation_matrix(
    price_series: Dict[str, pd.Series],
) -> pd.DataFrame:
    """Compute pairwise correlation matrix from closing price series.

    Args:
        price_series: Mapping of ticker to closing prices (Series indexed by date).
            All series should cover the same date range (missing dates are fine;
            they are aligned via inner join).

    Returns:
        DataFrame with tickers as both index and columns, values in [-1, 1].

    Raises:
        ValueError: If fewer than 2 tickers are provided or fewer than 10
            overlapping dates exist.
    """
    if len(price_series) < 2:
        raise ValueError("Need at least 2 tickers for a correlation matrix")

    returns = {}
    for ticker, prices in price_series.items():
        ret = prices.pct_change().dropna()
        if len(ret) > 0:
            returns[ticker] = ret

    if len(returns) < 2:
        raise ValueError("At least 2 tickers must have valid return data")

    df = pd.DataFrame(returns)
    df = df.dropna()

    if len(df) < 10:
        raise ValueError(
            f"Need at least 10 overlapping trading days, got {len(df)}"
        )

    return df.corr()


def calculate_covariance_matrix(
    price_series: Dict[str, pd.Series],
    annualize: bool = True,
) -> pd.DataFrame:
    """Compute the covariance matrix of daily returns.

    Args:
        price_series: Mapping of ticker to closing prices.
        annualize: If True, multiply by 252 to annualize.

    Returns:
        Covariance matrix as DataFrame.

    Raises:
        ValueError: If fewer than 2 tickers or insufficient overlapping dates.
    """
    if len(price_series) < 2:
        raise ValueError("Need at least 2 tickers for a covariance matrix")

    returns = {}
    for ticker, prices in price_series.items():
        ret = prices.pct_change().dropna()
        if len(ret) > 0:
            returns[ticker] = ret

    df = pd.DataFrame(returns).dropna()

    if len(df) < 10:
        raise ValueError(
            f"Need at least 10 overlapping trading days, got {len(df)}"
        )

    cov = df.cov()
    if annualize:
        cov = cov * 252
    return cov


def calculate_portfolio_volatility(
    weights: Dict[str, float],
    cov_matrix: pd.DataFrame,
) -> float:
    """Calculate annualized portfolio volatility from weights and covariance.

    Args:
        weights: Target weight per ticker.
        cov_matrix: Annualized covariance matrix (tickers as index/columns).

    Returns:
        Annualized portfolio standard deviation.
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])

    cov_sub = cov_matrix.loc[tickers, tickers].values
    port_var = float(w @ cov_sub @ w)
    return math.sqrt(max(port_var, 0.0))


def calculate_portfolio_var(
    weights: Dict[str, float],
    cov_matrix: pd.DataFrame,
    confidence: float = 0.95,
) -> float:
    """Estimate portfolio Value at Risk using the parametric (variance-covariance) method.

    Assumes daily returns are approximately normal.

    Args:
        weights: Target weight per ticker.
        cov_matrix: Annualized covariance matrix.
        confidence: Confidence level (e.g. 0.95).

    Returns:
        Daily VaR as a negative fraction (e.g. -0.02 = -2% loss).
    """
    from scipy.stats import norm

    port_annual_vol = calculate_portfolio_volatility(weights, cov_matrix)
    port_daily_vol = port_annual_vol / math.sqrt(252)
    z_score = norm.ppf(1 - confidence)
    return float(z_score * port_daily_vol)


def diversification_ratio(
    weights: Dict[str, float],
    volatilities: Dict[str, float],
    portfolio_volatility: float,
) -> float:
    """Calculate the diversification ratio.

    Defined as (weighted sum of individual volatilities) / portfolio volatility.
    A value > 1 indicates diversification benefit.

    Args:
        weights: Target weight per ticker.
        volatilities: Annualized volatility per ticker.
        portfolio_volatility: Annualized portfolio volatility.

    Returns:
        Diversification ratio (>= 1.0). Returns 1.0 if portfolio vol is near zero.
    """
    if portfolio_volatility < 1e-12:
        return 1.0

    weighted_sum = sum(
        weights.get(t, 0.0) * volatilities.get(t, 0.0) for t in weights
    )
    return max(weighted_sum / portfolio_volatility, 1.0)


def get_individual_volatilities(
    price_series: Dict[str, pd.Series],
    window: int = 60,
) -> Dict[str, float]:
    """Calculate annualized volatility for each ticker.

    Args:
        price_series: Mapping of ticker to closing prices.
        window: Lookback window in trading days.

    Returns:
        Dict mapping ticker to annualized volatility.
    """
    vols = {}
    for ticker, prices in price_series.items():
        recent = prices.tail(window)
        if len(recent) < 2:
            vols[ticker] = 0.0
            continue
        returns = recent.pct_change().dropna()
        daily_vol = float(returns.std())
        vols[ticker] = daily_vol * math.sqrt(252)
    return vols
