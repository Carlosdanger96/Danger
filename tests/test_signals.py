"""
Tests for signal processing.
"""

import pytest
from datetime import datetime

from src.signals import (
    SignalNormalizer,
    SignalScorer,
    WSBSignalGenerator,
    CramerSignalGenerator,
    ConsensusEngine,
)
from src.models import (
    TradeSignal,
    SignalSource,
    SignalDirection,
    SignalConfidence,
)
from src.config import init_config


@pytest.fixture
def config():
    return init_config()


@pytest.fixture
def normalizer():
    return SignalNormalizer()


@pytest.fixture
def scorer():
    return SignalScorer()


@pytest.fixture
def consensus_engine(config):
    return ConsensusEngine(config)


class TestSignalNormalizer:
    """Tests for SignalNormalizer."""
    
    def test_normalize_to_trade_signal(self, normalizer):
        """Test normalization of signal components."""
        signal = normalizer.normalize_to_trade_signal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            metadata={"test": "value"},
        )
        
        assert signal.source == SignalSource.WSB
        assert signal.ticker == "AAPL"
        assert signal.direction == SignalDirection.CALL
        assert signal.confidence == 0.85
        assert signal.urgency == 0.8
        assert signal.metadata == {"test": "value"}
        assert signal.score == 0.0  # Not set yet
    
    def test_determine_signal_level_extreme(self, normalizer):
        """Test signal level determination for extreme signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.95,
            urgency=0.9,
            timestamp=datetime.utcnow(),
            score=0.95,
        )
        
        level = SignalNormalizer._determine_signal_level(signal)
        assert level == SignalConfidence.EXTREME
    
    def test_determine_signal_level_high(self, normalizer):
        """Test signal level determination for high signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
        )
        
        level = SignalNormalizer._determine_signal_level(signal)
        assert level == SignalConfidence.HIGH
    
    def test_determine_signal_level_normal(self, normalizer):
        """Test signal level determination for normal signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.75,
            urgency=0.7,
            timestamp=datetime.utcnow(),
            score=0.75,
        )
        
        level = SignalNormalizer._determine_signal_level(signal)
        assert level == SignalConfidence.NORMAL
    
    def test_determine_signal_level_low(self, normalizer):
        """Test signal level determination for low signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.50,
            urgency=0.5,
            timestamp=datetime.utcnow(),
            score=0.50,
        )
        
        level = SignalNormalizer._determine_signal_level(signal)
        assert level == SignalConfidence.LOW


class TestSignalScorer:
    """Tests for SignalScorer."""
    
    def test_score_signal(self, scorer):
        """Test signal scoring."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
        )
        
        scored_signal = scorer.score_signal(signal)
        
        # Score should be weighted combination of confidence and urgency
        expected_score = 0.85 * 0.7 + 0.8 * 0.3
        assert abs(scored_signal.score - expected_score) < 0.001
    
    def test_is_tradable(self, scorer):
        """Test tradable check."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
        )
        
        assert scorer.is_tradable(signal) is True
        
        signal.score = 0.70
        assert scorer.is_tradable(signal) is False
    
    def test_is_extreme(self, scorer):
        """Test extreme signal check."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.95,
            urgency=0.9,
            timestamp=datetime.utcnow(),
            score=0.95,
        )
        
        assert scorer.is_extreme(signal) is True
        
        signal.score = 0.85
        assert scorer.is_extreme(signal) is False
    
    def test_filter_tradable(self, scorer):
        """Test filtering of tradable signals."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
            TradeSignal(
                source=SignalSource.WSB,
                ticker="GOOGL",
                direction=SignalDirection.CALL,
                confidence=0.60,
                urgency=0.6,
                timestamp=datetime.utcnow(),
                score=0.60,
            ),
        ]
        
        tradable = scorer.filter_tradable(signals)
        
        assert len(tradable) == 1
        assert tradable[0].ticker == "AAPL"


