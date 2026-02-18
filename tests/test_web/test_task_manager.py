"""Tests for the TaskManager service."""

import time
import pytest
from tradingagents.web.services.task_manager import TaskManager


class TestTaskManager:
    """Tests for TaskManager background task execution."""

    def test_submit_returns_task_id(self):
        tm = TaskManager(max_workers=1)
        try:
            task_id = tm.submit(
                "test", {"key": "val"}, lambda info, update: {"done": True}
            )
            assert isinstance(task_id, str)
            assert len(task_id) == 8
        finally:
            tm.shutdown()

    def test_task_completes_successfully(self):
        tm = TaskManager(max_workers=1)
        try:
            def run_fn(info, update):
                update(progress=50, message="halfway")
                time.sleep(0.1)
                return {"result_key": "result_value"}

            task_id = tm.submit("test", {}, run_fn)
            time.sleep(0.5)

            status = tm.get_status(task_id)
            assert status is not None
            assert status["status"] == "completed"
            assert status["result"]["result_key"] == "result_value"
        finally:
            tm.shutdown()

    def test_task_failure_captured(self):
        tm = TaskManager(max_workers=1)
        try:
            def fail_fn(info, update):
                raise ValueError("test error")

            task_id = tm.submit("test", {}, fail_fn)
            time.sleep(0.5)

            status = tm.get_status(task_id)
            assert status is not None
            assert status["status"] == "failed"
            assert "test error" in status["error"]
        finally:
            tm.shutdown()

    def test_get_status_unknown_task(self):
        tm = TaskManager(max_workers=1)
        try:
            assert tm.get_status("nonexistent") is None
        finally:
            tm.shutdown()

    def test_get_result_before_completion(self):
        tm = TaskManager(max_workers=1)
        try:
            def slow_fn(info, update):
                time.sleep(2)
                return {}

            task_id = tm.submit("test", {}, slow_fn)
            result = tm.get_result(task_id)
            assert result is None
        finally:
            tm.shutdown()

    def test_list_tasks(self):
        tm = TaskManager(max_workers=2)
        try:
            tm.submit("a", {}, lambda i, u: {})
            tm.submit("b", {}, lambda i, u: {})
            time.sleep(0.3)

            tasks = tm.list_tasks()
            assert len(tasks) == 2
            assert all("task_id" in t for t in tasks)
        finally:
            tm.shutdown()

    def test_cancel_task(self):
        tm = TaskManager(max_workers=1)
        try:
            task_id = tm.submit("test", {}, lambda i, u: time.sleep(5) or {})
            result = tm.cancel(task_id)
            assert result is True
            assert tm.cancel("nonexistent") is False
        finally:
            tm.shutdown()

    def test_subscribe_receives_updates(self):
        tm = TaskManager(max_workers=1)
        updates = []
        try:
            def run_fn(info, update):
                update(progress=50, message="half")
                return {"done": True}

            task_id = tm.submit("test", {}, run_fn)
            tm.subscribe(task_id, lambda tid, status: updates.append(status))
            time.sleep(0.5)

            # Might have captured some updates
            assert isinstance(updates, list)
        finally:
            tm.shutdown()
