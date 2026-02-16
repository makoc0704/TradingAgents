"""Data models for backtesting."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from tradingagents.risk.models import TradeSignal


@dataclass
class BacktestConfig:
    """Configuration for a single backtest run.

    Attributes:
        ticker: Stock ticker symbol to backtest.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        initial_capital: Starting portfolio value in USD.
        trading_frequency: How often to trade — "daily", "weekly", or "monthly".
        commission_rate: Commission as fraction of trade value (e.g. 0.001 = 0.1%).
        slippage_rate: Slippage as fraction of price (e.g. 0.0005 = 0.05%).
        selected_analysts: Which analysts to use (e.g. ["market", "fundamentals"]).
        backtest_profile: Cost/thoroughness profile — "full", "standard", or "quick".
        reflection_mode: When to reflect — "none", "end_only", or "periodic".
        reflection_interval: Trading days between reflections (for "periodic" mode).
        use_data_cache: Whether to cache vendor API responses to disk.
        config: Full DEFAULT_CONFIG dict passed through to TradingAgentsGraph.
    """

    ticker: str
    start_date: str
    end_date: str
    initial_capital: float = 100_000.0
    trading_frequency: str = "daily"
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    selected_analysts: List[str] = field(
        default_factory=lambda: ["market", "fundamentals"]
    )
    backtest_profile: str = "standard"
    reflection_mode: str = "periodic"
    reflection_interval: int = 20
    use_data_cache: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to plain dict (config excluded for brevity in reports)."""
        d = asdict(self)
        d.pop("config", None)
        return d


# --- Backtest profile presets ---

BACKTEST_PROFILES = {
    "full": {
        "selected_analysts": ["market", "social", "news", "fundamentals"],
    },
    "standard": {
        "selected_analysts": ["market", "fundamentals"],
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
    },
    "quick": {
        "selected_analysts": ["market"],
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
    },
}


@dataclass
class TradeRecord:
    """A single executed trade (or hold) in the backtest.

    Attributes:
        date: Trade date in YYYY-MM-DD format.
        ticker: Stock ticker symbol.
        action: Executed action — BUY, SELL, or HOLD.
        signal: Full TradeSignal from the agent graph (or None for fallback).
        price: Execution price after slippage.
        shares: Number of shares traded (0 for HOLD).
        commission: Commission paid for this trade.
        portfolio_value: Total portfolio value after this trade.
        cash: Cash balance after this trade.
        position_value: Value of held shares after this trade.
    """

    date: str
    ticker: str
    action: str
    signal: Optional[TradeSignal]
    price: float
    shares: int
    commission: float
    portfolio_value: float
    cash: float
    position_value: float

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        d = asdict(self)
        return d


@dataclass
class DailySnapshot:
    """Portfolio state at end of a trading day.

    Attributes:
        date: Snapshot date in YYYY-MM-DD format.
        portfolio_value: Total portfolio value (cash + positions).
        cash: Cash balance.
        position_shares: Number of shares currently held.
        position_value: Market value of held shares.
        daily_return: Return for this day as fraction (e.g. 0.01 = 1%).
        cumulative_return: Cumulative return since start as fraction.
        action: Action taken on this day (BUY, SELL, HOLD).
        risk_metrics: Quantitative risk metrics dict (or None).
    """

    date: str
    portfolio_value: float
    cash: float
    position_shares: int
    position_value: float
    daily_return: float
    cumulative_return: float
    action: str
    risk_metrics: Optional[dict] = None

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


@dataclass
class BacktestResult:
    """Complete result of a backtest run.

    Attributes:
        config: The BacktestConfig used.
        trades: Ordered list of all trade records.
        daily_snapshots: Ordered list of daily portfolio snapshots.
        performance: Aggregated performance metrics dict.
        total_trading_days: Number of trading days in the backtest.
        total_trades: Number of actual trades (BUY + SELL, excluding HOLD).
    """

    config: BacktestConfig
    trades: List[TradeRecord]
    daily_snapshots: List[DailySnapshot]
    performance: Dict[str, float]
    total_trading_days: int
    total_trades: int

    def to_dict(self) -> dict:
        """Serialize full result to plain dict."""
        return {
            "config": self.config.to_dict(),
            "trades": [t.to_dict() for t in self.trades],
            "daily_snapshots": [s.to_dict() for s in self.daily_snapshots],
            "performance": self.performance,
            "total_trading_days": self.total_trading_days,
            "total_trades": self.total_trades,
        }
