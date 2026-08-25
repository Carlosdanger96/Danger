"""
Cramer signal processing for Project DEGENERATE.

Implements the Inverse Cramer strategy:
- Captures explicit Cramer directional calls
- Normalizes them
- Inverts the direction
"""

import logging
from datetime import datetime
from typing import Any

from src.config import init_config
from src.models import (
    CramerRecommendation,
    CramerSignal,
    CramerStatement,
    SignalDirection,
    SignalSource,
    TradeSignal,
)
from src.signals.base import BaseSignalGenerator, SignalNormalizer, SignalScorer

logger = logging.getLogger(__name__)


# =============================================================================
# Cramer Statement Classifier
# =============================================================================

class CramerClassifier:
    """
    Classifies Cramer statements into recommendation levels.
    
    Uses keyword matching and pattern recognition to determine
    the strength and direction of Cramer's recommendations.
    """
    
    # Keyword mappings for different recommendation levels
    STRONG_BUY_KEYWORDS = [
        "i love",
        "i'm all in on",
        "this is a must buy",
        "you must buy",
        "this is a home run",
        "grand slam",
        "this is a screaming buy",
        "i'm pounding the table on",
        "this is a no-brainer",
        "this is a gift",
    ]
    
    BUY_KEYWORDS = [
        "i like",
        "i'm buying",
        "this is a buy",
        "you should buy",
        "i recommend",
        "this is attractive",
        "this is compelling",
        "i'm bullish on",
        "i think you should own",
        "this is a good opportunity",
    ]
    
    POSITIVE_KEYWORDS = [
        "this is interesting",
        "i'm intrigued by",
        "this has potential",
        "this could work",
        "i don't hate",
        "this is okay",
        "this is fine",
    ]
    
    NEUTRAL_KEYWORDS = [
        "i'm neutral on",
        "this is neutral",
        "i have no opinion on",
        "i don't know about",
        "this is unclear",
    ]
    
    NEGATIVE_KEYWORDS = [
        "i don't like",
        "this is concerning",
        "this worries me",
        "i have concerns about",
        "this is problematic",
        "i'm bearish on",
    ]
    
    SELL_KEYWORDS = [
        "i'm selling",
        "this is a sell",
        "you should sell",
        "i recommend selling",
        "this is overvalued",
        "this is too expensive",
        "this has run its course",
        "i'm taking profits on",
        "this is a sell-off",
        "i'm getting out of",
    ]
    
    STRONG_SELL_KEYWORDS = [
        "i hate",
        "this is a must sell",
        "you must sell",
        "this is a disaster",
        "this is terrible",
        "this is a train wreck",
        "this is a dumpster fire",
        "stay away from",
        "avoid at all costs",
        "this is toxic",
        "i'm shorting",
    ]
    
    # Explicit recommendation keywords
    EXPLICIT_KEYWORDS = [
        "buy",
        "sell",
        "like",
        "hate",
        "love",
        "recommend",
        "pounding the table",
        "all in",
        "must buy",
        "must sell",
        "stay away",
        "avoid",
    ]
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.confidence_threshold = self.config.signal_sources.cramer.confidence_threshold
    
    def classify_statement(self, statement: str) -> tuple[CramerRecommendation, float, float]:
        """
        Classify a Cramer statement.
        
        Args:
            statement: The statement to classify
            
        Returns:
            Tuple of (recommendation, polarity, confidence)
        """
        statement_lower = statement.lower()
        
        # Check for explicit recommendations
        is_explicit = any(kw in statement_lower for kw in self.EXPLICIT_KEYWORDS)
        
        if not is_explicit:
            return CramerRecommendation.NEUTRAL, 0.0, 0.0
        
        # Classify based on keywords
        recommendation = CramerRecommendation.NEUTRAL
        polarity = 0.0
        confidence = 0.0
        
        # Check for STRONG_BUY
        strong_buy_count = sum(1 for kw in self.STRONG_BUY_KEYWORDS if kw in statement_lower)
        if strong_buy_count > 0:
            recommendation = CramerRecommendation.STRONG_BUY
            polarity = 1.0
            confidence = min(1.0, strong_buy_count * 0.25)
        
        # Check for BUY
        if recommendation == CramerRecommendation.NEUTRAL:
            buy_count = sum(1 for kw in self.BUY_KEYWORDS if kw in statement_lower)
            if buy_count > 0:
                recommendation = CramerRecommendation.BUY
                polarity = 0.75
                confidence = min(1.0, buy_count * 0.2)
        
        # Check for POSITIVE
        if recommendation == CramerRecommendation.NEUTRAL:
            positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in statement_lower)
            if positive_count > 0:
                recommendation = CramerRecommendation.POSITIVE
                polarity = 0.5
                confidence = min(1.0, positive_count * 0.15)
        
        # Check for SELL
        sell_count = sum(1 for kw in self.SELL_KEYWORDS if kw in statement_lower)
        if sell_count > 0:
            recommendation = CramerRecommendation.SELL
            polarity = -0.75
            confidence = min(1.0, sell_count * 0.2)
        
        # Check for STRONG_SELL (overrides SELL)
        strong_sell_count = sum(1 for kw in self.STRONG_SELL_KEYWORDS if kw in statement_lower)
        if strong_sell_count > 0:
            recommendation = CramerRecommendation.STRONG_SELL
            polarity = -1.0
            confidence = min(1.0, strong_sell_count * 0.25)
        
        # Check for NEUTRAL
        if recommendation == CramerRecommendation.NEUTRAL:
            neutral_count = sum(1 for kw in self.NEUTRAL_KEYWORDS if kw in statement_lower)
            if neutral_count > 0:
                recommendation = CramerRecommendation.NEUTRAL
                polarity = 0.0
                confidence = min(1.0, neutral_count * 0.1)
        
        # Check for NEGATIVE
        if recommendation == CramerRecommendation.NEUTRAL:
            negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in statement_lower)
            if negative_count > 0:
                recommendation = CramerRecommendation.NEGATIVE
                polarity = -0.5
                confidence = min(1.0, negative_count * 0.15)
        
        return recommendation, polarity, confidence
    
    def should_act_on(self, recommendation: CramerRecommendation) -> bool:
        """
        Check if we should act on a Cramer recommendation.
        
        Only act on explicit directional recommendations.
        
        Args:
            recommendation: The classified recommendation
            
        Returns:
            True if we should act on this recommendation
        """
        return recommendation in [
            CramerRecommendation.STRONG_BUY,
            CramerRecommendation.BUY,
            CramerRecommendation.SELL,
            CramerRecommendation.STRONG_SELL,
        ]
    
    def invert_direction(self, recommendation: CramerRecommendation) -> SignalDirection:
        """
        Invert Cramer's direction.
        
        Args:
            recommendation: Cramer's recommendation
            
        Returns:
            Inverted direction for our trade
        """
        if recommendation in [CramerRecommendation.STRONG_BUY, CramerRecommendation.BUY]:
            return SignalDirection.PUT
        elif recommendation in [CramerRecommendation.STRONG_SELL, CramerRecommendation.SELL]:
            return SignalDirection.CALL
        else:
            return SignalDirection.NONE


