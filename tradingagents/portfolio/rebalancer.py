"""Rebalancing logic — drift detection and order generation.

Compares actual portfolio weights against targets and generates
orders to bring allocations back in line.
"""

import logging
from typing import Dict, List

from .models import Position, RebalanceOrder

logger = logging.getLogger(__name__)


class Rebalancer:
    """Detects allocation drift and generates rebalancing orders.

    Args:
        threshold: Minimum absolute drift (|actual - target|) to trigger
            rebalancing for any single ticker (e.g. 0.05 = 5%).
        min_trade_value: Minimum dollar value for a rebalancing trade.
            Orders below this threshold are skipped to avoid churning.
        commission_rate: Commission rate for cost-benefit analysis.
    """

    def __init__(
        self,
        threshold: float = 0.05,
        min_trade_value: float = 500.0,
        commission_rate: float = 0.001,
    ):
        self.threshold = threshold
        self.min_trade_value = min_trade_value
        self.commission_rate = commission_rate

    def check_drift(
        self,
        positions: Dict[str, Position],
        target_weights: Dict[str, float],
        cash: float,
        prices: Dict[str, float],
    ) -> bool:
        """Check whether any ticker has drifted beyond the threshold.

        Args:
            positions: Current positions per ticker.
            target_weights: Desired weights per ticker.
            cash: Current cash balance.
            prices: Current market prices per ticker.

        Returns:
            True if at least one ticker exceeds the drift threshold.
        """
        total_value = cash + sum(
            pos.shares * prices.get(pos.ticker, pos.current_price)
            for pos in positions.values()
        )
        if total_value <= 0:
            return False

        all_tickers = set(target_weights.keys()) | set(positions.keys())

        for ticker in all_tickers:
            target = target_weights.get(ticker, 0.0)
            pos = positions.get(ticker)
            actual = (
                (pos.shares * prices.get(ticker, pos.current_price)) / total_value
                if pos and pos.shares > 0
                else 0.0
            )
            if abs(actual - target) > self.threshold:
                return True

        return False

    def generate_orders(
        self,
        positions: Dict[str, Position],
        target_weights: Dict[str, float],
        prices: Dict[str, float],
        cash: float,
        total_value: float,
    ) -> List[RebalanceOrder]:
        """Generate rebalancing orders to move from actual to target weights.

        Sells overweight positions first (to free cash), then buys
        underweight positions.

        Args:
            positions: Current positions per ticker.
            target_weights: Desired weights per ticker.
            prices: Current market prices per ticker.
            cash: Current cash balance.
            total_value: Current total portfolio value.

        Returns:
            Ordered list of RebalanceOrders (sells first, then buys).
        """
        if total_value <= 0:
            return []

        all_tickers = set(target_weights.keys()) | set(positions.keys())

        sells = []
        buys = []

        for ticker in all_tickers:
            price = prices.get(ticker, 0.0)
            if price <= 0:
                continue

            target_w = target_weights.get(ticker, 0.0)
            pos = positions.get(ticker)
            current_shares = pos.shares if pos else 0
            current_value = current_shares * price
            actual_w = current_value / total_value if total_value > 0 else 0.0

            drift = target_w - actual_w
            if abs(drift) < self.threshold:
                continue

            target_value = total_value * target_w
            delta_value = target_value - current_value

            if delta_value < 0:
                shares_to_sell = min(
                    int(abs(delta_value) / price), current_shares
                )
                if shares_to_sell <= 0:
                    continue
                trade_value = shares_to_sell * price
                if trade_value < self.min_trade_value:
                    continue
                estimated_commission = trade_value * self.commission_rate
                if estimated_commission > abs(delta_value) * 0.5:
                    logger.debug(
                        "Skipping rebalance SELL %s: commission ($%.2f) > 50%% of drift ($%.2f)",
                        ticker, estimated_commission, abs(delta_value),
                    )
                    continue
                sells.append(RebalanceOrder(
                    ticker=ticker,
                    action="SELL",
                    target_shares=shares_to_sell,
                    estimated_value=trade_value,
                    reason=f"Overweight by {abs(drift)*100:.1f}% "
                           f"(actual={actual_w*100:.1f}%, target={target_w*100:.1f}%)",
                ))

            elif delta_value > 0:
                shares_to_buy = int(delta_value / price)
                if shares_to_buy <= 0:
                    continue
                trade_value = shares_to_buy * price
                if trade_value < self.min_trade_value:
                    continue
                buys.append(RebalanceOrder(
                    ticker=ticker,
                    action="BUY",
                    target_shares=shares_to_buy,
                    estimated_value=trade_value,
                    reason=f"Underweight by {abs(drift)*100:.1f}% "
                           f"(actual={actual_w*100:.1f}%, target={target_w*100:.1f}%)",
                ))

        return sells + buys

    def should_rebalance_today(
        self,
        day_index: int,
        frequency: str,
        trading_dates: list,
    ) -> bool:
        """Check if today is a valid rebalancing day based on frequency.

        Args:
            day_index: 0-based index of the current trading day.
            frequency: "daily", "weekly", or "monthly".
            trading_dates: Full list of trading date strings.

        Returns:
            True if rebalancing should be checked today.
        """
        if frequency == "daily":
            return True

        if day_index == 0:
            return True

        from datetime import datetime

        current = datetime.strptime(trading_dates[day_index], "%Y-%m-%d")
        previous = datetime.strptime(trading_dates[day_index - 1], "%Y-%m-%d")

        if frequency == "weekly":
            return current.isocalendar()[1] != previous.isocalendar()[1]
        elif frequency == "monthly":
            return current.month != previous.month

        return True
