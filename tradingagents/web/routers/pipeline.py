"""Pipeline router — view status and trigger pipeline jobs."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..dependencies import get_result_reader
from ..schemas.responses import (
    ApiResponse,
    PipelineStatusResponse,
    PipelineJobResponse,
)
from ..services.result_reader import ResultReader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline"])


@router.get(
    "/status",
    response_model=ApiResponse[PipelineStatusResponse],
    summary="Get pipeline status",
)
async def get_pipeline_status(
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse[PipelineStatusResponse]:
    """Get the current pipeline status and all job summaries."""
    job_names = reader.list_pipeline_jobs()

    jobs = []
    for name in job_names:
        latest = reader.get_pipeline_latest(name)
        job_resp = PipelineJobResponse(
            job_name=name,
            job_type=latest.get("job_type", "unknown") if latest else "unknown",
            last_status=latest.get("status") if latest else None,
            last_signal=latest.get("signal") if latest else None,
            last_run_at=latest.get("finished_at") if latest else None,
            last_duration_seconds=latest.get("duration_seconds") if latest else None,
        )
        jobs.append(job_resp)

    status = PipelineStatusResponse(
        running=False,  # Pipeline scheduler state is separate from web server
        total_jobs=len(jobs),
        enabled_jobs=len(jobs),
        jobs=jobs,
    )
    return ApiResponse(success=True, data=status)


@router.get(
    "/jobs/{job_name}/history",
    response_model=ApiResponse,
    summary="Get job execution history",
)
async def get_job_history(
    job_name: str,
    limit: int = 30,
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse:
    """Get execution history for a specific pipeline job."""
    history = reader.get_pipeline_history(job_name, limit=limit)
    if not history:
        return ApiResponse(
            success=False,
            error=f"No history found for job '{job_name}'",
        )
    return ApiResponse(success=True, data=history)


@router.get(
    "/jobs/{job_name}/latest",
    response_model=ApiResponse,
    summary="Get latest job result",
)
async def get_job_latest(
    job_name: str,
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse:
    """Get the latest result for a pipeline job."""
    latest = reader.get_pipeline_latest(job_name)
    if latest is None:
        return ApiResponse(
            success=False,
            error=f"No results found for job '{job_name}'",
        )
    return ApiResponse(success=True, data=latest)


@router.post(
    "/run-now/{job_name}",
    response_model=ApiResponse,
    summary="Trigger a pipeline job immediately",
)
async def run_job_now(
    job_name: str,
) -> ApiResponse:
    """Trigger immediate execution of a pipeline job.

    Note: This requires a running PipelineManager instance.
    If the pipeline scheduler is not running, this will return an error.
    """
    try:
        from tradingagents.pipeline import PipelineManager
        from tradingagents.default_config import DEFAULT_CONFIG

        config_path = DEFAULT_CONFIG.get("pipeline_config_path", "pipeline.yaml")
        manager = PipelineManager(config_path)
        result = manager.run_job(job_name)

        if result is None:
            return ApiResponse(
                success=False, error=f"Job '{job_name}' not found in config"
            )

        return ApiResponse(success=True, data=result.to_dict())

    except FileNotFoundError:
        return ApiResponse(
            success=False,
            error="Pipeline config file not found. Create a pipeline.yaml first.",
        )
    except Exception as exc:
        logger.error("Failed to run pipeline job '%s': %s", job_name, exc)
        return ApiResponse(success=False, error=str(exc))
