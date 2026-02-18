"""Tests for web configuration."""

import os
import pytest
from tradingagents.web.config import WebConfig


class TestWebConfig:
    """Tests for WebConfig dataclass."""

    def test_defaults(self):
        config = WebConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.dev_mode is False
        assert config.max_concurrent_tasks == 2
        assert config.task_ttl_seconds == 3600

    def test_custom_values(self):
        config = WebConfig(host="0.0.0.0", port=9000, dev_mode=True)
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.dev_mode is True

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("WEB_HOST", "0.0.0.0")
        monkeypatch.setenv("WEB_PORT", "9090")
        monkeypatch.setenv("WEB_DEV_MODE", "true")

        config = WebConfig.from_env()
        assert config.host == "0.0.0.0"
        assert config.port == 9090
        assert config.dev_mode is True

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("WEB_HOST", raising=False)
        monkeypatch.delenv("WEB_PORT", raising=False)
        monkeypatch.delenv("WEB_DEV_MODE", raising=False)

        config = WebConfig.from_env()
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.dev_mode is False
