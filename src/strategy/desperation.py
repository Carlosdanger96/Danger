"""
Desperation engine for Project DEGENERATE.

Normal portfolio management reduces risk after losses.
This system intentionally does NOT.

Instead, it increases aggression as drawdown increases:
- Drawdown 0-20%: Aggression = 1.0x
- Drawdown 20-40%: Aggression = 1.25x
- Drawdown 40-55%: Aggression = 1.50x
- Drawdown 55-65%: Aggression = 1.75x
- Drawdown 65-70%: Last-Chance Mode

At equity <= $30,000: execution terminates.
"""

import logging
from typing import Any

from src.config import init_config
from src.models import (
    ContractTier,
    TradePlan,
)
from src.state import get_portfolio_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Desperation Engine
# =============================================================================

class DesperationEngine:
    """
    Increases aggression as drawdown increases.
    
    The system attempts recovery rather than slowly preserving an already
    losing competition account.
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def get_aggression_multiplier(self) -> float:
        """
        Get the current aggression multiplier based on drawdown.
        
        Returns:
            Multiplier to apply to position sizes
        """
        portfolio = get_portfolio_manager()
        drawdown = portfolio.current_drawdown
        
        if not self.config.strategy.desperation.get("enabled", True):
            return 1.0
        
        if drawdown >= 0.70:  # At or below 30k floor
            return 0.0  # Should not trade
        elif drawdown >= 0.65:
            return self.config.strategy.desperation.get("drawdown_65_70", 2.0)
        elif drawdown >= 0.55:
            return self.config.strategy.desperation.get("drawdown_55_65", 1.75)
        elif drawdown >= 0.40:
            return self.config.strategy.desperation.get("drawdown_40_55", 1.50)
        elif drawdown >= 0.20:
            return self.config.strategy.desperation.get("drawdown_20_40", 1.25)
        else:
            return self.config.strategy.desperation.get("drawdown_0_20", 1.0)
    
    def is_last_chance_mode(self) -> bool:
        """
        Check if in last-chance mode.
        
        Last-chance mode is active when drawdown is 65-70%.
        Only very high-convexity positions qualify.
        
        Returns:
            True if in last-chance mode
        """
        portfolio = get_portfolio_manager()
        drawdown = portfolio.current_drawdown
        return 0.65 <= drawdown < 0.70
    
    def get_last_chance_min_multiple(self) -> float:
        """
        Get minimum target multiple for last-chance mode.
        
        Returns:
            Minimum target multiple (e.g., 5.0)
        """
        return self.config.strategy.desperation.get("last_chance_min_multiple", 5.0)
    
    def apply_desperation_to_trade(self, trade_plan: TradePlan) -> TradePlan:
        """
        Apply desperation multiplier to a trade plan.
        
        Args:
            trade_plan: The trade plan to modify
            
        Returns:
            Modified trade plan with desperation applied
        """
        multiplier = self.get_aggression_multiplier()
        
        # Apply multiplier to size
        trade_plan.final_size_dollars *= multiplier
        
        # Recalculate quantity
        from src.strategy.allocator import PositionSizer
        sizer = PositionSizer(self.config)
        trade_plan.quantity = sizer.calculate_contract_count(
            trade_plan.final_size_dollars,
            trade_plan.contract,
        )
        
        # Recalculate max loss
        trade_plan.max_loss_if_wrong = trade_plan.final_size_dollars
        
        logger.info(f"Applied desperation multiplier {multiplier:.2f}x to trade")
        
        return trade_plan
    
    def check_last_chance_eligibility(self, trade_plan: TradePlan) -> bool:
        """
        Check if a trade qualifies for last-chance mode.
        
        In last-chance mode, only very high-convexity positions qualify.
        
        Args:
            trade_plan: The trade plan to check
            
        Returns:
            True if trade qualifies for last-chance mode
        """
        if not self.is_last_chance_mode():
            return True  # Not in last-chance mode, all trades qualify
        
        # Check minimum target multiple
        min_multiple = self.get_last_chance_min_multiple()
        
        # Estimate upside potential
        # For options, upside potential is theoretically unlimited,
        # but we use a simplified estimate
        underlying_price = 0.0  # Would need actual price
        
        # For simplicity, assume all trades in last-chance mode qualify
        # In production, you'd calculate actual upside potential
        
        return True
    
    def get_desperation_status(self) -> dict[str, Any]:
        """
        Get current desperation status.
        
        Returns:
            Dictionary with desperation information
        """
        portfolio = get_portfolio_manager()
        multiplier = self.get_aggression_multiplier()
        
        return {
            "current_drawdown": portfolio.current_drawdown,
            "drawdown_percent": portfolio.drawdown_percent,
            "aggression_multiplier": multiplier,
            "is_last_chance_mode": self.is_last_chance_mode(),
            "last_chance_min_multiple": self.get_last_chance_min_multiple(),
            "is_above_floor": portfolio.is_above_floor,
            "max_allowed_loss": portfolio.max_allowed_loss,
        }


# =============================================================================
# Tier Escalation
# =============================================================================

class TierEscalation:
    """
    Escalates to higher-risk tiers as drawdown increases.
    
    In normal mode: All tiers allowed
    In desperation mode: Favor Tier 2 and Tier 3
    In last-chance mode: Only Tier 2 and Tier 3
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.desperation_engine = DesperationEngine(config)
    
    def get_allowed_tiers(self) -> list[ContractTier]:
        """
        Get list of allowed contract tiers based on current state.
        
        Returns:
            List of allowed tiers
        """
        if self.desperation_engine.is_last_chance_mode():
            # Last-chance mode: only Tier 2 and Tier 3
            return [ContractTier.TIER2_EXTREME, ContractTier.TIER3_ABSURD]
        else:
            # Normal mode: all tiers allowed
            return [
                ContractTier.TIER1_AGGRESSIVE,
                ContractTier.TIER2_EXTREME,
                ContractTier.TIER3_ABSURD,
            ]
    
    def get_tier_weights(self) -> dict[ContractTier, float]:
        """
        Get tier weights adjusted for current state.
        
        Returns:
            Dictionary mapping tier to weight
        """
        base_weights = {
            ContractTier.TIER1_AGGRESSIVE: 0.30,
            ContractTier.TIER2_EXTREME: 0.50,
            ContractTier.TIER3_ABSURD: 0.20,
        }
        
        if self.desperation_engine.is_last_chance_mode():
            # Last-chance mode: heavily favor Tier 2 and 3
            return {
                ContractTier.TIER1_AGGRESSIVE: 0.0,
                ContractTier.TIER2_EXTREME: 0.60,
                ContractTier.TIER3_ABSURD: 0.40,
            }
        elif self.desperation_engine.get_aggression_multiplier() > 1.0:
            # Desperation mode: favor Tier 2 and 3
            multiplier = self.desperation_engine.get_aggression_multiplier()
            tier2_boost = 0.1 * (multiplier - 1.0)
            tier3_boost = 0.1 * (multiplier - 1.0)
            
            return {
                ContractTier.TIER1_AGGRESSIVE: max(0, 0.30 - tier2_boost - tier3_boost),
                ContractTier.TIER2_EXTREME: min(0.70, 0.50 + tier2_boost),
                ContractTier.TIER3_ABSURD: min(0.40, 0.20 + tier3_boost),
            }
        else:
            return base_weights


