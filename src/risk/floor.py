"""
Floor monitoring for Project DEGENERATE.

Monitors the $30,000 hard floor and enforces constraints.
"""

import logging
from typing import Any

from src.config import init_config
from src.state import get_portfolio_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Floor Monitor
# =============================================================================

class FloorMonitor:
    """
    Monitors the hard floor constraint in real-time.
    
    Starting equity: $100,000
    Maximum allowed cumulative loss: $70,000
    Absolute equity floor: $30,000
    
    Before any trade:
    worst_case_equity = (
        current_equity
        - maximum_loss_of_new_position
        - maximum_loss_of_open_positions
    )
    
    Require: worst_case_equity >= $30,000
    Otherwise: RESIZE or REJECT
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.hard_floor = self.config.account.hard_floor
        self.starting_equity = self.config.account.starting_equity
        self.max_drawdown = self.config.account.max_drawdown
    
    def check_floor(self) -> bool:
        """
        Check if portfolio is above the hard floor.
        
        Returns:
            True if above floor, False if at or below floor
        """
        portfolio = get_portfolio_manager()
        return portfolio.is_above_floor
    
    def get_floor_status(self) -> dict[str, Any]:
        """
        Get current floor status.
        
        Returns:
            Dictionary with floor information
        """
        portfolio = get_portfolio_manager()
        
        return {
            "current_equity": portfolio.total_equity,
            "hard_floor": self.hard_floor,
            "is_above_floor": portfolio.is_above_floor,
            "distance_to_floor": portfolio.total_equity - self.hard_floor,
            "max_allowed_loss": portfolio.max_allowed_loss,
        }
    
    def check_worst_case(
        self,
        potential_loss: float,
    ) -> tuple[bool, float, float]:
        """
        Check worst-case equity after a potential trade.
        
        Args:
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            Tuple of (is_safe, worst_case_equity, max_allowed_loss)
        """
        portfolio = get_portfolio_manager()
        
        worst_case_equity = (
            portfolio.total_equity
            - potential_loss
            - portfolio.total_open_risk
        )
        
        max_allowed_loss = portfolio.total_equity - self.hard_floor - portfolio.total_open_risk
        
        is_safe = worst_case_equity >= self.hard_floor
        
        return is_safe, worst_case_equity, max_allowed_loss
    
    def get_resize_factor(self, potential_loss: float) -> float:
        """
        Calculate resize factor to stay above floor.
        
        Args:
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            Factor to multiply position size by
        """
        portfolio = get_portfolio_manager()
        
        max_allowed_loss = portfolio.total_equity - self.hard_floor - portfolio.total_open_risk
        
        if max_allowed_loss <= 0:
            return 0.0
        
        if potential_loss <= 0:
            return 1.0
        
        return min(max_allowed_loss / potential_loss, 1.0)
    
    def monitor_and_alert(self) -> None:
        """
        Monitor floor status and alert if approaching floor.
        """
        status = self.get_floor_status()
        
        if not status["is_above_floor"]:
            logger.critical(
                f"FLOOR VIOLATION: Equity ${status['current_equity']:,.2f} "
                f"<= ${self.hard_floor:,.2f}"
            )
        elif status["distance_to_floor"] < 5000:
            logger.warning(
                f"FLOOR APPROACH: Equity ${status['current_equity']:,.2f} "
                f"within ${status['distance_to_floor']:,.2f} of floor"
            )
        elif status["distance_to_floor"] < 10000:
            logger.info(
                f"FLOOR NEAR: Equity ${status['current_equity']:,.2f} "
                f"within ${status['distance_to_floor']:,.2f} of floor"
            )


# =============================================================================
# Floor Alert Levels
# =============================================================================

class FloorAlertLevel:
    """Defines alert levels for floor monitoring."""
    
    CRITICAL = "CRITICAL"      # At or below floor
    WARNING = "WARNING"        # Within $5,000 of floor
    INFO = "INFO"            # Within $10,000 of floor
    NORMAL = "NORMAL"        # Above $10,000 from floor
    
    @staticmethod
    def get_level(distance_to_floor: float, hard_floor: float) -> str:
        """
        Get alert level based on distance to floor.
        
        Args:
            distance_to_floor: Current distance to floor
            hard_floor: Hard floor value
            
        Returns:
            Alert level string
        """
        if distance_to_floor <= 0:
            return FloorAlertLevel.CRITICAL
        elif distance_to_floor <= 5000:
            return FloorAlertLevel.WARNING
        elif distance_to_floor <= 10000:
            return FloorAlertLevel.INFO
        else:
            return FloorAlertLevel.NORMAL


# =============================================================================
# Floor Violation Handler
# =============================================================================

class FloorViolationHandler:
    """Handles actions when floor is violated."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.floor_monitor = FloorMonitor(config)
    
    def handle_violation(self) -> None:
        """
        Handle floor violation.
        
        At equity <= $30,000: execution terminates.
        """
        portfolio = get_portfolio_manager()
        
        if portfolio.total_equity <= self.config.account.hard_floor:
            logger.critical("HARD FLOOR VIOLATED - TERMINATING EXECUTION")
            
            # Terminate all open positions
            # Close all open orders
            # Stop trading
            
            raise RuntimeError(
                f"Hard floor violated: ${portfolio.total_equity:,.2f} "
                f"<= ${self.config.account.hard_floor:,.2f}. Execution terminated."
            )
    
    def check_and_handle(self) -> None:
        """Check for floor violation and handle if necessary."""
        if not self.floor_monitor.check_floor():
            self.handle_violation()


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "FloorMonitor",
    "FloorAlertLevel",
    "FloorViolationHandler",
]
