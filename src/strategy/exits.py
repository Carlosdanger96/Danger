"""
Exit strategies for Project DEGENERATE.

Handles:
- Stop losses
- Take profits
- Time-based exits
- Signal-based exits
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.config import init_config
from src.models import (
    OptionContract,
    Position,
    SignalDirection,
    TradeSignal,
)
from src.state import get_portfolio_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Exit Strategy Base Class
# =============================================================================

class ExitStrategy:
    """Base class for exit strategies."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def should_exit(self, position: Position, current_price: float) -> tuple[bool, str]:
        """
        Check if we should exit a position.
        
        Args:
            position: The position to check
            current_price: Current market price
            
        Returns:
            Tuple of (should_exit, reason)
        """
        return False, ""
    
    def get_exit_order(
        self,
        position: Position,
        reason: str,
    ) -> dict[str, Any]:
        """
        Generate exit order.
        
        Args:
            position: The position to exit
            reason: Reason for exit
            
        Returns:
            Dictionary with order details
        """
        return {
            "symbol": position.symbol,
            "quantity": position.absolute_quantity,
            "side": "SELL_TO_CLOSE" if position.is_long else "BUY_TO_CLOSE",
            "order_type": "MARKET",
            "reason": reason,
        }


# =============================================================================
# Stop Loss Manager
# =============================================================================

class StopLossManager(ExitStrategy):
    """Manages stop losses for positions."""
    
    def __init__(self, config: Any = None, stop_loss_percent: float = 0.50):
        super().__init__(config)
        self.stop_loss_percent = stop_loss_percent  # 50% stop loss by default
    
    def should_exit(self, position: Position, current_price: float) -> tuple[bool, str]:
        """
        Check if stop loss is hit.
        
        Args:
            position: The position
            current_price: Current market price
            
        Returns:
            Tuple of (should_exit, reason)
        """
        if position.entry_price <= 0:
            return False, ""
        
        # Calculate current loss
        if position.is_long:
            loss_percent = (position.entry_price - current_price) / position.entry_price
        else:  # Short position
            loss_percent = (current_price - position.entry_price) / position.entry_price
        
        if loss_percent >= self.stop_loss_percent:
            return True, f"Stop loss hit: {loss_percent:.1%} loss"
        
        return False, ""
    
    def set_stop_loss(self, position: Position, stop_loss_percent: float) -> None:
        """
        Set stop loss for a position.
        
        Args:
            position: The position
            stop_loss_percent: Stop loss as percentage of entry price
        """
        self.stop_loss_percent = stop_loss_percent


# =============================================================================
# Take Profit Manager
# =============================================================================

class TakeProfitManager(ExitStrategy):
    """Manages take profit levels for positions."""
    
    def __init__(self, config: Any = None):
        super().__init__(config)
        # Multiple take profit levels
        self.levels = [
            {"percent": 0.50, "take_percent": 0.25},   # Take 25% at 50%
            {"percent": 1.00, "take_percent": 0.50},   # Take 50% at 100%
            {"percent": 1.50, "take_percent": 0.25},   # Take 25% at 150%
        ]
    
    def should_exit(self, position: Position, current_price: float) -> tuple[bool, str]:
        """
        Check if we should take profits.
        
        Args:
            position: The position
            current_price: Current market price
            
        Returns:
            Tuple of (should_exit, reason)
        """
        if position.entry_price <= 0:
            return False, ""
        
        # Calculate current profit
        if position.is_long:
            return_percent = (current_price - position.entry_price) / position.entry_price
        else:  # Short position
            return_percent = (position.entry_price - current_price) / position.entry_price
        
        # Check each level
        for level in self.levels:
            if return_percent >= level["percent"]:
                return True, f"Take profit at {return_percent:.1%}"
        
        return False, ""
    
    def get_take_profit_order(
        self,
        position: Position,
        current_price: float,
    ) -> dict[str, Any] | None:
        """
        Generate take profit order.
        
        Args:
            position: The position
            current_price: Current market price
            
        Returns:
            Dictionary with order details or None
        """
        if position.entry_price <= 0:
            return None
        
        if position.is_long:
            return_percent = (current_price - position.entry_price) / position.entry_price
        else:
            return_percent = (position.entry_price - current_price) / position.entry_price
        
        # Find which level we're at
        for level in self.levels:
            if return_percent >= level["percent"]:
                quantity = int(position.absolute_quantity * level["take_percent"])
                return {
                    "symbol": position.symbol,
                    "quantity": quantity,
                    "side": "SELL_TO_CLOSE" if position.is_long else "BUY_TO_CLOSE",
                    "order_type": "MARKET",
                    "reason": f"Taking {level['take_percent']:.0%} profits at {return_percent:.1%}",
                }
        
        return None


# =============================================================================
# Time-Based Exit
# =============================================================================

class TimeBasedExit(ExitStrategy):
    """Exits positions based on time."""
    
    def __init__(self, config: Any = None, max_hold_days: int = 7):
        super().__init__(config)
        self.max_hold_days = max_hold_days
    
    def should_exit(self, position: Position, current_price: float) -> tuple[bool, str]:
        """
        Check if we should exit based on time.
        
        Args:
            position: The position
            current_price: Current market price
            
        Returns:
            Tuple of (should_exit, reason)
        """
        hold_time = datetime.utcnow() - position.entry_timestamp
        
        if hold_time >= timedelta(days=self.max_hold_days):
            return True, f"Max hold time ({self.max_hold_days} days) reached"
        
        # Also check if near expiration for options
        if hasattr(position, 'expiration') and position.expiration:
            time_to_expiry = position.expiration - datetime.utcnow()
            if time_to_expiry <= timedelta(days=1):
                return True, "Near expiration"
        
        return False, ""


