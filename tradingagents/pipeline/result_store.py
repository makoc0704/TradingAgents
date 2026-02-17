"""ResultStore — persists pipeline job results as JSON with history support."""

import json
import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional

from .models import JobResult

logger = logging.getLogger(__name__)


class ResultStore:
    """File-based storage for pipeline job results.

    Each job gets its own subdirectory.  Results are stored as timestamped
    JSON files with a ``latest.json`` copy for quick access.

    Args:
        base_dir: Root directory for pipeline results.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _job_dir(self, job_name: str) -> str:
        """Return (and ensure) the directory for a given job."""
        d = os.path.join(self.base_dir, job_name)
        os.makedirs(d, exist_ok=True)
        return d

    def save(self, result: JobResult) -> str:
        """Persist a JobResult and update ``latest.json``.

        Args:
            result: The job result to save.

        Returns:
            Absolute path to the saved JSON file.
        """
        job_dir = self._job_dir(result.job_name)

        timestamp = result.finished_at.strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}.json"
        filepath = os.path.join(job_dir, filename)

        try:
            data = result.to_dict()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            latest_path = os.path.join(job_dir, "latest.json")
            shutil.copy2(filepath, latest_path)

            logger.info("Result saved: %s", filepath)
            return os.path.abspath(filepath)

        except (IOError, OSError) as e:
            logger.warning("Failed to save result for '%s': %s", result.job_name, e)
            return ""

    def get_latest(self, job_name: str) -> Optional[JobResult]:
        """Load the most recent result for a job.

        Args:
            job_name: Name of the pipeline job.

        Returns:
            The latest JobResult, or None if no results exist.
        """
        latest_path = os.path.join(self._job_dir(job_name), "latest.json")
        return self._load_result(latest_path)

    def get_history(self, job_name: str, limit: int = 30) -> List[JobResult]:
        """Load recent results for a job, newest first.

        Args:
            job_name: Name of the pipeline job.
            limit: Maximum number of results to return.

        Returns:
            List of JobResult objects, sorted newest-first.
        """
        job_dir = self._job_dir(job_name)
        files = [
            f for f in os.listdir(job_dir)
            if f.endswith(".json") and f != "latest.json"
        ]
        files.sort(reverse=True)

        results = []
        for filename in files[:limit]:
            filepath = os.path.join(job_dir, filename)
            result = self._load_result(filepath)
            if result:
                results.append(result)

        return results

    def has_signal_changed(self, job_name: str, new_signal: str) -> bool:
        """Check if the trade signal has changed since the last run.

        Args:
            job_name: Name of the pipeline job.
            new_signal: Signal from the current run.

        Returns:
            True if the signal changed or there is no previous result.
        """
        latest = self.get_latest(job_name)
        if latest is None:
            return True
        if latest.signal is None:
            return True

        old_signal = latest.signal.upper().strip()
        current = new_signal.upper().strip()
        return old_signal != current

    def _load_result(self, filepath: str) -> Optional[JobResult]:
        """Load a single JobResult from a JSON file."""
        if not os.path.isfile(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JobResult.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, IOError) as e:
            logger.warning("Failed to load result from '%s': %s", filepath, e)
            return None
