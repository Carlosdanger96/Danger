"""
Base signal processing for Project DEGENERATE.

Provides the foundation for all signal types.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.models import (
    SignalConfidence,
    SignalDirection,
    SignalSource,
    TradeSignal,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Signal Normalizer
# =============================================================================

class SignalNormalizer:
    """Normalizes signals from different sources to a common format."""
    
    @staticmethod
    def normalize_to_trade_signal(
        source: SignalSource,
        ticker: str,
        direction: SignalDirection,
        confidence: float,
        urgency: float,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TradeSignal:
        """
        Create a normalized TradeSignal from components.
        
        Args:
            source: Signal source
            ticker: Stock ticker
            direction: Signal direction
            confidence: Confidence score (0-1)
            urgency: Urgency score (0-1)
            timestamp: Timestamp of signal
            metadata: Additional metadata
            
        Returns:
            Normalized TradeSignal
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        if metadata is None:
            metadata = {}
        
        signal = TradeSignal(
            source=source,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            urgency=urgency,
            timestamp=timestamp,
            metadata=metadata,
        )
        
        # Determine signal level
        signal.signal_level = SignalNormalizer._determine_signal_level(signal)
        
        return signal
    
    @staticmethod
    def _determine_signal_level(signal: TradeSignal) -> SignalConfidence:
        """Determine signal confidence level based on score."""
        if signal.score >= 0.90:
            return SignalConfidence.EXTREME
        elif signal.score >= 0.80:
            return SignalConfidence.HIGH
        elif signal.score >= 0.70:
            return SignalConfidence.NORMAL
        else:
            return SignalConfidence.LOW


# =============================================================================
# Signal Scorer
# =============================================================================

class SignalScorer:
    """Scores and filters signals."""
    
    def __init__(self, minimum_threshold: float = 0.75, extreme_threshold: float = 0.90):
        self.minimum_threshold = minimum_threshold
        self.extreme_threshold = extreme_threshold
    
    def score_signal(self, signal: TradeSignal) -> TradeSignal:
        """
        Score a signal and update its score field.
        
        Args:
            signal: The signal to score
            
        Returns:
            The scored signal
        """
        # Base score is confidence weighted by urgency
        signal.score = signal.confidence * 0.7 + signal.urgency * 0.3
        
        # Update signal level
        signal.signal_level = SignalNormalizer._determine_signal_level(signal)
        
        return signal
    
    def is_tradable(self, signal: TradeSignal) -> bool:
        """Check if a signal meets minimum trading threshold."""
        return signal.score >= self.minimum_threshold
    
    def is_extreme(self, signal: TradeSignal) -> bool:
        """Check if a signal is extreme."""
        return signal.score >= self.extreme_threshold
    
    def filter_tradable(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """Filter to only tradable signals."""
        return [s for s in signals if self.is_tradable(s)]
    
    def sort_by_score(self, signals: list[TradeSignal], descending: bool = True) -> list[TradeSignal]:
        """Sort signals by score."""
        return sorted(signals, key=lambda x: x.score, reverse=descending)


# =============================================================================
# Base Signal Generator
# =============================================================================

class BaseSignalGenerator(ABC):
    """Abstract base class for signal generators."""
    
    def __init__(self, source: SignalSource):
        self.source = source
        self.normalizer = SignalNormalizer()
        self.scorer = SignalScorer()
    
    @abstractmethod
    def generate_signals(self) -> list[TradeSignal]:
        """Generate signals from the source."""
        pass
    
    @abstractmethod
    def get_latest_signal(self, ticker: str | None = None) -> TradeSignal | None:
        """Get the latest signal for a specific ticker or overall."""
        pass
    
    def score_and_filter(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """Score and filter signals."""
        scored = [self.scorer.score_signal(s) for s in signals]
        return self.scorer.filter_tradable(scored)


# =============================================================================
# Signal Aggregator
# =============================================================================

class SignalAggregator:
    """Aggregates signals from multiple sources."""
    
    def __init__(self):
        self.generators: dict[SignalSource, BaseSignalGenerator] = {}
    
    def register_generator(self, generator: BaseSignalGenerator) -> None:
        """Register a signal generator."""
        self.generators[generator.source] = generator
    
    def get_all_signals(self) -> list[TradeSignal]:
        """Get all signals from all registered generators."""
        all_signals = []
        for generator in self.generators.values():
            signals = generator.generate_signals()
            all_signals.extend(signals)
        return all_signals
    
    def get_signals_by_source(self, source: SignalSource) -> list[TradeSignal]:
        """Get signals from a specific source."""
        generator = self.generators.get(source)
        if generator:
            return generator.generate_signals()
        return []
    
    def get_signals_by_ticker(self, ticker: str) -> list[TradeSignal]:
        """Get all signals for a specific ticker."""
        all_signals = self.get_all_signals()
        return [s for s in all_signals if s.ticker == ticker]


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "SignalNormalizer",
    "SignalScorer",
    "BaseSignalGenerator",
    "SignalAggregator",
]
