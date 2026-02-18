"""Pydantic request models for the API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request body for running a single analysis."""

    ticker: str = Field(..., description="Stock ticker symbol, e.g. NVDA")
    analysis_date: str = Field(
        ..., description="Analysis date in YYYY-MM-DD format"
    )
    selected_analysts: List[str] = Field(
        default=["market", "fundamentals"],
        description="Analysts to use: market, social, news, fundamentals",
    )
    llm_provider: str = Field(
        default="openai",
        description="LLM provider: openai, anthropic, google, ollama",
    )

    model_config = {"json_schema_extra": {
        "examples": [{
            "ticker": "NVDA",
            "analysis_date": "2024-06-05",
            "selected_analysts": ["market", "fundamentals"],
            "llm_provider": "openai",
        }]
    }}


class BacktestRequest(BaseModel):
    """Request body for running a backtest."""

    ticker: str = Field(..., description="Stock ticker symbol")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    initial_capital: float = Field(
        default=100_000, ge=1000, description="Starting capital in USD"
    )
    backtest_profile: str = Field(
        default="quick",
        description="Profile: full, standard, or quick",
    )
    reflection_mode: str = Field(
        default="none",
        description="Reflection mode: none, end_only, or periodic",
    )
    trading_frequency: str = Field(
        default="daily",
        description="Trading frequency: daily, weekly, or monthly",
    )

    model_config = {"json_schema_extra": {
        "examples": [{
            "ticker": "NVDA",
            "start_date": "2024-06-03",
            "end_date": "2024-06-07",
            "initial_capital": 100000,
            "backtest_profile": "quick",
        }]
    }}


class PortfolioRequest(BaseModel):
    """Request body for running a portfolio backtest."""

    tickers: List[str] = Field(
        ..., min_length=2, description="List of ticker symbols"
    )
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    initial_capital: float = Field(
        default=100_000, ge=1000, description="Starting capital in USD"
    )
    weighting_strategy: str = Field(
        default="equal",
        description="Strategy: equal, risk_parity, min_variance, signal_weighted",
    )
    backtest_profile: str = Field(
        default="quick",
        description="Profile: full, standard, or quick",
    )
    rebalance_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Drift threshold for rebalancing",
    )

    model_config = {"json_schema_extra": {
        "examples": [{
            "tickers": ["NVDA", "AAPL", "MSFT"],
            "start_date": "2024-06-03",
            "end_date": "2024-06-07",
            "weighting_strategy": "equal",
        }]
    }}


class PipelineRunRequest(BaseModel):
    """Request body for triggering a pipeline job."""

    config_path: Optional[str] = Field(
        default=None,
        description="Path to pipeline YAML config (uses default if omitted)",
    )
