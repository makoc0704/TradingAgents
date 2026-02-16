"""Tests for tradingagents.portfolio.universe."""

import pytest
from tradingagents.portfolio.universe import resolve_universe, UNIVERSE_PRESETS


class TestResolveUniverse:
    def test_preset_magnificent_7(self):
        tickers = resolve_universe("magnificent_7")
        assert len(tickers) == 7
        assert "AAPL" in tickers
        assert "NVDA" in tickers

    def test_preset_case_insensitive(self):
        tickers = resolve_universe("Magnificent_7")
        assert len(tickers) == 7

    def test_custom_list(self):
        tickers = resolve_universe(["aapl", "nvda", "msft"])
        assert tickers == ["AAPL", "NVDA", "MSFT"]

    def test_deduplication(self):
        tickers = resolve_universe(["AAPL", "aapl", "NVDA"])
        assert len(tickers) == 2

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown universe preset"):
            resolve_universe("nonexistent_preset")

    def test_all_presets_are_nonempty(self):
        for name, tickers in UNIVERSE_PRESETS.items():
            assert len(tickers) > 0, f"Preset '{name}' is empty"
