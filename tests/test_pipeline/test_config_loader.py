"""Tests for pipeline config loader."""

import os
import tempfile

import pytest

from tradingagents.pipeline.config_loader import (
    load_pipeline_config,
    _substitute_env_vars,
)


class TestEnvVarSubstitution:
    def test_simple_substitution(self, monkeypatch):
        monkeypatch.setenv("MY_URL", "https://hooks.example.com")
        result = _substitute_env_vars("${MY_URL}")
        assert result == "https://hooks.example.com"

    def test_nested_dict(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "secret123")
        data = {"url": "${API_KEY}", "nested": {"key": "${API_KEY}"}}
        result = _substitute_env_vars(data)
        assert result["url"] == "secret123"
        assert result["nested"]["key"] == "secret123"

    def test_list_substitution(self, monkeypatch):
        monkeypatch.setenv("TICKER", "NVDA")
        result = _substitute_env_vars(["${TICKER}", "AAPL"])
        assert result == ["NVDA", "AAPL"]

    def test_missing_var_returns_empty(self, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR_12345", raising=False)
        result = _substitute_env_vars("${NONEXISTENT_VAR_12345}")
        assert result == ""

    def test_no_substitution_for_non_strings(self):
        assert _substitute_env_vars(42) == 42
        assert _substitute_env_vars(True) is True
        assert _substitute_env_vars(None) is None


class TestLoadPipelineConfig:
    def _write_yaml(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        f.write(content)
        f.close()
        return f.name

    def test_valid_config(self):
        path = self._write_yaml("""
results_dir: "./test_results"
log_level: "DEBUG"
max_concurrent_jobs: 2

jobs:
  - name: "test_job"
    job_type: "single_analysis"
    tickers: ["NVDA"]
    analysis_date: "today"
    schedule:
      cron_expression: "0 9 * * 1-5"
      timezone: "Europe/Berlin"
      enabled: true
      max_retries: 2
      retry_delay_seconds: 60
    notification:
      enabled: false
      channels: ["log"]
    config:
      llm_provider: "openai"
""")
        try:
            cfg = load_pipeline_config(path)
            assert cfg.results_dir == "./test_results"
            assert cfg.log_level == "DEBUG"
            assert len(cfg.jobs) == 1
            assert cfg.jobs[0].name == "test_job"
            assert cfg.jobs[0].job_type == "single_analysis"
            assert cfg.jobs[0].schedule.timezone == "Europe/Berlin"
        finally:
            os.unlink(path)

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_pipeline_config("/nonexistent/path.yaml")

    def test_invalid_job_type(self):
        path = self._write_yaml("""
jobs:
  - name: "bad_job"
    job_type: "invalid_type"
    tickers: ["AAPL"]
""")
        try:
            with pytest.raises(ValueError, match="invalid_type"):
                load_pipeline_config(path)
        finally:
            os.unlink(path)

    def test_missing_job_name(self):
        path = self._write_yaml("""
jobs:
  - job_type: "single_analysis"
    tickers: ["AAPL"]
""")
        try:
            with pytest.raises(ValueError, match="name"):
                load_pipeline_config(path)
        finally:
            os.unlink(path)

    def test_duplicate_job_names(self):
        path = self._write_yaml("""
jobs:
  - name: "dup"
    job_type: "single_analysis"
    tickers: ["AAPL"]
  - name: "dup"
    job_type: "backtest"
    tickers: ["NVDA"]
""")
        try:
            with pytest.raises(ValueError, match="Duplicate"):
                load_pipeline_config(path)
        finally:
            os.unlink(path)

    def test_empty_tickers(self):
        path = self._write_yaml("""
jobs:
  - name: "empty_tickers"
    job_type: "single_analysis"
    tickers: []
""")
        try:
            with pytest.raises(ValueError, match="non-empty"):
                load_pipeline_config(path)
        finally:
            os.unlink(path)

    def test_env_var_in_config(self, monkeypatch):
        monkeypatch.setenv("TEST_WEBHOOK", "https://hook.test.com")
        path = self._write_yaml("""
jobs:
  - name: "env_test"
    job_type: "single_analysis"
    tickers: ["SPY"]
    notification:
      enabled: true
      channels: ["webhook"]
      webhook_url: "${TEST_WEBHOOK}"
""")
        try:
            cfg = load_pipeline_config(path)
            assert cfg.jobs[0].notification.webhook_url == "https://hook.test.com"
        finally:
            os.unlink(path)
