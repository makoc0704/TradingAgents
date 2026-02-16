"""Tests for tradingagents.risk.models — data model integrity."""

import pytest

from tradingagents.risk.models import RiskMetrics, PositionSize, TradeSignal


@pytest.fixture
def sample_risk_metrics():
    return RiskMetrics(
        ticker="AAPL",
        date="2024-06-15",
        daily_volatility=0.018,
        annualized_volatility=0.286,
        atr=3.25,
        atr_percent=0.0175,
        max_drawdown=-0.12,
        current_drawdown=-0.03,
        var_95=-0.028,
        var_99=-0.042,
        cvar_95=-0.035,
        beta=1.15,
        sharpe_ratio=1.42,
        sortino_ratio=1.85,
        current_price=185.50,
        sma_50=180.25,
        sma_200=170.10,
        rsi=62.5,
    )


class TestRiskMetrics:
    def test_to_dict(self, sample_risk_metrics):
        d = sample_risk_metrics.to_dict()
        assert isinstance(d, dict)
        assert d["ticker"] == "AAPL"
        assert d["daily_volatility"] == 0.018
        assert d["sharpe_ratio"] == 1.42

    def test_roundtrip(self, sample_risk_metrics):
        """to_dict -> reconstruct via **kwargs should produce equal object."""
        d = sample_risk_metrics.to_dict()
        reconstructed = RiskMetrics(**d)
        assert reconstructed == sample_risk_metrics

    def test_format_for_prompt_contains_key_data(self, sample_risk_metrics):
        text = sample_risk_metrics.format_for_prompt()
        assert "AAPL" in text
        assert "Quantitative Risk Assessment" in text
        assert "VaR 95%" in text
        assert "Sharpe Ratio" in text
        assert "BULLISH" in text  # SMA 50 > SMA 200

    def test_bearish_trend(self):
        rm = RiskMetrics(
            ticker="TEST", date="2024-01-01",
            daily_volatility=0.02, annualized_volatility=0.32,
            atr=2.0, atr_percent=0.02,
            max_drawdown=-0.20, current_drawdown=-0.10,
            var_95=-0.03, var_99=-0.05, cvar_95=-0.04,
            beta=1.0, sharpe_ratio=0.5, sortino_ratio=0.6,
            current_price=100.0, sma_50=95.0, sma_200=105.0,
            rsi=35.0,
        )
        text = rm.format_for_prompt()
        assert "BEARISH" in text

    def test_rsi_zones(self):
        for rsi, expected in [(75, "OVERBOUGHT"), (25, "OVERSOLD"), (50, "NEUTRAL")]:
            rm = RiskMetrics(
                ticker="T", date="2024-01-01",
                daily_volatility=0.01, annualized_volatility=0.16,
                atr=1.0, atr_percent=0.01,
                max_drawdown=-0.05, current_drawdown=0.0,
                var_95=-0.02, var_99=-0.03, cvar_95=-0.025,
                beta=1.0, sharpe_ratio=1.0, sortino_ratio=1.2,
                current_price=100.0, sma_50=100.0, sma_200=100.0,
                rsi=rsi,
            )
            assert expected in rm.format_for_prompt()


class TestTradeSignal:
    def test_str_returns_action(self):
        signal = TradeSignal(
            action="BUY",
            confidence=0.8,
            position_size=None,
            risk_metrics=None,
            reasoning="Test",
        )
        assert str(signal) == "BUY"

    def test_to_dict(self, sample_risk_metrics):
        ps = PositionSize(method="vol", fraction=0.15, max_loss_percent=0.04, stop_loss_price=178.0)
        signal = TradeSignal(
            action="BUY",
            confidence=0.85,
            position_size=ps,
            risk_metrics=sample_risk_metrics,
            reasoning="Strong fundamentals",
        )
        d = signal.to_dict()
        assert d["action"] == "BUY"
        assert d["confidence"] == 0.85
        assert d["position_size"]["method"] == "vol"
        assert d["risk_metrics"]["ticker"] == "AAPL"

    def test_backward_compat_with_hold(self):
        """TradeSignal with HOLD action should work in old if-checks."""
        signal = TradeSignal(
            action="HOLD",
            confidence=0.5,
            position_size=None,
            risk_metrics=None,
            reasoning="Uncertain",
        )
        # Old code might do: if decision == "HOLD"
        assert str(signal) == "HOLD"
