"""Report generation for backtest results.

Generates JSON, human-readable text, and pandas DataFrame outputs.
No LLM calls — pure data transformation.
"""

import json
import logging
from typing import Optional

import pandas as pd

from .models import BacktestResult

logger = logging.getLogger(__name__)


class BacktestReport:
    """Generate reports from a BacktestResult in various formats."""

    def __init__(self, result: BacktestResult):
        self.result = result

    def to_json(self, indent: int = 2) -> str:
        """Serialize the full result to JSON.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string of the complete backtest result.
        """
        return json.dumps(self.result.to_dict(), indent=indent, default=str)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert daily snapshots to a pandas DataFrame.

        Returns:
            DataFrame indexed by date with portfolio metrics.
        """
        if not self.result.daily_snapshots:
            return pd.DataFrame()

        records = [s.to_dict() for s in self.result.daily_snapshots]
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    def to_trades_dataframe(self) -> pd.DataFrame:
        """Convert trade records to a pandas DataFrame.

        Returns:
            DataFrame of all trades (excluding signal details for readability).
        """
        if not self.result.trades:
            return pd.DataFrame()

        records = []
        for t in self.result.trades:
            records.append({
                "date": t.date,
                "ticker": t.ticker,
                "action": t.action,
                "price": t.price,
                "shares": t.shares,
                "commission": t.commission,
                "portfolio_value": t.portfolio_value,
                "cash": t.cash,
                "position_value": t.position_value,
            })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    def to_summary(self) -> str:
        """Generate a human-readable text summary.

        Returns:
            Multi-line string suitable for CLI output.
        """
        r = self.result
        p = r.performance
        c = r.config

        lines = [
            "=" * 60,
            "  BACKTEST RESULT SUMMARY",
            "=" * 60,
            "",
            f"  Ticker:          {c.ticker}",
            f"  Period:          {c.start_date} to {c.end_date}",
            f"  Trading Days:    {r.total_trading_days}",
            f"  Profile:         {c.backtest_profile}",
            f"  Initial Capital: ${c.initial_capital:,.2f}",
            "",
            "--- Performance ---",
            f"  Final Value:     ${p.get('final_portfolio_value', 0):,.2f}",
            f"  Total Return:    {p.get('total_return', 0) * 100:+.2f}%",
            f"  Annual Return:   {p.get('annualized_return', 0) * 100:+.2f}%",
            f"  Max Drawdown:    {p.get('max_drawdown', 0) * 100:.2f}%",
            f"  Sharpe Ratio:    {p.get('sharpe_ratio', 0):.2f}",
            f"  Sortino Ratio:   {p.get('sortino_ratio', 0):.2f}",
            "",
            "--- Trades ---",
            f"  Total Trades:    {p.get('total_trades', 0)}",
            f"  Buy Orders:      {p.get('buy_trades', 0)}",
            f"  Sell Orders:     {p.get('sell_trades', 0)}",
            f"  Win Rate:        {p.get('win_rate', 0) * 100:.1f}%",
            f"  Profit Factor:   {p.get('profit_factor', 0):.2f}",
            f"  Total Commission:${p.get('total_commission', 0):,.2f}",
            f"  Exposure Time:   {p.get('exposure_time', 0) * 100:.1f}%",
            "",
            "--- Benchmark ---",
            f"  Buy & Hold:      {p.get('buy_and_hold_return', 0) * 100:+.2f}%",
            f"  Alpha:           {p.get('alpha', 0) * 100:+.2f}%",
            "",
            "=" * 60,
        ]

        return "\n".join(lines)

    def save_json(self, path: str) -> None:
        """Save the full result as a JSON file.

        Args:
            path: File path to write to.
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        logger.info("Backtest result saved to %s", path)

    def save_summary(self, path: str) -> None:
        """Save the text summary to a file.

        Args:
            path: File path to write to.
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_summary())
        logger.info("Backtest summary saved to %s", path)