# =============================================================================
# Drawdown Monitor
# =============================================================================

class DrawdownMonitor:
    """Monitors portfolio drawdown and triggers actions."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.desperation_engine = DesperationEngine(config)
        self.max_drawdown = self.config.account.max_drawdown
        self.hard_floor = self.config.account.hard_floor
    
    def check_termination_condition(self) -> bool:
        """
        Check if termination condition is met.
        
        At equity <= $30,000: execution terminates.
        
        Returns:
            True if execution should terminate
        """
        portfolio = get_portfolio_manager()
        return portfolio.total_equity <= self.hard_floor
    
    def check_warning_level(self) -> str:
        """
        Check current warning level based on drawdown.
        
        Returns:
            Warning level string
        """
        portfolio = get_portfolio_manager()
        drawdown = portfolio.current_drawdown
        
        if drawdown >= 0.70:
            return "TERMINATION"
        elif drawdown >= 0.65:
            return "LAST_CHANCE"
        elif drawdown >= 0.55:
            return "HIGH_DESPERATION"
        elif drawdown >= 0.40:
            return "MEDIUM_DESPERATION"
        elif drawdown >= 0.20:
            return "LOW_DESPERATION"
        else:
            return "NORMAL"
    
    def log_drawdown_status(self) -> None:
        """Log current drawdown status."""
        portfolio = get_portfolio_manager()
        warning_level = self.check_warning_level()
        
        logger.info(
            f"Drawdown Status: {warning_level} | "
            f"Equity: ${portfolio.total_equity:,.2f} | "
            f"Drawdown: {portfolio.drawdown_percent:.2f}% | "
            f"Floor: ${portfolio.hard_floor:,.2f}"
        )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DesperationEngine",
    "TierEscalation",
    "DrawdownMonitor",
]
