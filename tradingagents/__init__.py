"""TradingAgents: Multi-Agents LLM Financial Trading Framework."""

import logging

from dotenv import load_dotenv

# Load environment variables from .env file at package import time
load_dotenv()

# Configure logging for the tradingagents package
logging.getLogger(__name__).addHandler(logging.NullHandler())


def configure_logging(level: int = logging.INFO) -> None:
    """Configure logging for the TradingAgents package.

    Call this from your application entry point to enable log output.

    Args:
        level: Logging level (e.g. logging.DEBUG, logging.INFO).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
