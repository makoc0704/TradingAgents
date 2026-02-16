"""Portfolio tracking and paper trade execution for backtesting."""

import logging
from typing import Optional, Union

from tradingagents.risk.models import TradeSignal
from .models import TradeRecord, DailySnapshot

logger = logging.getLogger(__name__)


class Portfolio:
    """Tracks cash, positions, and executes paper trades.

    Supports a single position per ticker (long only).
    Commission and slippage are applied on every buy/sell execution.

    Args:
        initial_capital: Starting cash amount in USD.
        commission_rate: Commission as fraction of trade value (e.g. 0.001).
        slippage_rate: Slippage as fraction of price (e.g. 0.0005).
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

        # Position state
        self.shares: int = 0
        self.ticker: Optional[str] = None
        self.avg_entry_price: float = 0.0

        # Tracking
        self._prev_portfolio_value: float = initial_capital

    def get_value(self, current_price: float) -> float:
        """Calculate total portfolio value at a given price.

        Args:
            current_price: Current market price of the held asset.

        Returns:
            Total portfolio value (cash + position value).
        """
        return self.cash + self.shares * current_price

    def execute_signal(
        self,
        signal: Union[TradeSignal, str],
        ticker: str,
        price: float,
        date: str,
    ) -> TradeRecord:
        """Execute a trade signal and return the resulting TradeRecord.

        Dispatches to execute_buy, execute_sell, or hold based on the signal.

        Args:
            signal: TradeSignal object or plain action string (BUY/SELL/HOLD).
            ticker: Stock ticker symbol.
            price: Current market price before slippage.
            date: Trade date in YYYY-MM-DD format.

        Returns:
            TradeRecord documenting the executed action.
        """
        if isinstance(signal, TradeSignal):
            action = signal.action.upper()
            fraction = (
                signal.position_size.fraction
                if signal.position_size is not None
                else 0.10
            )
        else:
            action = str(signal).upper()
            fraction = 0.10

        if action == "BUY":
            return self.execute_buy(ticker, price, fraction, date, signal)
        elif action == "SELL":
            return self.execute_sell(ticker, price, date, signal)
        else:
            return self.hold(ticker, price, date, signal)

    def execute_buy(
        self,
        ticker: str,
        price: float,
        fraction: float,
        date: str,
        signal: Optional[TradeSignal] = None,
    ) -> TradeRecord:
        """Execute a buy order.

        Buys whole shares using the specified fraction of portfolio value.
        Applies slippage (price goes up) and commission.

        Args:
            ticker: Stock ticker.
            price: Market price before slippage.
            fraction: Fraction of portfolio value to allocate (0.0-1.0).
            date: Trade date.
            signal: Optional full TradeSignal for record keeping.

        Returns:
            TradeRecord for this buy execution.
        """
        # Apply slippage — buying pushes price up
        exec_price = price * (1 + self.slippage_rate)

        # Calculate how much to invest
        portfolio_value = self.get_value(price)
        invest_amount = portfolio_value * fraction

        # Limit to available cash
        invest_amount = min(invest_amount, self.cash)

        # Calculate whole shares
        if exec_price <= 0:
            return self.hold(ticker, price, date, signal)

        shares_to_buy = int(invest_amount / exec_price)

        if shares_to_buy <= 0:
            logger.info("Insufficient funds for BUY on %s — treating as HOLD", date)
            return self.hold(ticker, price, date, signal)

        # Calculate costs
        trade_value = shares_to_buy * exec_price
        commission = trade_value * self.commission_rate

        # Check if we can afford trade + commission
        total_cost = trade_value + commission
        if total_cost > self.cash:
            shares_to_buy = int((self.cash / (1 + self.commission_rate)) / exec_price)
            if shares_to_buy <= 0:
                logger.info("Cannot afford commission for BUY on %s — HOLD", date)
                return self.hold(ticker, price, date, signal)
            trade_value = shares_to_buy * exec_price
            commission = trade_value * self.commission_rate
            total_cost = trade_value + commission

        # Execute
        self.cash -= total_cost
        self.shares += shares_to_buy
        self.ticker = ticker

        # Update average entry price
        total_shares = self.shares
        self.avg_entry_price = (
            (self.avg_entry_price * (total_shares - shares_to_buy)
             + exec_price * shares_to_buy)
            / total_shares
            if total_shares > 0
            else exec_price
        )

        current_value = self.get_value(price)
        logger.info(
            "BUY %d shares of %s @ $%.2f (slipped: $%.2f) on %s | Commission: $%.2f | Portfolio: $%.2f",
            shares_to_buy, ticker, price, exec_price, date, commission, current_value,
        )

        return TradeRecord(
            date=date,
            ticker=ticker,
            action="BUY",
            signal=signal,
            price=exec_price,
            shares=shares_to_buy,
            commission=commission,
            portfolio_value=current_value,
            cash=self.cash,
            position_value=self.shares * price,
        )

    def execute_sell(
        self,
        ticker: str,
        price: float,
        date: str,
        signal: Optional[TradeSignal] = None,
    ) -> TradeRecord:
        """Execute a sell order — sells entire position.

        Applies slippage (price goes down) and commission.

        Args:
            ticker: Stock ticker.
            price: Market price before slippage.
            date: Trade date.
            signal: Optional full TradeSignal for record keeping.

        Returns:
            TradeRecord for this sell execution.
        """
        if self.shares <= 0:
            logger.info("No position to SELL on %s — treating as HOLD", date)
            return self.hold(ticker, price, date, signal)

        # Apply slippage — selling pushes price down
        exec_price = price * (1 - self.slippage_rate)
        shares_to_sell = self.shares

        # Calculate proceeds
        trade_value = shares_to_sell * exec_price
        commission = trade_value * self.commission_rate
        net_proceeds = trade_value - commission

        # Execute
        self.cash += net_proceeds
        self.shares = 0
        self.avg_entry_price = 0.0

        current_value = self.get_value(price)
        logger.info(
            "SELL %d shares of %s @ $%.2f (slipped: $%.2f) on %s | Commission: $%.2f | Portfolio: $%.2f",
            shares_to_sell, ticker, price, exec_price, date, commission, current_value,
        )

        return TradeRecord(
            date=date,
            ticker=ticker,
            action="SELL",
            signal=signal,
            price=exec_price,
            shares=shares_to_sell,
            commission=commission,
            portfolio_value=current_value,
            cash=self.cash,
            position_value=0.0,
        )

    def hold(
        self,
        ticker: str,
        price: float,
        date: str,
        signal: Optional[TradeSignal] = None,
    ) -> TradeRecord:
        """Record a hold (no-op) for audit trail.

        Args:
            ticker: Stock ticker.
            price: Current market price.
            date: Trade date.
            signal: Optional full TradeSignal for record keeping.

        Returns:
            TradeRecord with zero shares/commission.
        """
        current_value = self.get_value(price)
        return TradeRecord(
            date=date,
            ticker=ticker,
            action="HOLD",
            signal=signal,
            price=price,
            shares=0,
            commission=0.0,
            portfolio_value=current_value,
            cash=self.cash,
            position_value=self.shares * price,
        )

    def get_daily_snapshot(
        self,
        date: str,
        price: float,
        action: str,
        risk_metrics: Optional[dict] = None,
    ) -> DailySnapshot:
        """Create a snapshot of the portfolio at end of day.

        Args:
            date: Snapshot date.
            price: Closing price for the day.
            action: Action taken on this day.
            risk_metrics: Optional risk metrics dict.

        Returns:
            DailySnapshot for this day.
        """
        current_value = self.get_value(price)
        position_value = self.shares * price

        daily_return = (
            (current_value - self._prev_portfolio_value) / self._prev_portfolio_value
            if self._prev_portfolio_value > 0
            else 0.0
        )
        cumulative_return = (
            (current_value - self.initial_capital) / self.initial_capital
            if self.initial_capital > 0
            else 0.0
        )

        self._prev_portfolio_value = current_value

        return DailySnapshot(
            date=date,
            portfolio_value=current_value,
            cash=self.cash,
            position_shares=self.shares,
            position_value=position_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            action=action,
            risk_metrics=risk_metrics,
        )
