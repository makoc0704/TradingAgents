"""Data models for portfolio management."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class PortfolioConfig:
    """Configuration for a portfolio backtest run.

    Attributes:
        tickers: List of stock ticker symbols in the portfolio.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        initial_capital: Starting portfolio value in USD.
        weighting_strategy: Allocation method — "equal", "risk_parity",
            "min_variance", or "signal_weighted".
        max_position_fraction: Maximum weight for a single ticker (0.0-1.0).
        min_position_fraction: Minimum weight for a single ticker (0.0-1.0).
        rebalance_threshold: Drift that triggers rebalancing (e.g. 0.05 = 5%).
        rebalance_frequency: How often to check drift — "daily", "weekly", "monthly".
        trading_frequency: How often to trade — "daily", "weekly", "monthly".
        backtest_profile: Cost/thoroughness profile — "full", "standard", "quick".
        reflection_mode: When to reflect — "none", "end_only", "periodic".
        reflection_interval: Trading days between reflections (for "periodic").
        use_data_cache: Whether to cache vendor API responses to disk.
        commission_rate: Commission as fraction of trade value (e.g. 0.001).
        slippage_rate: Slippage as fraction of price (e.g. 0.0005).
        config: Full DEFAULT_CONFIG dict passed through to TradingAgentsGraph.
    """

    tickers: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 100_000.0
    weighting_strategy: str = "equal"
    max_position_fraction: float = 0.30
    min_position_fraction: float = 0.05
    rebalance_threshold: float = 0.05
    rebalance_frequency: str = "weekly"
    trading_frequency: str = "daily"
    backtest_profile: str = "standard"
    reflection_mode: str = "periodic"
    reflection_interval: int = 20
    use_data_cache: bool = True
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    selected_analysts: List[str] = field(
        default_factory=lambda: ["market", "fundamentals"]
    )
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to plain dict (config excluded for brevity in reports)."""
        d = asdict(self)
        d.pop("config", None)
        return d


@dataclass
class Position:
    """A single position in the portfolio.

    Attributes:
        ticker: Stock ticker symbol.
        shares: Number of shares held (whole shares only).
        avg_entry_price: Volume-weighted average entry price.
        current_price: Latest market price.
        target_weight: Desired allocation fraction.
        actual_weight: Current allocation fraction based on market value.
    """

    ticker: str
    shares: int
    avg_entry_price: float
    current_price: float
    target_weight: float
    actual_weight: float

    @property
    def market_value(self) -> float:
        """Current market value of this position."""
        return self.shares * self.current_price

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        d = asdict(self)
        d["market_value"] = self.market_value
        return d


@dataclass
class AllocationResult:
    """Result of a portfolio optimization / weighting calculation.

    Attributes:
        weights: Target weight per ticker (e.g. {"AAPL": 0.25, "NVDA": 0.35}).
        method: Weighting strategy used.
        portfolio_volatility: Estimated annualized portfolio volatility.
        portfolio_var_95: Estimated 95% daily VaR for the portfolio.
        diversification_ratio: Ratio of weighted individual vols to portfolio vol.
        correlation_matrix: Pairwise correlations as nested dict.
    """

    weights: Dict[str, float]
    method: str
    portfolio_volatility: float = 0.0
    portfolio_var_95: float = 0.0
    diversification_ratio: float = 1.0
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


@dataclass
class RebalanceOrder:
    """A single rebalancing order to move from actual to target weight.

    Attributes:
        ticker: Stock ticker symbol.
        action: "BUY" or "SELL".
        target_shares: Number of shares to trade.
        estimated_value: Estimated dollar value of the trade.
        reason: Human-readable reason for the order.
    """

    ticker: str
    action: str
    target_shares: int
    estimated_value: float
    reason: str

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


@dataclass
class PortfolioSnapshot:
    """Portfolio state at end of a trading day.

    Attributes:
        date: Snapshot date in YYYY-MM-DD format.
        total_value: Total portfolio value (cash + all positions).
        cash: Cash balance.
        positions: Per-ticker position data.
        allocation: Allocation result from optimizer (or None on first day).
        daily_return: Return for this day as fraction.
        cumulative_return: Cumulative return since start as fraction.
        actions: Actions taken per ticker on this day.
    """

    date: str
    total_value: float
    cash: float
    positions: Dict[str, Position]
    allocation: Optional[AllocationResult]
    daily_return: float
    cumulative_return: float
    actions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return {
            "date": self.date,
            "total_value": self.total_value,
            "cash": self.cash,
            "positions": {t: p.to_dict() for t, p in self.positions.items()},
            "allocation": self.allocation.to_dict() if self.allocation else None,
            "daily_return": self.daily_return,
            "cumulative_return": self.cumulative_return,
            "actions": self.actions,
        }


@dataclass
class PortfolioResult:
    """Complete result of a portfolio backtest run.

    Attributes:
        config: The PortfolioConfig used.
        snapshots: Ordered list of daily portfolio snapshots.
        all_trades: Ordered list of all trade records (across all tickers).
        performance: Aggregated performance metrics dict.
        per_ticker_performance: Performance metrics per ticker.
        total_trading_days: Number of trading days in the backtest.
        total_trades: Number of actual trades (BUY + SELL, excluding HOLD).
    """

    config: PortfolioConfig
    snapshots: List[PortfolioSnapshot]
    all_trades: List[Dict[str, Any]]
    performance: Dict[str, float]
    per_ticker_performance: Dict[str, Dict[str, float]]
    total_trading_days: int
    total_trades: int

    def to_dict(self) -> dict:
        """Serialize full result to plain dict."""
        return {
            "config": self.config.to_dict(),
            "snapshots": [s.to_dict() for s in self.snapshots],
            "all_trades": self.all_trades,
            "performance": self.performance,
            "per_ticker_performance": self.per_ticker_performance,
            "total_trading_days": self.total_trading_days,
            "total_trades": self.total_trades,
        }
