"""FastAPI application factory for the TradingAgents Dashboard."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import WebConfig
from .dependencies import init_dependencies, shutdown_dependencies, get_task_manager
from .routers import (
    analysis_router,
    backtest_router,
    portfolio_router,
    pipeline_router,
    results_router,
    risk_router,
    live_router,
)
from .websocket.stream import websocket_stream_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    config = getattr(app.state, "web_config", WebConfig())
    init_dependencies(config)
    logger.info("TradingAgents Dashboard started on %s:%d", config.host, config.port)
    yield
    shutdown_dependencies()
    logger.info("TradingAgents Dashboard stopped.")


def create_app(config: WebConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Web configuration. Uses defaults if not provided.

    Returns:
        Configured FastAPI application instance.
    """
    if config is None:
        config = WebConfig.from_env()

    app = FastAPI(
        title="TradingAgents Dashboard",
        description="Web interface for the TradingAgents multi-agent trading system",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.state.web_config = config

    # CORS middleware
    origins = config.cors_origins
    if config.dev_mode:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    app.include_router(analysis_router, prefix="/api/analysis")
    app.include_router(backtest_router, prefix="/api/backtest")
    app.include_router(portfolio_router, prefix="/api/portfolio")
    app.include_router(pipeline_router, prefix="/api/pipeline")
    app.include_router(results_router, prefix="/api/results")
    app.include_router(risk_router, prefix="/api/risk")
    app.include_router(live_router, prefix="/api/live")

    # WebSocket endpoint
    @app.websocket("/ws/stream/{task_id}")
    async def ws_stream(websocket: WebSocket, task_id: str) -> None:
        task_manager = get_task_manager()
        await websocket_stream_handler(websocket, task_id, task_manager)

    # Health check
    @app.get("/api/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "ok", "service": "tradingagents-dashboard"}

    # Task list endpoint
    @app.get("/api/tasks", tags=["system"])
    async def list_tasks() -> dict:
        task_manager = get_task_manager()
        return {"tasks": task_manager.list_tasks()}

    # Static file serving (production mode: built React app)
    frontend_dist = os.path.join(
        os.path.dirname(__file__), "frontend", "dist"
    )
    if os.path.isdir(frontend_dist) and not config.dev_mode:
        app.mount(
            "/",
            StaticFiles(directory=frontend_dist, html=True),
            name="frontend",
        )
        logger.info("Serving frontend from %s", frontend_dist)

    return app
