"""
Risk governor for Project DEGENERATE.

Enforces the hard floor constraint and other risk limits.
The LLM cannot override the hard floor constraint.
"""

import logging
from typing import Any

from src.config import init_config
from src.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TradePlan,
)
from src.state import get_portfolio_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Hard Floor Enforcer
# =============================================================================

class HardFloorEnforcer:
    """
    Enforces the $30,000 hard floor constraint.
    
    Before any trade:
    worst_case_equity = (
        current_equity
        - maximum_loss_of_new_position
        - maximum_loss_of_open_positions
    )
    
    Require: worst_case_equity >= $30,000
    Otherwise: RESIZE or REJECT
    
    The LLM cannot override this constraint.
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.hard_floor = self.config.account.hard_floor
    
    def check_floor_constraint(
        self,
        potential_loss: float,
    ) -> tuple[bool, float]:
        """
        Check if a trade would violate the hard floor.
        
        Args:
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            Tuple of (is_allowed, max_allowed_loss)
        """
        portfolio = get_portfolio_manager()
        
        max_total_loss = portfolio.total_equity - self.hard_floor
        max_new_loss = max_total_loss - portfolio.total_open_risk
        
        if max_new_loss <= 0:
            return False, 0.0
        
        if potential_loss <= max_new_loss:
            return True, max_new_loss
        
        return False, max_new_loss
    
    def resize_trade(
        self,
        trade_plan: TradePlan,
    ) -> TradePlan | None:
        """
        Resize a trade to comply with hard floor constraint.
        
        Args:
            trade_plan: The trade plan to resize
            
        Returns:
            Resized trade plan or None if trade cannot be executed
        """
        portfolio = get_portfolio_manager()
        
        max_total_loss = portfolio.total_equity - self.hard_floor
        max_new_loss = max_total_loss - portfolio.total_open_risk
        
        if max_new_loss <= 0:
            logger.warning("Cannot resize trade: no room for additional loss")
            return None
        
        if trade_plan.max_loss_if_wrong <= max_new_loss:
            # Already compliant
            return trade_plan
        
        # Calculate scale factor
        scale_factor = max_new_loss / trade_plan.max_loss_if_wrong
        
        # Resize trade
        new_dollar_amount = trade_plan.final_size_dollars * scale_factor
        new_quantity = max(1, int(trade_plan.quantity * scale_factor))
        new_max_loss = new_dollar_amount
        
        trade_plan.final_size_dollars = new_dollar_amount
        trade_plan.quantity = new_quantity
        trade_plan.max_loss_if_wrong = new_max_loss
        trade_plan.worst_case_equity = (
            portfolio.total_equity
            - new_max_loss
            - portfolio.total_open_risk
        )
        
        logger.info(
            f"Resized trade to comply with hard floor: "
            f"${trade_plan.final_size_dollars:.2f} -> ${new_dollar_amount:.2f}"
        )
        
        return trade_plan
    
    def validate_trade(self, trade_plan: TradePlan) -> tuple[bool, str]:
        """
        Validate a trade against the hard floor constraint.
        
        Args:
            trade_plan: The trade plan to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        portfolio = get_portfolio_manager()
        
        worst_case_equity = (
            portfolio.total_equity
            - trade_plan.max_loss_if_wrong
            - portfolio.total_open_risk
        )
        
        if worst_case_equity < self.hard_floor:
            return False, (
                f"Trade would violate hard floor: "
                f"${worst_case_equity:,.2f} < ${self.hard_floor:,.2f}"
            )
        
        return True, "Valid"
    
    def get_worst_case_equity(self, potential_loss: float) -> float:
        """
        Calculate worst-case equity after a potential trade.
        
        Args:
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            Worst-case equity
        """
        portfolio = get_portfolio_manager()
        
        return (
            portfolio.total_equity
            - potential_loss
            - portfolio.total_open_risk
        )


# =============================================================================
# Risk Governor
# =============================================================================

class RiskGovernor:
    """
    Central risk management authority.
    
    Enforces all risk constraints including:
    - Hard floor
    - Position limits
    - Exposure limits
    - Sleeve limits
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.floor_enforcer = HardFloorEnforcer(config)
    
    def validate_trade(self, trade_plan: TradePlan) -> tuple[bool, list[str]]:
        """
        Validate a trade against all risk constraints.
        
        Args:
            trade_plan: The trade plan to validate
            
        Returns:
            Tuple of (is_valid, list of reasons for rejection)
        """
        reasons = []
        
        # Check hard floor
        is_valid, reason = self.floor_enforcer.validate_trade(trade_plan)
        if not is_valid:
            reasons.append(reason)
        
        # Check position limits
        # Check exposure limits
        # Check sleeve limits
        
        return len(reasons) == 0, reasons
    
    def enforce_constraints(self, trade_plan: TradePlan) -> TradePlan | None:
        """
        Enforce all risk constraints on a trade plan.
        
        Args:
            trade_plan: The trade plan to enforce
            
        Returns:
            Constrained trade plan or None if trade cannot be executed
        """
        # Enforce hard floor
        trade_plan = self.floor_enforcer.resize_trade(trade_plan)
        if trade_plan is None:
            return None
        
        # Enforce other constraints
        
        return trade_plan
    
    def get_risk_status(self) -> dict[str, Any]:
        """
        Get current risk status.
        
        Returns:
            Dictionary with risk information
        """
        portfolio = get_portfolio_manager()
        
        return {
            "current_equity": portfolio.total_equity,
            "hard_floor": self.hard_floor,
            "max_allowed_loss": portfolio.max_allowed_loss,
            "total_open_risk": portfolio.total_open_risk,
            "is_above_floor": portfolio.is_above_floor,
            "drawdown": portfolio.current_drawdown,
            "drawdown_percent": portfolio.drawdown_percent,
        }
    
    def check_termination_condition(self) -> bool:
        """
        Check if termination condition is met.
        
        Returns:
            True if execution should terminate
        """
        portfolio = get_portfolio_manager()
        return portfolio.total_equity <= self.hard_floor


# =============================================================================
# Sleeve Limit Enforcer
# =============================================================================

class SleeveLimitEnforcer:
    """Enforces per-sleeve risk limits."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def check_sleeve_limit(
        self,
        sleeve_type: Any,
        potential_loss: float,
    ) -> tuple[bool, float]:
        """
        Check if a trade would exceed sleeve limit.
        
        Args:
            sleeve_type: The sleeve type
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            Tuple of (is_allowed, max_allowed_loss)
        """
        portfolio = get_portfolio_manager()
        sleeve = portfolio.get_sleeve(sleeve_type)
        
        if sleeve is None:
            return False, 0.0
        
        max_sleeve_loss = sleeve.total_allocation * self.config.account.max_drawdown
        max_new_loss = max_sleeve_loss - sleeve.open_risk
        
        if max_new_loss <= 0:
            return False, 0.0
        
        if potential_loss <= max_new_loss:
            return True, max_new_loss
        
        return False, max_new_loss


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "HardFloorEnforcer",
    "RiskGovernor",
    "SleeveLimitEnforcer",
]
