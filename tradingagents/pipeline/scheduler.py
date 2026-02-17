"""PipelineScheduler — wraps APScheduler for cron-based job execution."""

import logging
import signal
import threading
from datetime import datetime
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .models import JobConfig, PipelineConfig
from .job_runner import JobRunner

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Manages scheduled execution of pipeline jobs via APScheduler.

    Uses ``BackgroundScheduler`` with ``CronTrigger`` for each enabled job.
    Supports immediate one-off execution via ``run_now()``.

    Args:
        config: Pipeline configuration with job definitions.
        runner: JobRunner instance for executing jobs.
    """

    def __init__(self, config: PipelineConfig, runner: JobRunner):
        self.config = config
        self.runner = runner
        self._scheduler: Optional[BackgroundScheduler] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the scheduler and block until stopped.

        Registers all enabled jobs and installs signal handlers for
        graceful shutdown (SIGINT, SIGTERM).
        """
        self._scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": self.config.max_concurrent_jobs,
                "misfire_grace_time": 3600,
            }
        )

        enabled_count = 0
        for job_config in self.config.jobs:
            if not job_config.schedule.enabled:
                logger.info("Job '%s' is disabled — skipping", job_config.name)
                continue

            self._add_job(job_config)
            enabled_count += 1

        if enabled_count == 0:
            logger.warning("No enabled jobs found — scheduler will idle")

        self._install_signal_handlers()
        self._scheduler.start()

        logger.info(
            "Pipeline scheduler started with %d jobs. Press Ctrl+C to stop.",
            enabled_count,
        )

        self._stop_event.wait()

        logger.info("Scheduler stop requested — shutting down...")
        self._scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped.")

    def stop(self) -> None:
        """Signal the scheduler to stop gracefully."""
        self._stop_event.set()

    def run_now(self, job_name: str) -> None:
        """Execute a job immediately (bypasses schedule).

        Args:
            job_name: Name of the job to execute.

        Raises:
            ValueError: If the job name is not found.
        """
        job_config = self.config.get_job(job_name)
        if not job_config:
            raise ValueError(
                f"Job '{job_name}' not found. "
                f"Available: {[j.name for j in self.config.jobs]}"
            )

        logger.info("Running job '%s' immediately...", job_name)
        self.runner.execute(job_config)

    def list_jobs(self) -> List[Dict]:
        """Return status information for all configured jobs.

        Returns:
            List of dicts with job name, type, enabled status, cron, and
            next run time.
        """
        result = []
        for job_config in self.config.jobs:
            info = {
                "name": job_config.name,
                "job_type": job_config.job_type,
                "enabled": job_config.schedule.enabled,
                "cron": job_config.schedule.cron_expression,
                "timezone": job_config.schedule.timezone,
                "tickers": job_config.tickers,
            }

            if self._scheduler:
                apjob = self._scheduler.get_job(job_config.name)
                nrt = getattr(apjob, "next_run_time", None) if apjob else None
                if nrt:
                    info["next_run"] = nrt.isoformat()
                else:
                    info["next_run"] = None
            else:
                info["next_run"] = None

            result.append(info)
        return result

    def next_run(self, job_name: str) -> Optional[datetime]:
        """Return the next scheduled run time for a job.

        Args:
            job_name: Name of the pipeline job.

        Returns:
            Next run datetime, or None if not scheduled.
        """
        if not self._scheduler:
            return None
        apjob = self._scheduler.get_job(job_name)
        if apjob:
            return getattr(apjob, "next_run_time", None)
        return None

    def _add_job(self, job_config: JobConfig) -> None:
        """Register a single job with the APScheduler."""
        cron_parts = job_config.schedule.cron_expression.split()
        if len(cron_parts) != 5:
            logger.error(
                "Invalid cron expression for '%s': '%s' (expected 5 fields)",
                job_config.name, job_config.schedule.cron_expression,
            )
            return

        trigger = CronTrigger(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4],
            timezone=job_config.schedule.timezone,
        )

        self._scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            args=[job_config],
            id=job_config.name,
            name=job_config.name,
            replace_existing=True,
        )

        next_time = self.next_run(job_config.name)
        next_str = next_time.isoformat() if next_time else "unknown"
        logger.info(
            "Scheduled job '%s' [%s] cron='%s' tz=%s (next: %s)",
            job_config.name,
            job_config.job_type,
            job_config.schedule.cron_expression,
            job_config.schedule.timezone,
            next_str,
        )

    def _execute_job(self, job_config: JobConfig) -> None:
        """Callback for APScheduler — runs a job via the runner."""
        try:
            self.runner.execute(job_config)
        except Exception as e:
            logger.error(
                "Unhandled error in job '%s': %s",
                job_config.name, e,
            )

    def _install_signal_handlers(self) -> None:
        """Install SIGINT/SIGTERM handlers for graceful shutdown."""
        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Received %s — stopping scheduler...", sig_name)
            self.stop()

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except (OSError, ValueError):
            logger.debug("Could not install signal handlers (not main thread?)")