# =============================================================================
# Cramer Analyzer
# =============================================================================

class CramerAnalyzer:
    """Analyzes Cramer statements and extracts trading signals."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.classifier = CramerClassifier(config)
    
    def analyze_statement(
        self,
        statement: str,
        ticker: str,
        timestamp: datetime | None = None,
        source: str = "Unknown",
    ) -> CramerStatement | None:
        """
        Analyze a Cramer statement.
        
        Args:
            statement: The statement to analyze
            ticker: The stock ticker mentioned
            timestamp: Timestamp of the statement
            source: Source of the statement (e.g., "Mad Money")
            
        Returns:
            CramerStatement if valid, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Classify the statement
        recommendation, polarity, confidence = self.classifier.classify_statement(statement)
        
        # Only return if explicit recommendation
        if not self.classifier.should_act_on(recommendation):
            return None
        
        return CramerStatement(
            ticker=ticker,
            recommendation=recommendation,
            statement=statement,
            confidence=confidence,
            timestamp=timestamp,
            source=source,
            polarity=polarity,
        )
    
    def extract_ticker(self, statement: str) -> str | None:
        """
        Extract ticker from a statement.
        
        Args:
            statement: The statement to parse
            
        Returns:
            Extracted ticker or None
        """
        # Simple extraction - look for common ticker patterns
        # This would be enhanced with proper NLP in production
        
        # Common patterns: "$AAPL", "AAPL", "Apple (AAPL)"
        import re
        
        # Pattern 1: $TICKER
        match = re.search(r'\$([A-Z]{1,5})', statement)
        if match:
            return match.group(1)
        
        # Pattern 2: (TICKER)
        match = re.search(r'\(([A-Z]{1,5})\)', statement)
        if match:
            return match.group(1)
        
        # Pattern 3: TICKER (capitalized word)
        match = re.search(r'\b([A-Z]{2,5})\b', statement)
        if match:
            # Verify it's a valid ticker (check against known list or API)
            return match.group(1)
        
        return None


# =============================================================================
# Cramer Signal Generator
# =============================================================================

