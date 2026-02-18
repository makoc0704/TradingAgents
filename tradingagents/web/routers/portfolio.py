"""Portfolio router — run multi-asset backtests and retrieve results."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..dependencies import get_task_manager
from ..schemas.requests import PortfolioRequest
from ..schemas.responses import ApiResponse, TaskStatusResponse
from ..services.task_manager import TaskManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolio"])


def _run_portfolio(task_info: Any, update_fn: Any) -> Dict[str, Any]:
    """Execute a portfolio backtest in a background thread."""
    config = task_info.config

    update_fn(progress=5, message="Initializing portfolio backtest...")

    from tradingagents.portfolio import PortfolioManager, PortfolioConfig
    from tradingagents.default_config import DEFAULT_CONFIG

    pf_config = PortfolioConfig(
        tickers=config["tickers"],
        start_date=config["start_date"],
        end_date=config["end_date"],
        initial_capital=config.get("initial_capital", 100_000),
        weighting_strategy=config.get("weighting_strategy", "equal"),
        backtest_profile=config.get("backtest_profile", "quick"),
        rebalance_threshold=config.get("rebalance_threshold", 0.05),
        config={**DEFAULT_CONFIG},
    )

    tickers_str = ", ".join(pf_config.tickers)
    update_fn(
        progress=10,
        message=f"Running portfolio backtest for [{tickers_str}] "
        f"({pf_config.start_date} to {pf_config.end_date})...",
    )

    manager = PortfolioManager(pf_config)
    result = manager.run()

    update_fn(progress=100, message="Portfolio backtest complete")

    return result.to_dict()


@router.post(
    "/run",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Start a portfolio backtest",
)
async def run_portfolio(
    request: PortfolioRequest,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse[TaskStatusResponse]:
    """Submit a portfolio backtest as a background task."""
    task_id = task_manager.submit(
        task_type="portfolio",
        config=request.model_dump(),
        run_fn=_run_portfolio,
    )
    status = task_manager.get_status(task_id)
    return ApiResponse(success=True, data=TaskStatusResponse(**status))


@router.get(
    "/status/{task_id}",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Get portfolio task status",
)
async def get_portfolio_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse:
    """Poll the status of a running portfolio task."""
    status = task_manager.get_status(task_id)
    if status is None:
        return ApiResponse(success=False, error=f"Task '{task_id}' not found")
    return ApiResponse(success=True, data=TaskStatusResponse(**status))


@router.get(
    "/result/{task_id}",
    response_model=ApiResponse,
    summary="Get portfolio result",
)
async def get_portfolio_result(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse:
    """Get the result of a completed portfolio backtest."""
    result = task_manager.get_result(task_id)
    if result is None:
        return ApiResponse(success=False, error="Result not available yet")
    return ApiResponse(success=True, data=result)
