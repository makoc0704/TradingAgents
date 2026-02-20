"""Abstract broker interface for live trading."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from tradingagents.risk.models import TradeSignal


@dataclass
class Position:
    """A single position held by the broker.
    
    Attributes:
        ticker: Stock ticker symbol.
        shares: Number of shares held (whole shares only).
        avg_entry_price: Average entry price per share.
        current_price: Last known price per share.
    """
    
    ticker: str
    shares: int
    avg_entry_price: float
    current_price: float


@dataclass
class OrderResult:
    """Result of placing an order.
    
    Attributes:
        success: Whether the order was executed successfully.
        order_id: Unique identifier for this order.
        ticker: Stock ticker symbol.
        action: Action executed (BUY, SELL, HOLD).
        shares: Number of shares traded (0 for HOLD).
        execution_price: Price at which order was executed (after slippage).
        commission: Commission paid for this trade.
        message: Human-readable message describing the result.
        timestamp: ISO format timestamp of execution.
    """
    
    success: bool
    order_id: str
    ticker: str
    action: str  # BUY, SELL, HOLD
    shares: int
    execution_price: float
    commission: float
    message: str
    timestamp: str


class BrokerInterface(ABC):
    """Abstract interface for broker implementations.
    
    This allows swapping between paper trading (DummyBroker) and
    real brokers (Alpaca, Interactive Brokers, etc.) without
    changing the LiveRunner code.
    """
    
    @abstractmethod
    def place_order(
        self,
        ticker: str,
        signal: TradeSignal,
        current_price: float,
        date: str,
    ) -> OrderResult:
        """Place an order based on a trade signal.
        
        Args:
            ticker: Stock ticker symbol.
            signal: TradeSignal from the agent graph.
            current_price: Current market price (before slippage).
            date: Trade date in YYYY-MM-DD format.
            
        Returns:
            OrderResult describing what was executed.
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all current positions.
        
        Returns:
            List of Position objects.
        """
        pass
    
    @abstractmethod
    def get_cash(self) -> float:
        """Get current cash balance.
        
        Returns:
            Cash balance in USD.
        """
        pass
    
    @abstractmethod
    def get_last_price(self, ticker: str) -> float:
        """Get the last known price for a ticker.
        
        Args:
            ticker: Stock ticker symbol.
            
        Returns:
            Last known price, or 0.0 if ticker not found.
        """
        pass
    
    @abstractmethod
    def get_portfolio_value(self) -> float:
        """Get total portfolio value (cash + positions).
        
        Returns:
            Total portfolio value in USD.
        """
        pass
