"""Tests for pipeline scheduler."""

import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.pipeline.scheduler import PipelineScheduler
from tradingagents.pipeline.models import (
    JobConfig,
    PipelineConfig,
    ScheduleConfig,
)
from tradingagents.pipeline.job_runner import JobRunner
from tradingagents.pipeline.notifier import Notifier
from tradingagents.pipeline.result_store import ResultStore


def _make_scheduler(jobs=None):
    """Create a PipelineScheduler with mocked dependencies."""
    if jobs is None:
        jobs = [
            JobConfig(
                name="test_job",
                job_type="single_analysis",
                schedule=ScheduleConfig(
                    cron_expression="0 9 * * 1-5",
                    enabled=True,
                ),
            ),
        ]
    config = PipelineConfig(jobs=jobs)
    store = ResultStore(tempfile.mkdtemp())
    notifier = Notifier()
    runner = JobRunner(store, notifier)
    return PipelineScheduler(config, runner)


class TestListJobs:
    def test_list_returns_all_jobs(self):
        scheduler = _make_scheduler()
        jobs = scheduler.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["name"] == "test_job"
        assert jobs[0]["enabled"] is True
        assert jobs[0]["cron"] == "0 9 * * 1-5"

    def test_list_multiple_jobs(self):
        jobs = [
            JobConfig(name="a", job_type="single_analysis"),
            JobConfig(name="b", job_type="portfolio",
                      schedule=ScheduleConfig(enabled=False)),
        ]
        scheduler = _make_scheduler(jobs)
        result = scheduler.list_jobs()
        assert len(result) == 2
        names = {j["name"] for j in result}
        assert names == {"a", "b"}


class TestRunNow:
    def test_run_now_unknown_job_raises(self):
        scheduler = _make_scheduler()
        with pytest.raises(ValueError, match="not found"):
            scheduler.run_now("nonexistent_job")


class TestNextRun:
    def test_next_run_without_scheduler(self):
        scheduler = _make_scheduler()
        assert scheduler.next_run("test_job") is None


class TestSchedulerStartStop:
    def test_stop_unblocks_start(self):
        scheduler = _make_scheduler()

        started = threading.Event()

        def run_scheduler():
            started.set()
            scheduler.start()

        t = threading.Thread(target=run_scheduler, daemon=True)
        t.start()
        started.wait(timeout=5)
        time.sleep(0.5)

        scheduler.stop()
        t.join(timeout=5)
        assert not t.is_alive()
