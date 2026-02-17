"""PipelineManager — top-level orchestrator for the automated pipeline."""

import logging
from typing import Dict, List, Optional

from .config_loader import load_pipeline_config
from .job_runner import JobRunner
from .models import PipelineConfig
from .notifier import Notifier
from .result_store import ResultStore
from .scheduler import PipelineScheduler

logger = logging.getLogger(__name__)


class PipelineManager:
    """Single entry point for the automated pipeline.

    Loads configuration, creates all required components, and manages
    the scheduler lifecycle.

    Usage::

        manager = PipelineManager("pipeline.yaml")
        manager.start()        # blocks until Ctrl+C
        # or
        manager.run_job("daily_nvda_analysis")  # one-off execution

    Args:
        config_path: Path to the pipeline YAML config file.
    """

    def __init__(self, config_path: str = "pipeline.yaml"):
        self.config_path = config_path
        self._config: Optional[PipelineConfig] = None
        self._result_store: Optional[ResultStore] = None
        self._notifier: Optional[Notifier] = None
        self._runner: Optional[JobRunner] = None
        self._scheduler: Optional[PipelineScheduler] = None

    def _setup(self) -> None:
        """Load config and create internal components."""
        self._config = load_pipeline_config(self.config_path)

        log_level = getattr(logging, self._config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        self._result_store = ResultStore(self._config.results_dir)
        self._notifier = Notifier()
        self._runner = JobRunner(self._result_store, self._notifier)
        self._scheduler = PipelineScheduler(self._config, self._runner)

        logger.info(
            "PipelineManager initialized: %d jobs, results_dir='%s'",
            len(self._config.jobs), self._config.results_dir,
        )

    def start(self) -> None:
        """Load config, register jobs, and start the scheduler.

        This method **blocks** until the scheduler is stopped (via Ctrl+C
        or ``stop()``).
        """
        self._setup()
        logger.info("Starting pipeline scheduler...")
        self._scheduler.start()

    def stop(self) -> None:
        """Signal the scheduler to stop gracefully."""
        if self._scheduler:
            self._scheduler.stop()

    def run_job(self, job_name: str) -> None:
        """Execute a single job immediately without starting the scheduler.

        Args:
            job_name: Name of the job to run.

        Raises:
            ValueError: If the job name is not found.
        """
        if not self._config:
            self._setup()
        self._scheduler.run_now(job_name)

    def status(self) -> Dict:
        """Return current pipeline status.

        Returns:
            Dict with pipeline state and per-job information.
        """
        if not self._config:
            self._setup()

        jobs_status = self._scheduler.list_jobs()

        for info in jobs_status:
            latest = self._result_store.get_latest(info["name"])
            if latest:
                info["last_run"] = latest.finished_at.isoformat()
                info["last_status"] = latest.status
                info["last_signal"] = latest.signal
                info["last_duration"] = latest.duration_seconds
            else:
                info["last_run"] = None
                info["last_status"] = None
                info["last_signal"] = None
                info["last_duration"] = None

        return {
            "config_path": self.config_path,
            "results_dir": self._config.results_dir,
            "total_jobs": len(self._config.jobs),
            "enabled_jobs": sum(
                1 for j in self._config.jobs if j.schedule.enabled
            ),
            "jobs": jobs_status,
        }

    def list_jobs(self) -> List[Dict]:
        """List all configured jobs with their schedule info.

        Returns:
            List of job info dicts.
        """
        if not self._config:
            self._setup()
        return self._scheduler.list_jobs()