# =============================================================================
# Signal-Based Exit
# =============================================================================

class SignalBasedExit(ExitStrategy):
    """Exits positions based on signal changes."""
    
    def __init__(self, config: Any = None):
        super().__init__(config)
    
    def should_exit(
        self,
        position: Position,
        current_price: float,
        current_signal: TradeSignal | None = None,
    ) -> tuple[bool, str]:
        """
        Check if we should exit based on signal changes.
        
        Args:
            position: The position
            current_price: Current market price
            current_signal: Current signal for the ticker
            
        Returns:
            Tuple of (should_exit, reason)
        """
        # If signal has reversed, consider exiting
        if current_signal:
            # Get original signal direction from position metadata
            # This would need to be stored when position was opened
            original_direction = SignalDirection.CALL  # Placeholder
            
            if current_signal.direction != original_direction:
                return True, f"Signal reversed: {original_direction} -> {current_signal.direction}"
            
            # If signal confidence dropped significantly
            if current_signal.confidence < 0.5:
                return True, "Signal confidence dropped"
        
        return False, ""


# =============================================================================
# Exit Manager
# =============================================================================

class ExitManager:
    """Manages all exit strategies."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.stop_loss = StopLossManager(config)
        self.take_profit = TakeProfitManager(config)
        self.time_exit = TimeBasedExit(config)
        self.signal_exit = SignalBasedExit(config)
    
    def check_all_exits(
        self,
        position: Position,
        current_price: float,
        current_signal: TradeSignal | None = None,
    ) -> list[dict[str, Any]]:
        """
        Check all exit strategies for a position.
        
        Args:
            position: The position
            current_price: Current market price
            current_signal: Current signal for the ticker
            
        Returns:
            List of exit orders to execute
        """
        exit_orders = []
        
        # Check stop loss
        should_exit, reason = self.stop_loss.should_exit(position, current_price)
        if should_exit:
            exit_orders.append(self.stop_loss.get_exit_order(position, reason))
            logger.info(f"Exit: {position.symbol} - {reason}")
            return exit_orders  # Stop loss takes precedence
        
        # Check take profit
        take_profit_order = self.take_profit.get_take_profit_order(position, current_price)
        if take_profit_order:
            exit_orders.append(take_profit_order)
            logger.info(f"Exit: {position.symbol} - {take_profit_order['reason']}")
            return exit_orders  # Take profit
        
        # Check time-based exit
        should_exit, reason = self.time_exit.should_exit(position, current_price)
        if should_exit:
            exit_orders.append(self.time_exit.get_exit_order(position, reason))
            logger.info(f"Exit: {position.symbol} - {reason}")
            return exit_orders
        
        # Check signal-based exit
        should_exit, reason = self.signal_exit.should_exit(position, current_price, current_signal)
        if should_exit:
            exit_orders.append(self.signal_exit.get_exit_order(position, reason))
            logger.info(f"Exit: {position.symbol} - {reason}")
        
        return exit_orders
    
    def check_all_positions(self) -> dict[str, list[dict[str, Any]]]:
        """
        Check all open positions for exits.
        
        Returns:
            Dictionary mapping position symbol to list of exit orders
        """
        portfolio = get_portfolio_manager()
        results = {}
        
        for sleeve in portfolio.sleeves.values():
            for pos_symbol in sleeve.open_positions:
                # Get position (placeholder - would get from database)
                position = Position(
                    symbol=pos_symbol,
                    underlying=pos_symbol.split()[0] if ' ' in pos_symbol else pos_symbol,
                    quantity=1,
                    entry_price=1.0,
                    current_price=1.5,  # Placeholder
                )
                
                # Get current signal for this ticker
                ticker = position.underlying
                signal_aggregator = get_signal_aggregator()
                signals = signal_aggregator.get_signals_by_ticker(ticker)
                current_signal = signals[0] if signals else None
                
                # Check exits
                exit_orders = self.check_all_exits(position, position.current_price, current_signal)
                if exit_orders:
                    results[pos_symbol] = exit_orders
        
        return results


# =============================================================================
# Forced Exit
# =============================================================================

class ForcedExit(ExitStrategy):
    """Forces exit of all positions (for termination)."""
    
    def __init__(self, config: Any = None):
        super().__init__(config)
    
    def exit_all_positions(self) -> list[dict[str, Any]]:
        """
        Generate orders to exit all positions.
        
        Returns:
            List of exit orders for all positions
        """
        portfolio = get_portfolio_manager()
        exit_orders = []
        
        for sleeve in portfolio.sleeves.values():
            for pos_symbol in sleeve.open_positions:
                # Create placeholder position
                position = Position(
                    symbol=pos_symbol,
                    underlying=pos_symbol.split()[0] if ' ' in pos_symbol else pos_symbol,
                    quantity=1,
                    entry_price=1.0,
                    current_price=1.0,
                )
                
                exit_order = self.get_exit_order(position, "Forced exit - termination")
                exit_orders.append(exit_order)
                
                logger.info(f"Forced exit: {pos_symbol}")
        
        return exit_orders


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ExitStrategy",
    "StopLossManager",
    "TakeProfitManager",
    "TimeBasedExit",
    "SignalBasedExit",
    "ExitManager",
    "ForcedExit",
]
