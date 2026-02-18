"""TradingAgents Web Interface — FastAPI backend + React frontend."""

from .app import create_app
from .config import WebConfig

__all__ = ["create_app", "WebConfig"]
