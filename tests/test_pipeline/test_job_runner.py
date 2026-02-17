"""Tests for pipeline job runner."""

import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

from tradingagents.pipeline.job_runner import JobRunner
from tradingagents.pipeline.models import JobConfig, JobResult, ScheduleConfig
from tradingagents.pipeline.notifier import Notifier
from tradingagents.pipeline.result_store import ResultStore


def _make_success_result(name="test", signal="BUY"):
    now = datetime.now()
    return JobResult(
        job_name=name,
        job_type="single_analysis",
        started_at=now,
        finished_at=now,
        status="success",
        duration_seconds=1.0,
        signal=signal,
    )


class TestJobRunnerDateResolution:
    def setup_method(self):
        self.store = ResultStore(tempfile.mkdtemp())
        self.notifier = Notifier()
        self.runner = JobRunner(self.store, self.notifier)

    def test_resolve_today(self):
        result = self.runner._resolve_date("today")
        expected = datetime.now().strftime("%Y-%m-%d")
        assert result == expected

    def test_resolve_yesterday(self):
        from datetime import timedelta
        result = self.runner._resolve_date("yesterday")
        expected = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert result == expected

    def test_resolve_explicit_date(self):
        result = self.runner._resolve_date("2024-06-03")
        assert result == "2024-06-03"


class TestJobRunnerRetry:
    def setup_method(self):
        self.store = ResultStore(tempfile.mkdtemp())
        self.notifier = Notifier()
        self.runner = JobRunner(self.store, self.notifier)

    @patch.object(JobRunner, "_run_job")
    def test_success_on_first_attempt(self, mock_run):
        mock_run.return_value = _make_success_result()

        job = JobConfig(
            name="test",
            job_type="single_analysis",
            schedule=ScheduleConfig(max_retries=3, retry_delay_seconds=0),
        )
        result = self.runner.execute(job)
        assert mock_run.call_count == 1
        assert result.status == "success"

    @patch.object(JobRunner, "_run_job")
    def test_retries_on_failure(self, mock_run):
        mock_run.side_effect = [
            RuntimeError("Fail 1"),
            RuntimeError("Fail 2"),
            RuntimeError("Fail 3"),
        ]

        job = JobConfig(
            name="failing",
            job_type="single_analysis",
            schedule=ScheduleConfig(
                max_retries=3, retry_delay_seconds=0,
            ),
        )
        result = self.runner.execute(job)
        assert mock_run.call_count == 3
        assert result.status == "failure"
        assert "Fail 3" in result.error

    @patch.object(JobRunner, "_run_job")
    def test_succeeds_after_retry(self, mock_run):
        mock_run.side_effect = [
            RuntimeError("Fail"),
            _make_success_result(signal="HOLD"),
        ]

        job = JobConfig(
            name="test",
            job_type="single_analysis",
            schedule=ScheduleConfig(
                max_retries=3, retry_delay_seconds=0,
            ),
        )
        result = self.runner.execute(job)
        assert mock_run.call_count == 2
        assert result.status == "success"


class TestJobRunnerUnknownType:
    def setup_method(self):
        self.store = ResultStore(tempfile.mkdtemp())
        self.notifier = Notifier()
        self.runner = JobRunner(self.store, self.notifier)

    def test_unknown_job_type_fails(self):
        job = JobConfig(
            name="bad",
            job_type="single_analysis",
            schedule=ScheduleConfig(max_retries=1, retry_delay_seconds=0),
        )
        # Monkey-patch job_type after creation to bypass validation
        job.job_type = "unknown_type"
        result = self.runner.execute(job)
        assert result.status == "failure"
        assert "unknown_type" in result.error
