"""Live Trading router — read live portfolio state and trigger runs."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..dependencies import get_task_manager
from ..schemas.responses import ApiResponse, LiveRunRequest, TaskStatusResponse
from ..services.task_manager import TaskManager
from ..services.live_reader import LiveReader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["live"])

_live_reader: LiveReader | None = None


def _get_live_reader() -> LiveReader:
    """Lazy-init the LiveReader singleton."""
    global _live_reader
    if _live_reader is None:
        import os
        state_path = os.environ.get(
            "LIVE_STATE_PATH", "./live_portfolio/state.json"
        )
        _live_reader = LiveReader(state_path=state_path)
    return _live_reader


@router.get(
    "/portfolio",
    response_model=ApiResponse,
    summary="Get current live portfolio state",
)
async def get_live_portfolio(
    reader: LiveReader = Depends(_get_live_reader),
) -> ApiResponse:
    """Return current portfolio value, cash, positions, and returns."""
    data = reader.get_portfolio()
    if data is None:
        return ApiResponse(
            success=False,
            error="No live portfolio state found. Run a live trading session first.",
        )
    return ApiResponse(success=True, data=data)


@router.get(
    "/trades",
    response_model=ApiResponse,
    summary="Get recent live trades",
)
async def get_live_trades(
    limit: int = 50,
    reader: LiveReader = Depends(_get_live_reader),
) -> ApiResponse:
    """Return the most recent trades from the live portfolio."""
    trades = reader.get_trades(limit=limit)
    return ApiResponse(success=True, data=trades)


@router.get(
    "/performance",
    response_model=ApiResponse,
    summary="Get aggregate live performance metrics",
)
async def get_live_performance(
    reader: LiveReader = Depends(_get_live_reader),
) -> ApiResponse:
    """Return computed performance: return, Sharpe, drawdown, etc."""
    data = reader.get_performance()
    if data is None:
        return ApiResponse(
            success=False,
            error="No live performance data available.",
        )
    return ApiResponse(success=True, data=data)


@router.get(
    "/history",
    response_model=ApiResponse,
    summary="Get run snapshots for equity curve",
)
async def get_live_history(
    reader: LiveReader = Depends(_get_live_reader),
) -> ApiResponse:
    """Return daily run snapshots for charting the equity curve."""
    history = reader.get_run_history()
    return ApiResponse(success=True, data=history)


def _run_live_trading(task_info: Any, update_fn: Any) -> Dict[str, Any]:
    """Execute a live trading run in a background thread."""
    update_fn(progress=5, message="Initializing live trading run...")

    from tradingagents.live.runner import LiveRunner
    from tradingagents.live.models import LiveConfig

    config = LiveConfig(
        tickers=task_info.config.get("tickers", ["NVDA"]),
        initial_capital=task_info.config.get("initial_capital", 200.0),
        backtest_profile=task_info.config.get("backtest_profile", "quick"),
    )

    update_fn(progress=15, message=f"Running for {len(config.tickers)} ticker(s)...")

    runner = LiveRunner(config)
    result = runner.run()

    update_fn(progress=100, message="Live trading run complete")
    return result.to_dict()


@router.post(
    "/run-now",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Trigger an immediate live trading run",
)
async def run_live_now(
    body: LiveRunRequest | None = None,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse[TaskStatusResponse]:
    """Submit a live trading run as a background task."""
    req = body or LiveRunRequest()
    task_id = task_manager.submit(
        task_type="live_trading",
        config={
            "tickers": req.tickers,
            "initial_capital": req.initial_capital,
            "backtest_profile": req.backtest_profile,
        },
        run_fn=_run_live_trading,
    )
    status = task_manager.get_status(task_id)
    return ApiResponse(success=True, data=TaskStatusResponse(**status))
