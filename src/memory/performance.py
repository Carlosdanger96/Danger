"""
Performance memory for Project DEGENERATE.

Records and analyzes performance data.
"""

import logging
from datetime import datetime
from typing import Any

from src.models import (
    PerformanceRecord,
    PerformanceSummary,
    SignalConfidence,
    SignalSource,
    SleeveType,
    ContractTier,
)
from src.database import get_performance_repository

logger = logging.getLogger(__name__)


# =============================================================================
# Performance Recorder
# =============================================================================

class PerformanceRecorder:
    """Records performance data to persistent storage."""
    
    def __init__(self):
        self.perf_repo = get_performance_repository()
    
    def record_performance(self, record: PerformanceRecord) -> None:
        """
        Record a performance record.
        
        Args:
            record: The performance record to record
        """
        self.perf_repo.save_performance_record(record)
        
        logger.info(
            f"Recorded performance: {record.trade_id} | "
            f"{record.signal_source.value} | "
            f"{record.ticker} | "
            f"{record.return_percent:.2%}"
        )
    
    def record_trade_completion(
        self,
        trade_id: str,
        signal_source: SignalSource,
        sleeve_type: SleeveType,
        ticker: str,
        contract_symbol: str,
        entry_timestamp: datetime,
        exit_timestamp: datetime,
        entry_price: float,
        exit_price: float,
        quantity: int,
        max_gain: float,
        max_loss: float,
        final_return: float,
        contract_tier: ContractTier | None = None,
        signal_confidence: SignalConfidence | None = None,
    ) -> None:
        """
        Record a completed trade's performance.
        
        Args:
            trade_id: The trade ID
            signal_source: Signal source
            sleeve_type: Sleeve type
            ticker: Stock ticker
            contract_symbol: Contract symbol
            entry_timestamp: Entry timestamp
            exit_timestamp: Exit timestamp
            entry_price: Entry price
            exit_price: Exit price
            quantity: Quantity
            max_gain: Maximum gain
            max_loss: Maximum loss
            final_return: Final return
            contract_tier: Contract tier
            signal_confidence: Signal confidence
        """
        return_percent = (final_return / (entry_price * quantity * 100)) * 100 if (entry_price * quantity * 100) > 0 else 0.0
        
        record = PerformanceRecord(
            trade_id=trade_id,
            signal_source=signal_source,
            sleeve_type=sleeve_type,
            ticker=ticker,
            contract_symbol=contract_symbol,
            entry_timestamp=entry_timestamp,
            exit_timestamp=exit_timestamp,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            max_gain=max_gain,
            max_loss=max_loss,
            final_return=final_return,
            return_percent=return_percent,
            contract_tier=contract_tier,
            signal_confidence=signal_confidence,
        )
        
        self.record_performance(record)


# =============================================================================
# Performance Memory
# =============================================================================

class PerformanceMemory:
    """Retrieves and analyzes performance data."""
    
    def __init__(self):
        self.perf_repo = get_performance_repository()
    
    def get_performance_summary(self) -> PerformanceSummary:
        """
        Get summary of all performance data.
        
        Returns:
            PerformanceSummary object
        """
        summary_data = self.perf_repo.get_performance_summary()
        
        return PerformanceSummary(**summary_data)
    
    def get_performance_by_source(self) -> dict[SignalSource, dict[str, float]]:
        """
        Get performance by signal source.
        
        Returns:
            Dictionary mapping source to performance metrics
        """
        summary = self.get_performance_summary()
        return summary.source_performance
    
    def get_performance_by_sleeve(self) -> dict[SleeveType, dict[str, float]]:
        """
        Get performance by sleeve.
        
        Returns:
            Dictionary mapping sleeve to performance metrics
        """
        summary = self.get_performance_summary()
        return summary.sleeve_performance
    
    def get_performance_by_tier(self) -> dict[ContractTier, dict[str, float]]:
        """
        Get performance by contract tier.
        
        Returns:
            Dictionary mapping tier to performance metrics
        """
        # Placeholder - would query database
        return {}
    
    def get_performance_by_confidence(self) -> dict[SignalConfidence, dict[str, float]]:
        """
        Get performance by signal confidence level.
        
        Returns:
            Dictionary mapping confidence to performance metrics
        """
        # Placeholder - would query database
        return {}
    
    def get_recent_performance(self, limit: int = 100) -> list[PerformanceRecord]:
        """
        Get recent performance records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of PerformanceRecord objects
        """
        # Placeholder - would query database
        return []
    
    def get_best_trades(self, limit: int = 10) -> list[PerformanceRecord]:
        """
        Get best performing trades.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of best PerformanceRecord objects
        """
        all_records = self.get_recent_performance(limit=1000)
        return sorted(
            all_records,
            key=lambda x: x.return_percent,
            reverse=True,
        )[:limit]
    
    def get_worst_trades(self, limit: int = 10) -> list[PerformanceRecord]:
        """
        Get worst performing trades.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of worst PerformanceRecord objects
        """
        all_records = self.get_recent_performance(limit=1000)
        return sorted(
            all_records,
            key=lambda x: x.return_percent,
        )[:limit]
    
    def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Dictionary with all performance metrics
        """
        summary = self.get_performance_summary()
        
        return {
            "total_trades": summary.total_trades,
            "winning_trades": summary.winning_trades,
            "losing_trades": summary.losing_trades,
            "win_rate": summary.win_rate,
            "total_pnl": summary.total_pnl,
            "avg_win": summary.avg_win,
            "avg_loss": summary.avg_loss,
            "max_win": summary.max_win,
            "max_loss": summary.max_loss,
            "profit_factor": summary.profit_factor,
            "by_source": self.get_performance_by_source(),
            "by_sleeve": self.get_performance_by_sleeve(),
        }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "PerformanceRecorder",
    "PerformanceMemory",
]
