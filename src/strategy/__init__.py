"""
Strategy module for Project DEGENERATE.

Provides:
- Position sizing and allocation
- Contract selection
- Desperation engine
- Winner engine
- Exit strategies
"""

from src.strategy.allocator import PositionSizer, CapitalAllocator
from src.strategy.contract_selector import ContractSelector
from src.strategy.desperation import DesperationEngine
from src.strategy.winner_engine import WinnerEngine
from src.strategy.exits import ExitStrategy, StopLossManager, TakeProfitManager

__all__ = [
    "PositionSizer",
    "CapitalAllocator",
    "ContractSelector",
    "DesperationEngine",
    "WinnerEngine",
    "ExitStrategy",
    "StopLossManager",
    "TakeProfitManager",
]
