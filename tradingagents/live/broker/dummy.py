"""Dummy broker implementation for paper trading.

This broker simulates trading with persistent state. It uses the same
execution logic as backtesting/portfolio.py but persists state to disk.
"""

import logging
from typing import List
from datetime import datetime

from tradingagents.risk.models import TradeSignal
from .interface import BrokerInterface, Position, OrderResult
from ..state import LivePortfolioState

logger = logging.getLogger(__name__)


class DummyBroker(BrokerInterface):
    """Paper trading broker with persistent state.
    
    Implements BrokerInterface using the same execution logic as
    backtesting/portfolio.py, but with persistent state management.
    This allows "live paper trading" where positions persist across runs.
    
    Args:
        state: LivePortfolioState instance for persistence.
        commission_rate: Commission as fraction of trade value.
        slippage_rate: Slippage as fraction of price.
    """
    
    def __init__(
        self,
        state: LivePortfolioState,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.state = state
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
    
    def place_order(
        self,
        ticker: str,
        signal: TradeSignal,
        current_price: float,
        date: str,
    ) -> OrderResult:
        """Execute a trade signal and persist the result.
        
        Uses the same logic as backtesting/portfolio.py but updates
        persistent state instead of in-memory only.
        """
        action = signal.action.upper()
        fraction = (
            signal.position_size.fraction
            if signal.position_size is not None
            else 0.10
        )
        
        if action == "BUY":
            result = self._execute_buy(ticker, current_price, fraction, date, signal)
        elif action == "SELL":
            result = self._execute_sell(ticker, current_price, date, signal)
        else:
            result = self._execute_hold(ticker, current_price, date, signal)

        if not result.success and result.action == "HOLD":
            self.state.record_trade(
                date, ticker, "HOLD", current_price, 0,
                0.0,
            )

        return result
    
    def _execute_buy(
        self,
        ticker: str,
        price: float,
        fraction: float,
        date: str,
        signal: TradeSignal,
    ) -> OrderResult:
        """Execute a buy order with slippage and commission."""
        # Apply slippage (buying pushes price up)
        exec_price = price * (1 + self.slippage_rate)
        
        # Calculate how much to invest
        portfolio_value = self.get_portfolio_value()
        invest_amount = portfolio_value * fraction
        
        # Limit to available cash
        cash = self.get_cash()
        invest_amount = min(invest_amount, cash)
        
        if exec_price <= 0:
            return OrderResult(
                success=False,
                order_id=f"hold-{date}-{ticker}",
                ticker=ticker,
                action="HOLD",
                shares=0,
                execution_price=price,
                commission=0.0,
                message="Invalid price",
                timestamp=datetime.now().isoformat(),
            )
        
        shares_to_buy = int(invest_amount / exec_price)
        
        if shares_to_buy <= 0:
            return OrderResult(
                success=False,
                order_id=f"hold-{date}-{ticker}",
                ticker=ticker,
                action="HOLD",
                shares=0,
                execution_price=price,
                commission=0.0,
                message="Insufficient funds",
                timestamp=datetime.now().isoformat(),
            )
        
        # Calculate costs
        trade_value = shares_to_buy * exec_price
        commission = trade_value * self.commission_rate
        total_cost = trade_value + commission
        
        # Check if we can afford trade + commission
        if total_cost > cash:
            shares_to_buy = int((cash / (1 + self.commission_rate)) / exec_price)
            if shares_to_buy <= 0:
                return OrderResult(
                    success=False,
                    order_id=f"hold-{date}-{ticker}",
                    ticker=ticker,
                    action="HOLD",
                    shares=0,
                    execution_price=price,
                    commission=0.0,
                    message="Cannot afford commission",
                    timestamp=datetime.now().isoformat(),
                )
            trade_value = shares_to_buy * exec_price
            commission = trade_value * self.commission_rate
            total_cost = trade_value + commission
        
        # Update persistent state
        self.state.add_position(ticker, shares_to_buy, exec_price)
        self.state.subtract_cash(total_cost)
        self.state.record_trade(date, ticker, "BUY", exec_price, shares_to_buy, commission)
        
        logger.info(
            "BUY %d shares of %s @ $%.2f (slipped: $%.2f) on %s | Commission: $%.2f",
            shares_to_buy, ticker, price, exec_price, date, commission,
        )
        
        return OrderResult(
            success=True,
            order_id=f"buy-{date}-{ticker}-{int(datetime.now().timestamp())}",
            ticker=ticker,
            action="BUY",
            shares=shares_to_buy,
            execution_price=exec_price,
            commission=commission,
            message=f"Bought {shares_to_buy} shares",
            timestamp=datetime.now().isoformat(),
        )
    
    def _execute_sell(
        self,
        ticker: str,
        price: float,
        date: str,
        signal: TradeSignal,
    ) -> OrderResult:
        """Execute a sell order (sells entire position)."""
        position = self.state.get_position(ticker)
        
        if position is None or position.shares <= 0:
            return OrderResult(
                success=False,
                order_id=f"hold-{date}-{ticker}",
                ticker=ticker,
                action="HOLD",
                shares=0,
                execution_price=price,
                commission=0.0,
                message="No position to sell",
                timestamp=datetime.now().isoformat(),
            )
        
        if price <= 0:
            return OrderResult(
                success=False,
                order_id=f"hold-{date}-{ticker}",
                ticker=ticker,
                action="HOLD",
                shares=0,
                execution_price=0.0,
                commission=0.0,
                message="Invalid price — refusing to sell at zero",
                timestamp=datetime.now().isoformat(),
            )
        
        # Apply slippage (selling pushes price down)
        exec_price = price * (1 - self.slippage_rate)
        shares_to_sell = position.shares
        
        # Calculate proceeds
        trade_value = shares_to_sell * exec_price
        commission = trade_value * self.commission_rate
        net_proceeds = trade_value - commission
        
        # Update persistent state
        self.state.remove_position(ticker)
        self.state.add_cash(net_proceeds)
        self.state.record_trade(date, ticker, "SELL", exec_price, shares_to_sell, commission)
        
        logger.info(
            "SELL %d shares of %s @ $%.2f (slipped: $%.2f) on %s | Commission: $%.2f",
            shares_to_sell, ticker, price, exec_price, date, commission,
        )
        
        return OrderResult(
            success=True,
            order_id=f"sell-{date}-{ticker}-{int(datetime.now().timestamp())}",
            ticker=ticker,
            action="SELL",
            shares=shares_to_sell,
            execution_price=exec_price,
            commission=commission,
            message=f"Sold {shares_to_sell} shares",
            timestamp=datetime.now().isoformat(),
        )
    
    def _execute_hold(
        self,
        ticker: str,
        price: float,
        date: str,
        signal: TradeSignal,
    ) -> OrderResult:
        """Record a hold (no-op)."""
        return OrderResult(
            success=True,
            order_id=f"hold-{date}-{ticker}",
            ticker=ticker,
            action="HOLD",
            shares=0,
            execution_price=price,
            commission=0.0,
            message="Holding position",
            timestamp=datetime.now().isoformat(),
        )
    
    def get_positions(self) -> List[Position]:
        """Get all current positions from state."""
        return self.state.get_all_positions()
    
    def get_cash(self) -> float:
        """Get current cash balance from state."""
        return self.state.get_cash()
    
    def get_last_price(self, ticker: str) -> float:
        """Get last known price (from state or fetch from data vendor).
        
        For DummyBroker, we fetch current price from yfinance/Alpha Vantage.
        Real brokers would use their own price feed.
        """
        # Try to get price from position first
        position = self.state.get_position(ticker)
        if position and position.avg_entry_price > 0:
            # For paper trading, we need to fetch current market price
            # This is a placeholder - actual implementation should fetch from data vendor
            return position.avg_entry_price
        
        # If no position, return 0.0 (caller should fetch from data vendor)
        return 0.0
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        cash = self.get_cash()
        positions = self.get_positions()
        total_value = cash
        
        # Note: For accurate portfolio value, caller should provide current prices
        # This is a conservative estimate using avg_entry_price
        for pos in positions:
            if pos.avg_entry_price > 0:
                total_value += pos.shares * pos.avg_entry_price
        
        return total_value
