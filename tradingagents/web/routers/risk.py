"""Risk router — compute and retrieve risk metrics for a ticker."""

import logging

from fastapi import APIRouter

from ..schemas.responses import ApiResponse, RiskMetricsResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["risk"])


@router.get(
    "/{ticker}/{date}",
    response_model=ApiResponse[RiskMetricsResponse],
    summary="Calculate risk metrics",
)
async def get_risk_metrics(
    ticker: str,
    date: str,
) -> ApiResponse[RiskMetricsResponse]:
    """Calculate quantitative risk metrics for a ticker on a given date.

    This endpoint runs the RiskCalculator synchronously as it's relatively fast
    (no LLM calls, only market data fetching + math).
    """
    try:
        from tradingagents.risk import RiskCalculator
        from tradingagents.default_config import DEFAULT_CONFIG

        calculator = RiskCalculator(DEFAULT_CONFIG)
        metrics = calculator.calculate_risk_metrics(ticker.upper(), date)

        return ApiResponse(
            success=True,
            data=RiskMetricsResponse(
                ticker=metrics.ticker,
                date=metrics.date,
                daily_volatility=metrics.daily_volatility,
                annualized_volatility=metrics.annualized_volatility,
                atr=metrics.atr,
                atr_percent=metrics.atr_percent,
                max_drawdown=metrics.max_drawdown,
                current_drawdown=metrics.current_drawdown,
                var_95=metrics.var_95,
                var_99=metrics.var_99,
                cvar_95=metrics.cvar_95,
                beta=metrics.beta,
                sharpe_ratio=metrics.sharpe_ratio,
                sortino_ratio=metrics.sortino_ratio,
                current_price=metrics.current_price,
                sma_50=metrics.sma_50,
                sma_200=metrics.sma_200,
                rsi=metrics.rsi,
            ),
        )
    except Exception as exc:
        logger.error(
            "Failed to calculate risk metrics for %s on %s: %s",
            ticker, date, exc,
        )
        return ApiResponse(success=False, error=str(exc))
