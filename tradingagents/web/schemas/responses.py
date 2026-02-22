"""Pydantic response models for the API."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    Every endpoint returns this structure for consistency.
    """

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


# --- Live Trading Requests ---


class LiveRunRequest(BaseModel):
    """Request body for triggering a live trading run."""

    tickers: List[str] = Field(default=["NVDA"], min_length=1)
    initial_capital: float = Field(default=200.0, gt=0)
    backtest_profile: str = "quick"


# --- Task management ---


class TaskStatusResponse(BaseModel):
    """Status of a background task."""

    task_id: str
    task_type: str
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    progress_percent: int = 0
    message: str = ""
    created_at: str = ""
    result: Optional[Dict[str, Any]] = None


# --- Risk ---


class RiskMetricsResponse(BaseModel):
    """Risk metrics for a single ticker."""

    ticker: str
    date: str
    daily_volatility: float
    annualized_volatility: float
    atr: float
    atr_percent: float
    max_drawdown: float
    current_drawdown: float
    var_95: float
    var_99: float
    cvar_95: float
    beta: float
    sharpe_ratio: float
    sortino_ratio: float
    current_price: float
    sma_50: float
    sma_200: float
    rsi: float


# --- Backtest ---


class TradeRecordResponse(BaseModel):
    """A single trade in a backtest."""

    date: str
    ticker: str
    action: str
    price: float
    shares: int
    commission: float
    portfolio_value: float
    cash: float
    position_value: float


class DailySnapshotResponse(BaseModel):
    """Daily portfolio snapshot."""

    date: str
    portfolio_value: float
    cash: float
    position_shares: int
    position_value: float
    daily_return: float
    cumulative_return: float
    action: str


class BacktestResultResponse(BaseModel):
    """Complete backtest result."""

    config: Dict[str, Any]
    trades: List[TradeRecordResponse]
    daily_snapshots: List[DailySnapshotResponse]
    performance: Dict[str, float]
    total_trading_days: int
    total_trades: int


# --- Portfolio ---


class PositionResponse(BaseModel):
    """A single position in the portfolio."""

    ticker: str
    shares: int
    avg_entry_price: float
    current_price: float
    target_weight: float
    actual_weight: float
    market_value: float


class AllocationResponse(BaseModel):
    """Portfolio allocation result."""

    weights: Dict[str, float]
    method: str
    portfolio_volatility: float
    portfolio_var_95: float
    diversification_ratio: float


class PortfolioSnapshotResponse(BaseModel):
    """Daily portfolio snapshot for multi-asset."""

    date: str
    total_value: float
    cash: float
    positions: Dict[str, PositionResponse]
    allocation: Optional[AllocationResponse] = None
    daily_return: float
    cumulative_return: float
    actions: Dict[str, str]


class PortfolioResultResponse(BaseModel):
    """Complete portfolio backtest result."""

    config: Dict[str, Any]
    snapshots: List[PortfolioSnapshotResponse]
    all_trades: List[Dict[str, Any]]
    performance: Dict[str, float]
    per_ticker_performance: Dict[str, Dict[str, float]]
    total_trading_days: int
    total_trades: int


# --- Pipeline ---


class PipelineJobResponse(BaseModel):
    """A single pipeline job status."""

    job_name: str
    job_type: str
    enabled: bool = True
    cron_expression: str = ""
    next_run: Optional[str] = None
    last_status: Optional[str] = None
    last_signal: Optional[str] = None
    last_run_at: Optional[str] = None
    last_duration_seconds: Optional[float] = None


class PipelineStatusResponse(BaseModel):
    """Overall pipeline status."""

    running: bool
    total_jobs: int
    enabled_jobs: int
    jobs: List[PipelineJobResponse]


# --- Results listing ---


class ResultEntryResponse(BaseModel):
    """A single saved result entry."""

    filename: str
    date: str
    path: str
    size_bytes: int = 0


class AnalysisResultResponse(BaseModel):
    """Analysis result with agent reports."""

    ticker: str
    date: str
    final_decision: str = ""
    signal: str = ""
    confidence: str = ""
    market_report: str = ""
    sentiment_report: str = ""
    news_report: str = ""
    fundamentals_report: str = ""
    risk_metrics: Optional[Dict[str, Any]] = None
    investment_debate: Optional[Dict[str, Any]] = None
    risk_debate: Optional[Dict[str, Any]] = None
