"""LiveRunner — orchestrates live trading execution with current market data."""

import logging
from typing import Dict, Optional

from tradingagents.backtesting.models import BACKTEST_PROFILES
from tradingagents.dataflows.utils import get_current_date
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.risk.models import TradeSignal

from .models import LiveConfig, LiveRunResult, PortfolioSnapshot
from .state import LivePortfolioState
from .broker import BrokerInterface, DummyBroker
from .performance import calculate_live_performance

logger = logging.getLogger(__name__)


class LiveRunner:
    """Orchestrates live trading execution.
    
    Runs TradingAgentsGraph.propagate() with current date and executes
    signals via a broker interface (currently DummyBroker for paper trading).
    
    Args:
        config: LiveConfig with tickers, mode, broker settings, etc.
    """
    
    def __init__(self, config: LiveConfig):
        self.config = config
        self._graph = None
        self._broker: Optional[BrokerInterface] = None
        self._state: Optional[LivePortfolioState] = None
        self._prev_portfolio_value: Optional[float] = None
    
    def run(self) -> LiveRunResult:
        """Execute a live trading run.
        
        For each ticker:
        1. Run graph.propagate(ticker, today) → TradeSignal
        2. Fetch current price
        3. Execute signal via broker (if mode == "paper")
        4. Record snapshot
        
        Returns:
            LiveRunResult with signals, executed orders, and performance snapshot.
        """
        if not self.config.tickers:
            raise ValueError("LiveConfig.tickers is empty — nothing to trade")

        valid_tickers = [t for t in self.config.tickers if t and t.strip()]
        if len(valid_tickers) != len(self.config.tickers):
            logger.warning(
                "Removed %d invalid/empty ticker(s) from config",
                len(self.config.tickers) - len(valid_tickers),
            )
            self.config.tickers = valid_tickers

        logger.info(
            "Starting live trading run: %d tickers, mode=%s, broker=%s",
            len(self.config.tickers),
            self.config.mode,
            self.config.broker_type,
        )
        
        today = get_current_date()
        logger.info("Trading date: %s", today)
        
        # Build effective config
        effective_config = self._build_effective_config()
        
        # Initialize graph (lazy import to avoid circular deps)
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        profile = BACKTEST_PROFILES.get(
            self.config.backtest_profile,
            BACKTEST_PROFILES["standard"],
        )
        selected_analysts = profile.get(
            "selected_analysts", self.config.selected_analysts
        )

        self._graph = TradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=False,
            config=effective_config,
        )
        
        # Initialize state and broker
        self._state = LivePortfolioState(
            state_path=self.config.state_path,
            initial_capital=self.config.initial_capital,
        )
        
        self._broker = self._create_broker()
        
        # Load previous portfolio value for daily return calculation
        initial_capital = self._state.get_initial_capital()
        current_portfolio_value = self._broker.get_portfolio_value()
        
        # Fetch current prices for all tickers (needed for portfolio value calculation)
        prices = self._fetch_current_prices()
        
        # Recalculate portfolio value with current prices
        current_portfolio_value = self._calculate_portfolio_value(prices)
        
        # Get previous value from state or use initial capital
        prev_value = self._get_previous_portfolio_value(initial_capital)
        
        # Run propagation and execution for each ticker
        signals: Dict[str, TradeSignal] = {}
        executed_orders = []
        
        for ticker in self.config.tickers:
            logger.info("Processing ticker: %s", ticker)
            
            # Run graph propagation
            signal, current_price = self._run_propagation(ticker, today, prices)
            signals[ticker] = signal
            
            # Execute signal if in paper mode
            if self.config.mode == "paper":
                order_result = self._broker.place_order(
                    ticker=ticker,
                    signal=signal,
                    current_price=current_price,
                    date=today,
                )
                executed_orders.append(order_result)
                logger.info(
                    "Order executed: %s %s %s",
                    order_result.action,
                    order_result.shares,
                    ticker,
                )
            elif self.config.mode == "dry_run":
                logger.info(
                    "DRY RUN: Signal for %s = %s (not executed)",
                    ticker,
                    signal.action,
                )
        
        # Recalculate portfolio value after execution
        prices_after = self._fetch_current_prices()
        final_portfolio_value = self._calculate_portfolio_value(prices_after)
        
        # Calculate returns
        daily_return = (
            (final_portfolio_value - prev_value) / prev_value
            if prev_value > 0
            else 0.0
        )
        cumulative_return = (
            (final_portfolio_value - initial_capital) / initial_capital
            if initial_capital > 0
            else 0.0
        )
        
        # Create portfolio snapshot
        positions_dict = {}
        for pos in self._broker.get_positions():
            positions_dict[pos.ticker] = {
                "shares": pos.shares,
                "avg_entry_price": pos.avg_entry_price,
                "current_price": prices_after.get(pos.ticker, pos.avg_entry_price),
            }
        
        snapshot = PortfolioSnapshot(
            date=today,
            cash=self._broker.get_cash(),
            positions=positions_dict,
            total_value=final_portfolio_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
        )
        
        # Store lightweight snapshot in state for aggregate performance
        self._state.append_run_snapshot({
            "date": today,
            "total_value": final_portfolio_value,
            "cash": self._broker.get_cash(),
            "positions": positions_dict,
            "orders": [
                {"action": o.action, "shares": o.shares, "commission": o.commission}
                for o in executed_orders
                if hasattr(o, "action")
            ],
        })

        # Aggregate performance from full run history
        performance_metrics = self._calculate_aggregate_performance(
            initial_capital, daily_return, cumulative_return, final_portfolio_value,
        )
        
        result = LiveRunResult(
            date=today,
            signals=signals,
            executed_orders=executed_orders,
            portfolio_snapshot=snapshot,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            performance_metrics=performance_metrics,
        )
        
        # Persist portfolio value for next run's daily-return calculation
        self._state.set_last_portfolio_value(final_portfolio_value)

        logger.info(
            "Live trading run complete: Portfolio value = $%.2f (%.2f%% return)",
            final_portfolio_value,
            cumulative_return * 100,
        )
        
        return result
    
    def _build_effective_config(self) -> dict:
        """Merge LiveConfig with DEFAULT_CONFIG and apply profile overrides.

        Mirrors BacktestRunner._build_effective_config() so that
        backtest_profile settings (debate rounds, etc.) take effect.
        """
        config = DEFAULT_CONFIG.copy()
        config.update(self.config.config)

        profile = BACKTEST_PROFILES.get(self.config.backtest_profile, {})
        for key, value in profile.items():
            if key != "selected_analysts":
                config[key] = value

        return config
    
    def _create_broker(self) -> BrokerInterface:
        """Create broker instance based on config."""
        if self.config.broker_type == "dummy":
            return DummyBroker(
                state=self._state,
                commission_rate=self.config.commission_rate,
                slippage_rate=self.config.slippage_rate,
            )
        else:
            raise ValueError(f"Unknown broker type: {self.config.broker_type}")
    
    def _run_propagation(
        self,
        ticker: str,
        date: str,
        prices: Dict[str, float],
    ) -> tuple:
        """Run graph.propagate() and handle failures gracefully.
        
        Returns:
            Tuple of (signal, current_price). On failure, returns (HOLD signal, 0.0).
        """
        try:
            state, signal = self._graph.propagate(ticker, date)
            
            # Extract current price from risk metrics or use fetched price
            current_price = prices.get(ticker, 0.0)
            if current_price == 0.0:
                risk_metrics = state.get("risk_metrics")
                if risk_metrics and isinstance(risk_metrics, dict):
                    current_price = risk_metrics.get("current_price", 0.0)
            
            return signal, current_price
            
        except Exception as e:
            logger.error(
                "propagate() failed for %s on %s: %s — treating as HOLD",
                ticker,
                date,
                e,
            )
            # Create a HOLD signal
            hold_signal = TradeSignal(
                action="HOLD",
                confidence=0.0,
                position_size=None,
                risk_metrics=None,
                reasoning=f"Error during propagation: {e}",
            )
            return hold_signal, prices.get(ticker, 0.0)
    
    def _fetch_current_prices(self) -> Dict[str, float]:
        """Fetch current market prices for all tickers via yfinance.

        Falls back to broker's last known price if yfinance fails.
        Never calls propagate() — that would re-run the full LLM graph.
        """
        prices: Dict[str, float] = {}

        try:
            import yfinance as yf
            tickers_str = " ".join(self.config.tickers)
            data = yf.download(tickers_str, period="1d", progress=False)
            if data is not None and not data.empty:
                close = data["Close"]
                for ticker in self.config.tickers:
                    try:
                        val = close[ticker].iloc[-1] if len(self.config.tickers) > 1 else close.iloc[-1]
                        prices[ticker] = float(val) if val == val else 0.0  # NaN check
                    except (KeyError, IndexError):
                        prices[ticker] = 0.0
        except Exception as e:
            logger.warning("yfinance batch download failed: %s", e)

        for ticker in self.config.tickers:
            if prices.get(ticker, 0.0) <= 0.0 and self._broker:
                prices[ticker] = self._broker.get_last_price(ticker)
            prices.setdefault(ticker, 0.0)

        return prices
    
    def _calculate_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value using current prices."""
        cash = self._broker.get_cash()
        positions = self._broker.get_positions()
        total_value = cash
        
        for pos in positions:
            price = prices.get(pos.ticker, pos.avg_entry_price)
            if price > 0:
                total_value += pos.shares * price
            elif pos.avg_entry_price > 0:
                total_value += pos.shares * pos.avg_entry_price
        
        return total_value
    
    def _get_previous_portfolio_value(self, initial_capital: float) -> float:
        """Get portfolio value stored at end of last run.

        Falls back to initial_capital on the very first run.
        """
        if self._state:
            return self._state.get_last_portfolio_value()
        return initial_capital

    def _calculate_aggregate_performance(
        self,
        initial_capital: float,
        daily_return: float,
        cumulative_return: float,
        portfolio_value: float,
    ) -> Dict[str, float]:
        """Build performance metrics from full run history stored in state.

        On the first run the result is minimal; after several runs the
        aggregate Sharpe / drawdown / win-rate numbers become meaningful.
        """
        run_history_dicts = self._state.get_run_history() if self._state else []

        if len(run_history_dicts) < 2:
            return {
                "daily_return": daily_return,
                "cumulative_return": cumulative_return,
                "portfolio_value": portfolio_value,
            }

        try:
            from .models import LiveRunResult, PortfolioSnapshot
            from .broker.interface import OrderResult

            run_results = []
            for snap in run_history_dicts:
                orders = [
                    OrderResult(
                        success=True,
                        order_id="",
                        ticker="",
                        action=o.get("action", "HOLD"),
                        shares=o.get("shares", 0),
                        execution_price=0.0,
                        commission=o.get("commission", 0.0),
                        message="",
                        timestamp="",
                    )
                    for o in snap.get("orders", [])
                ]
                run_results.append(LiveRunResult(
                    date=snap["date"],
                    signals={},
                    executed_orders=orders,
                    portfolio_snapshot=PortfolioSnapshot(
                        date=snap["date"],
                        cash=snap.get("cash", 0.0),
                        positions=snap.get("positions", {}),
                        total_value=snap["total_value"],
                        daily_return=0.0,
                        cumulative_return=0.0,
                    ),
                    daily_return=0.0,
                    cumulative_return=0.0,
                    performance_metrics={},
                ))

            return calculate_live_performance(run_results, initial_capital)
        except Exception as e:
            logger.warning("Aggregate performance calculation failed: %s", e)
            return {
                "daily_return": daily_return,
                "cumulative_return": cumulative_return,
                "portfolio_value": portfolio_value,
            }
