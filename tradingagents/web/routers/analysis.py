"""Analysis router — run single-ticker analysis and retrieve results."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..dependencies import get_task_manager, get_result_reader
from ..schemas.requests import AnalysisRequest
from ..schemas.responses import ApiResponse, TaskStatusResponse, AnalysisResultResponse
from ..services.task_manager import TaskManager
from ..services.result_reader import ResultReader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


def _run_analysis(task_info: Any, update_fn: Any) -> Dict[str, Any]:
    """Execute a single analysis in a background thread."""
    config = task_info.config
    ticker = config["ticker"]
    date = config["analysis_date"]

    update_fn(progress=5, message=f"Initializing analysis for {ticker}...")

    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG

    graph_config = {**DEFAULT_CONFIG}
    graph_config["llm_provider"] = config.get("llm_provider", "openai")

    selected = config.get("selected_analysts", ["market", "fundamentals"])
    graph = TradingAgentsGraph(
        debug=True,
        config=graph_config,
        selected_analysts=selected,
    )

    update_fn(progress=20, message=f"Running agent graph for {ticker} on {date}...")
    state, decision = graph.propagate(ticker, date)

    signal = "HOLD"
    if hasattr(decision, "action"):
        signal = decision.action
    elif isinstance(decision, str):
        for s in ("BUY", "SELL", "HOLD"):
            if s in decision.upper():
                signal = s
                break

    update_fn(progress=100, message=f"Analysis complete: {signal}")

    return {
        "ticker": ticker,
        "date": date,
        "signal": signal,
        "decision": str(decision),
        "final_trade_decision": state.get("final_trade_decision", ""),
        "risk_metrics": state.get("risk_metrics", {}),
    }


@router.post(
    "/run",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Start a new analysis",
)
async def run_analysis(
    request: AnalysisRequest,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse[TaskStatusResponse]:
    """Submit a single-ticker analysis as a background task."""
    task_id = task_manager.submit(
        task_type="analysis",
        config=request.model_dump(),
        run_fn=_run_analysis,
    )
    status = task_manager.get_status(task_id)
    return ApiResponse(
        success=True,
        data=TaskStatusResponse(**status),
    )


@router.get(
    "/status/{task_id}",
    response_model=ApiResponse[TaskStatusResponse],
    summary="Get analysis task status",
)
async def get_analysis_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ApiResponse:
    """Poll the status of a running analysis task."""
    status = task_manager.get_status(task_id)
    if status is None:
        return ApiResponse(success=False, error=f"Task '{task_id}' not found")
    return ApiResponse(success=True, data=TaskStatusResponse(**status))


@router.get(
    "/{ticker}/{date}",
    response_model=ApiResponse[AnalysisResultResponse],
    summary="Get saved analysis result",
)
async def get_analysis_result(
    ticker: str,
    date: str,
    reader: ResultReader = Depends(get_result_reader),
) -> ApiResponse:
    """Retrieve a previously saved analysis result."""
    data = reader.get_analysis_result(ticker.upper(), date)
    if data is None:
        return ApiResponse(
            success=False,
            error=f"No analysis result found for {ticker} on {date}",
        )

    flat = _flatten_state_log(data, ticker.upper(), date)
    return ApiResponse(success=True, data=flat)


def _flatten_state_log(
    data: Dict[str, Any], ticker: str, date: str
) -> Dict[str, Any]:
    """Flatten a state log dict into an AnalysisResultResponse-compatible dict."""
    if date in data and isinstance(data[date], dict):
        entry = data[date]
    else:
        entry = data

    decision_text = entry.get("final_trade_decision", "")
    signal = "HOLD"
    for s in ("BUY", "SELL", "HOLD"):
        if s in decision_text.upper():
            signal = s
            break

    confidence = ""
    for marker in ("CONFIDENCE:", "Confidence:"):
        if marker in decision_text:
            confidence = decision_text.split(marker, 1)[1].split("\n")[0].strip()
            break

    debate_state = entry.get("investment_debate_state", {})
    risk_debate = entry.get("risk_debate_state", {})

    return {
        "ticker": ticker,
        "date": date,
        "final_decision": decision_text,
        "signal": signal,
        "confidence": confidence,
        "market_report": entry.get("market_report", ""),
        "sentiment_report": entry.get("sentiment_report", ""),
        "news_report": entry.get("news_report", ""),
        "fundamentals_report": entry.get("fundamentals_report", ""),
        "risk_metrics": entry.get("risk_metrics"),
        "investment_debate": debate_state if debate_state else None,
        "risk_debate": risk_debate if risk_debate else None,
    }
