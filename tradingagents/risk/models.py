"""Data models for quantitative risk assessment."""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class RiskMetrics:
    """Quantitative risk metrics computed for a single ticker on a given date.

    All percentage values are expressed as decimals (e.g. 0.02 = 2%).
    """

    ticker: str
    date: str

    # Volatility
    daily_volatility: float       # Standard deviation of daily returns
    annualized_volatility: float  # daily_volatility * sqrt(252)
    atr: float                    # Average True Range (absolute dollar value)
    atr_percent: float            # ATR as fraction of current price

    # Drawdown
    max_drawdown: float           # Maximum drawdown in lookback window (negative)
    current_drawdown: float       # Current drawdown from peak (negative or zero)

    # Value at Risk
    var_95: float                 # 95% daily VaR (negative, worst-case loss)
    var_99: float                 # 99% daily VaR
    cvar_95: float                # Conditional VaR / Expected Shortfall at 95%

    # Market context
    beta: float                   # Beta relative to benchmark
    sharpe_ratio: float           # Annualized Sharpe ratio
    sortino_ratio: float          # Annualized Sortino ratio (downside only)

    # Price context
    current_price: float
    sma_50: float
    sma_200: float
    rsi: float

    def to_dict(self) -> dict:
        """Convert to plain dict for storage in AgentState."""
        return asdict(self)

    def format_for_prompt(self) -> str:
        """Format metrics as readable text for injection into LLM prompts."""
        trend = "BULLISH" if self.sma_50 > self.sma_200 else "BEARISH"
        rsi_zone = (
            "OVERBOUGHT" if self.rsi > 70
            else "OVERSOLD" if self.rsi < 30
            else "NEUTRAL"
        )
        return (
            "=== Quantitative Risk Assessment ===\n"
            f"Ticker: {self.ticker} | Date: {self.date}\n"
            f"Current Price: ${self.current_price:.2f}\n"
            "\n--- Volatility ---\n"
            f"Daily Volatility: {self.daily_volatility:.4f} ({self.daily_volatility * 100:.2f}%)\n"
            f"Annualized Volatility: {self.annualized_volatility:.4f} ({self.annualized_volatility * 100:.1f}%)\n"
            f"ATR: ${self.atr:.2f} ({self.atr_percent * 100:.2f}% of price)\n"
            "\n--- Drawdown ---\n"
            f"Max Drawdown (lookback): {self.max_drawdown * 100:.2f}%\n"
            f"Current Drawdown: {self.current_drawdown * 100:.2f}%\n"
            "\n--- Value at Risk (daily) ---\n"
            f"VaR 95%: {self.var_95 * 100:.2f}%\n"
            f"VaR 99%: {self.var_99 * 100:.2f}%\n"
            f"CVaR 95% (Expected Shortfall): {self.cvar_95 * 100:.2f}%\n"
            "\n--- Market Context ---\n"
            f"Beta (vs benchmark): {self.beta:.2f}\n"
            f"Sharpe Ratio: {self.sharpe_ratio:.2f}\n"
            f"Sortino Ratio: {self.sortino_ratio:.2f}\n"
            "\n--- Trend ---\n"
            f"SMA 50: ${self.sma_50:.2f} | SMA 200: ${self.sma_200:.2f} | Trend: {trend}\n"
            f"RSI: {self.rsi:.1f} ({rsi_zone})\n"
            "=== End Risk Assessment ==="
        )


@dataclass
class PositionSize:
    """Recommended position sizing for a trade.

    Attributes:
        method: Sizing algorithm used (kelly, fixed_fraction, volatility_adjusted).
        fraction: Fraction of portfolio to allocate (0.0 to max_position_fraction).
        max_loss_percent: Maximum expected loss as fraction of position value.
        stop_loss_price: Suggested stop-loss price level.
    """

    method: str
    fraction: float
    max_loss_percent: float
    stop_loss_price: float

    def to_dict(self) -> dict:
        """Convert to plain dict."""
        return asdict(self)

    def format_for_prompt(self) -> str:
        """Format for injection into LLM prompts."""
        return (
            f"Position Sizing ({self.method}):\n"
            f"  Recommended allocation: {self.fraction * 100:.1f}% of portfolio\n"
            f"  Max expected loss: {self.max_loss_percent * 100:.2f}%\n"
            f"  Suggested stop-loss: ${self.stop_loss_price:.2f}"
        )


@dataclass
class TradeSignal:
    """Extended trade signal replacing the plain BUY/SELL/HOLD string.

    Attributes:
        action: Trading action (BUY, SELL, or HOLD).
        confidence: Confidence level from 0.0 (no confidence) to 1.0 (full confidence).
        position_size: Recommended position sizing.
        risk_metrics: Quantitative risk metrics at time of signal.
        reasoning: LLM-generated reasoning text.
    """

    action: str
    confidence: float
    position_size: Optional[PositionSize]
    risk_metrics: Optional[RiskMetrics]
    reasoning: str

    def to_dict(self) -> dict:
        """Convert to plain dict."""
        return asdict(self)

    def __str__(self) -> str:
        """Backward-compatible string representation (returns action)."""
        return self.action
