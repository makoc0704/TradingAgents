"""Tests for pipeline data models."""

from datetime import datetime

from tradingagents.pipeline.models import (
    JobConfig,
    JobResult,
    NotificationConfig,
    PipelineConfig,
    ScheduleConfig,
)


class TestScheduleConfig:
    def test_defaults(self):
        cfg = ScheduleConfig()
        assert cfg.cron_expression == "0 9 * * 1-5"
        assert cfg.timezone == "UTC"
        assert cfg.enabled is True
        assert cfg.max_retries == 3
        assert cfg.retry_delay_seconds == 300


class TestNotificationConfig:
    def test_defaults(self):
        cfg = NotificationConfig()
        assert cfg.enabled is False
        assert cfg.channels == ["log"]
        assert cfg.webhook_url is None

    def test_custom_channels(self):
        cfg = NotificationConfig(
            enabled=True,
            channels=["webhook", "email"],
            webhook_url="https://example.com/hook",
            email_to="test@example.com",
        )
        assert "webhook" in cfg.channels
        assert cfg.webhook_url == "https://example.com/hook"


class TestJobConfig:
    def test_defaults(self):
        cfg = JobConfig(name="test", job_type="single_analysis")
        assert cfg.name == "test"
        assert cfg.tickers == ["NVDA"]
        assert cfg.analysis_date == "today"
        assert isinstance(cfg.schedule, ScheduleConfig)
        assert isinstance(cfg.notification, NotificationConfig)

    def test_to_dict(self):
        cfg = JobConfig(name="test", job_type="backtest", tickers=["AAPL"])
        d = cfg.to_dict()
        assert d["name"] == "test"
        assert d["tickers"] == ["AAPL"]


class TestJobResult:
    def test_to_dict_and_from_dict(self):
        now = datetime(2024, 6, 3, 9, 0, 0)
        later = datetime(2024, 6, 3, 9, 5, 30)
        result = JobResult(
            job_name="test_job",
            job_type="single_analysis",
            started_at=now,
            finished_at=later,
            status="success",
            duration_seconds=330.0,
            signal="BUY",
        )
        d = result.to_dict()
        assert d["started_at"] == "2024-06-03T09:00:00"
        assert d["status"] == "success"
        assert d["signal"] == "BUY"

        restored = JobResult.from_dict(d)
        assert restored.job_name == "test_job"
        assert restored.started_at == now
        assert restored.signal == "BUY"

    def test_failure_result(self):
        now = datetime.now()
        result = JobResult(
            job_name="failing",
            job_type="backtest",
            started_at=now,
            finished_at=now,
            status="failure",
            duration_seconds=1.5,
            error="Connection timeout",
        )
        assert result.status == "failure"
        assert result.error == "Connection timeout"


class TestPipelineConfig:
    def test_get_job(self):
        j1 = JobConfig(name="job_a", job_type="single_analysis")
        j2 = JobConfig(name="job_b", job_type="portfolio")
        cfg = PipelineConfig(jobs=[j1, j2])
        assert cfg.get_job("job_a") is j1
        assert cfg.get_job("job_b") is j2
        assert cfg.get_job("nonexistent") is None

    def test_defaults(self):
        cfg = PipelineConfig()
        assert cfg.results_dir == "./results/pipeline"
        assert cfg.log_level == "INFO"
        assert cfg.max_concurrent_jobs == 1
