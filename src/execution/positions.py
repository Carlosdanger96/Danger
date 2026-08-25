"""
Position management for Project DEGENERATE.

Tracks and manages open positions.
"""

import logging
from datetime import datetime
from typing import Any

from src.models import (
    OptionContract,
    OptionType,
    Position,
    SignalDirection,
    SignalSource,
    SleeveType,
    TradeExecution,
)
from src.execution.alpaca_mcp import get_executor
from src.database import get_position_repository

logger = logging.getLogger(__name__)


# =============================================================================
# Position Tracker
# =============================================================================

class PositionTracker:
    """Tracks all open positions."""
    
    def __init__(self):
        self.positions: dict[str, Position] = {}
        self.repo = get_position_repository()
    
    def add_position(self, position: Position) -> None:
        """
        Add or update a position.
        
        Args:
            position: The position to add
        """
        self.positions[position.symbol] = position
        self.repo.save_position(position)
        
        logger.info(
            f"Position: {position.symbol} | {position.quantity} @ "
            f"${position.entry_price:.2f} | "
            f"Sleeve: {position.sleeve_type}"
        )
    
    def update_position(self, symbol: str, current_price: float) -> None:
        """
        Update a position's current price.
        
        Args:
            symbol: The position symbol
            current_price: Current market price
        """
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = current_price
            self.repo.save_position(position)
            
            logger.debug(
                f"Updated {symbol}: ${current_price:.2f} | "
                f"P&L: ${position.unrealized_pnl:.2f}"
            )
    
    def close_position(self, symbol: str, exit_price: float) -> Position | None:
        """
        Close a position.
        
        Args:
            symbol: The position symbol
            exit_price: Exit price
            
        Returns:
            Closed position or None if not found
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.current_price = exit_price
        
        # Mark as closed
        self.repo.close_position(symbol, exit_price)
        del self.positions[symbol]
        
        logger.info(
            f"Closed {symbol}: ${exit_price:.2f} | "
            f"P&L: ${position.unrealized_pnl:.2f}"
        )
        
        return position
    
    def get_position(self, symbol: str) -> Position | None:
        """
        Get a position by symbol.
        
        Args:
            symbol: The position symbol
            
        Returns:
            Position or None if not found
        """
        if symbol in self.positions:
            return self.positions[symbol]
        
        # Try to get from database
        position = self.repo.get_position(symbol)
        if position:
            self.positions[symbol] = position
        
        return position
    
    def get_all_positions(self) -> list[Position]:
        """
        Get all open positions.
        
        Returns:
            List of all open positions
        """
        return list(self.positions.values())
    
    def get_positions_by_sleeve(self, sleeve_type: SleeveType) -> list[Position]:
        """
        Get positions for a specific sleeve.
        
        Args:
            sleeve_type: The sleeve type
            
        Returns:
            List of positions for the sleeve
        """
        return [
            p for p in self.positions.values()
            if p.sleeve_type == sleeve_type
        ]
    
    def get_positions_by_ticker(self, ticker: str) -> list[Position]:
        """
        Get positions for a specific ticker.
        
        Args:
            ticker: The stock ticker
            
        Returns:
            List of positions for the ticker
        """
        return [
            p for p in self.positions.values()
            if p.underlying == ticker
        ]
    
    def get_position_pnl(self, symbol: str) -> float:
        """
        Get unrealized P&L for a position.
        
        Args:
            symbol: The position symbol
            
        Returns:
            Unrealized P&L
        """
        position = self.get_position(symbol)
        if position:
            return position.unrealized_pnl
        return 0.0
    
    def get_total_pnl(self) -> float:
        """
        Get total unrealized P&L for all positions.
        
        Returns:
            Total unrealized P&L
        """
        return sum(
            p.unrealized_pnl for p in self.positions.values()
        )
    
    def refresh_all_prices(self) -> None:
        """Refresh prices for all positions."""
        executor = get_executor()
        
        for symbol in self.positions:
            # Get current price from Alpaca
            # For options, this would need to query the option chain
            # For now, use placeholder
            current_price = executor.client.get_underlying_price(
                self.positions[symbol].underlying
            )
            self.update_position(symbol, current_price)


# =============================================================================
# Position Manager
# =============================================================================

class PositionManager:
    """Manages position lifecycle."""
    
    def __init__(self):
        self.tracker = PositionTracker()
        self.executor = get_executor()
    
    def open_position(
        self,
        trade_execution: TradeExecution,
    ) -> Position | None:
        """
        Open a new position from a trade execution.
        
        Args:
            trade_execution: The trade execution
            
        Returns:
            Position or None if failed
        """
        if trade_execution.order is None or trade_execution.trade_plan is None:
            return None
        
        order = trade_execution.order
        trade_plan = trade_execution.trade_plan
        
        # Create position
        position = Position(
            symbol=order.symbol,
            underlying=trade_plan.contract.underlying,
            option_type=trade_plan.contract.option_type,
            strike=trade_plan.contract.strike,
            expiration=trade_plan.contract.expiration,
            quantity=order.quantity if order.side in ["BUY", "BUY_TO_OPEN"] else -order.quantity,
            entry_price=order.filled_price,
            entry_timestamp=datetime.utcnow(),
            current_price=order.filled_price,
            signal_source=trade_plan.signal.source,
            sleeve_type=trade_plan.sleeve_type,
        )
        
        self.tracker.add_position(position)
        
        return position
    
    def close_position(self, symbol: str, exit_price: float) -> Position | None:
        """
        Close a position.
        
        Args:
            symbol: The position symbol
            exit_price: Exit price
            
        Returns:
            Closed position or None
        """
        return self.tracker.close_position(symbol, exit_price)
    
    def partial_close(
        self,
        symbol: str,
        quantity: int,
        exit_price: float,
    ) -> Position | None:
        """
        Partially close a position.
        
        Args:
            symbol: The position symbol
            quantity: Quantity to close
            exit_price: Exit price
            
        Returns:
            Updated position or None
        """
        position = self.tracker.get_position(symbol)
        if position is None:
            return None
        
        if position.is_long:
            new_quantity = position.quantity - quantity
        else:
            new_quantity = position.quantity + quantity
        
        if new_quantity == 0:
            return self.close_position(symbol, exit_price)
        
        # Update position
        position.quantity = new_quantity
        position.current_price = exit_price
        self.tracker.add_position(position)
        
        return position
    
    def roll_position(
        self,
        old_symbol: str,
        new_contract: OptionContract,
        new_quantity: int,
        new_price: float,
    ) -> tuple[Position | None, Position | None]:
        """
        Roll a position from one contract to another.
        
        Args:
            old_symbol: Symbol of position to close
            new_contract: New contract
            new_quantity: Quantity for new position
            new_price: Entry price for new position
            
        Returns:
            Tuple of (closed_position, new_position)
        """
        # Close old position
        old_position = self.close_position(old_symbol, new_price)
        
        if old_position is None:
            return None, None
        
        # Open new position
        new_position = Position(
            symbol=new_contract.symbol,
            underlying=new_contract.underlying,
            option_type=new_contract.option_type,
            strike=new_contract.strike,
            expiration=new_contract.expiration,
            quantity=new_quantity,
            entry_price=new_price,
            entry_timestamp=datetime.utcnow(),
            current_price=new_price,
            signal_source=old_position.signal_source,
            sleeve_type=old_position.sleeve_type,
        )
        
        self.tracker.add_position(new_position)
        
        logger.info(
            f"Rolled: {old_symbol} -> {new_contract.symbol} | "
            f"Qty: {new_quantity} @ ${new_price:.2f}"
        )
        
        return old_position, new_position
    
    def get_position_summary(self) -> dict[str, Any]:
        """
        Get summary of all positions.
        
        Returns:
            Dictionary with position summary
        """
        positions = self.tracker.get_all_positions()
        
        summary = {
            "total_positions": len(positions),
            "total_pnl": self.tracker.get_total_pnl(),
            "long_positions": sum(1 for p in positions if p.is_long),
            "short_positions": sum(1 for p in positions if p.is_short),
            "by_sleeve": {},
            "by_ticker": {},
        }
        
        for position in positions:
            # By sleeve
            sleeve = position.sleeve_type.value if position.sleeve_type else "UNKNOWN"
            if sleeve not in summary["by_sleeve"]:
                summary["by_sleeve"][sleeve] = {"count": 0, "pnl": 0.0}
            summary["by_sleeve"][sleeve]["count"] += 1
            summary["by_sleeve"][sleeve]["pnl"] += position.unrealized_pnl
            
            # By ticker
            ticker = position.underlying
            if ticker not in summary["by_ticker"]:
                summary["by_ticker"][ticker] = {"count": 0, "pnl": 0.0, "quantity": 0}
            summary["by_ticker"][ticker]["count"] += 1
            summary["by_ticker"][ticker]["pnl"] += position.unrealized_pnl
            summary["by_ticker"][ticker]["quantity"] += position.absolute_quantity
        
        return summary


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "PositionTracker",
    "PositionManager",
]