class CramerSignalGenerator(BaseSignalGenerator):
    """Generates trading signals from Cramer statements."""
    
    def __init__(self, config: Any = None):
        super().__init__(SignalSource.INVERSE_CRAMER)
        self.config = config or init_config()
        self.analyzer = CramerAnalyzer(config)
        self.classifier = CramerClassifier(config)
        
        # Statement queue for processing
        self.statement_queue: list[tuple[str, str, datetime, str]] = []
    
    def add_statement(
        self,
        statement: str,
        ticker: str | None = None,
        timestamp: datetime | None = None,
        source: str = "Unknown",
    ) -> None:
        """
        Add a Cramer statement for processing.
        
        Args:
            statement: The Cramer statement
            ticker: The stock ticker (optional, will be extracted)
            timestamp: Timestamp of the statement
            source: Source of the statement
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        if ticker is None:
            ticker = self.analyzer.extract_ticker(statement)
        
        if ticker:
            self.statement_queue.append((statement, ticker, timestamp, source))
    
    def process_statement(
        self,
        statement: str,
        ticker: str,
        timestamp: datetime,
        source: str,
    ) -> TradeSignal | None:
        """
        Process a single Cramer statement into a signal.
        
        Args:
            statement: The statement to process
            ticker: The stock ticker
            timestamp: Timestamp
            source: Source
            
        Returns:
            TradeSignal or None if not actionable
        """
        # Analyze the statement
        cramer_statement = self.analyzer.analyze_statement(
            statement, ticker, timestamp, source
        )
        
        if cramer_statement is None:
            return None
        
        # Invert the direction
        direction = self.classifier.invert_direction(cramer_statement.recommendation)
        
        if direction == SignalDirection.NONE:
            return None
        
        # Calculate urgency based on recommendation strength
        urgency = self._calculate_urgency(cramer_statement)
        
        # Create normalized signal
        signal = SignalNormalizer.normalize_to_trade_signal(
            source=SignalSource.INVERSE_CRAMER,
            ticker=ticker,
            direction=direction,
            confidence=cramer_statement.confidence,
            urgency=urgency,
            timestamp=timestamp,
            metadata={
                "cramer_statement": cramer_statement.statement,
                "cramer_recommendation": cramer_statement.recommendation.value,
                "cramer_polarity": cramer_statement.polarity,
                "source": source,
            },
        )
        
        # Score the signal
        return self.scorer.score_signal(signal)
    
    def _calculate_urgency(self, statement: CramerStatement) -> float:
        """
        Calculate urgency score for a Cramer statement.
        
        Args:
            statement: The Cramer statement
            
        Returns:
            Urgency score (0-1)
        """
        # Strong recommendations have higher urgency
        if statement.recommendation in [
            CramerRecommendation.STRONG_BUY,
            CramerRecommendation.STRONG_SELL,
        ]:
            return 0.9
        elif statement.recommendation in [
            CramerRecommendation.BUY,
            CramerRecommendation.SELL,
        ]:
            return 0.7
        else:
            return 0.5
    
    def generate_signals(self) -> list[TradeSignal]:
        """Generate signals from queued statements."""
        signals = []
        
        while self.statement_queue:
            statement, ticker, timestamp, source = self.statement_queue.pop(0)
            signal = self.process_statement(statement, ticker, timestamp, source)
            if signal:
                signals.append(signal)
        
        return self.score_and_filter(signals)
    
    def get_latest_signal(self, ticker: str | None = None) -> TradeSignal | None:
        """Get the latest signal."""
        signals = self.generate_signals()
        
        if ticker:
            signals = [s for s in signals if s.ticker == ticker]
        
        if signals:
            return max(signals, key=lambda x: x.timestamp)
        return None
    
    def clear_queue(self) -> None:
        """Clear the statement queue."""
        self.statement_queue.clear()


# =============================================================================
# LLM-Based Cramer Classifier (Optional)
# =============================================================================

class LLMCramerClassifier:
    """
    Uses LLM to classify Cramer statements (optional enhancement).
    
    This provides more accurate classification than keyword matching.
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.model = self.config.signal_sources.cramer.classification_model
    
    def classify_with_llm(self, statement: str, ticker: str) -> tuple[CramerRecommendation, float, float]:
        """
        Classify a statement using LLM.
        
        Args:
            statement: The statement to classify
            ticker: The stock ticker
            
        Returns:
            Tuple of (recommendation, polarity, confidence)
        """
        # Placeholder - would integrate with OpenAI or other LLM provider
        # For now, fall back to keyword-based classifier
        classifier = CramerClassifier(self.config)
        return classifier.classify_statement(statement)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "CramerClassifier",
    "CramerAnalyzer",
    "CramerSignalGenerator",
    "LLMCramerClassifier",
]
