# TradingAgents/graph/signal_processing.py

import logging
import re
from typing import Optional, Union

from langchain_openai import ChatOpenAI

from tradingagents.risk.models import RiskMetrics, PositionSize, TradeSignal
from tradingagents.risk import RiskCalculator

logger = logging.getLogger(__name__)

# Mapping for confidence text to float
_CONFIDENCE_MAP = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.3}


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        risk_calculator: Optional[RiskCalculator] = None,
    ):
        """Initialize with an LLM for processing.

        Args:
            quick_thinking_llm: Fast LLM for signal extraction.
            risk_calculator: Optional RiskCalculator for position sizing.
        """
        self.quick_thinking_llm = quick_thinking_llm
        self.risk_calculator = risk_calculator

    def process_signal(
        self,
        full_signal: str,
        risk_metrics_dict: Optional[dict] = None,
    ) -> Union[TradeSignal, str]:
        """Process a full trading signal to extract the core decision.

        Args:
            full_signal: Complete trading signal text from the Risk Judge.
            risk_metrics_dict: Optional risk metrics dict from state.

        Returns:
            TradeSignal if risk metrics are available, otherwise a plain string
            (BUY, SELL, or HOLD) for backward compatibility.
        """
        messages = [
            (
                "system",
                "You are an efficient assistant designed to analyze paragraphs or financial reports provided by a group of analysts. "
                "Your task is to extract the investment decision and metadata. "
                "Output EXACTLY in this format (one per line, nothing else):\n"
                "ACTION: BUY or SELL or HOLD\n"
                "CONFIDENCE: HIGH or MEDIUM or LOW\n"
                "ALLOCATION: a number between 0 and 25",
            ),
            ("human", full_signal),
        ]

        raw = self.quick_thinking_llm.invoke(messages).content.strip()

        # Parse structured output
        action = self._extract_field(raw, "ACTION", default="HOLD")
        confidence_str = self._extract_field(raw, "CONFIDENCE", default="MEDIUM")
        allocation_str = self._extract_field(raw, "ALLOCATION", default="10")

        confidence = _CONFIDENCE_MAP.get(confidence_str.upper(), 0.5)

        try:
            allocation = float(allocation_str) / 100.0
        except ValueError:
            allocation = 0.10

        # Build RiskMetrics object if available
        risk_metrics = None
        if risk_metrics_dict and isinstance(risk_metrics_dict, dict) and "ticker" in risk_metrics_dict:
            try:
                risk_metrics = RiskMetrics(**risk_metrics_dict)
            except (TypeError, KeyError):
                pass

        # Calculate position size if we have metrics + calculator
        position_size = None
        if risk_metrics and self.risk_calculator:
            position_size = self.risk_calculator.calculate_position_size(risk_metrics)
        elif risk_metrics:
            position_size = PositionSize(
                method="llm_suggested",
                fraction=min(allocation, 0.25),
                max_loss_percent=0.0,
                stop_loss_price=0.0,
            )

        # If no risk data at all, fall back to simple string for backward compat
        if risk_metrics is None and position_size is None:
            return action

        return TradeSignal(
            action=action,
            confidence=confidence,
            position_size=position_size,
            risk_metrics=risk_metrics,
            reasoning=full_signal,
        )

    @staticmethod
    def _extract_field(text: str, field: str, default: str = "") -> str:
        """Extract a field value from structured LLM output."""
        pattern = rf"{field}\s*:\s*\**\s*(\w+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default
