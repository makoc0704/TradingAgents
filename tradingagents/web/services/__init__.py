"""Backend services for the web interface."""

from .task_manager import TaskManager
from .result_reader import ResultReader

__all__ = ["TaskManager", "ResultReader"]
