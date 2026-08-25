"""
Exposure management for Project DEGENERATE.

Manages position limits, concentration risk, and exposure constraints.
"""

import logging
from collections import defaultdict
from typing import Any

from src.config import init_config
from src.models import (
    Position,
    SleeveType,
    SignalSource,
)
from src.state import get_portfolio_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Exposure Manager
# =============================================================================

class ExposureManager:
    """
    Manages overall portfolio exposure.
    
    Tracks:
    - Total exposure by sleeve
    - Total exposure by ticker
    - Total exposure by direction
    - Concentration risk
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def get_exposure_by_sleeve(self) -> dict[SleeveType, float]:
        """
        Get total exposure by sleeve.
        
        Returns:
            Dictionary mapping sleeve type to exposure amount
        """
        portfolio = get_portfolio_manager()
        exposure = {}
        
        for sleeve_type, sleeve in portfolio.sleeves.items():
            exposure[sleeve_type] = sleeve.open_risk
        
        return exposure
    
    def get_exposure_by_ticker(self) -> dict[str, float]:
        """
        Get total exposure by ticker.
        
        Returns:
            Dictionary mapping ticker to exposure amount
        """
        portfolio = get_portfolio_manager()
        ticker_exposure: dict[str, float] = defaultdict(float)
        
        for sleeve in portfolio.sleeves.values():
            for pos_symbol in sleeve.open_positions:
                # Extract ticker from symbol
                if ' ' in pos_symbol:
                    ticker = pos_symbol.split()[0]
                else:
                    ticker = pos_symbol
                
                # In production, get actual exposure from position
                # For now, use placeholder
                ticker_exposure[ticker] += 1000.0  # Placeholder
        
        return dict(ticker_exposure)
    
    def get_concentration_risk(self) -> dict[str, Any]:
        """
        Calculate concentration risk metrics.
        
        Returns:
            Dictionary with concentration risk information
        """
        ticker_exposure = self.get_exposure_by_ticker()
        total_exposure = sum(ticker_exposure.values())
        
        if total_exposure == 0:
            return {
                "max_ticker_percent": 0.0,
                "top_3_percent": 0.0,
                "top_5_percent": 0.0,
            }
        
        # Sort by exposure (descending)
        sorted_exposure = sorted(
            ticker_exposure.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        # Calculate percentages
        max_percent = (sorted_exposure[0][1] / total_exposure * 100) if sorted_exposure else 0.0
        top_3_percent = sum(
            exp[1] for exp in sorted_exposure[:3]
        ) / total_exposure * 100 if len(sorted_exposure) >= 3 else 0.0
        top_5_percent = sum(
            exp[1] for exp in sorted_exposure[:5]
        ) / total_exposure * 100 if len(sorted_exposure) >= 5 else 0.0
        
        return {
            "max_ticker_percent": max_percent,
            "top_3_percent": top_3_percent,
            "top_5_percent": top_5_percent,
            "total_exposure": total_exposure,
        }
    
    def check_concentration_limit(self, ticker: str, additional_exposure: float) -> bool:
        """
        Check if adding exposure to a ticker would exceed concentration limit.
        
        Args:
            ticker: The ticker
            additional_exposure: Additional exposure to add
            
        Returns:
            True if within limit, False if would exceed
        """
        ticker_exposure = self.get_exposure_by_ticker()
        current_exposure = ticker_exposure.get(ticker, 0.0)
        total_exposure = sum(ticker_exposure.values())
        
        # Max 30% concentration in any single ticker
        max_concentration = 0.30
        
        new_exposure = current_exposure + additional_exposure
        new_total = total_exposure + additional_exposure
        
        if new_total == 0:
            return True
        
        return (new_exposure / new_total) <= max_concentration


# =============================================================================
# Position Limit Manager
# =============================================================================

class PositionLimitManager:
    """
    Manages position size limits.
    
    Enforces:
    - Max position size
    - Max position count
    - Position size as % of portfolio
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.max_position_size = self.config.execution.max_position_size
        self.max_order_size = self.config.execution.max_order_size
    
    def check_position_size(self, position_size: float) -> bool:
        """
        Check if position size is within limits.
        
        Args:
            position_size: Size of the position
            
        Returns:
            True if within limit, False if exceeds
        """
        return position_size <= self.max_position_size
    
    def check_order_size(self, order_size: float) -> bool:
        """
        Check if order size is within limits.
        
        Args:
            order_size: Size of the order
            
        Returns:
            True if within limit, False if exceeds
        """
        return order_size <= self.max_order_size
    
    def check_position_count(self) -> bool:
        """
        Check if we've reached max position count.
        
        Returns:
            True if within limit, False if at max
        """
        portfolio = get_portfolio_manager()
        total_positions = sum(
            len(sleeve.open_positions) for sleeve in portfolio.sleeves.values()
        )
        
        # Max 20 open positions
        max_positions = 20
        
        return total_positions < max_positions
    
    def get_position_limits(self) -> dict[str, Any]:
        """
        Get current position limit status.
        
        Returns:
            Dictionary with position limit information
        """
        portfolio = get_portfolio_manager()
        
        total_positions = sum(
            len(sleeve.open_positions) for sleeve in portfolio.sleeves.values()
        )
        
        return {
            "max_position_size": self.max_position_size,
            "max_order_size": self.max_order_size,
            "current_positions": total_positions,
            "max_positions": 20,
            "can_open_new_position": self.check_position_count(),
        }


# =============================================================================
# Direction Exposure Manager
# =============================================================================

class DirectionExposureManager:
    """Manages exposure by direction (long/short)."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def get_direction_exposure(self) -> dict[str, float]:
        """
        Get exposure by direction.
        
        Returns:
            Dictionary with long and short exposure
        """
        portfolio = get_portfolio_manager()
        
        long_exposure = 0.0
        short_exposure = 0.0
        
        for sleeve in portfolio.sleeves.values():
            for pos_symbol in sleeve.open_positions:
                # In production, determine direction from position
                # For now, assume all are long
                long_exposure += 1000.0  # Placeholder
        
        return {
            "long": long_exposure,
            "short": short_exposure,
        }
    
    def get_net_exposure(self) -> float:
        """
        Get net exposure (long - short).
        
        Returns:
            Net exposure
        """
        exposure = self.get_direction_exposure()
        return exposure["long"] - exposure["short"]
    
    def get_gross_exposure(self) -> float:
        """
        Get gross exposure (long + short).
        
        Returns:
            Gross exposure
        """
        exposure = self.get_direction_exposure()
        return exposure["long"] + exposure["short"]


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ExposureManager",
    "PositionLimitManager",
    "DirectionExposureManager",
]