class TestConsensusEngine:
    """Tests for ConsensusEngine."""
    
    def test_find_consensus(self, consensus_engine):
        """Test consensus finding."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
            TradeSignal(
                source=SignalSource.INVERSE_CRAMER,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.90,
                urgency=0.9,
                timestamp=datetime.utcnow(),
                score=0.90,
            ),
            TradeSignal(
                source=SignalSource.WSB,
                ticker="GOOGL",
                direction=SignalDirection.CALL,
                confidence=0.75,
                urgency=0.7,
                timestamp=datetime.utcnow(),
                score=0.75,
            ),
        ]
        
        consensus = consensus_engine.find_consensus(signals)
        
        assert "AAPL" in consensus
        assert SignalDirection.CALL in consensus["AAPL"]
        assert len(consensus["AAPL"][SignalDirection.CALL]) == 2
    
    def test_get_consensus_multiplier_one_source(self, consensus_engine):
        """Test consensus multiplier for one source."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
        ]
        
        multiplier = consensus_engine.get_consensus_multiplier(
            ticker="AAPL",
            direction=SignalDirection.CALL,
            signals=signals,
        )
        
        assert multiplier == 1.0
    
    def test_get_consensus_multiplier_two_sources(self, consensus_engine):
        """Test consensus multiplier for two sources."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
            TradeSignal(
                source=SignalSource.INVERSE_CRAMER,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.90,
                urgency=0.9,
                timestamp=datetime.utcnow(),
                score=0.90,
            ),
        ]
        
        multiplier = consensus_engine.get_consensus_multiplier(
            ticker="AAPL",
            direction=SignalDirection.CALL,
            signals=signals,
        )
        
        assert multiplier == 1.5
    
    def test_get_consensus_multiplier_three_sources(self, consensus_engine):
        """Test consensus multiplier for three sources."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
            TradeSignal(
                source=SignalSource.INVERSE_CRAMER,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.90,
                urgency=0.9,
                timestamp=datetime.utcnow(),
                score=0.90,
            ),
            TradeSignal(
                source=SignalSource.PELOSI,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.80,
                urgency=0.7,
                timestamp=datetime.utcnow(),
                score=0.80,
            ),
        ]
        
        multiplier = consensus_engine.get_consensus_multiplier(
            ticker="AAPL",
            direction=SignalDirection.CALL,
            signals=signals,
        )
        
        assert multiplier == 2.0
    
    def test_get_all_consensus_signals(self, consensus_engine):
        """Test getting all consensus signals."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
            TradeSignal(
                source=SignalSource.INVERSE_CRAMER,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.90,
                urgency=0.9,
                timestamp=datetime.utcnow(),
                score=0.90,
            ),
            TradeSignal(
                source=SignalSource.WSB,
                ticker="GOOGL",
                direction=SignalDirection.CALL,
                confidence=0.75,
                urgency=0.7,
                timestamp=datetime.utcnow(),
                score=0.75,
            ),
        ]
        
        consensus_signals = consensus_engine.get_all_consensus_signals(signals)
        
        assert len(consensus_signals) == 1
        assert consensus_signals[0].ticker == "AAPL"
    
    def test_get_three_way_consensus(self, consensus_engine):
        """Test getting three-way consensus signals."""
        signals = [
            TradeSignal(
                source=SignalSource.WSB,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.85,
                urgency=0.8,
                timestamp=datetime.utcnow(),
                score=0.85,
            ),
            TradeSignal(
                source=SignalSource.INVERSE_CRAMER,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.90,
                urgency=0.9,
                timestamp=datetime.utcnow(),
                score=0.90,
            ),
            TradeSignal(
                source=SignalSource.PELOSI,
                ticker="AAPL",
                direction=SignalDirection.CALL,
                confidence=0.80,
                urgency=0.7,
                timestamp=datetime.utcnow(),
                score=0.80,
            ),
        ]
        
        three_way = consensus_engine.get_three_way_consensus(signals)
        
        assert len(three_way) == 1
        assert three_way[0].ticker == "AAPL"
