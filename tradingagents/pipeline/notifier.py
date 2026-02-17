"""Notifier — sends webhook, email, and log notifications for pipeline jobs."""

import json
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

import requests

from .models import JobResult, NotificationConfig

logger = logging.getLogger(__name__)


class Notifier:
    """Dispatches notifications based on job results and config.

    Channels:
    - ``log``: Always active — logs result via the ``logging`` module.
    - ``webhook``: HTTP POST to a configured URL (Discord/Slack/Custom).
    - ``email``: Sends an email via SMTP.

    Notification failures never crash the pipeline — they are logged as warnings.

    Args:
        config: Default notification config (can be overridden per job).
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.default_config = config or NotificationConfig()

    def notify(
        self,
        result: JobResult,
        config: Optional[NotificationConfig] = None,
        signal_changed: bool = False,
    ) -> None:
        """Send notifications for a job result.

        Args:
            result: The job result to report.
            config: Job-specific notification config (overrides default).
            signal_changed: Whether the signal changed since the last run.
        """
        cfg = config or self.default_config

        if not cfg.enabled:
            self._log_result(result)
            return

        should_notify = self._should_notify(result, cfg, signal_changed)
        if not should_notify:
            logger.debug(
                "Skipping notification for '%s' (trigger conditions not met)",
                result.job_name,
            )
            return

        self._log_result(result)

        for channel in cfg.channels:
            if channel == "log":
                continue
            elif channel == "webhook":
                self._send_webhook(result, cfg, signal_changed)
            elif channel == "email":
                self._send_email(result, cfg, signal_changed)
            else:
                logger.warning("Unknown notification channel: '%s'", channel)

    def _should_notify(
        self,
        result: JobResult,
        cfg: NotificationConfig,
        signal_changed: bool,
    ) -> bool:
        """Check if notification should be sent based on trigger conditions."""
        triggers = cfg.notify_on

        if result.status == "success" and "success" in triggers:
            return True
        if result.status == "failure" and "failure" in triggers:
            return True
        if signal_changed and "signal_change" in triggers:
            return True
        return False

    def _log_result(self, result: JobResult) -> None:
        """Log the job result (always active)."""
        if result.status == "failure":
            logger.warning(
                "Job '%s' FAILED after %.1fs: %s",
                result.job_name, result.duration_seconds, result.error,
            )
        else:
            signal_str = f" | Signal: {result.signal}" if result.signal else ""
            perf_str = ""
            if result.performance:
                ret = result.performance.get("total_return")
                if ret is not None:
                    perf_str = f" | Return: {ret * 100:+.2f}%"

            logger.info(
                "Job '%s' completed in %.1fs [%s]%s%s",
                result.job_name, result.duration_seconds,
                result.status, signal_str, perf_str,
            )

    def _build_payload(
        self,
        result: JobResult,
        signal_changed: bool,
    ) -> dict:
        """Build a notification payload dict."""
        payload = {
            "job_name": result.job_name,
            "job_type": result.job_type,
            "status": result.status,
            "duration_seconds": round(result.duration_seconds, 1),
            "timestamp": result.finished_at.isoformat(),
        }
        if result.signal:
            payload["signal"] = result.signal
        if result.performance:
            payload["performance"] = result.performance
        if result.error:
            payload["error"] = result.error
        if signal_changed:
            payload["signal_changed"] = True
        return payload

    def _build_summary(self, result: JobResult, signal_changed: bool) -> str:
        """Build a human-readable text summary."""
        lines = [
            f"[TradingAgents] Job: {result.job_name}",
            f"Status: {result.status.upper()}",
            f"Type: {result.job_type}",
            f"Duration: {result.duration_seconds:.1f}s",
        ]
        if result.signal:
            lines.append(f"Signal: {result.signal}")
        if signal_changed:
            lines.append("*** Signal has CHANGED ***")
        if result.performance:
            ret = result.performance.get("total_return")
            if ret is not None:
                lines.append(f"Return: {ret * 100:+.2f}%")
        if result.error:
            lines.append(f"Error: {result.error}")
        return "\n".join(lines)

    def _send_webhook(
        self,
        result: JobResult,
        cfg: NotificationConfig,
        signal_changed: bool,
    ) -> None:
        """Send a webhook notification via HTTP POST."""
        if not cfg.webhook_url:
            logger.warning("Webhook URL not configured for job '%s'", result.job_name)
            return

        payload = self._build_payload(result, signal_changed)

        try:
            resp = requests.post(
                cfg.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code < 300:
                logger.info(
                    "Webhook sent for '%s' (HTTP %d)",
                    result.job_name, resp.status_code,
                )
            else:
                logger.warning(
                    "Webhook failed for '%s' (HTTP %d): %s",
                    result.job_name, resp.status_code, resp.text[:200],
                )
        except requests.RequestException as e:
            logger.warning("Webhook error for '%s': %s", result.job_name, e)

    def _send_email(
        self,
        result: JobResult,
        cfg: NotificationConfig,
        signal_changed: bool,
    ) -> None:
        """Send an email notification via SMTP."""
        if not cfg.email_to or not cfg.smtp_host:
            logger.warning(
                "Email not configured for job '%s' (need email_to + smtp_host)",
                result.job_name,
            )
            return

        subject = f"[TradingAgents] {result.job_name}: {result.status.upper()}"
        body = self._build_summary(result, signal_changed)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"tradingagents@{cfg.smtp_host}"
        msg["To"] = cfg.email_to
        msg.set_content(body)

        try:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as server:
                server.ehlo()
                if cfg.smtp_port == 587:
                    server.starttls()
                server.send_message(msg)

            logger.info("Email sent for '%s' to %s", result.job_name, cfg.email_to)
        except (smtplib.SMTPException, OSError) as e:
            logger.warning("Email error for '%s': %s", result.job_name, e)
