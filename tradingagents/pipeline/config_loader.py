"""Pipeline configuration loader — reads YAML, validates, substitutes env vars."""

import logging
import os
import re
from typing import Any, Dict

import yaml

from .models import (
    JobConfig,
    NotificationConfig,
    PipelineConfig,
    ScheduleConfig,
)

logger = logging.getLogger(__name__)

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _substitute_env_vars(value: Any) -> Any:
    """Recursively substitute ``${ENV_VAR}`` placeholders in strings."""
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            env_val = os.environ.get(var_name, "")
            if not env_val:
                logger.warning(
                    "Environment variable '%s' is not set — using empty string",
                    var_name,
                )
            return env_val

        return _ENV_VAR_PATTERN.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    return value


def _parse_schedule(data: dict) -> ScheduleConfig:
    """Parse a schedule section from YAML data."""
    if not data:
        return ScheduleConfig()
    return ScheduleConfig(
        cron_expression=data.get("cron_expression", "0 9 * * 1-5"),
        timezone=data.get("timezone", "UTC"),
        enabled=data.get("enabled", True),
        max_retries=data.get("max_retries", 3),
        retry_delay_seconds=data.get("retry_delay_seconds", 300),
    )


def _parse_notification(data: dict) -> NotificationConfig:
    """Parse a notification section from YAML data."""
    if not data:
        return NotificationConfig()
    return NotificationConfig(
        enabled=data.get("enabled", False),
        channels=data.get("channels", ["log"]),
        webhook_url=data.get("webhook_url"),
        email_to=data.get("email_to"),
        smtp_host=data.get("smtp_host"),
        smtp_port=data.get("smtp_port", 587),
        notify_on=data.get("notify_on", ["success", "failure"]),
    )


def _parse_job(data: dict) -> JobConfig:
    """Parse a single job configuration from YAML data.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    name = data.get("name")
    if not name:
        raise ValueError("Job config missing required field 'name'")

    job_type = data.get("job_type")
    valid_types = ("single_analysis", "backtest", "portfolio")
    if job_type not in valid_types:
        raise ValueError(
            f"Job '{name}': invalid job_type '{job_type}'. "
            f"Must be one of {valid_types}"
        )

    tickers = data.get("tickers", ["NVDA"])
    if not isinstance(tickers, list) or not tickers:
        raise ValueError(
            f"Job '{name}': 'tickers' must be a non-empty list"
        )

    return JobConfig(
        name=name,
        job_type=job_type,
        tickers=tickers,
        analysis_date=data.get("analysis_date", "today"),
        schedule=_parse_schedule(data.get("schedule", {})),
        notification=_parse_notification(data.get("notification", {})),
        config=data.get("config", {}),
    )


def load_pipeline_config(path: str = "pipeline.yaml") -> PipelineConfig:
    """Load pipeline configuration from a YAML file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Validated PipelineConfig.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the config is invalid.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Pipeline config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Pipeline config must be a YAML mapping, got {type(raw).__name__}")

    raw = _substitute_env_vars(raw)

    jobs_data = raw.get("jobs", [])
    if not isinstance(jobs_data, list):
        raise ValueError("'jobs' must be a list")

    jobs = [_parse_job(job_data) for job_data in jobs_data]

    job_names = [j.name for j in jobs]
    duplicates = [n for n in job_names if job_names.count(n) > 1]
    if duplicates:
        raise ValueError(f"Duplicate job names: {set(duplicates)}")

    config = PipelineConfig(
        jobs=jobs,
        results_dir=raw.get("results_dir", "./results/pipeline"),
        log_level=raw.get("log_level", "INFO"),
        max_concurrent_jobs=raw.get("max_concurrent_jobs", 1),
    )

    logger.info(
        "Loaded pipeline config: %d jobs from '%s'",
        len(config.jobs), path,
    )
    return config
