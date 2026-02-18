"""Backtest router — run backtests and retrieve results."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..dependencies import get_task_manager, get_result_reader
from ..schemas.requests import BacktestRequest
from ..schemas.responses import ApiResponse, TaskStatusResponse
from ..services.task_manager import TaskManager
from ..services.result_reader import ResultReader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["backtest"])


def _run_backtest(task_info: Any, update_fn: Any) -> Dict[str, Any]:
    """Execute a backtest in a background thread."""
    config = task_info.config

    update_fn(progress=5, message="Initializing backtest...")

    from tradingagents.backtesting import BacktestRunner, BacktestConfig
    from tradingagents.default_config import DEFAULT_CONFIG

    bt_config = BacktestConfig(
        ticker=config["ticker"],
        start_date=config["start_date"],
        end_date=config["end_date"],
        initial_capital=config.get("initial_capital", 100_000),
        backtest_profile=config.get("backtest_profile", "quick"),
        reflection_mode=config.get("reflection_mode", "none"),
        trading_frequency=config.get("trading_frequency", "daily"),
        config={**DEFAULT_CONFIG},
    )

    update_fn(
        progress=10,
        message=f"Running backtest for {bt_config.ticker} "
        f"({bt_config.start_date} to {bt_config.end_date})...",
    )

    runner = BacktestRunner(bt_config)
    result = runner.run()

    update_fn(progress=100, message="Backtest complete")

    return result.to_dict()


@router.post(
    "/run",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Start a new backtest",
)
async def run_backtest(
    request: BacktestRequest,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse[TaskStatusResponse]:
    """Submit a backtest as a background task."""
    task_id = task_manager.submit(
        task_type="backtest",
        config=request.model_dump(),
        run_fn=_run_backtest,
    )
    status = task_manager.get_status(task_id)
    return ApiResponse(success=True, data=TaskStatusResponse(**status))


@router.get(
    "/status/{task_id}",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Get backtest task status",
)
async def get_backtest_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse:
    """Poll the status of a running backtest task."""
    status = task_manager.get_status(task_id)
    if status is None:
        return ApiResponse(success=False, error=f"Task '{task_id}' not found")
    return ApiResponse(success=True, data=TaskStatusResponse(**status))


@router.get(
    "/result/{task_id}",
    response_model=ApiResponse,
    summary="Get backtest result",
)
async def get_backtest_result(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse:
    """Get the result of a completed backtest task."""
    result = task_manager.get_result(task_id)
    if result is None:
        return ApiResponse(success=False, error="Result not available yet")
    return ApiResponse(success=True, data=result)
