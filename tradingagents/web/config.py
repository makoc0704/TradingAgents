"""Web-specific configuration."""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class WebConfig:
    """Configuration for the web interface server.

    Attributes:
        host: Bind address for the server.
        port: Port number for the server.
        cors_origins: Allowed CORS origins.
        dev_mode: Enable development mode (auto-reload, relaxed CORS).
        max_concurrent_tasks: Maximum number of background tasks.
        task_ttl_seconds: Time-to-live for completed task results in memory.
        results_dir: Base directory for reading persisted results.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: List[str] = field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    dev_mode: bool = False
    max_concurrent_tasks: int = 2
    task_ttl_seconds: int = 3600
    results_dir: str = "./results"

    @classmethod
    def from_env(cls) -> "WebConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("WEB_HOST", "127.0.0.1"),
            port=int(os.getenv("WEB_PORT", "8000")),
            dev_mode=os.getenv("WEB_DEV_MODE", "false").lower() == "true",
            results_dir=os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
        )
