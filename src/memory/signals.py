"""
Signal memory for Project DEGENERATE.

Records and retrieves signal history.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.models import TradeSignal
from src.database import get_signal_repository

logger = logging.getLogger(__name__)


# =============================================================================
# Signal Recorder
# =============================================================================

class SignalRecorder:
    """Records signals to persistent storage."""
    
    def __init__(self):
        self.signal_repo = get_signal_repository()
    
    def record_signal(self, signal: TradeSignal) -> str:
        """
        Record a signal.
        
        Args:
            signal: The signal to record
            
        Returns:
            Signal ID
        """
        signal_id = self.signal_repo.save_signal(signal)
        
        logger.debug(f"Recorded signal: {signal_id} for {signal.ticker}")
        
        return signal_id
    
    def record_signals(self, signals: list[TradeSignal]) -> list[str]:
        """
        Record multiple signals.
        
        Args:
            signals: List of signals to record
            
        Returns:
            List of signal IDs
        """
        return [self.record_signal(signal) for signal in signals]


# =============================================================================
# Signal Memory
# =============================================================================

class SignalMemory:
    """Retrieves and analyzes signal history."""
    
    def __init__(self):
        self.signal_repo = get_signal_repository()
    
    def get_signal(self, signal_id: str) -> TradeSignal | None:
        """
        Get a specific signal.
        
        Args:
            signal_id: The signal ID
            
        Returns:
            TradeSignal or None
        """
        return self.signal_repo.get_signal(signal_id)
    
    def get_all_signals(self) -> list[TradeSignal]:
        """
        Get all signals.
        
        Returns:
            List of all TradeSignal objects
        """
        return self.signal_repo.get_unprocessed_signals() + [
            s for s in self.signal_repo.get_unprocessed_signals()
            if s not in self.signal_repo.get_unprocessed_signals()
        ]
    
    def get_signals_by_source(self, source: Any) -> list[TradeSignal]:
        """
        Get signals by source.
        
        Args:
            source: The signal source
            
        Returns:
            List of TradeSignal objects
        """
        all_signals = self.get_all_signals()
        return [s for s in all_signals if s.source == source]
    
    def get_signals_by_ticker(self, ticker: str) -> list[TradeSignal]:
        """
        Get signals by ticker.
        
        Args:
            ticker: The stock ticker
            
        Returns:
            List of TradeSignal objects
        """
        return self.signal_repo.get_signals_by_ticker(ticker)
    
    def get_signals_by_direction(self, direction: Any) -> list[TradeSignal]:
        """
        Get signals by direction.
        
        Args:
            direction: The signal direction
            
        Returns:
            List of TradeSignal objects
        """
        all_signals = self.get_all_signals()
        return [s for s in all_signals if s.direction == direction]
    
    def get_recent_signals(self, limit: int = 100) -> list[TradeSignal]:
        """
        Get recent signals.
        
        Args:
            limit: Maximum number of signals to return
            
        Returns:
            List of recent TradeSignal objects
        """
        all_signals = self.get_all_signals()
        return sorted(
            all_signals,
            key=lambda x: x.timestamp,
            reverse=True,
        )[:limit]
    
    def get_signals_in_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[TradeSignal]:
        """
        Get signals in a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of TradeSignal objects
        """
        all_signals = self.get_all_signals()
        return [
            s for s in all_signals
            if start_time <= s.timestamp <= end_time
        ]
    
    def get_signals_last_n_minutes(self, minutes: int = 60) -> list[TradeSignal]:
        """
        Get signals from the last N minutes.
        
        Args:
            minutes: Number of minutes
            
        Returns:
            List of TradeSignal objects
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)
        
        return self.get_signals_in_time_range(start_time, end_time)
    
    def get_signal_summary(self) -> dict[str, Any]:
        """
        Get summary of all signals.
        
        Returns:
            Dictionary with signal summary
        """
        all_signals = self.get_all_signals()
        
        summary = {
            "total_signals": len(all_signals),
            "by_source": {},
            "by_direction": {},
            "by_ticker": {},
            "avg_confidence": 0.0,
            "avg_urgency": 0.0,
            "avg_score": 0.0,
        }
        
        if not all_signals:
            return summary
        
        for signal in all_signals:
            # By source
            source = signal.source.value
            if source not in summary["by_source"]:
                summary["by_source"][source] = 0
            summary["by_source"][source] += 1
            
            # By direction
            direction = signal.direction.value
            if direction not in summary["by_direction"]:
                summary["by_direction"][direction] = 0
            summary["by_direction"][direction] += 1
            
            # By ticker
            ticker = signal.ticker
            if ticker not in summary["by_ticker"]:
                summary["by_ticker"][ticker] = 0
            summary["by_ticker"][ticker] += 1
        
        # Calculate averages
        summary["avg_confidence"] = sum(
            s.confidence for s in all_signals
        ) / len(all_signals)
        summary["avg_urgency"] = sum(
            s.urgency for s in all_signals
        ) / len(all_signals)
        summary["avg_score"] = sum(
            s.score for s in all_signals
        ) / len(all_signals)
        
        return summary


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "SignalRecorder",
    "SignalMemory",
]
