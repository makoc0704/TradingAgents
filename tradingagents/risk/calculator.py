"""RiskCalculator facade — single entry point for all risk computations.

Fetches price data via the existing vendor routing, computes all metrics,
and returns structured RiskMetrics / PositionSize objects.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd

import tradingagents.dataflows.interface as _interface_mod
from .models import RiskMetrics, PositionSize
from . import metrics as m
from . import position_sizing as ps

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Central facade for quantitative risk assessment.

    Args:
        config: Project configuration dict (DEFAULT_CONFIG or custom).
    """

    def __init__(self, config: Dict[str, Any]):
        self.lookback_days = config.get("risk_lookback_days", 60)
        self.benchmark = config.get("risk_benchmark", "SPY")
        self.risk_free_rate = config.get("risk_free_rate", 0.05)
        self.max_position_fraction = config.get("max_position_fraction", 0.25)
        self.default_portfolio_value = config.get("default_portfolio_value", 100000)

    def _fetch_price_data(self, ticker: str, trade_date: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for a ticker using the vendor routing system.

        Returns:
            DataFrame with columns [Open, High, Low, Close, Volume] indexed by date,
            or None if fetching fails.
        """
        try:
            end_dt = datetime.strptime(trade_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=self.lookback_days + 60)
            start_str = start_dt.strftime("%Y-%m-%d")

            raw = _interface_mod.route_to_vendor("get_stock_data", ticker, start_str, trade_date)

            if not raw or not isinstance(raw, str) or len(raw.strip()) == 0:
                logger.warning("Empty stock data returned for %s", ticker)
                return None

            df = self._parse_csv(raw)
            return df

        except Exception as e:
            logger.error("Failed to fetch price data for %s: %s", ticker, e)
            return None

    def _parse_csv(self, csv_text: str) -> pd.DataFrame:
        """Parse CSV text from vendor into a clean DataFrame.

        Handles various CSV formats returned by yfinance, Alpha Vantage, etc.
        The vendor functions prepend comment lines (starting with ``#``) and
        blank lines before the actual CSV data.  We strip those first so
        ``pd.read_csv`` sees a clean header row.
        """
        from io import StringIO

        # Strip comment lines and leading blank lines added by vendor wrappers
        clean_lines = []
        for line in csv_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Skip blank lines that appear before the actual CSV header
            if not stripped and not clean_lines:
                continue
            clean_lines.append(line)

        clean_csv = "\n".join(clean_lines)
        if not clean_csv.strip():
            raise ValueError("CSV text is empty after stripping comments")

        df = pd.read_csv(StringIO(clean_csv))

        # Normalize column names — vendors use different capitalization
        col_map = {}
        for col in df.columns:
            lower = col.strip().lower()
            if "date" in lower or "time" in lower:
                col_map[col] = "Date"
            elif lower in ("open",):
                col_map[col] = "Open"
            elif lower in ("high",):
                col_map[col] = "High"
            elif lower in ("low",):
                col_map[col] = "Low"
            elif lower in ("close", "adj close", "adjusted close"):
                col_map[col] = "Close"
            elif lower in ("volume",):
                col_map[col] = "Volume"

        df = df.rename(columns=col_map)

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")

        # Ensure required columns exist
        required = ["Open", "High", "Low", "Close"]
        for col in required:
            if col not in df.columns:
                # Try to find close-enough match
                for orig_col in df.columns:
                    if col.lower() in orig_col.lower():
                        df[col] = df[orig_col]
                        break

        df = df.sort_index()

        # Convert to numeric, coerce errors
        for col in required:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["Close"])
        return df

    def calculate_risk_metrics(self, ticker: str, trade_date: str) -> Optional[RiskMetrics]:
        """Compute all risk metrics for a ticker on a given date.

        Args:
            ticker: Stock ticker symbol.
            trade_date: Date string in YYYY-MM-DD format.

        Returns:
            RiskMetrics dataclass, or None if data is insufficient.
        """
        df = self._fetch_price_data(ticker, trade_date)
        if df is None or len(df) < 15:
            logger.warning("Insufficient data for risk metrics: %s on %s", ticker, trade_date)
            return None

        close = df["Close"]
        returns = close.pct_change().dropna()

        # --- Volatility ---
        try:
            daily_vol, annual_vol = m.calculate_volatility(close, window=min(30, len(close) - 1))
        except ValueError:
            daily_vol, annual_vol = 0.0, 0.0

        # --- ATR ---
        try:
            atr = m.calculate_atr(df["High"], df["Low"], close, window=14)
        except (ValueError, KeyError):
            atr = 0.0
        current_price = float(close.iloc[-1])
        atr_pct = atr / current_price if current_price > 0 else 0.0

        # --- Drawdown ---
        try:
            max_dd, current_dd = m.calculate_max_drawdown(close)
        except ValueError:
            max_dd, current_dd = 0.0, 0.0

        # --- VaR ---
        try:
            var_95, cvar_95 = m.calculate_var(returns, confidence=0.95)
        except ValueError:
            var_95, cvar_95 = 0.0, 0.0
        try:
            var_99, _ = m.calculate_var(returns, confidence=0.99)
        except ValueError:
            var_99 = 0.0

        # --- Beta ---
        try:
            bench_df = self._fetch_price_data(self.benchmark, trade_date)
            if bench_df is not None and len(bench_df) > 10:
                bench_returns = bench_df["Close"].pct_change().dropna()
                beta = m.calculate_beta(returns, bench_returns)
            else:
                beta = 1.0
        except (ValueError, Exception) as e:
            logger.warning("Beta calculation failed, defaulting to 1.0: %s", e)
            beta = 1.0

        # --- Sharpe & Sortino ---
        try:
            sharpe = m.calculate_sharpe_ratio(returns, self.risk_free_rate)
        except ValueError:
            sharpe = 0.0
        try:
            sortino = m.calculate_sortino_ratio(returns, self.risk_free_rate)
        except ValueError:
            sortino = 0.0

        # --- Trend indicators ---
        sma_50 = m.calculate_sma(close, 50)
        sma_200 = m.calculate_sma(close, 200)
        try:
            rsi = m.calculate_rsi(close, 14)
        except ValueError:
            rsi = 50.0

        return RiskMetrics(
            ticker=ticker,
            date=trade_date,
            daily_volatility=daily_vol,
            annualized_volatility=annual_vol,
            atr=atr,
            atr_percent=atr_pct,
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            beta=beta,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            current_price=current_price,
            sma_50=sma_50,
            sma_200=sma_200,
            rsi=rsi,
        )

    def calculate_position_size(
        self,
        risk_metrics: RiskMetrics,
        portfolio_value: Optional[float] = None,
    ) -> PositionSize:
        """Calculate recommended position size based on risk metrics.

        Uses volatility-adjusted sizing as the primary method.

        Args:
            risk_metrics: Pre-computed risk metrics.
            portfolio_value: Total portfolio value. Defaults to config value.

        Returns:
            PositionSize recommendation.
        """
        if portfolio_value is None:
            portfolio_value = self.default_portfolio_value

        return ps.volatility_adjusted(
            annualized_volatility=risk_metrics.annualized_volatility,
            target_volatility=0.15,
            current_price=risk_metrics.current_price,
            atr=risk_metrics.atr,
            max_fraction=self.max_position_fraction,
        )
