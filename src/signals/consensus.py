"""
Consensus engine for Project DEGENERATE.

Detects when multiple signal sources agree and applies multipliers.
"""

import logging
from collections import defaultdict
from typing import Any

from src.config import init_config
from src.models import (
    SignalDirection,
    SignalSource,
    TradeSignal,
)
from src.signals.base import SignalNormalizer

logger = logging.getLogger(__name__)


# =============================================================================
# Consensus Engine
# =============================================================================

class ConsensusEngine:
    """
    Detects consensus among signal sources and applies multipliers.
    
    Rules:
    1 source  -> 1.0x
    2 sources -> 1.5x
    3 sources -> 2.0x
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.consensus_multipliers = self.config.strategy.consensus
    
    def find_consensus(self, signals: list[TradeSignal]) -> dict[str, dict[SignalDirection, list[SignalSource]]]:
        """
        Find consensus among signals.
        
        Args:
            signals: List of TradeSignals from all sources
            
        Returns:
            Dictionary mapping ticker -> direction -> list of sources
        """
        consensus: dict[str, dict[SignalDirection, list[SignalSource]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        for signal in signals:
            ticker = signal.ticker
            direction = signal.direction
            source = signal.source
            
            consensus[ticker][direction].append(source)
        
        return consensus
    
    def get_consensus_multiplier(
        self,
        ticker: str,
        direction: SignalDirection,
        signals: list[TradeSignal],
    ) -> float:
        """
        Get the consensus multiplier for a ticker and direction.
        
        Args:
            ticker: The stock ticker
            direction: The signal direction
            signals: List of all signals to check
            
        Returns:
            Multiplier based on number of agreeing sources
        """
        consensus = self.find_consensus(signals)
        
        if ticker not in consensus:
            return self.consensus_multipliers.get("one_source", 1.0)
        
        if direction not in consensus[ticker]:
            return self.consensus_multipliers.get("one_source", 1.0)
        
        sources = consensus[ticker][direction]
        num_sources = len(sources)
        
        if num_sources >= 3:
            return self.consensus_multipliers.get("three_sources", 2.0)
        elif num_sources >= 2:
            return self.consensus_multipliers.get("two_sources", 1.5)
        else:
            return self.consensus_multipliers.get("one_source", 1.0)
    
    def get_all_consensus_signals(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """
        Get all signals that have consensus from multiple sources.
        
        Args:
            signals: List of all signals
            
        Returns:
            List of signals with consensus (2+ sources)
        """
        consensus = self.find_consensus(signals)
        consensus_signals = []
        
        for ticker, directions in consensus.items():
            for direction, sources in directions.items():
                if len(sources) >= 2:
                    # Find the signal with highest confidence for this consensus
                    matching_signals = [
                        s for s in signals
                        if s.ticker == ticker and s.direction == direction
                    ]
                    if matching_signals:
                        best_signal = max(matching_signals, key=lambda x: x.confidence)
                        consensus_signals.append(best_signal)
        
        return consensus_signals
    
    def get_three_way_consensus(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """
        Get signals with consensus from all three sources.
        
        Args:
            signals: List of all signals
            
        Returns:
            List of signals with 3-source consensus
        """
        consensus = self.find_consensus(signals)
        three_way_signals = []
        
        for ticker, directions in consensus.items():
            for direction, sources in directions.items():
                if len(sources) >= 3:
                    matching_signals = [
                        s for s in signals
                        if s.ticker == ticker and s.direction == direction
                    ]
                    if matching_signals:
                        best_signal = max(matching_signals, key=lambda x: x.confidence)
                        three_way_signals.append(best_signal)
        
        return three_way_signals
    
    def create_consensus_signal(
        self,
        signals: list[TradeSignal],
    ) -> list[TradeSignal]:
        """
        Create enhanced signals with consensus information.
        
        Args:
            signals: List of signals to enhance
            
        Returns:
            List of signals with consensus metadata added
        """
        consensus = self.find_consensus(signals)
        
        enhanced_signals = []
        for signal in signals:
            ticker = signal.ticker
            direction = signal.direction
            
            if ticker in consensus and direction in consensus[ticker]:
                num_sources = len(consensus[ticker][direction])
                multiplier = self.get_consensus_multiplier(ticker, direction, signals)
                
                # Create enhanced signal with consensus metadata
                metadata = signal.metadata.copy()
                metadata["consensus_sources"] = num_sources
                metadata["consensus_multiplier"] = multiplier
                metadata["consensus_ticker"] = ticker
                
                enhanced_signal = TradeSignal(
                    source=signal.source,
                    ticker=signal.ticker,
                    direction=signal.direction,
                    confidence=signal.confidence,
                    urgency=signal.urgency,
                    timestamp=signal.timestamp,
                    metadata=metadata,
                    score=signal.score,
                    signal_level=signal.signal_level,
                )
                enhanced_signals.append(enhanced_signal)
            else:
                enhanced_signals.append(signal)
        
        return enhanced_signals


# =============================================================================
# Signal Deduplicator
# =============================================================================

class SignalDeduplicator:
    """Removes duplicate signals."""
    
    def __init__(self):
        pass
    
    def deduplicate(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """
        Remove duplicate signals.
        
        Args:
            signals: List of signals
            
        Returns:
            List of unique signals
        """
        seen: dict[str, TradeSignal] = {}
        
        for signal in signals:
            # Create a unique key based on source, ticker, and direction
            key = f"{signal.source.value}_{signal.ticker}_{signal.direction.value}"
            
            # If we've seen this key, keep the one with higher confidence
            if key in seen:
                if signal.confidence > seen[key].confidence:
                    seen[key] = signal
            else:
                seen[key] = signal
        
        return list(seen.values())


# =============================================================================
# Signal Prioritizer
# =============================================================================

class SignalPrioritizer:
    """Prioritizes signals for execution."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.consensus_engine = ConsensusEngine(config)
        self.deduplicator = SignalDeduplicator()
    
    def prioritize(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """
        Prioritize signals for execution.
        
        Priority order:
        1. Three-way consensus signals
        2. Two-way consensus signals
        3. Extreme confidence signals
        4. High confidence signals
        5. Normal confidence signals
        
        Args:
            signals: List of signals to prioritize
            
        Returns:
            Prioritized list of signals
        """
        # Deduplicate first
        signals = self.deduplicator.deduplicate(signals)
        
        # Add consensus information
        signals = self.consensus_engine.create_consensus_signal(signals)
        
        # Sort by priority
        def priority_key(signal: TradeSignal) -> tuple:
            # Priority components (higher is better)
            consensus_sources = signal.metadata.get("consensus_sources", 0)
            confidence = signal.confidence
            urgency = signal.urgency
            score = signal.score
            
            # Three-way consensus first
            if consensus_sources >= 3:
                return (3, score, urgency, confidence)
            elif consensus_sources >= 2:
                return (2, score, urgency, confidence)
            elif score >= self.config.strategy.signal_thresholds.get("extreme", 0.90):
                return (1, score, urgency, confidence)
            elif score >= self.config.strategy.signal_thresholds.get("minimum", 0.75):
                return (0, score, urgency, confidence)
            else:
                return (-1, score, urgency, confidence)
        
        return sorted(signals, key=priority_key, reverse=True)
    
    def get_top_signals(self, signals: list[TradeSignal], limit: int = 5) -> list[TradeSignal]:
        """Get top N signals by priority."""
        prioritized = self.prioritize(signals)
        return prioritized[:limit]


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ConsensusEngine",
    "SignalDeduplicator",
    "SignalPrioritizer",
]
