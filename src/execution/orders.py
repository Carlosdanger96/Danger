"""
Order management for Project DEGENERATE.

Handles order construction, tracking, and management.
"""

import logging
from datetime import datetime
from typing import Any

from src.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    TradeExecution,
    TradePlan,
)
from src.execution.alpaca_mcp import get_executor

logger = logging.getLogger(__name__)


# =============================================================================
# Order Builder
# =============================================================================

class OrderBuilder:
    """Builds order objects from trade plans."""
    
    def __init__(self):
        self.executor = get_executor()
    
    def build_order(
        self,
        trade_plan: TradePlan,
    ) -> Order:
        """
        Build an order from a trade plan.
        
        Args:
            trade_plan: The trade plan
            
        Returns:
            Order object
        """
        # Determine side
        if trade_plan.signal.direction == "CALL":
            side = OrderSide.BUY_TO_OPEN
        else:
            side = OrderSide.SELL_TO_OPEN
        
        # Build order
        order = Order(
            order_id=f"order_{datetime.utcnow().isoformat()}",
            symbol=trade_plan.contract.symbol,
            order_type=trade_plan.order_type,
            side=side,
            quantity=trade_plan.quantity,
            limit_price=trade_plan.limit_price,
            time_in_force="DAY",
            created_at=datetime.utcnow(),
            status=OrderStatus.PENDING,
            signal_source=trade_plan.signal.source,
            sleeve_type=trade_plan.sleeve_type,
        )
        
        return order
    
    def build_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        signal_source: Any = None,
        sleeve_type: Any = None,
    ) -> Order:
        """
        Build a market order.
        
        Args:
            symbol: Contract symbol
            side: Order side
            quantity: Number of contracts
            signal_source: Signal source
            sleeve_type: Sleeve type
            
        Returns:
            Order object
        """
        return Order(
            order_id=f"order_{datetime.utcnow().isoformat()}",
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=side,
            quantity=quantity,
            time_in_force="DAY",
            created_at=datetime.utcnow(),
            status=OrderStatus.PENDING,
            signal_source=signal_source,
            sleeve_type=sleeve_type,
        )
    
    def build_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        limit_price: float,
        signal_source: Any = None,
        sleeve_type: Any = None,
    ) -> Order:
        """
        Build a limit order.
        
        Args:
            symbol: Contract symbol
            side: Order side
            quantity: Number of contracts
            limit_price: Limit price
            signal_source: Signal source
            sleeve_type: Sleeve type
            
        Returns:
            Order object
        """
        return Order(
            order_id=f"order_{datetime.utcnow().isoformat()}",
            symbol=symbol,
            order_type=OrderType.LIMIT,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            time_in_force="DAY",
            created_at=datetime.utcnow(),
            status=OrderStatus.PENDING,
            signal_source=signal_source,
            sleeve_type=sleeve_type,
        )


# =============================================================================
# Order Manager
# =============================================================================

class OrderManager:
    """Manages all orders."""
    
    def __init__(self):
        self.builder = OrderBuilder()
        self.executor = get_executor()
        self.pending_orders: dict[str, Order] = {}
        self.completed_orders: dict[str, Order] = {}
    
    def create_order(self, trade_plan: TradePlan) -> Order:
        """
        Create and return an order from a trade plan.
        
        Args:
            trade_plan: The trade plan
            
        Returns:
            Order object
        """
        order = self.builder.build_order(trade_plan)
        self.pending_orders[order.order_id] = order
        return order
    
    def submit_order(self, order: Order) -> Order | None:
        """
        Submit an order for execution.
        
        Args:
            order: The order to submit
            
        Returns:
            Updated order with execution details or None if failed
        """
        try:
            # Execute through Alpaca
            executed_order = self.executor.client.execute_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type=order.order_type,
                limit_price=order.limit_price,
            )
            
            if executed_order is None:
                logger.error(f"Failed to execute order: {order.symbol}")
                order.status = OrderStatus.REJECTED
                return order
            
            # Update order with execution details
            order.order_id = executed_order.order_id
            order.status = executed_order.status
            order.filled_quantity = executed_order.filled_quantity
            order.filled_price = executed_order.filled_price
            
            # Move to completed if filled
            if order.status == OrderStatus.FILLED:
                self.completed_orders[order.order_id] = order
                del self.pending_orders[order.order_id]
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            order.status = OrderStatus.REJECTED
            return order
    
    def submit_trade_plan(self, trade_plan: TradePlan) -> TradeExecution | None:
        """
        Submit a complete trade plan for execution.
        
        Args:
            trade_plan: The trade plan
            
        Returns:
            TradeExecution or None if failed
        """
        # Create order
        order = self.create_order(trade_plan)
        
        # Submit order
        executed_order = self.submit_order(order)
        
        if executed_order is None or executed_order.status == OrderStatus.REJECTED:
            return None
        
        # Create trade execution
        execution = TradeExecution(
            trade_id=f"trade_{datetime.utcnow().isoformat()}",
            trade_plan=trade_plan,
            order=executed_order,
            execution_timestamp=datetime.utcnow(),
            filled_quantity=executed_order.filled_quantity,
            filled_price=executed_order.filled_price,
            total_cost=executed_order.filled_price * executed_order.filled_quantity * 100,
        )
        
        return execution
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: The order ID
            
        Returns:
            True if cancelled, False otherwise
        """
        if order_id not in self.pending_orders:
            return False
        
        order = self.pending_orders[order_id]
        success = self.executor.cancel_trade(
            TradeExecution(
                trade_id="",
                trade_plan=None,
                order=order,
            )
        )
        
        if success:
            order.status = OrderStatus.CANCELED
            del self.pending_orders[order_id]
            self.completed_orders[order_id] = order
        
        return success
    
    def get_order_status(self, order_id: str) -> Order | None:
        """
        Get status of an order.
        
        Args:
            order_id: The order ID
            
        Returns:
            Order or None if not found
        """
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]
        elif order_id in self.completed_orders:
            return self.completed_orders[order_id]
        else:
            # Try to get from Alpaca
            order = self.executor.client.get_order_status(order_id)
            if order:
                if order.is_open:
                    self.pending_orders[order_id] = order
                else:
                    self.completed_orders[order_id] = order
                return order
        
        return None
    
    def get_all_orders(self) -> dict[str, Order]:
        """
        Get all orders (pending and completed).
        
        Returns:
            Dictionary of all orders
        """
        all_orders = {}
        all_orders.update(self.pending_orders)
        all_orders.update(self.completed_orders)
        return all_orders
    
    def get_open_orders(self) -> list[Order]:
        """
        Get all open orders.
        
        Returns:
            List of open orders
        """
        return list(self.pending_orders.values())
    
    def get_completed_orders(self) -> list[Order]:
        """
        Get all completed orders.
        
        Returns:
            List of completed orders
        """
        return list(self.completed_orders.values())
    
    def cleanup_completed_orders(self) -> None:
        """Clean up old completed orders."""
        # Keep only recent completed orders
        cutoff = datetime.utcnow() - datetime.timedelta(days=7)
        old_orders = [
            order_id for order_id, order in self.completed_orders.items()
            if order.created_at < cutoff
        ]
        for order_id in old_orders:
            del self.completed_orders[order_id]


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "OrderBuilder",
    "OrderManager",
]
