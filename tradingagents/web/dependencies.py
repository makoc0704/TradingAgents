"""FastAPI dependency injection — shared singleton instances."""

import logging
from typing import Optional

from .config import WebConfig
from .services.task_manager import TaskManager
from .services.result_reader import ResultReader

logger = logging.getLogger(__name__)

# Module-level singletons, initialized by the app lifespan handler.
_task_manager: Optional[TaskManager] = None
_result_reader: Optional[ResultReader] = None
_web_config: Optional[WebConfig] = None


def init_dependencies(config: WebConfig) -> None:
    """Initialize shared dependencies (called during app startup).

    Args:
        config: Web configuration.
    """
    global _task_manager, _result_reader, _web_config
    _web_config = config
    _task_manager = TaskManager(
        max_workers=config.max_concurrent_tasks,
        ttl_seconds=config.task_ttl_seconds,
    )
    _result_reader = ResultReader(results_dir=config.results_dir)
    logger.info(
        "Dependencies initialized (results_dir=%s, max_tasks=%d)",
        config.results_dir,
        config.max_concurrent_tasks,
    )


def shutdown_dependencies() -> None:
    """Clean up shared dependencies (called during app shutdown)."""
    global _task_manager
    if _task_manager:
        _task_manager.shutdown()
        _task_manager = None
    logger.info("Dependencies shut down.")


def get_task_manager() -> TaskManager:
    """FastAPI dependency: get the TaskManager singleton."""
    if _task_manager is None:
        raise RuntimeError("TaskManager not initialized — call init_dependencies() first")
    return _task_manager


def get_result_reader() -> ResultReader:
    """FastAPI dependency: get the ResultReader singleton."""
    if _result_reader is None:
        raise RuntimeError("ResultReader not initialized — call init_dependencies() first")
    return _result_reader


def get_web_config() -> WebConfig:
    """FastAPI dependency: get the WebConfig."""
    if _web_config is None:
        raise RuntimeError("WebConfig not initialized — call init_dependencies() first")
    return _web_config
