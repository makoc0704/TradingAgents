"""PortfolioManager — top-level orchestration for multi-asset backtesting.

Calls ``TradingAgentsGraph.propagate()`` once per ticker per trading day
(sequentially), collects signals, optimizes weights, rebalances, and records
portfolio snapshots.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.risk.models import RiskMetrics, TradeSignal
from tradingagents.backtesting.models import TradeRecord, BACKTEST_PROFILES
from tradingagents.backtesting.data_cache import DataCache, create_cached_route_to_vendor

from .models import (
    PortfolioConfig,
    PortfolioResult,
    PortfolioSnapshot,
    AllocationResult,
)
from .multi_portfolio import MultiAssetPortfolio
from .optimizer import PortfolioOptimizer
from .rebalancer import Rebalancer
from .correlation import get_individual_volatilities

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Orchestrates multi-asset backtesting.

    Single entry point: create an instance with a ``PortfolioConfig``,
    then call ``run()`` to execute the full backtest.

    Args:
        config: Portfolio configuration.
    """

    def __init__(self, config: PortfolioConfig):
        self.config = config
        self._graph = None
        self._portfolio: Optional[MultiAssetPortfolio] = None
        self._optimizer: Optional[PortfolioOptimizer] = None
        self._rebalancer: Optional[Rebalancer] = None
        self._cache: Optional[DataCache] = None

    def run(self) -> PortfolioResult:
        """Execute the full portfolio backtest and return results.

        Returns:
            PortfolioResult with snapshots, trades, and performance metrics.
        """
        logger.info(
            "Starting portfolio backtest: %s from %s to %s "
            "(strategy=%s, profile=%s, reflection=%s)",
            ", ".join(self.config.tickers),
            self.config.start_date,
            self.config.end_date,
            self.config.weighting_strategy,
            self.config.backtest_profile,
            self.config.reflection_mode,
        )

        effective_config = self._build_effective_config()

        self._setup_cache(effective_config)
        self._setup_graph(effective_config)
        self._setup_portfolio()
        self._setup_optimizer()
        self._setup_rebalancer()

        trading_dates = self._generate_trading_dates()
        logger.info("Generated %d trading dates", len(trading_dates))

        if not trading_dates:
            logger.warning("No valid trading dates — returning empty result")
            return self._build_empty_result()

        price_data = self._fetch_all_price_series(trading_dates)

        all_trades: List[Dict] = []
        snapshots: List[PortfolioSnapshot] = []
        days_since_reflection = 0
        current_allocation: Optional[AllocationResult] = None

        for i, date_str in enumerate(trading_dates):
            logger.info("Day %d/%d: %s", i + 1, len(trading_dates), date_str)

            prices = self._get_prices_for_date(price_data, date_str)
            if not prices:
                logger.warning("No price data for %s — skipping", date_str)
                continue

            signals, risk_metrics_map = self._run_all_propagations(date_str)

            price_series = self._extract_price_series(price_data, date_str)
            allocation = self._optimizer.optimize(
                strategy=self.config.weighting_strategy,
                tickers=self.config.tickers,
                price_series=price_series,
                risk_metrics=risk_metrics_map,
                signals=signals,
            )
            current_allocation = allocation
            self._portfolio.set_target_weights(allocation.weights)

            day_actions: Dict[str, str] = {}
            day_trades: List[TradeRecord] = []

            if i == 0:
                day_trades, day_actions = self._initial_buy(
                    allocation, prices, date_str, signals,
                )
            else:
                should_rebalance = self._rebalancer.should_rebalance_today(
                    i, self.config.rebalance_frequency, trading_dates,
                )
                if should_rebalance:
                    positions = self._portfolio.get_all_positions(prices)
                    drift = self._rebalancer.check_drift(
                        positions, allocation.weights, self._portfolio.cash, prices,
                    )
                    if drift:
                        day_trades, day_actions = self._execute_rebalance(
                            allocation, prices, date_str,
                        )

                if not day_actions:
                    day_trades, day_actions = self._execute_signals(
                        signals, allocation, prices, date_str,
                    )

            for tr in day_trades:
                all_trades.append(tr.to_dict())

            snapshot = self._portfolio.get_snapshot(
                date=date_str,
                prices=prices,
                actions=day_actions,
                allocation=current_allocation,
            )
            snapshots.append(snapshot)

            days_since_reflection += 1
            if self._should_reflect(days_since_reflection, i, len(trading_dates)):
                self._do_reflection(snapshots)
                days_since_reflection = 0

        if self.config.reflection_mode == "end_only" and snapshots:
            self._do_reflection(snapshots)

        self._restore_cache()

        performance = self._calculate_performance(snapshots, all_trades)
        per_ticker = self._calculate_per_ticker_performance(all_trades, price_data, trading_dates)
        actual_trades = [
            t for t in all_trades if t.get("action") in ("BUY", "SELL")
        ]

        if self._cache:
            stats = self._cache.stats
            logger.info(
                "Data cache stats: %d hits, %d misses (%.1f%% hit rate)",
                stats["hits"], stats["misses"], stats["hit_rate"] * 100,
            )

        result = PortfolioResult(
            config=self.config,
            snapshots=snapshots,
            all_trades=all_trades,
            performance=performance,
            per_ticker_performance=per_ticker,
            total_trading_days=len(snapshots),
            total_trades=len(actual_trades),
        )

        logger.info(
            "Portfolio backtest complete: %d days, %d trades, return: %.2f%%",
            len(snapshots), len(actual_trades),
            performance.get("total_return", 0) * 100,
        )

        return result

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _build_effective_config(self) -> dict:
        """Merge PortfolioConfig with DEFAULT_CONFIG and profile overrides."""
        config = DEFAULT_CONFIG.copy()
        config.update(self.config.config)

        profile = BACKTEST_PROFILES.get(self.config.backtest_profile, {})
        for key, value in profile.items():
            if key != "selected_analysts":
                config[key] = value

        return config

    def _setup_cache(self, effective_config: dict) -> None:
        """Initialize data cache and monkey-patch route_to_vendor."""
        cache_dir = os.path.join(
            effective_config.get("data_cache_dir", "data_cache"),
            "backtest_cache",
        )
        self._cache = DataCache(cache_dir, enabled=self.config.use_data_cache)

        if self.config.use_data_cache:
            import tradingagents.dataflows.interface as interface_mod
            cached_fn = create_cached_route_to_vendor(self._cache)
            self._original_route = interface_mod.route_to_vendor
            interface_mod.route_to_vendor = cached_fn
            logger.info("Data cache installed (dir=%s)", self._cache.cache_dir)

    def _restore_cache(self) -> None:
        """Restore original route_to_vendor after backtest."""
        if hasattr(self, "_original_route"):
            import tradingagents.dataflows.interface as interface_mod
            interface_mod.route_to_vendor = self._original_route

    def _setup_graph(self, effective_config: dict) -> None:
        """Initialize the TradingAgentsGraph."""
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        profile = BACKTEST_PROFILES.get(
            self.config.backtest_profile, BACKTEST_PROFILES["standard"]
        )
        selected_analysts = profile.get(
            "selected_analysts", self.config.selected_analysts,
        )

        self._graph = TradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=False,
            config=effective_config,
        )

    def _setup_portfolio(self) -> None:
        """Initialize the MultiAssetPortfolio."""
        self._portfolio = MultiAssetPortfolio(
            initial_capital=self.config.initial_capital,
            commission_rate=self.config.commission_rate,
            slippage_rate=self.config.slippage_rate,
        )

    def _setup_optimizer(self) -> None:
        """Initialize the PortfolioOptimizer."""
        self._optimizer = PortfolioOptimizer(
            max_position=self.config.max_position_fraction,
            min_position=self.config.min_position_fraction,
        )

    def _setup_rebalancer(self) -> None:
        """Initialize the Rebalancer."""
        self._rebalancer = Rebalancer(
            threshold=self.config.rebalance_threshold,
            commission_rate=self.config.commission_rate,
        )

    # ------------------------------------------------------------------
    # Trading date generation
    # ------------------------------------------------------------------

    def _generate_trading_dates(self) -> List[str]:
        """Generate valid trading dates (skip weekends)."""
        start = datetime.strptime(self.config.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.config.end_date, "%Y-%m-%d")

        all_dates = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                all_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        freq = self.config.trading_frequency
        if freq == "weekly":
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
            filtered = []
            last_month = None
            for d_str in all_dates:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                if dt.month != last_month:
                    filtered.append(d_str)
                    last_month = dt.month
            return filtered

        return all_dates

    # ------------------------------------------------------------------
    # Price data
    # ------------------------------------------------------------------

    def _fetch_all_price_series(
        self, trading_dates: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """Fetch closing prices for all tickers over the trading period.

        Returns:
            Nested dict: ``{ticker: {date_str: price}}``.
        """
        import yfinance as yf

        result = {}
        start = trading_dates[0]
        end_dt = datetime.strptime(trading_dates[-1], "%Y-%m-%d") + timedelta(days=5)
        end = end_dt.strftime("%Y-%m-%d")

        for ticker in self.config.tickers:
            try:
                obj = yf.Ticker(ticker)
                hist = obj.history(start=start, end=end)

                if hist.empty:
                    logger.error("No price data for %s", ticker)
                    result[ticker] = {}
                    continue

                if hist.index.tz is not None:
                    hist.index = hist.index.tz_localize(None)

                prices = {}
                for date_str in trading_dates:
                    dt = pd.Timestamp(date_str)
                    if dt in hist.index:
                        prices[date_str] = float(hist.loc[dt, "Close"])
                    else:
                        idx = hist.index.get_indexer([dt], method="nearest")
                        if len(idx) > 0 and idx[0] >= 0:
                            prices[date_str] = float(hist.iloc[idx[0]]["Close"])

                result[ticker] = prices
                logger.info("Fetched %d/%d prices for %s",
                            len(prices), len(trading_dates), ticker)

            except Exception as e:
                logger.error("Failed to fetch prices for %s: %s", ticker, e)
                result[ticker] = {}

        return result

    def _get_prices_for_date(
        self,
        price_data: Dict[str, Dict[str, float]],
        date_str: str,
    ) -> Dict[str, float]:
        """Extract prices for all tickers on a given date."""
        prices = {}
        for ticker in self.config.tickers:
            p = price_data.get(ticker, {}).get(date_str)
            if p is not None and p > 0:
                prices[ticker] = p
        return prices

    def _extract_price_series(
        self,
        price_data: Dict[str, Dict[str, float]],
        up_to_date: str,
    ) -> Dict[str, pd.Series]:
        """Build price Series per ticker up to the given date for optimizer."""
        result = {}
        for ticker, date_prices in price_data.items():
            dates = sorted(d for d in date_prices if d <= up_to_date)
            if len(dates) < 5:
                continue
            idx = pd.to_datetime(dates)
            vals = [date_prices[d] for d in dates]
            result[ticker] = pd.Series(vals, index=idx, name=ticker)
        return result

    # ------------------------------------------------------------------
    # Agent propagation
    # ------------------------------------------------------------------

    def _run_all_propagations(
        self, date_str: str,
    ) -> tuple:
        """Run graph.propagate() for each ticker sequentially.

        Returns:
            Tuple of (signals_dict, risk_metrics_dict).
        """
        signals: Dict[str, Union[TradeSignal, str]] = {}
        risk_metrics_map: Dict[str, RiskMetrics] = {}

        for ticker in self.config.tickers:
            try:
                state, signal = self._graph.propagate(ticker, date_str)
                signals[ticker] = signal

                rm = state.get("risk_metrics")
                if rm and isinstance(rm, dict) and rm.get("ticker"):
                    risk_metrics_map[ticker] = RiskMetrics(**rm)
                elif rm and isinstance(rm, RiskMetrics):
                    risk_metrics_map[ticker] = rm

            except Exception as e:
                logger.error(
                    "propagate() failed for %s on %s: %s — treating as HOLD",
                    ticker, date_str, e,
                )
                signals[ticker] = "HOLD"

        return signals, risk_metrics_map

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def _initial_buy(
        self,
        allocation: AllocationResult,
        prices: Dict[str, float],
        date_str: str,
        signals: Dict[str, Union[TradeSignal, str]],
    ) -> tuple:
        """Execute initial buys on the first trading day.

        Returns:
            Tuple of (trades_list, actions_dict).
        """
        trades = []
        actions = {}

        for ticker in self.config.tickers:
            weight = allocation.weights.get(ticker, 0.0)
            price = prices.get(ticker)

            if weight < 1e-6 or price is None or price <= 0:
                actions[ticker] = "HOLD"
                continue

            sig = signals.get(ticker)
            action = self._get_action(sig)

            if action == "SELL":
                actions[ticker] = "HOLD"
                continue

            tr = self._portfolio.execute_order(
                ticker=ticker,
                action="BUY",
                price=price,
                fraction=weight,
                date=date_str,
                signal=sig,
            )
            trades.append(tr)
            actions[ticker] = tr.action

        return trades, actions

    def _execute_rebalance(
        self,
        allocation: AllocationResult,
        prices: Dict[str, float],
        date_str: str,
    ) -> tuple:
        """Execute rebalancing orders.

        Returns:
            Tuple of (trades_list, actions_dict).
        """
        positions = self._portfolio.get_all_positions(prices)
        total_value = self._portfolio.get_total_value(prices)

        orders = self._rebalancer.generate_orders(
            positions=positions,
            target_weights=allocation.weights,
            prices=prices,
            cash=self._portfolio.cash,
            total_value=total_value,
        )

        trades = []
        actions = {t: "HOLD" for t in self.config.tickers}

        for order in orders:
            price = prices.get(order.ticker)
            if price is None or price <= 0:
                continue

            if order.action == "SELL":
                fraction = 1.0
            else:
                fraction = order.estimated_value / total_value if total_value > 0 else 0.0

            tr = self._portfolio.execute_order(
                ticker=order.ticker,
                action=order.action,
                price=price,
                fraction=fraction,
                date=date_str,
            )
            trades.append(tr)
            actions[order.ticker] = tr.action

            logger.info(
                "REBALANCE %s %s: %s",
                order.action, order.ticker, order.reason,
            )

        return trades, actions

    def _execute_signals(
        self,
        signals: Dict[str, Union[TradeSignal, str]],
        allocation: AllocationResult,
        prices: Dict[str, float],
        date_str: str,
    ) -> tuple:
        """Execute agent signals when no rebalancing is needed.

        Returns:
            Tuple of (trades_list, actions_dict).
        """
        trades = []
        actions = {}

        for ticker in self.config.tickers:
            sig = signals.get(ticker, "HOLD")
            action = self._get_action(sig)
            price = prices.get(ticker)

            if price is None or price <= 0:
                actions[ticker] = "HOLD"
                continue

            weight = allocation.weights.get(ticker, 0.0)
            fraction = weight if action == "BUY" else 0.0

            tr = self._portfolio.execute_order(
                ticker=ticker,
                action=action,
                price=price,
                fraction=fraction,
                date=date_str,
                signal=sig,
            )
            trades.append(tr)
            actions[ticker] = tr.action

        return trades, actions

    @staticmethod
    def _get_action(signal) -> str:
        """Extract action string from a TradeSignal or plain string."""
        if isinstance(signal, TradeSignal):
            return signal.action.upper()
        return str(signal).upper() if signal else "HOLD"

    # ------------------------------------------------------------------
    # Reflection
    # ------------------------------------------------------------------

    def _should_reflect(
        self, days_since_last: int, current_index: int, total_days: int,
    ) -> bool:
        """Determine if reflection should happen now."""
        mode = self.config.reflection_mode
        if mode == "none" or mode == "end_only":
            return False
        if mode == "periodic":
            return days_since_last >= self.config.reflection_interval
        return False

    def _do_reflection(self, snapshots: List[PortfolioSnapshot]) -> None:
        """Run graph.reflect_and_remember() with portfolio performance."""
        if not self._graph or not snapshots:
            return
        try:
            snap = snapshots[-1]
            reflection_data = (
                f"Portfolio value: ${snap.total_value:,.2f} | "
                f"Cumulative return: {snap.cumulative_return * 100:+.2f}% | "
                f"Days traded: {len(snapshots)} | "
                f"Tickers: {', '.join(self.config.tickers)}"
            )
            self._graph.reflect_and_remember(reflection_data)
            logger.info("Reflection completed (return: %.2f%%)", snap.cumulative_return * 100)
        except Exception as e:
            logger.warning("Reflection failed: %s", e)

    # ------------------------------------------------------------------
    # Performance calculation
    # ------------------------------------------------------------------

    def _calculate_performance(
        self,
        snapshots: List[PortfolioSnapshot],
        all_trades: List[dict],
    ) -> Dict[str, float]:
        """Calculate portfolio-level performance metrics."""
        if not snapshots:
            return {}

        final_value = snapshots[-1].total_value
        total_return = (final_value - self.config.initial_capital) / self.config.initial_capital

        daily_returns = pd.Series([s.daily_return for s in snapshots])
        trading_days = len(snapshots)

        annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1

        from tradingagents.risk.metrics import (
            calculate_sharpe_ratio,
            calculate_sortino_ratio,
            calculate_max_drawdown,
        )

        try:
            sharpe = calculate_sharpe_ratio(daily_returns, 0.05)
        except ValueError:
            sharpe = 0.0
        try:
            sortino = calculate_sortino_ratio(daily_returns, 0.05)
        except ValueError:
            sortino = 0.0

        values = pd.Series([s.total_value for s in snapshots])
        try:
            max_dd, _ = calculate_max_drawdown(values)
        except ValueError:
            max_dd = 0.0

        actual_trades = [t for t in all_trades if t.get("action") in ("BUY", "SELL")]
        total_commission = sum(t.get("commission", 0) for t in actual_trades)

        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "total_trades": len(actual_trades),
            "total_commission": total_commission,
            "final_value": final_value,
            "trading_days": trading_days,
        }

    def _calculate_per_ticker_performance(
        self,
        all_trades: List[dict],
        price_data: Dict[str, Dict[str, float]],
        trading_dates: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """Calculate performance metrics per ticker."""
        result = {}
        for ticker in self.config.tickers:
            ticker_trades = [t for t in all_trades if t.get("ticker") == ticker]
            buys = [t for t in ticker_trades if t.get("action") == "BUY"]
            sells = [t for t in ticker_trades if t.get("action") == "SELL"]
            commission = sum(t.get("commission", 0) for t in ticker_trades)

            prices = price_data.get(ticker, {})
            if trading_dates and prices:
                first_price = prices.get(trading_dates[0], 0)
                last_price = prices.get(trading_dates[-1], 0)
                buy_hold = (
                    (last_price - first_price) / first_price
                    if first_price > 0
                    else 0.0
                )
            else:
                buy_hold = 0.0

            result[ticker] = {
                "total_trades": len(buys) + len(sells),
                "buy_orders": len(buys),
                "sell_orders": len(sells),
                "total_commission": commission,
                "buy_and_hold_return": buy_hold,
            }
        return result

    def _build_empty_result(self) -> PortfolioResult:
        """Build an empty result for edge cases."""
        return PortfolioResult(
            config=self.config,
            snapshots=[],
            all_trades=[],
            performance={},
            per_ticker_performance={},
            total_trading_days=0,
            total_trades=0,
        )
