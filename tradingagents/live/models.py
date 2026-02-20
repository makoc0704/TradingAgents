"""Data models for live trading."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

from tradingagents.risk.models import TradeSignal


@dataclass
class LiveConfig:
    """Configuration for live trading execution.
    
    Attributes:
        tickers: List of ticker symbols to trade.
        mode: Execution mode — "dry_run" (log only) or "paper" (execute via broker).
        broker_type: Broker implementation to use — "dummy" (paper trading).
        state_path: Path to persistent state JSON file.
        initial_capital: Starting capital in USD/EUR.
        commission_rate: Commission as fraction of trade value (e.g. 0.001 = 0.1%).
        slippage_rate: Slippage as fraction of price (e.g. 0.0005 = 0.05%).
        selected_analysts: Which analysts to use (e.g. ["market", "fundamentals"]).
        backtest_profile: Cost/thoroughness profile — "full", "standard", or "quick".
        config: Full DEFAULT_CONFIG dict passed through to TradingAgentsGraph.
    """
    
    tickers: List[str]
    mode: str = "paper"  # "dry_run" | "paper" | "live" (future)
    broker_type: str = "dummy"  # "dummy" | "alpaca" | "ib" (future)
    state_path: str = "results/live/state.json"
    initial_capital: float = 200.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    selected_analysts: List[str] = field(
        default_factory=lambda: ["market", "fundamentals"]
    )
    backtest_profile: str = "standard"
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state at a point in time.
    
    Attributes:
        date: Snapshot date in YYYY-MM-DD format.
        cash: Cash balance.
        positions: Dict mapping ticker to Position.
        total_value: Total portfolio value (cash + positions).
        daily_return: Return for this day as fraction (e.g. 0.01 = 1%).
        cumulative_return: Cumulative return since start as fraction.
    """
    
    date: str
    cash: float
    positions: Dict[str, Any]  # Dict[str, Position] but serialized as dict
    total_value: float
    daily_return: float
    cumulative_return: float
    
    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


@dataclass
class LiveRunResult:
    """Result of a single live trading run.
    
    Attributes:
        date: Run date in YYYY-MM-DD format (always current date).
        signals: Dict mapping ticker to TradeSignal.
        executed_orders: List of OrderResult (empty if dry_run mode).
        portfolio_snapshot: PortfolioSnapshot for this run.
        daily_return: Return since yesterday as fraction.
        cumulative_return: Return since start as fraction.
        performance_metrics: Dict of performance metrics (Sharpe, drawdown, etc.).
    """
    
    date: str
    signals: Dict[str, TradeSignal]
    executed_orders: List[Any]  # List[OrderResult] but serialized as dict
    portfolio_snapshot: PortfolioSnapshot
    daily_return: float
    cumulative_return: float
    performance_metrics: Dict[str, float]
    
    def to_dict(self) -> dict:
        """Serialize to plain dict without double-traversal."""
        return {
            "date": self.date,
            "signals": {
                ticker: signal.to_dict() if hasattr(signal, "to_dict") else str(signal)
                for ticker, signal in self.signals.items()
            },
            "executed_orders": [
                asdict(order) if hasattr(order, "__dataclass_fields__") else
                order.to_dict() if hasattr(order, "to_dict") else
                str(order)
                for order in self.executed_orders
            ],
            "portfolio_snapshot": self.portfolio_snapshot.to_dict(),
            "daily_return": self.daily_return,
            "cumulative_return": self.cumulative_return,
            "performance_metrics": self.performance_metrics,
        }
