"""
Alpaca MCP integration for Project DEGENERATE.

Provides the interface to Alpaca's MCP server for:
- Account state
- Market data
- Option chains with Greeks
- Positions
- Order execution (including multi-leg spreads)
- Paper trading (default)
"""

import logging
from datetime import datetime
from typing import Any, Optional

from src.config import get_alpaca_config
from src.market.alpaca import AlpacaMCPClient as BaseAlpacaMCPClient
from src.models import (
    OptionContract,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TradeExecution,
    TradePlan,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Alpaca MCP Client
# =============================================================================

class AlpacaMCPClient:
    """
    Client for Alpaca's MCP server.
    
    Wraps the base Alpaca client with MCP-specific functionality.
    """
    
    def __init__(self):
        """Initialize Alpaca MCP client."""
        config = get_alpaca_config()
        self.client = BaseAlpacaMCPClient(
            api_key=config.get("api_key"),
            api_secret=config.get("api_secret"),
            paper=config.get("paper", True),
        )
    
    def get_account(self) -> dict[str, Any]:
        """Get account information."""
        return self.client.get_account_info()
    
    def get_option_chain(self, underlying: str) -> list[OptionContract]:
        """Get option chain for an underlying."""
        return self.client.get_option_chain(underlying)
    
    def get_option_chain_with_greeks(self, underlying: str) -> list[OptionContract]:
        """Get option chain with Greeks."""
        return self.client.get_option_chain_with_greeks(underlying)
    
    def get_underlying_price(self, symbol: str) -> float:
        """Get current price for an underlying."""
        return self.client.get_underlying_price(symbol)
    
    def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float | None = None,
    ) -> Order:
        """Execute an order."""
        return self.client.execute_option_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
        )
    
    def get_positions(self) -> list[Position]:
        """Get all current positions."""
        return self.client.get_positions()
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position."""
        return self.client.get_position(symbol)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.client.cancel_order(order_id)
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status."""
        return self.client.get_order_status(order_id)
    
    def get_open_orders(self) -> list[Order]:
        """Get all open orders."""
        return self.client.get_open_orders()
    
    def execute_multi_leg_order(
        self,
        legs: list[tuple[str, OrderSide, int]],
        order_type: OrderType = OrderType.MARKET,
    ) -> Order | None:
        """
        Execute a multi-leg spread order.
        
        Args:
            legs: List of (symbol, side, quantity) tuples
            order_type: Order type
            
        Returns:
            Order object or None if failed
        """
        # Placeholder - would implement multi-leg order logic
        # Alpaca supports multi-leg orders through their API
        
        logger.warning("Multi-leg order execution not yet implemented")
        return None


# =============================================================================
# Alpaca Executor
# =============================================================================

class AlpacaExecutor:
    """
    Executes trades through Alpaca MCP.
    
    Handles:
    - Single-leg option orders
    - Multi-leg spread orders
    - Paper trading (default)
    - Order validation
    - Execution confirmation
    """
    
    def __init__(self):
        self.client = AlpacaMCPClient()
    
    def execute_trade_plan(self, trade_plan: TradePlan) -> TradeExecution | None:
        """
        Execute a trade plan.
        
        Args:
            trade_plan: The trade plan to execute
            
        Returns:
            TradeExecution or None if failed
        """
        try:
            # Determine side
            if trade_plan.signal.direction == "CALL":
                side = OrderSide.BUY_TO_OPEN
            else:
                side = OrderSide.SELL_TO_OPEN
            
            # Execute order
            order = self.client.execute_order(
                symbol=trade_plan.contract.symbol,
                side=side,
                quantity=trade_plan.quantity,
                order_type=trade_plan.order_type,
                limit_price=trade_plan.limit_price,
            )
            
            if order is None:
                logger.error(f"Failed to execute order for {trade_plan.contract.symbol}")
                return None
            
            # Create trade execution record
            execution = TradeExecution(
                trade_id=f"trade_{datetime.utcnow().isoformat()}",
                trade_plan=trade_plan,
                order=order,
                execution_timestamp=datetime.utcnow(),
                filled_quantity=order.filled_quantity,
                filled_price=order.filled_price,
                total_cost=order.filled_price * order.filled_quantity * 100,
            )
            
            logger.info(
                f"Executed: {side.value} {order.quantity} {order.symbol} @ "
                f"${order.filled_price:.2f} (cost: ${execution.total_cost:.2f})"
            )
            
            return execution
            
        except Exception as e:
            logger.error(f"Failed to execute trade plan: {e}")
            return None
    
    def execute_multi_leg_spread(
        self,
        legs: list[tuple[str, OrderSide, int]],
    ) -> list[TradeExecution] | None:
        """
        Execute a multi-leg spread.
        
        Args:
            legs: List of (symbol, side, quantity) tuples
            
        Returns:
            List of TradeExecution or None if failed
        """
        try:
            # Execute multi-leg order
            order = self.client.execute_multi_leg_order(legs)
            
            if order is None:
                logger.error("Failed to execute multi-leg order")
                return None
            
            # Create execution records for each leg
            executions = []
            for i, (symbol, side, quantity) in enumerate(legs):
                execution = TradeExecution(
                    trade_id=f"spread_{datetime.utcnow().isoformat()}_{i}",
                    trade_plan=None,  # Would need proper trade plan
                    order=order,
                    execution_timestamp=datetime.utcnow(),
                )
                executions.append(execution)
            
            logger.info(f"Executed multi-leg spread with {len(legs)} legs")
            
            return executions
            
        except Exception as e:
            logger.error(f"Failed to execute multi-leg spread: {e}")
            return None
    
    def cancel_trade(self, trade_execution: TradeExecution) -> bool:
        """
        Cancel a trade execution.
        
        Args:
            trade_execution: The trade execution to cancel
            
        Returns:
            True if cancelled, False otherwise
        """
        if trade_execution.order is None:
            return False
        
        return self.client.cancel_order(trade_execution.order.order_id)
    
    def get_execution_status(self, trade_execution: TradeExecution) -> OrderStatus:
        """
        Get status of a trade execution.
        
        Args:
            trade_execution: The trade execution to check
            
        Returns:
            Current order status
        """
        if trade_execution.order is None:
            return OrderStatus.REJECTED
        
        order = self.client.get_order_status(trade_execution.order.order_id)
        if order is None:
            return OrderStatus.REJECTED
        
        return order.status


# =============================================================================
# Singleton Client
# =============================================================================

_executor: AlpacaExecutor | None = None


def get_executor() -> AlpacaExecutor:
    """Get the global Alpaca executor."""
    global _executor
    if _executor is None:
        _executor = AlpacaExecutor()
    return _executor


def init_executor() -> AlpacaExecutor:
    """Initialize the global Alpaca executor."""
    global _executor
    _executor = AlpacaExecutor()
    return _executor


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "AlpacaMCPClient",
    "AlpacaExecutor",
    "get_executor",
    "init_executor",
]
