"""Tests for tradingagents.backtesting.data_cache — file-based caching."""

import os
import tempfile
import pytest

from tradingagents.backtesting.data_cache import DataCache


@pytest.fixture
def cache_dir(tmp_path):
    """Temporary directory for cache files."""
    return str(tmp_path / "test_cache")


@pytest.fixture
def cache(cache_dir):
    """Enabled DataCache instance."""
    return DataCache(cache_dir, enabled=True)


class TestDataCache:
    def test_cache_miss(self, cache):
        result = cache.get("get_stock_data", ("AAPL", "2024-01-01", "2024-06-01"), {})
        assert result is None
        assert cache.stats["misses"] == 1

    def test_cache_put_and_hit(self, cache):
        method = "get_stock_data"
        args = ("AAPL", "2024-01-01", "2024-06-01")
        response = "Date,Close\n2024-01-02,185.5\n2024-01-03,186.0"

        cache.put(method, args, {}, response)
        result = cache.get(method, args, {})

        assert result == response
        assert cache.stats["hits"] == 1

    def test_different_args_different_keys(self, cache):
        cache.put("get_stock_data", ("AAPL",), {}, "data_aapl")
        cache.put("get_stock_data", ("MSFT",), {}, "data_msft")

        assert cache.get("get_stock_data", ("AAPL",), {}) == "data_aapl"
        assert cache.get("get_stock_data", ("MSFT",), {}) == "data_msft"

    def test_disabled_cache_always_misses(self, cache_dir):
        cache = DataCache(cache_dir, enabled=False)
        cache.put("test", ("a",), {}, "data")
        assert cache.get("test", ("a",), {}) is None

    def test_stats(self, cache):
        cache.get("a", (), {})
        cache.get("b", (), {})
        cache.put("a", (), {}, "data")
        cache.get("a", (), {})

        stats = cache.stats
        assert stats["misses"] == 2
        assert stats["hits"] == 1
        assert stats["total"] == 3

    def test_cache_creates_directory(self, tmp_path):
        new_dir = str(tmp_path / "nested" / "cache" / "dir")
        cache = DataCache(new_dir, enabled=True)
        assert os.path.isdir(new_dir)

    def test_cache_files_are_json(self, cache, cache_dir):
        cache.put("test_method", ("arg1",), {}, "response_data")
        files = os.listdir(cache_dir)
        assert len(files) == 1
        assert files[0].endswith(".json")
