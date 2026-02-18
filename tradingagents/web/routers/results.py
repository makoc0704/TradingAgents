"""Results router — browse and retrieve stored analysis/backtest results."""

import logging
from typing import List

from fastapi import APIRouter, Depends

from ..dependencies import get_result_reader
from ..schemas.responses import ApiResponse
from ..services.result_reader import ResultReader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["results"])


@router.get(
    "/tickers",
    response_model=ApiResponse[List[str]],
    summary="List tickers with results",
)
async def list_tickers(
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse[List[str]]:
    """List all tickers that have stored analysis results."""
    tickers = reader.list_tickers()
    return ApiResponse(success=True, data=tickers)


@router.get(
    "/tickers/{ticker}/dates",
    response_model=ApiResponse[List[str]],
    summary="List analysis dates for a ticker",
)
async def list_ticker_dates(
    ticker: str,
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse[List[str]]:
    """List available analysis dates for a specific ticker."""
    dates = reader.list_dates_for_ticker(ticker.upper())
    return ApiResponse(success=True, data=dates)


@router.get(
    "/files",
    response_model=ApiResponse,
    summary="List all result files",
)
async def list_result_files(
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse:
    """List all JSON result files in the results directory."""
    files = reader.list_result_files()
    return ApiResponse(success=True, data=files)


@router.get(
    "/pipeline/jobs",
    response_model=ApiResponse[List[str]],
    summary="List pipeline job names with results",
)
async def list_pipeline_jobs(
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse[List[str]]:
    """List all pipeline job names that have stored results."""
    jobs = reader.list_pipeline_jobs()
    return ApiResponse(success=True, data=jobs)
