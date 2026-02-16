"""Tests for tradingagents.risk.metrics — pure mathematical risk calculations."""

import pytest
import pandas as pd
import numpy as np

from tradingagents.risk.metrics import (
    calculate_volatility,
    calculate_var,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_beta,
    calculate_atr,
    calculate_rsi,
    calculate_sma,
)


# --- Fixtures ---

@pytest.fixture
def rising_prices():
    """Steadily rising price series (100 days)."""
    return pd.Series(
        [100 + i * 0.5 for i in range(100)],
        index=pd.date_range("2024-01-01", periods=100),
    )


@pytest.fixture
def volatile_prices():
    """Volatile price series with known properties."""
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return pd.Series(prices, index=pd.date_range("2024-01-01", periods=101))


@pytest.fixture
def ohlc_data():
    """OHLC DataFrame for ATR calculation."""
    np.random.seed(42)
    n = 30
    close = [100.0]
    for _ in range(n - 1):
        close.append(close[-1] * (1 + np.random.normal(0, 0.015)))
    close = pd.Series(close)
    high = close * (1 + abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - abs(np.random.normal(0, 0.005, n)))
    return high, low, close


# --- Volatility ---

class TestVolatility:
    def test_returns_tuple(self, volatile_prices):
        daily, annual = calculate_volatility(volatile_prices)
        assert isinstance(daily, float)
        assert isinstance(annual, float)

    def test_annualized_greater_than_daily(self, volatile_prices):
        daily, annual = calculate_volatility(volatile_prices)
        assert annual > daily

    def test_rising_prices_low_volatility(self, rising_prices):
        daily, _ = calculate_volatility(rising_prices)
        assert daily < 0.01

    def test_window_parameter(self, volatile_prices):
        d10, _ = calculate_volatility(volatile_prices, window=10)
        d50, _ = calculate_volatility(volatile_prices, window=50)
        assert isinstance(d10, float)
        assert isinstance(d50, float)

    def test_insufficient_data(self):
        with pytest.raises(ValueError, match="at least 2"):
            calculate_volatility(pd.Series([100.0]), window=5)


# --- VaR ---

class TestVaR:
    def test_var_is_negative(self, volatile_prices):
        returns = volatile_prices.pct_change().dropna()
        var, cvar = calculate_var(returns, confidence=0.95)
        assert var < 0
        assert cvar <= var

    def test_var_99_worse_than_95(self, volatile_prices):
        returns = volatile_prices.pct_change().dropna()
        var95, _ = calculate_var(returns, 0.95)
        var99, _ = calculate_var(returns, 0.99)
        assert var99 <= var95

    def test_insufficient_data(self):
        with pytest.raises(ValueError, match="at least 10"):
            calculate_var(pd.Series([0.01, -0.01, 0.02]))


# --- Drawdown ---

class TestDrawdown:
    def test_rising_prices_no_drawdown(self, rising_prices):
        max_dd, current_dd = calculate_max_drawdown(rising_prices)
        assert max_dd == 0.0
        assert current_dd == 0.0

    def test_known_drawdown(self):
        prices = pd.Series([100, 110, 90, 95, 105])
        max_dd, current_dd = calculate_max_drawdown(prices)
        assert max_dd == pytest.approx(-20 / 110, rel=1e-6)
        # 105 < 110 (the peak), so still in drawdown: (105-110)/110
        assert current_dd == pytest.approx(-5 / 110, rel=1e-6)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_max_drawdown(pd.Series([], dtype=float))


# --- Sharpe Ratio ---

class TestSharpe:
    def test_positive_for_rising_prices(self, rising_prices):
        returns = rising_prices.pct_change().dropna()
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        assert sharpe > 0

    def test_zero_vol_returns_zero(self):
        returns = pd.Series([0.0] * 20)
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe == 0.0

    def test_insufficient_data(self):
        with pytest.raises(ValueError, match="at least 2"):
            calculate_sharpe_ratio(pd.Series([0.01]))


# --- Sortino Ratio ---

class TestSortino:
    def test_positive_for_rising_prices(self, rising_prices):
        returns = rising_prices.pct_change().dropna()
        sortino = calculate_sortino_ratio(returns)
        assert sortino > 0

    def test_insufficient_data(self):
        with pytest.raises(ValueError, match="at least 2"):
            calculate_sortino_ratio(pd.Series([0.01]))


# --- Beta ---

class TestBeta:
    def test_self_beta_is_one(self, volatile_prices):
        returns = volatile_prices.pct_change().dropna()
        beta = calculate_beta(returns, returns)
        assert beta == pytest.approx(1.0, rel=1e-4)

    def test_insufficient_overlap(self):
        s1 = pd.Series([0.01, -0.01], index=[0, 1])
        s2 = pd.Series([0.02, -0.02], index=[0, 1])
        with pytest.raises(ValueError, match="at least 10"):
            calculate_beta(s1, s2)


# --- ATR ---

class TestATR:
    def test_atr_positive(self, ohlc_data):
        high, low, close = ohlc_data
        atr = calculate_atr(high, low, close, window=14)
        assert atr > 0

    def test_insufficient_data(self):
        short = pd.Series([100.0] * 5)
        with pytest.raises(ValueError, match="at least"):
            calculate_atr(short, short, short, window=14)


# --- RSI ---

class TestRSI:
    def test_rsi_rising_prices(self, rising_prices):
        rsi = calculate_rsi(rising_prices)
        assert 50 < rsi <= 100

    def test_rsi_range(self, volatile_prices):
        rsi = calculate_rsi(volatile_prices)
        assert 0 <= rsi <= 100

    def test_insufficient_data(self):
        with pytest.raises(ValueError, match="at least"):
            calculate_rsi(pd.Series([100.0] * 5), window=14)


# --- SMA ---

class TestSMA:
    def test_sma_with_enough_data(self, rising_prices):
        sma = calculate_sma(rising_prices, 50)
        assert isinstance(sma, float)
        assert sma > 0

    def test_sma_fallback_short_data(self):
        prices = pd.Series([10.0, 20.0, 30.0])
        sma = calculate_sma(prices, 50)
        assert sma == pytest.approx(20.0)
