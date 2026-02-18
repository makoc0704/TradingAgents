"""TaskManager — runs long-running analysis/backtest/portfolio jobs in background threads."""

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """In-memory state for a running or completed task."""

    task_id: str
    task_type: str  # "analysis", "backtest", "portfolio"
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress_percent: int = 0
    message: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = ""
    finished_at: str = ""
    _cancel_flag: bool = False


class TaskManager:
    """Manages background execution of long-running trading tasks.

    Uses a ThreadPoolExecutor to run blocking LLM calls without
    blocking the FastAPI async event loop.

    Args:
        max_workers: Maximum concurrent background tasks.
        ttl_seconds: Time-to-live for completed tasks in memory.
    """

    def __init__(self, max_workers: int = 2, ttl_seconds: int = 3600):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="task"
        )
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._ttl_seconds = ttl_seconds

    def submit(
        self, task_type: str, config: Dict[str, Any], run_fn: Callable
    ) -> str:
        """Submit a new background task.

        Args:
            task_type: Type of task (analysis, backtest, portfolio).
            config: Configuration dict for the task.
            run_fn: Callable that performs the actual work.
                Must accept (task_info, update_fn) and return a result dict.

        Returns:
            Unique task_id string.
        """
        task_id = str(uuid.uuid4())[:8]
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            config=config,
            created_at=datetime.now().isoformat(),
        )

        with self._lock:
            self._tasks[task_id] = task_info

        self._executor.submit(self._run_task, task_info, run_fn)
        logger.info("Task submitted: %s (%s)", task_id, task_type)
        return task_id

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task.

        Returns:
            Status dict or None if task not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            return None
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
            "progress_percent": task.progress_percent,
            "message": task.message,
            "created_at": task.created_at,
            "result": task.result,
            "error": task.error,
        }

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed task.

        Returns:
            Result dict or None if not available.
        """
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None or task.status != "completed":
            return None
        return task.result

    def cancel(self, task_id: str) -> bool:
        """Request cancellation of a running task.

        Returns:
            True if cancellation was requested, False if task not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            return False
        task._cancel_flag = True
        logger.info("Cancellation requested for task: %s", task_id)
        return True

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks (active and recently completed)."""
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "progress_percent": t.progress_percent,
                    "message": t.message,
                    "created_at": t.created_at,
                }
                for t in self._tasks.values()
            ]

    def subscribe(self, task_id: str, callback: Callable) -> None:
        """Subscribe to progress updates for a task.

        Args:
            task_id: The task to subscribe to.
            callback: Called with (task_id, status_dict) on each update.
        """
        with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = []
            self._subscribers[task_id].append(callback)

    def unsubscribe(self, task_id: str, callback: Callable) -> None:
        """Remove a subscription."""
        with self._lock:
            subs = self._subscribers.get(task_id, [])
            if callback in subs:
                subs.remove(callback)

    def shutdown(self) -> None:
        """Gracefully shut down the executor."""
        logger.info("Shutting down TaskManager...")
        self._executor.shutdown(wait=False)

    def _run_task(self, task_info: TaskInfo, run_fn: Callable) -> None:
        """Execute a task in a background thread."""
        task_info.status = "running"
        self._notify(task_info)

        try:

            def update_fn(
                progress: int = 0, message: str = "", **kwargs: Any
            ) -> None:
                task_info.progress_percent = progress
                task_info.message = message
                self._notify(task_info)

            result = run_fn(task_info, update_fn)

            task_info.status = "completed"
            task_info.progress_percent = 100
            task_info.result = result if isinstance(result, dict) else {}
            task_info.finished_at = datetime.now().isoformat()
            logger.info("Task completed: %s", task_info.task_id)

        except Exception as exc:
            task_info.status = "failed"
            task_info.error = str(exc)
            task_info.finished_at = datetime.now().isoformat()
            logger.error(
                "Task failed: %s — %s", task_info.task_id, exc, exc_info=True
            )

        self._notify(task_info)

    def _notify(self, task_info: TaskInfo) -> None:
        """Notify all subscribers of a status change."""
        with self._lock:
            subs = list(self._subscribers.get(task_info.task_id, []))

        status = self.get_status(task_info.task_id)
        for callback in subs:
            try:
                callback(task_info.task_id, status)
            except Exception as exc:
                logger.warning("Subscriber callback error: %s", exc)
