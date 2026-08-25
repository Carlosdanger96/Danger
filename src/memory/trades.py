"""
Trade memory for Project DEGENERATE.

Records and retrieves trade history.
"""

import logging
from datetime import datetime
from typing import Any

from src.models import (
    Order,
    OrderStatus,
    Position,
    TradeExecution,
)
from src.database import get_trade_repository, get_position_repository

logger = logging.getLogger(__name__)


# =============================================================================
# Trade Recorder
# =============================================================================

class TradeRecorder:
    """Records trades to persistent storage."""
    
    def __init__(self):
        self.trade_repo = get_trade_repository()
        self.position_repo = get_position_repository()
    
    def record_trade(self, trade_execution: TradeExecution) -> str:
        """
        Record a trade execution.
        
        Args:
            trade_execution: The trade execution to record
            
        Returns:
            Trade ID
        """
        trade_id = self.trade_repo.save_trade(trade_execution)
        
        logger.info(f"Recorded trade: {trade_id}")
        
        return trade_id
    
    def record_position(self, position: Position) -> None:
        """
        Record a position.
        
        Args:
            position: The position to record
        """
        self.position_repo.save_position(position)
        
        logger.debug(f"Recorded position: {position.symbol}")
    
    def record_trade_and_position(
        self,
        trade_execution: TradeExecution,
        position: Position,
    ) -> str:
        """
        Record both trade and resulting position.
        
        Args:
            trade_execution: The trade execution
            position: The resulting position
            
        Returns:
            Trade ID
        """
        trade_id = self.record_trade(trade_execution)
        self.record_position(position)
        
        return trade_id


# =============================================================================
# Trade Memory
# =============================================================================

class TradeMemory:
    """Retrieves and analyzes trade history."""
    
    def __init__(self):
        self.trade_repo = get_trade_repository()
    
    def get_trade(self, trade_id: str) -> TradeExecution | None:
        """
        Get a specific trade.
        
        Args:
            trade_id: The trade ID
            
        Returns:
            TradeExecution or None
        """
        return self.trade_repo.get_trade(trade_id)
    
    def get_all_trades(self) -> list[TradeExecution]:
        """
        Get all trades.
        
        Returns:
            List of all TradeExecution objects
        """
        # Placeholder - would query database
        return []
    
    def get_open_trades(self) -> list[TradeExecution]:
        """
        Get all open trades.
        
        Returns:
            List of open TradeExecution objects
        """
        return self.trade_repo.get_open_trades()
    
    def get_trades_by_signal_source(self, source: Any) -> list[TradeExecution]:
        """
        Get trades by signal source.
        
        Args:
            source: The signal source
            
        Returns:
            List of TradeExecution objects
        """
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t.trade_plan.signal.source == source]
    
    def get_trades_by_sleeve(self, sleeve_type: Any) -> list[TradeExecution]:
        """
        Get trades by sleeve type.
        
        Args:
            sleeve_type: The sleeve type
            
        Returns:
            List of TradeExecution objects
        """
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t.trade_plan.sleeve_type == sleeve_type]
    
    def get_trades_by_ticker(self, ticker: str) -> list[TradeExecution]:
        """
        Get trades by ticker.
        
        Args:
            ticker: The stock ticker
            
        Returns:
            List of TradeExecution objects
        """
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t.trade_plan.signal.ticker == ticker]
    
    def get_recent_trades(self, limit: int = 100) -> list[TradeExecution]:
        """
        Get recent trades.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of recent TradeExecution objects
        """
        all_trades = self.get_all_trades()
        return sorted(
            all_trades,
            key=lambda x: x.execution_timestamp,
            reverse=True,
        )[:limit]
    
    def get_trade_summary(self) -> dict[str, Any]:
        """
        Get summary of all trades.
        
        Returns:
            Dictionary with trade summary
        """
        all_trades = self.get_all_trades()
        
        summary = {
            "total_trades": len(all_trades),
            "open_trades": len(self.get_open_trades()),
            "by_source": {},
            "by_sleeve": {},
            "by_ticker": {},
        }
        
        for trade in all_trades:
            # By source
            source = trade.trade_plan.signal.source.value
            if source not in summary["by_source"]:
                summary["by_source"][source] = 0
            summary["by_source"][source] += 1
            
            # By sleeve
            sleeve = trade.trade_plan.sleeve_type.value
            if sleeve not in summary["by_sleeve"]:
                summary["by_sleeve"][sleeve] = 0
            summary["by_sleeve"][sleeve] += 1
            
            # By ticker
            ticker = trade.trade_plan.signal.ticker
            if ticker not in summary["by_ticker"]:
                summary["by_ticker"][ticker] = 0
            summary["by_ticker"][ticker] += 1
        
        return summary


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "TradeRecorder",
    "TradeMemory",
]
