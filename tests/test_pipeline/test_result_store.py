"""Tests for pipeline result store."""

import os
import tempfile

from datetime import datetime

from tradingagents.pipeline.result_store import ResultStore
from tradingagents.pipeline.models import JobResult


def _make_result(job_name: str = "test_job", status: str = "success",
                 signal: str = "BUY", finished: datetime = None) -> JobResult:
    finished = finished or datetime(2024, 6, 3, 9, 5, 0)
    return JobResult(
        job_name=job_name,
        job_type="single_analysis",
        started_at=datetime(2024, 6, 3, 9, 0, 0),
        finished_at=finished,
        status=status,
        duration_seconds=300.0,
        signal=signal,
    )


class TestResultStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = ResultStore(self.tmpdir)

    def test_save_creates_file(self):
        result = _make_result()
        path = self.store.save(result)
        assert os.path.isfile(path)
        assert "2024-06-03_090500.json" in path

    def test_save_creates_latest(self):
        result = _make_result()
        self.store.save(result)
        latest_path = os.path.join(self.tmpdir, "test_job", "latest.json")
        assert os.path.isfile(latest_path)

    def test_get_latest(self):
        result = _make_result(signal="SELL")
        self.store.save(result)
        loaded = self.store.get_latest("test_job")
        assert loaded is not None
        assert loaded.signal == "SELL"
        assert loaded.job_name == "test_job"

    def test_get_latest_nonexistent(self):
        assert self.store.get_latest("no_such_job") is None

    def test_get_history(self):
        r1 = _make_result(finished=datetime(2024, 6, 3, 9, 5, 0))
        r2 = _make_result(finished=datetime(2024, 6, 4, 9, 5, 0))
        self.store.save(r1)
        self.store.save(r2)

        history = self.store.get_history("test_job")
        assert len(history) == 2
        # Newest first
        assert history[0].finished_at > history[1].finished_at

    def test_get_history_limit(self):
        for day in range(1, 6):
            r = _make_result(finished=datetime(2024, 6, day, 9, 5, 0))
            self.store.save(r)

        history = self.store.get_history("test_job", limit=3)
        assert len(history) == 3

    def test_has_signal_changed_true(self):
        result = _make_result(signal="HOLD")
        self.store.save(result)
        assert self.store.has_signal_changed("test_job", "BUY") is True

    def test_has_signal_changed_false(self):
        result = _make_result(signal="BUY")
        self.store.save(result)
        assert self.store.has_signal_changed("test_job", "BUY") is False

    def test_has_signal_changed_case_insensitive(self):
        result = _make_result(signal="buy")
        self.store.save(result)
        assert self.store.has_signal_changed("test_job", "BUY") is False

    def test_has_signal_changed_no_previous(self):
        assert self.store.has_signal_changed("new_job", "BUY") is True
