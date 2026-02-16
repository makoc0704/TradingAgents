"""BacktestRunner — orchestrates the TradingAgentsGraph over a date range.

The runner is the single entry point for backtesting. It:
1. Generates valid trading dates.
2. Iterates, calling graph.propagate() per date.
3. Executes signals via Portfolio.
4. Optionally triggers reflection.
5. Computes aggregate performance.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Union

import pandas as pd

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.risk.models import TradeSignal

from .models import (
    BacktestConfig,
    BacktestResult,
    BACKTEST_PROFILES,
)
from .portfolio import Portfolio
from .performance import calculate_backtest_performance
from .data_cache import DataCache, create_cached_route_to_vendor

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Runs the TradingAgentsGraph over a historical date range.

    Args:
        backtest_config: Configuration for this backtest run.
    """

    def __init__(self, backtest_config: BacktestConfig):
        self.bt_config = backtest_config
        self._graph = None
        self._portfolio = None
        self._cache = None

    def run(self) -> BacktestResult:
        """Execute the full backtest and return results.

        Returns:
            BacktestResult with trades, snapshots, and performance metrics.
        """
        logger.info(
            "Starting backtest: %s from %s to %s (profile=%s, reflection=%s)",
            self.bt_config.ticker,
            self.bt_config.start_date,
            self.bt_config.end_date,
            self.bt_config.backtest_profile,
            self.bt_config.reflection_mode,
        )

        # Build the effective config
        effective_config = self._build_effective_config()

        # Initialize data cache
        cache_dir = os.path.join(
            effective_config.get("data_cache_dir", "data_cache"),
            "backtest_cache",
        )
        self._cache = DataCache(cache_dir, enabled=self.bt_config.use_data_cache)

        # Patch route_to_vendor if caching is enabled
        if self.bt_config.use_data_cache:
            self._install_cache_hook()

        # Initialize the graph (lazy import to avoid circular deps)
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        profile = BACKTEST_PROFILES.get(
            self.bt_config.backtest_profile, BACKTEST_PROFILES["standard"]
        )
        selected_analysts = profile.get(
            "selected_analysts", self.bt_config.selected_analysts
        )

        self._graph = TradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=False,
            config=effective_config,
        )

        # Initialize portfolio
        self._portfolio = Portfolio(
            initial_capital=self.bt_config.initial_capital,
            commission_rate=self.bt_config.commission_rate,
            slippage_rate=self.bt_config.slippage_rate,
        )

        # Generate trading dates
        trading_dates = self._generate_trading_dates()
        logger.info("Generated %d trading dates", len(trading_dates))

        if not trading_dates:
            logger.warning("No valid trading dates in range — returning empty result")
            return self._build_empty_result()

        # Fetch price data for the entire period (for daily snapshots)
        price_data = self._fetch_price_series(trading_dates)

        # Main backtest loop
        trades = []
        snapshots = []
        days_since_reflection = 0

        for i, date_str in enumerate(trading_dates):
            logger.info(
                "Day %d/%d: %s",
                i + 1, len(trading_dates), date_str,
            )

            # Get price for this day
            price = price_data.get(date_str)
            if price is None or price <= 0:
                logger.warning("No price data for %s — skipping", date_str)
                continue

            # Run the agent graph
            signal, risk_metrics_dict = self._run_propagation(date_str)

            # Execute signal
            trade_record = self._portfolio.execute_signal(
                signal=signal,
                ticker=self.bt_config.ticker,
                price=price,
                date=date_str,
            )
            trades.append(trade_record)

            # Record daily snapshot
            action = trade_record.action
            snapshot = self._portfolio.get_daily_snapshot(
                date=date_str,
                price=price,
                action=action,
                risk_metrics=risk_metrics_dict,
            )
            snapshots.append(snapshot)

            # Periodic reflection
            days_since_reflection += 1
            if self._should_reflect(days_since_reflection, i, len(trading_dates)):
                self._do_reflection(snapshots)
                days_since_reflection = 0

        # End-of-backtest reflection
        if self.bt_config.reflection_mode == "end_only" and snapshots:
            self._do_reflection(snapshots)

        # Compute performance
        performance = calculate_backtest_performance(
            snapshots=snapshots,
            trades=trades,
            initial_capital=self.bt_config.initial_capital,
            risk_free_rate=effective_config.get("risk_free_rate", 0.05),
        )

        actual_trades = [t for t in trades if t.action in ("BUY", "SELL")]

        # Log cache stats
        if self._cache:
            stats = self._cache.stats
            logger.info(
                "Data cache stats: %d hits, %d misses (%.1f%% hit rate)",
                stats["hits"], stats["misses"], stats["hit_rate"] * 100,
            )

        result = BacktestResult(
            config=self.bt_config,
            trades=trades,
            daily_snapshots=snapshots,
            performance=performance,
            total_trading_days=len(snapshots),
            total_trades=len(actual_trades),
        )

        logger.info(
            "Backtest complete: %d days, %d trades, total return: %.2f%%",
            len(snapshots), len(actual_trades),
            performance.get("total_return", 0) * 100,
        )

        return result

    def _build_effective_config(self) -> dict:
        """Merge BacktestConfig with DEFAULT_CONFIG and profile overrides."""
        config = DEFAULT_CONFIG.copy()
        config.update(self.bt_config.config)

        # Apply profile overrides
        profile = BACKTEST_PROFILES.get(
            self.bt_config.backtest_profile, {}
        )
        for key, value in profile.items():
            if key != "selected_analysts":
                config[key] = value

        return config

    def _install_cache_hook(self) -> None:
        """Monkey-patch the dataflows interface to use our cache.

        This replaces route_to_vendor with a cached version for the
        duration of the backtest.
        """
        import tradingagents.dataflows.interface as interface_mod

        cached_fn = create_cached_route_to_vendor(self._cache)
        self._original_route = interface_mod.route_to_vendor
        interface_mod.route_to_vendor = cached_fn
        logger.info("Data cache installed (dir=%s)", self._cache.cache_dir)

    def _restore_route_hook(self) -> None:
        """Restore the original route_to_vendor after backtest."""
        if hasattr(self, "_original_route"):
            import tradingagents.dataflows.interface as interface_mod
            interface_mod.route_to_vendor = self._original_route

    def _generate_trading_dates(self) -> List[str]:
        """Generate valid trading dates between start and end date.

        Skips weekends. For weekly/monthly frequency, samples accordingly.

        Returns:
            Sorted list of date strings in YYYY-MM-DD format.
        """
        start = datetime.strptime(self.bt_config.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.bt_config.end_date, "%Y-%m-%d")

        all_dates = []
        current = start
        while current <= end:
            # Skip weekends (5=Saturday, 6=Sunday)
            if current.weekday() < 5:
                all_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        # Apply frequency filter
        freq = self.bt_config.trading_frequency
        if freq == "weekly":
            # Take every Monday (or first weekday of each week)
            filtered = []
            last_week = None
            for d_str in all_dates:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                week_num = dt.isocalendar()[1]
                if week_num != last_week:
                    filtered.append(d_str)
                    last_week = week_num
            return filtered
        elif freq == "monthly":
            # Take the first trading day of each month
            filtered = []
            last_month = None
            for d_str in all_dates:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                if dt.month != last_month:
                    filtered.append(d_str)
                    last_month = dt.month
            return filtered

        return all_dates

    def _fetch_price_series(self, trading_dates: List[str]) -> dict:
        """Fetch closing prices for all trading dates.

        Uses yfinance directly to get a complete price series efficiently
        in a single API call rather than per-date.

        Returns:
            Dict mapping date string to closing price.
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(self.bt_config.ticker)
            start = trading_dates[0]
            # Add a buffer day to ensure we get the last date
            end_dt = datetime.strptime(trading_dates[-1], "%Y-%m-%d") + timedelta(days=5)
            end = end_dt.strftime("%Y-%m-%d")

            hist = ticker.history(start=start, end=end)

            if hist.empty:
                logger.error("No price data from yfinance for %s", self.bt_config.ticker)
                return {}

            # Normalize timezone
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)

            prices = {}
            for date_str in trading_dates:
                dt = pd.Timestamp(date_str)
                if dt in hist.index:
                    prices[date_str] = float(hist.loc[dt, "Close"])
                else:
                    # Try nearest available date
                    idx = hist.index.get_indexer([dt], method="nearest")
                    if len(idx) > 0 and idx[0] >= 0:
                        prices[date_str] = float(hist.iloc[idx[0]]["Close"])

            logger.info(
                "Fetched %d/%d prices for %s",
                len(prices), len(trading_dates), self.bt_config.ticker,
            )
            return prices

        except Exception as e:
            logger.error("Failed to fetch price series: %s", e)
            return {}

    def _run_propagation(self, date_str: str) -> tuple:
        """Run graph.propagate() and handle failures gracefully.

        Returns:
            Tuple of (signal, risk_metrics_dict). On failure, returns
            ("HOLD", {}).
        """
        try:
            state, signal = self._graph.propagate(
                self.bt_config.ticker, date_str
            )
            risk_metrics_dict = state.get("risk_metrics", {})
            return signal, risk_metrics_dict

        except Exception as e:
            logger.error(
                "propagate() failed for %s on %s: %s — treating as HOLD",
                self.bt_config.ticker, date_str, e,
            )
            return "HOLD", {}

    def _should_reflect(
        self,
        days_since_last: int,
        current_index: int,
        total_days: int,
    ) -> bool:
        """Determine if we should trigger a reflection now."""
        mode = self.bt_config.reflection_mode

        if mode == "none":
            return False
        if mode == "end_only":
            return False
        if mode == "periodic":
            return days_since_last >= self.bt_config.reflection_interval

        return False

    def _do_reflection(self, snapshots) -> None:
        """Run graph.reflect_and_remember() with current performance data."""
        if not self._graph or not snapshots:
            return

        try:
            # Calculate cumulative return as the reflection input
            cum_return = snapshots[-1].cumulative_return
            portfolio_value = snapshots[-1].portfolio_value

            # Pass structured info as returns_losses
            reflection_data = (
                f"Portfolio value: ${portfolio_value:,.2f} | "
                f"Cumulative return: {cum_return * 100:+.2f}% | "
                f"Days traded: {len(snapshots)}"
            )

            self._graph.reflect_and_remember(reflection_data)
            logger.info("Reflection completed (cumulative return: %.2f%%)", cum_return * 100)

        except Exception as e:
            logger.warning("Reflection failed: %s", e)

    def _build_empty_result(self) -> BacktestResult:
        """Build an empty result for edge cases."""
        return BacktestResult(
            config=self.bt_config,
            trades=[],
            daily_snapshots=[],
            performance={},
            total_trading_days=0,
            total_trades=0,
        )
