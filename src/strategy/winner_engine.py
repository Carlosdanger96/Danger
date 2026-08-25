"""
Winner engine for Project DEGENERATE.

Extreme winners should be exploited:
- At +100%: Recover approximately initial premium
- Continue holding or roll some profit into higher-convexity contract
- Creates possibility of nonlinear compounding during major move
"""

import logging
from typing import Any

from src.config import init_config
from src.models import (
    Position,
    TradeSignal,
)
from src.state import get_portfolio_manager, get_signal_aggregator

logger = logging.getLogger(__name__)


# =============================================================================
# Winner Engine
# =============================================================================

class WinnerEngine:
    """
    Manages winning positions to maximize returns.
    
    Potential sequence:
    $5k -> $10k -> principal removed -> $5k runner -> $20k -> roll $10k -> new high-gamma position
    
    This creates the possibility of nonlinear compounding during a major move.
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def check_winners(self) -> list[Position]:
        """
        Check all open positions for winners.
        
        Returns:
            List of winning positions
        """
        portfolio = get_portfolio_manager()
        positions = []
        
        for sleeve in portfolio.sleeves.values():
            for pos_symbol in sleeve.open_positions:
                # In production, get actual position from database
                # For now, create placeholder
                position = Position(
                    symbol=pos_symbol,
                    underlying=pos_symbol.split()[0] if ' ' in pos_symbol else pos_symbol,
                    quantity=1,
                    entry_price=1.0,
                    current_price=2.0,  # Placeholder - would be actual price
                )
                positions.append(position)
        
        # Filter for winners
        winners = [p for p in positions if p.unrealized_pnl > 0]
        
        return winners
    
    def is_extreme_winner(self, position: Position, threshold: float = 1.0) -> bool:
        """
        Check if a position is an extreme winner.
        
        At +100%: Recover approximately initial premium.
        
        Args:
            position: The position to check
            threshold: Minimum return multiple to be considered extreme
            
        Returns:
            True if position is an extreme winner
        """
        if position.entry_price <= 0:
            return False
        
        current_value = position.current_price * position.absolute_quantity
        cost_basis = position.entry_price * position.absolute_quantity
        
        if cost_basis <= 0:
            return False
        
        return_percent = (current_value - cost_basis) / cost_basis
        
        return return_percent >= threshold
    
    def manage_winner(self, position: Position) -> dict[str, Any]:
        """
        Manage a winning position.
        
        Strategy:
        - At +100%: Recover approximately initial premium
        - Continue holding or roll some profit into higher-convexity contract
        
        Args:
            position: The winning position
            
        Returns:
            Dictionary with management actions
        """
        if not self.is_extreme_winner(position, threshold=1.0):
            return {"action": "hold", "reason": "not extreme winner yet"}
        
        # Calculate current value
        current_value = position.current_price * position.absolute_quantity
        cost_basis = position.entry_price * position.absolute_quantity
        
        if cost_basis <= 0:
            return {"action": "hold", "reason": "invalid cost basis"}
        
        return_percent = (current_value - cost_basis) / cost_basis
        
        # Determine action based on return
        if return_percent >= 2.0:  # 200% return
            # Consider rolling profits into higher-convexity position
            return {
                "action": "consider_roll",
                "reason": f"{return_percent:.0%} return - consider rolling profits",
                "principal_recovered": cost_basis,
                "runner_value": current_value - cost_basis,
            }
        elif return_percent >= 1.0:  # 100% return
            # Recover principal, keep runner
            return {
                "action": "recover_principal",
                "reason": f"{return_percent:.0%} return - recover principal",
                "principal_recovered": cost_basis,
                "runner_value": current_value - cost_basis,
            }
        else:
            return {"action": "hold", "reason": f"{return_percent:.0%} return - continue holding"}
    
    def calculate_runner_size(self, position: Position) -> float:
        """
        Calculate the size of the runner after recovering principal.
        
        Args:
            position: The winning position
            
        Returns:
            Dollar value of the runner
        """
        current_value = position.current_price * position.absolute_quantity
        cost_basis = position.entry_price * position.absolute_quantity
        
        if cost_basis <= 0:
            return 0.0
        
        return max(0, current_value - cost_basis)
    
    def roll_to_higher_convexity(
        self,
        position: Position,
        runner_size: float,
    ) -> dict[str, Any]:
        """
        Roll profits into a higher-convexity contract.
        
        Args:
            position: The current winning position
            runner_size: Size of the runner to roll
            
        Returns:
            Dictionary with roll information
        """
        # Placeholder - would select new contract with higher convexity
        
        return {
            "action": "roll",
            "runner_size": runner_size,
            "new_contract": None,  # Would be selected contract
            "reason": "Rolling runner into higher-convexity position",
        }
    
    def manage_all_winners(self) -> dict[str, Any]:
        """
        Manage all winning positions.
        
        Returns:
            Dictionary with all winner management actions
        """
        winners = self.check_winners()
        results = {}
        
        for winner in winners:
            action = self.manage_winner(winner)
            results[winner.symbol] = action
            
            if action["action"] == "recover_principal":
                runner_size = self.calculate_runner_size(winner)
                logger.info(
                    f"Winner: {winner.symbol} at {action['reason']} | "
                    f"Principal: ${action['principal_recovered']:,.2f} | "
                    f"Runner: ${runner_size:,.2f}"
                )
            elif action["action"] == "consider_roll":
                runner_size = self.calculate_runner_size(winner)
                logger.info(
                    f"Extreme Winner: {winner.symbol} at {action['reason']} | "
                    f"Runner: ${runner_size:,.2f} | "
                    f"Consider rolling to higher convexity"
                )
        
        return results


# =============================================================================
# Compound Tracker
# =============================================================================

class CompoundTracker:
    """Tracks compounding of winners across trades."""
    
    def __init__(self):
        self.compound_chain: list[dict[str, Any]] = []
    
    def record_compound(
        self,
        trade_id: str,
        initial_size: float,
        final_size: float,
        return_multiple: float,
    ) -> None:
        """
        Record a compounding event.
        
        Args:
            trade_id: The trade ID
            initial_size: Initial position size
            final_size: Final position size
            return_multiple: Return multiple
        """
        self.compound_chain.append({
            "trade_id": trade_id,
            "initial_size": initial_size,
            "final_size": final_size,
            "return_multiple": return_multiple,
            "timestamp": datetime.utcnow(),
        })
        
        logger.info(
            f"Compound: {trade_id} | ${initial_size:,.2f} -> ${final_size:,.2f} | "
            f"{return_multiple:.2f}x"
        )
    
    def get_compound_chain(self) -> list[dict[str, Any]]:
        """Get the complete compound chain."""
        return self.compound_chain
    
    def get_total_compound_return(self) -> float:
        """
        Calculate total compound return.
        
        Returns:
            Total compound return as a multiple
        """
        if not self.compound_chain:
            return 1.0
        
        total = 1.0
        for link in self.compound_chain:
            total *= link["return_multiple"]
        
        return total


# =============================================================================
# Profit Taking Strategy
# =============================================================================

class ProfitTakingStrategy:
    """Strategy for taking profits on winning positions."""
    
    def __init__(self):
        self.levels = {
            0.5: 0.25,   # Take 25% off at 50% profit
            1.0: 0.50,   # Take 50% off at 100% profit
            1.5: 0.25,   # Take 25% more at 150% profit
            2.0: 0.25,   # Take 25% more at 200% profit
        }
    
    def should_take_profits(self, position: Position) -> tuple[bool, float]:
        """
        Check if we should take profits on a position.
        
        Args:
            position: The position to check
            
        Returns:
            Tuple of (should_take, percentage_to_take)
        """
        if position.entry_price <= 0:
            return False, 0.0
        
        current_value = position.current_price * position.absolute_quantity
        cost_basis = position.entry_price * position.absolute_quantity
        
        if cost_basis <= 0:
            return False, 0.0
        
        return_percent = (current_value - cost_basis) / cost_basis
        
        # Check each level
        for level, percentage in sorted(self.levels.items(), reverse=True):
            if return_percent >= level:
                return True, percentage
        
        return False, 0.0
    
    def calculate_take_profit_order(
        self,
        position: Position,
        percentage: float,
    ) -> dict[str, Any]:
        """
        Calculate order to take profits.
        
        Args:
            position: The position
            percentage: Percentage of position to close
            
        Returns:
            Dictionary with order details
        """
        quantity_to_close = int(position.absolute_quantity * percentage)
        
        return {
            "symbol": position.symbol,
            "quantity": quantity_to_close,
            "side": "SELL_TO_CLOSE" if position.is_long else "BUY_TO_CLOSE",
            "order_type": "MARKET",
            "reason": f"Taking {percentage:.0%} profits at {position.unrealized_pnl:.2f}",
        }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "WinnerEngine",
    "CompoundTracker",
    "ProfitTakingStrategy",
]
