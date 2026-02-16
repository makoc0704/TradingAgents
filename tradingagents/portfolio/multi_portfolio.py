"""Multi-asset portfolio tracking and paper trade execution.

Extends the single-ticker concept from ``backtesting.portfolio`` to support
simultaneous positions in multiple tickers with a shared cash pool.
"""

import logging
from typing import Dict, List, Optional, Union

from tradingagents.risk.models import TradeSignal
from tradingagents.backtesting.models import TradeRecord

from .models import Position, AllocationResult, PortfolioSnapshot

logger = logging.getLogger(__name__)


class MultiAssetPortfolio:
    """Tracks cash and multiple positions for paper trading.

    Long-only, whole shares, shared cash pool across all tickers.
    Commission and slippage are applied on every buy/sell execution.

    Args:
        initial_capital: Starting cash amount in USD.
        commission_rate: Commission as fraction of trade value.
        slippage_rate: Slippage as fraction of price.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        self._positions: Dict[str, _PositionState] = {}
        self._prev_total_value: float = initial_capital

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute_order(
        self,
        ticker: str,
        action: str,
        price: float,
        fraction: float,
        date: str,
        signal: Optional[Union[TradeSignal, str]] = None,
    ) -> TradeRecord:
        """Execute an order for a single ticker.

        Args:
            ticker: Stock ticker symbol.
            action: "BUY", "SELL", or "HOLD".
            price: Market price before slippage.
            fraction: Fraction of total portfolio value to allocate
                (used for BUY only).
            date: Trade date in YYYY-MM-DD format.
            signal: Optional TradeSignal or string for record keeping.

        Returns:
            TradeRecord documenting the executed action.
        """
        action = action.upper()
        if action == "BUY":
            return self._execute_buy(ticker, price, fraction, date, signal)
        elif action == "SELL":
            return self._execute_sell(ticker, price, date, signal)
        else:
            return self._hold(ticker, price, date, signal)

    def get_position(self, ticker: str) -> Optional[Position]:
        """Get the current position for a ticker, or None if no position.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Position dataclass or None.
        """
        state = self._positions.get(ticker)
        if state is None or state.shares <= 0:
            return None
        total_val = self.get_total_value({ticker: state.current_price})
        actual_weight = (
            (state.shares * state.current_price) / total_val
            if total_val > 0
            else 0.0
        )
        return Position(
            ticker=ticker,
            shares=state.shares,
            avg_entry_price=state.avg_entry_price,
            current_price=state.current_price,
            target_weight=state.target_weight,
            actual_weight=actual_weight,
        )

    def get_all_positions(
        self,
        prices: Dict[str, float],
    ) -> Dict[str, Position]:
        """Get all non-empty positions with current prices.

        Args:
            prices: Current market prices per ticker.

        Returns:
            Dict mapping ticker to Position for every held ticker.
        """
        self._update_prices(prices)
        total_val = self.get_total_value(prices)
        result = {}
        for ticker, state in self._positions.items():
            if state.shares <= 0:
                continue
            actual_weight = (
                (state.shares * state.current_price) / total_val
                if total_val > 0
                else 0.0
            )
            result[ticker] = Position(
                ticker=ticker,
                shares=state.shares,
                avg_entry_price=state.avg_entry_price,
                current_price=state.current_price,
                target_weight=state.target_weight,
                actual_weight=actual_weight,
            )
        return result

    def get_total_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (cash + all positions).

        Args:
            prices: Current market prices per ticker.

        Returns:
            Total portfolio value in USD.
        """
        self._update_prices(prices)
        position_value = sum(
            s.shares * s.current_price for s in self._positions.values()
        )
        return self.cash + position_value

    def set_target_weights(self, weights: Dict[str, float]) -> None:
        """Update target weights from an allocation result.

        Creates empty position states for new tickers.

        Args:
            weights: Target weight per ticker.
        """
        for ticker, weight in weights.items():
            if ticker not in self._positions:
                self._positions[ticker] = _PositionState(ticker=ticker)
            self._positions[ticker].target_weight = weight

    def get_snapshot(
        self,
        date: str,
        prices: Dict[str, float],
        actions: Dict[str, str],
        allocation: Optional[AllocationResult] = None,
    ) -> PortfolioSnapshot:
        """Create a snapshot of the portfolio at end of day.

        Args:
            date: Snapshot date.
            prices: Closing prices per ticker.
            actions: Actions taken per ticker on this day.
            allocation: Allocation result from optimizer.

        Returns:
            PortfolioSnapshot for this day.
        """
        self._update_prices(prices)
        total_value = self.get_total_value(prices)
        positions = self.get_all_positions(prices)

        daily_return = (
            (total_value - self._prev_total_value) / self._prev_total_value
            if self._prev_total_value > 0
            else 0.0
        )
        cumulative_return = (
            (total_value - self.initial_capital) / self.initial_capital
            if self.initial_capital > 0
            else 0.0
        )

        self._prev_total_value = total_value

        return PortfolioSnapshot(
            date=date,
            total_value=total_value,
            cash=self.cash,
            positions=positions,
            allocation=allocation,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            actions=actions,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _update_prices(self, prices: Dict[str, float]) -> None:
        """Update current_price on all tracked positions."""
        for ticker, price in prices.items():
            if ticker in self._positions:
                self._positions[ticker].current_price = price

    def _execute_buy(
        self,
        ticker: str,
        price: float,
        fraction: float,
        date: str,
        signal=None,
    ) -> TradeRecord:
        """Buy shares of a single ticker."""
        exec_price = price * (1 + self.slippage_rate)

        total_value = self.cash + sum(
            s.shares * s.current_price for s in self._positions.values()
        )
        invest_amount = total_value * fraction
        invest_amount = min(invest_amount, self.cash)

        if exec_price <= 0:
            return self._hold(ticker, price, date, signal)

        shares_to_buy = int(invest_amount / exec_price)
        if shares_to_buy <= 0:
            logger.info("Insufficient funds for BUY %s on %s", ticker, date)
            return self._hold(ticker, price, date, signal)

        trade_value = shares_to_buy * exec_price
        commission = trade_value * self.commission_rate
        total_cost = trade_value + commission

        if total_cost > self.cash:
            shares_to_buy = int(
                (self.cash / (1 + self.commission_rate)) / exec_price
            )
            if shares_to_buy <= 0:
                logger.info("Cannot afford commission for BUY %s on %s", ticker, date)
                return self._hold(ticker, price, date, signal)
            trade_value = shares_to_buy * exec_price
            commission = trade_value * self.commission_rate
            total_cost = trade_value + commission

        self.cash -= total_cost

        if ticker not in self._positions:
            self._positions[ticker] = _PositionState(ticker=ticker)
        state = self._positions[ticker]

        old_shares = state.shares
        state.shares += shares_to_buy
        state.current_price = price
        state.avg_entry_price = (
            (state.avg_entry_price * old_shares + exec_price * shares_to_buy)
            / state.shares
            if state.shares > 0
            else exec_price
        )

        portfolio_value = self.cash + sum(
            s.shares * s.current_price for s in self._positions.values()
        )

        logger.info(
            "BUY %d shares of %s @ $%.2f (slipped: $%.2f) on %s | "
            "Commission: $%.2f | Portfolio: $%.2f",
            shares_to_buy, ticker, price, exec_price, date,
            commission, portfolio_value,
        )

        return TradeRecord(
            date=date,
            ticker=ticker,
            action="BUY",
            signal=signal,
            price=exec_price,
            shares=shares_to_buy,
            commission=commission,
            portfolio_value=portfolio_value,
            cash=self.cash,
            position_value=state.shares * price,
        )

    def _execute_sell(
        self,
        ticker: str,
        price: float,
        date: str,
        signal=None,
    ) -> TradeRecord:
        """Sell entire position of a single ticker."""
        state = self._positions.get(ticker)
        if state is None or state.shares <= 0:
            logger.info("No position to SELL %s on %s", ticker, date)
            return self._hold(ticker, price, date, signal)

        exec_price = price * (1 - self.slippage_rate)
        shares_to_sell = state.shares

        trade_value = shares_to_sell * exec_price
        commission = trade_value * self.commission_rate
        net_proceeds = trade_value - commission

        self.cash += net_proceeds
        state.shares = 0
        state.avg_entry_price = 0.0
        state.current_price = price

        portfolio_value = self.cash + sum(
            s.shares * s.current_price for s in self._positions.values()
        )

        logger.info(
            "SELL %d shares of %s @ $%.2f (slipped: $%.2f) on %s | "
            "Commission: $%.2f | Portfolio: $%.2f",
            shares_to_sell, ticker, price, exec_price, date,
            commission, portfolio_value,
        )

        return TradeRecord(
            date=date,
            ticker=ticker,
            action="SELL",
            signal=signal,
            price=exec_price,
            shares=shares_to_sell,
            commission=commission,
            portfolio_value=portfolio_value,
            cash=self.cash,
            position_value=0.0,
        )

    def _hold(
        self,
        ticker: str,
        price: float,
        date: str,
        signal=None,
    ) -> TradeRecord:
        """Record a hold for audit trail."""
        if ticker in self._positions:
            self._positions[ticker].current_price = price

        position_value = 0.0
        state = self._positions.get(ticker)
        if state and state.shares > 0:
            position_value = state.shares * price

        portfolio_value = self.cash + sum(
            s.shares * s.current_price for s in self._positions.values()
        )

        return TradeRecord(
            date=date,
            ticker=ticker,
            action="HOLD",
            signal=signal,
            price=price,
            shares=0,
            commission=0.0,
            portfolio_value=portfolio_value,
            cash=self.cash,
            position_value=position_value,
        )


class _PositionState:
    """Internal mutable state for a single position.

    Not exposed publicly — ``get_position()`` returns an immutable
    ``Position`` dataclass instead.
    """

    __slots__ = (
        "ticker", "shares", "avg_entry_price", "current_price", "target_weight",
    )

    def __init__(
        self,
        ticker: str = "",
        shares: int = 0,
        avg_entry_price: float = 0.0,
        current_price: float = 0.0,
        target_weight: float = 0.0,
    ):
        self.ticker = ticker
        self.shares = shares
        self.avg_entry_price = avg_entry_price
        self.current_price = current_price
        self.target_weight = target_weight
