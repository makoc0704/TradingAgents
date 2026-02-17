"""Data models for the automated pipeline."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class ScheduleConfig:
    """Schedule configuration for a pipeline job.

    Attributes:
        cron_expression: Cron expression, e.g. "0 9 * * 1-5" (weekdays 09:00).
        timezone: Timezone name, e.g. "Europe/Berlin".
        enabled: Whether the job is active.
        max_retries: Max retry attempts on failure.
        retry_delay_seconds: Delay between retries in seconds.
    """

    cron_expression: str = "0 9 * * 1-5"
    timezone: str = "UTC"
    enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 300


@dataclass
class NotificationConfig:
    """Notification configuration for a pipeline job.

    Attributes:
        enabled: Whether notifications are active.
        channels: List of channels — "webhook", "email", "log".
        webhook_url: URL for webhook notifications (Discord/Slack/Custom).
        email_to: Recipient email address.
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port.
        notify_on: Trigger conditions — "success", "failure", "signal_change".
    """

    enabled: bool = False
    channels: List[str] = field(default_factory=lambda: ["log"])
    webhook_url: Optional[str] = None
    email_to: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    notify_on: List[str] = field(
        default_factory=lambda: ["success", "failure"]
    )


@dataclass
class JobConfig:
    """Configuration for a single pipeline job.

    Attributes:
        name: Unique job identifier.
        job_type: Type — "single_analysis", "backtest", or "portfolio".
        schedule: Schedule configuration.
        notification: Notification configuration.
        tickers: Ticker symbols or universe preset name.
        analysis_date: Date string — "today", "yesterday", or "YYYY-MM-DD".
        config: Extra config merged with DEFAULT_CONFIG.
    """

    name: str
    job_type: str
    tickers: List[str] = field(default_factory=lambda: ["NVDA"])
    analysis_date: str = "today"
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to plain dict."""
        return asdict(self)


@dataclass
class JobResult:
    """Result of a single pipeline job execution.

    Attributes:
        job_name: Name of the job that was executed.
        job_type: Type of the job.
        started_at: When execution started.
        finished_at: When execution finished.
        status: Outcome — "success", "failure", or "partial".
        duration_seconds: How long the job took.
        signal: Trade signal for single_analysis jobs.
        performance: Performance dict for backtest/portfolio jobs.
        error: Error message on failure.
        result_path: Path to the saved JSON result.
    """

    job_name: str
    job_type: str
    started_at: datetime
    finished_at: datetime
    status: str
    duration_seconds: float
    signal: Optional[str] = None
    performance: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    result_path: str = ""

    def to_dict(self) -> dict:
        """Serialize to plain dict with ISO timestamps."""
        d = asdict(self)
        d["started_at"] = self.started_at.isoformat()
        d["finished_at"] = self.finished_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "JobResult":
        """Deserialize from plain dict."""
        data = data.copy()
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        data["finished_at"] = datetime.fromisoformat(data["finished_at"])
        return cls(**data)


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration.

    Attributes:
        jobs: List of job configurations.
        results_dir: Base directory for pipeline results.
        log_level: Logging level — "DEBUG", "INFO", "WARNING".
        max_concurrent_jobs: Max parallel jobs (1 = sequential).
    """

    jobs: List[JobConfig] = field(default_factory=list)
    results_dir: str = "./results/pipeline"
    log_level: str = "INFO"
    max_concurrent_jobs: int = 1

    def get_job(self, name: str) -> Optional[JobConfig]:
        """Find a job config by name."""
        for job in self.jobs:
            if job.name == name:
                return job
        return None
