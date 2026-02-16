"""Portfolio management module — multi-asset orchestration.

Public API:
    PortfolioManager   — top-level entry point for portfolio backtesting
    PortfolioConfig    — configuration dataclass
    PortfolioResult    — result dataclass
    PortfolioOptimizer — weighting strategies
    MultiAssetPortfolio — multi-position tracking
    Rebalancer         — drift detection and order generation
    resolve_universe   — resolve preset names to ticker lists
"""

from .models import (
    PortfolioConfig,
    PortfolioResult,
    PortfolioSnapshot,
    Position,
    AllocationResult,
    RebalanceOrder,
)
from .universe import resolve_universe, UNIVERSE_PRESETS
from .optimizer import PortfolioOptimizer
from .multi_portfolio import MultiAssetPortfolio
from .rebalancer import Rebalancer
from .manager import PortfolioManager

__all__ = [
    "PortfolioManager",
    "PortfolioConfig",
    "PortfolioResult",
    "PortfolioSnapshot",
    "Position",
    "AllocationResult",
    "RebalanceOrder",
    "PortfolioOptimizer",
    "MultiAssetPortfolio",
    "Rebalancer",
    "resolve_universe",
    "UNIVERSE_PRESETS",
]
