"""Portfolio optimization — weighting strategies.

Stateless optimizer: all methods take data as arguments and return
``AllocationResult``.  No LLM calls.
"""

import logging
import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from tradingagents.risk.models import RiskMetrics, TradeSignal

from .models import AllocationResult
from . import correlation as corr

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Compute target weights for a set of tickers.

    Supports four strategies:
    - ``equal``: 1/n for each ticker.
    - ``risk_parity``: inversely proportional to annualized volatility.
    - ``min_variance``: minimize portfolio variance via quadratic optimization.
    - ``signal_weighted``: weight by LLM confidence from ``TradeSignal``.

    Args:
        max_position: Maximum weight per ticker (0.0-1.0).
        min_position: Minimum weight per ticker (0.0-1.0).
    """

    def __init__(
        self,
        max_position: float = 0.30,
        min_position: float = 0.05,
    ):
        self.max_position = max_position
        self.min_position = min_position

    def optimize(
        self,
        strategy: str,
        tickers: List[str],
        price_series: Optional[Dict[str, pd.Series]] = None,
        risk_metrics: Optional[Dict[str, RiskMetrics]] = None,
        signals: Optional[Dict[str, TradeSignal]] = None,
    ) -> AllocationResult:
        """Run the specified weighting strategy.

        Args:
            strategy: One of "equal", "risk_parity", "min_variance",
                "signal_weighted".
            tickers: List of ticker symbols to include.
            price_series: Historical closing prices per ticker
                (required for risk_parity and min_variance).
            risk_metrics: Pre-computed risk metrics per ticker
                (used by risk_parity as fallback for volatilities).
            signals: Trade signals per ticker
                (required for signal_weighted).

        Returns:
            AllocationResult with clamped, normalized weights.

        Raises:
            ValueError: If the strategy name is unknown.
        """
        strategy = strategy.lower().strip()
        dispatch = {
            "equal": self._equal_weight,
            "risk_parity": self._risk_parity,
            "min_variance": self._min_variance,
            "signal_weighted": self._signal_weighted,
        }

        if strategy not in dispatch:
            raise ValueError(
                f"Unknown weighting strategy '{strategy}'. "
                f"Available: {', '.join(dispatch.keys())}"
            )

        return dispatch[strategy](
            tickers=tickers,
            price_series=price_series,
            risk_metrics=risk_metrics,
            signals=signals,
        )

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _equal_weight(self, tickers, **_kwargs) -> AllocationResult:
        """Assign 1/n weight to each ticker."""
        n = len(tickers)
        if n == 0:
            return AllocationResult(weights={}, method="equal")

        raw_weight = 1.0 / n
        weights = {t: raw_weight for t in tickers}
        weights = self._clamp_and_normalize(weights)

        return AllocationResult(weights=weights, method="equal")

    def _risk_parity(
        self, tickers, price_series=None, risk_metrics=None, **_kwargs,
    ) -> AllocationResult:
        """Weight inversely proportional to annualized volatility."""
        vols = self._get_volatilities(tickers, price_series, risk_metrics)

        inv_vols = {}
        for t in tickers:
            vol = vols.get(t, 0.0)
            inv_vols[t] = 1.0 / vol if vol > 1e-12 else 0.0

        total_inv = sum(inv_vols.values())
        if total_inv < 1e-12:
            return self._equal_weight(tickers)

        weights = {t: iv / total_inv for t, iv in inv_vols.items()}
        weights = self._clamp_and_normalize(weights)

        port_vol, port_var, div_ratio, corr_dict = self._compute_portfolio_stats(
            weights, price_series, vols,
        )

        return AllocationResult(
            weights=weights,
            method="risk_parity",
            portfolio_volatility=port_vol,
            portfolio_var_95=port_var,
            diversification_ratio=div_ratio,
            correlation_matrix=corr_dict,
        )

    def _min_variance(
        self, tickers, price_series=None, risk_metrics=None, **_kwargs,
    ) -> AllocationResult:
        """Minimize portfolio variance using quadratic optimization."""
        if price_series is None or len(price_series) < 2:
            logger.warning("Insufficient price data for min_variance — falling back to equal")
            return self._equal_weight(tickers)

        try:
            from scipy.optimize import minimize

            cov_matrix = corr.calculate_covariance_matrix(price_series)
            cov_arr = cov_matrix.loc[tickers, tickers].values
            n = len(tickers)

            def portfolio_variance(w):
                return float(w @ cov_arr @ w)

            constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
            bounds = [(self.min_position, self.max_position)] * n
            x0 = np.array([1.0 / n] * n)

            result = minimize(
                portfolio_variance,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                weights = {tickers[i]: float(result.x[i]) for i in range(n)}
            else:
                logger.warning("min_variance optimization failed: %s — falling back to equal", result.message)
                return self._equal_weight(tickers)

        except Exception as e:
            logger.warning("min_variance optimization error: %s — falling back to equal", e)
            return self._equal_weight(tickers)

        weights = self._clamp_and_normalize(weights)
        vols = self._get_volatilities(tickers, price_series, risk_metrics)

        port_vol, port_var, div_ratio, corr_dict = self._compute_portfolio_stats(
            weights, price_series, vols,
        )

        return AllocationResult(
            weights=weights,
            method="min_variance",
            portfolio_volatility=port_vol,
            portfolio_var_95=port_var,
            diversification_ratio=div_ratio,
            correlation_matrix=corr_dict,
        )

    def _signal_weighted(
        self, tickers, signals=None, price_series=None, risk_metrics=None,
        **_kwargs,
    ) -> AllocationResult:
        """Weight by LLM confidence: BUY gets high weight, SELL gets zero."""
        if signals is None:
            logger.warning("No signals for signal_weighted — falling back to equal")
            return self._equal_weight(tickers)

        raw_weights = {}
        for t in tickers:
            sig = signals.get(t)
            if sig is None:
                raw_weights[t] = 0.5
                continue

            if isinstance(sig, TradeSignal):
                action = sig.action.upper()
                confidence = sig.confidence
            else:
                action = str(sig).upper()
                confidence = 0.5

            if action == "SELL":
                raw_weights[t] = 0.0
            elif action == "BUY":
                raw_weights[t] = 0.5 + 0.5 * confidence
            else:
                raw_weights[t] = 0.3 * confidence

        total = sum(raw_weights.values())
        if total < 1e-12:
            return self._equal_weight(tickers)

        weights = {t: w / total for t, w in raw_weights.items()}
        weights = self._clamp_and_normalize(weights)

        vols = self._get_volatilities(tickers, price_series, risk_metrics)
        port_vol, port_var, div_ratio, corr_dict = self._compute_portfolio_stats(
            weights, price_series, vols,
        )

        return AllocationResult(
            weights=weights,
            method="signal_weighted",
            portfolio_volatility=port_vol,
            portfolio_var_95=port_var,
            diversification_ratio=div_ratio,
            correlation_matrix=corr_dict,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clamp_and_normalize(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Clamp weights to [min, max] and re-normalize so sum <= 1.0.

        Tickers with weight < min_position are removed (set to 0) to avoid
        tiny positions.  Remaining weights are clamped to max_position and
        scaled so they sum to at most 1.0 (excess goes to cash).
        """
        clamped = {}
        for t, w in weights.items():
            if w < self.min_position:
                clamped[t] = 0.0
            else:
                clamped[t] = min(w, self.max_position)

        total = sum(clamped.values())
        if total > 1.0:
            clamped = {t: w / total for t, w in clamped.items()}

        return clamped

    def _get_volatilities(
        self,
        tickers: List[str],
        price_series: Optional[Dict[str, pd.Series]],
        risk_metrics: Optional[Dict[str, RiskMetrics]],
    ) -> Dict[str, float]:
        """Get annualized volatility per ticker from best available source."""
        if price_series and len(price_series) >= 2:
            return corr.get_individual_volatilities(price_series)

        vols = {}
        for t in tickers:
            if risk_metrics and t in risk_metrics:
                vols[t] = risk_metrics[t].annualized_volatility
            else:
                vols[t] = 0.20
        return vols

    def _compute_portfolio_stats(
        self,
        weights: Dict[str, float],
        price_series: Optional[Dict[str, pd.Series]],
        vols: Dict[str, float],
    ) -> tuple:
        """Compute portfolio-level stats when price_series are available.

        Returns:
            Tuple of (portfolio_volatility, portfolio_var_95,
                diversification_ratio, correlation_matrix_dict).
        """
        port_vol = 0.0
        port_var = 0.0
        div_ratio = 1.0
        corr_dict: Dict[str, Dict[str, float]] = {}

        if price_series and len(price_series) >= 2:
            try:
                cov_matrix = corr.calculate_covariance_matrix(price_series)
                active = [t for t, w in weights.items() if w > 1e-12]
                if len(active) >= 2:
                    active_weights = {t: weights[t] for t in active}
                    port_vol = corr.calculate_portfolio_volatility(
                        active_weights, cov_matrix,
                    )
                    port_var = corr.calculate_portfolio_var(
                        active_weights, cov_matrix,
                    )
                    div_ratio = corr.diversification_ratio(
                        active_weights, vols, port_vol,
                    )
                    corr_mat = corr.calculate_correlation_matrix(price_series)
                    corr_dict = corr_mat.to_dict()
            except (ValueError, Exception) as e:
                logger.warning("Portfolio stats computation failed: %s", e)

        return port_vol, port_var, div_ratio, corr_dict
