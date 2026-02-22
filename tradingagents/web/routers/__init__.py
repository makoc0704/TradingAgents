"""API routers for the web interface."""

from .analysis import router as analysis_router
from .backtest import router as backtest_router
from .portfolio import router as portfolio_router
from .pipeline import router as pipeline_router
from .results import router as results_router
from .risk import router as risk_router
from .live import router as live_router

__all__ = [
    "analysis_router",
    "backtest_router",
    "portfolio_router",
    "pipeline_router",
    "results_router",
    "risk_router",
    "live_router",
]
