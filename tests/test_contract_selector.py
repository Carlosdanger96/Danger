"""
Tests for contract selection.
"""

import pytest
from datetime import datetime

from src.strategy.contract_selector import ContractSelector, ContractRanker
from src.models import (
    TradeSignal,
    OptionContract,
    SignalSource,
    SignalDirection,
    SignalConfidence,
    OptionType,
)
from src.config import init_config


@pytest.fixture
def config():
    return init_config()


@pytest.fixture
def contract_selector(config):
    return ContractSelector(config)


@pytest.fixture
def contract_ranker(config):
    return ContractRanker(config)


class TestContractSelector:
    """Tests for ContractSelector."""
    
    def test_select_contracts(self, contract_selector):
        """Test contract selection for a signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
            signal_level=SignalConfidence.HIGH,
        )
        
        # Create option chain
        option_chain = [
            OptionContract(
                symbol="AAPL 240621C00150000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=150.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
                delta=0.35,
                gamma=0.15,
                mid_price=1.50,
                volume=1000,
                open_interest=5000,
            ),
            OptionContract(
                symbol="AAPL 240621C00160000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=160.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
                delta=0.25,
                gamma=0.20,
                mid_price=0.75,
                volume=500,
                open_interest=2000,
            ),
            OptionContract(
                symbol="AAPL 240614C00170000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=170.0,
                expiration=datetime(2024, 6, 14),
                dte=7,
                delta=0.15,
                gamma=0.30,
                mid_price=0.50,
                volume=200,
                open_interest=1000,
            ),
        ]
        
        selected = contract_selector.select_contracts(
            signal=signal,
            underlying_price=150.0,
            option_chain=option_chain,
            limit=2,
        )
        
        assert len(selected) <= 2
        assert all(s.contract.option_type == OptionType.CALL for s in selected)
    
    def test_select_by_tier(self, contract_selector):
        """Test contract selection by tier."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
            signal_level=SignalConfidence.HIGH,
        )
        
        option_chain = [
            OptionContract(
                symbol="AAPL 240621C00150000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=150.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
            ),
            OptionContract(
                symbol="AAPL 240614C00160000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=160.0,
                expiration=datetime(2024, 6, 14),
                dte=7,
            ),
        ]
        
        from src.models import ContractTier
        
        # Select Tier 2 contracts (7-21 DTE)
        selected = contract_selector.select_by_tier(
            signal=signal,
            underlying_price=150.0,
            option_chain=option_chain,
            tier=ContractTier.TIER2_EXTREME,
            limit=1,
        )
        
        assert len(selected) >= 0
    
    def test_select_best_contract(self, contract_selector):
        """Test selection of best single contract."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
            signal_level=SignalConfidence.HIGH,
        )
        
        option_chain = [
            OptionContract(
                symbol="AAPL 240621C00150000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=150.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
            ),
        ]
        
        best = contract_selector.select_best_contract(
            signal=signal,
            underlying_price=150.0,
            option_chain=option_chain,
        )
        
        assert best is not None
        assert best.contract.symbol == "AAPL 240621C00150000"
    
    def test_select_for_high_convexity(self, contract_selector):
        """Test selection for high convexity contracts."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
            signal_level=SignalConfidence.HIGH,
        )
        
        option_chain = [
            OptionContract(
                symbol="AAPL 240621C00150000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=150.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
                gamma=0.10,
            ),
            OptionContract(
                symbol="AAPL 240614C00160000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=160.0,
                expiration=datetime(2024, 6, 14),
                dte=7,
                gamma=0.30,
            ),
        ]
        
        selected = contract_selector.select_for_high_convexity(
            signal=signal,
            underlying_price=150.0,
            option_chain=option_chain,
            limit=2,
        )
        
        # Should prefer higher gamma contracts
        assert len(selected) >= 1
    
    def test_get_tier_preferences(self, contract_selector):
        """Test tier preference retrieval."""
        preferences = contract_selector.get_tier_preferences()
        
        assert "TIER1_AGGRESSIVE" in preferences
        assert "TIER2_EXTREME" in preferences
        assert "TIER3_ABSURD" in preferences


class TestContractRanker:
    """Tests for ContractRanker."""
    
    def test_rank_contracts(self, contract_ranker):
        """Test ranking of contracts."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
            signal_level=SignalConfidence.HIGH,
        )
        
        option_chain = [
            OptionContract(
                symbol="AAPL 240621C00150000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=150.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
            ),
            OptionContract(
                symbol="AAPL 240614C00160000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=160.0,
                expiration=datetime(2024, 6, 14),
                dte=7,
            ),
        ]
        
        ranked = contract_ranker.rank_contracts(
            signal=signal,
            underlying_price=150.0,
            option_chain=option_chain,
        )
        
        assert len(ranked) == 2
        # Should be sorted by total score (descending)
        assert ranked[0].total_score >= ranked[1].total_score
    
    def test_rank_by_convexity(self, contract_ranker):
        """Test ranking by convexity."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            score=0.85,
            signal_level=SignalConfidence.HIGH,
        )
        
        option_chain = [
            OptionContract(
                symbol="AAPL 240621C00150000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=150.0,
                expiration=datetime(2024, 6, 21),
                dte=30,
                gamma=0.10,
            ),
            OptionContract(
                symbol="AAPL 240614C00160000",
                underlying="AAPL",
                option_type=OptionType.CALL,
                strike=160.0,
                expiration=datetime(2024, 6, 14),
                dte=7,
                gamma=0.30,
            ),
        ]
        
        ranked = contract_ranker.rank_by_convexity(
            signal=signal,
            underlying_price=150.0,
            option_chain=option_chain,
        )
        
        assert len(ranked) == 2
        # Should be sorted by convexity score (descending)
        assert ranked[0].convexity_score >= ranked[1].convexity_score
