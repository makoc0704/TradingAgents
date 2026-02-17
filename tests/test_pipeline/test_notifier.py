"""Tests for pipeline notifier."""

from datetime import datetime
from unittest.mock import patch, MagicMock

from tradingagents.pipeline.notifier import Notifier
from tradingagents.pipeline.models import JobResult, NotificationConfig


def _make_result(status="success", signal="BUY") -> JobResult:
    return JobResult(
        job_name="test_job",
        job_type="single_analysis",
        started_at=datetime(2024, 6, 3, 9, 0, 0),
        finished_at=datetime(2024, 6, 3, 9, 5, 0),
        status=status,
        duration_seconds=300.0,
        signal=signal,
    )


class TestNotifierShouldNotify:
    def test_success_trigger(self):
        n = Notifier()
        cfg = NotificationConfig(enabled=True, notify_on=["success"])
        assert n._should_notify(_make_result("success"), cfg, False) is True

    def test_failure_trigger(self):
        n = Notifier()
        cfg = NotificationConfig(enabled=True, notify_on=["failure"])
        assert n._should_notify(_make_result("failure"), cfg, False) is True

    def test_signal_change_trigger(self):
        n = Notifier()
        cfg = NotificationConfig(enabled=True, notify_on=["signal_change"])
        assert n._should_notify(_make_result(), cfg, signal_changed=True) is True
        assert n._should_notify(_make_result(), cfg, signal_changed=False) is False

    def test_no_matching_trigger(self):
        n = Notifier()
        cfg = NotificationConfig(enabled=True, notify_on=["failure"])
        assert n._should_notify(_make_result("success"), cfg, False) is False


class TestNotifierLog:
    def test_log_success(self, caplog):
        n = Notifier()
        import logging
        with caplog.at_level(logging.INFO):
            n._log_result(_make_result("success", "BUY"))
        assert "test_job" in caplog.text
        assert "success" in caplog.text

    def test_log_failure(self, caplog):
        n = Notifier()
        result = _make_result("failure")
        result.error = "Connection timeout"
        import logging
        with caplog.at_level(logging.WARNING):
            n._log_result(result)
        assert "FAILED" in caplog.text
        assert "Connection timeout" in caplog.text


class TestNotifierWebhook:
    @patch("tradingagents.pipeline.notifier.requests.post")
    def test_webhook_sends_post(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        n = Notifier()
        cfg = NotificationConfig(
            enabled=True,
            channels=["webhook"],
            webhook_url="https://hooks.example.com/test",
            notify_on=["success"],
        )
        result = _make_result()
        n.notify(result, config=cfg)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.example.com/test"
        payload = call_args[1]["json"]
        assert payload["job_name"] == "test_job"
        assert payload["status"] == "success"

    @patch("tradingagents.pipeline.notifier.requests.post")
    def test_webhook_failure_does_not_crash(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.RequestException("Connection refused")

        n = Notifier()
        cfg = NotificationConfig(
            enabled=True,
            channels=["webhook"],
            webhook_url="https://broken.example.com",
            notify_on=["success"],
        )
        # Should not raise
        n.notify(_make_result(), config=cfg)

    def test_webhook_missing_url_logs_warning(self, caplog):
        import logging
        n = Notifier()
        cfg = NotificationConfig(
            enabled=True,
            channels=["webhook"],
            webhook_url=None,
            notify_on=["success"],
        )
        with caplog.at_level(logging.WARNING):
            n.notify(_make_result(), config=cfg)
        assert "not configured" in caplog.text


class TestNotifierDisabled:
    def test_disabled_only_logs(self, caplog):
        import logging
        n = Notifier()
        cfg = NotificationConfig(enabled=False)
        with caplog.at_level(logging.INFO):
            n.notify(_make_result(), config=cfg)
        assert "test_job" in caplog.text


class TestBuildPayload:
    def test_payload_structure(self):
        n = Notifier()
        result = _make_result("success", "BUY")
        payload = n._build_payload(result, signal_changed=True)
        assert payload["job_name"] == "test_job"
        assert payload["signal"] == "BUY"
        assert payload["signal_changed"] is True

    def test_payload_without_signal(self):
        n = Notifier()
        result = _make_result("success")
        result.signal = None
        payload = n._build_payload(result, signal_changed=False)
        assert "signal" not in payload
        assert "signal_changed" not in payload
