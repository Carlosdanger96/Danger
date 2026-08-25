"""
Tests for position sizing and capital allocation.
"""

import pytest
from datetime import datetime

from src.strategy.allocator import PositionSizer, CapitalAllocator
from src.models import (
    TradeSignal,
    OptionContract,
    SignalSource,
    SignalDirection,
    SignalConfidence,
    SleeveType,
    OptionType,
)
from src.config import init_config
from src.state import init_state


@pytest.fixture
def config():
    return init_config()


@pytest.fixture
def portfolio_manager(config):
    portfolio, _ = init_state()
    return portfolio


@pytest.fixture
def position_sizer(config):
    return PositionSizer(config)


@pytest.fixture
def capital_allocator(config):
    return CapitalAllocator(config)


class TestPositionSizer:
    """Tests for PositionSizer."""
    
    def test_calculate_base_size_extreme(self, position_sizer):
        """Test base size calculation for extreme signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.95,
            urgency=0.9,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.EXTREME,
        )
        
        base_size = position_sizer.calculate_base_size(signal, SleeveType.WSB)
        
        # Extreme signals should get 30% of sleeve
        assert base_size == 0.30
    
    def test_calculate_base_size_high(self, position_sizer):
        """Test base size calculation for high signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.HIGH,
        )
        
        base_size = position_sizer.calculate_base_size(signal, SleeveType.WSB)
        
        # High signals should get 20% of sleeve
        assert base_size == 0.20
    
    def test_calculate_base_size_normal(self, position_sizer):
        """Test base size calculation for normal signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.75,
            urgency=0.7,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.NORMAL,
        )
        
        base_size = position_sizer.calculate_base_size(signal, SleeveType.WSB)
        
        # Normal signals should get 10% of sleeve
        assert base_size == 0.10
    
    def test_calculate_base_size_low(self, position_sizer):
        """Test base size calculation for low signal."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.50,
            urgency=0.5,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.LOW,
        )
        
        base_size = position_sizer.calculate_base_size(signal, SleeveType.WSB)
        
        # Low signals should get 5% of sleeve
        assert base_size == 0.05
    
    def test_calculate_dollar_size(self, position_sizer, portfolio_manager):
        """Test dollar size calculation."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.HIGH,
        )
        
        contract = OptionContract(
            symbol="AAPL 240621C00150000",
            underlying="AAPL",
            option_type=OptionType.CALL,
            strike=150.0,
            expiration=datetime(2024, 6, 21),
            dte=30,
            mid_price=1.50,
        )
        
        dollar_size = position_sizer.calculate_dollar_size(
            signal=signal,
            sleeve_type=SleeveType.WSB,
            contract=contract,
        )
        
        # WSB sleeve has $25,000 allocation
        # High signal gets 20% = $5,000
        assert dollar_size == 5000.0
    
    def test_calculate_contract_count(self, position_sizer):
        """Test contract count calculation."""
        contract = OptionContract(
            symbol="AAPL 240621C00150000",
            underlying="AAPL",
            option_type=OptionType.CALL,
            strike=150.0,
            expiration=datetime(2024, 6, 21),
            dte=30,
            mid_price=1.50,
        )
        
        # $5,000 / ($1.50 * 100) = 33.33 contracts
        count = position_sizer.calculate_contract_count(5000.0, contract)
        
        assert count == 33
    
    def test_create_trade_plan(self, position_sizer, portfolio_manager):
        """Test trade plan creation."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.HIGH,
        )
        
        contract = OptionContract(
            symbol="AAPL 240621C00150000",
            underlying="AAPL",
            option_type=OptionType.CALL,
            strike=150.0,
            expiration=datetime(2024, 6, 21),
            dte=30,
            mid_price=1.50,
        )
        
        plan = position_sizer.create_trade_plan(
            signal=signal,
            contract=contract,
            sleeve_type=SleeveType.WSB,
            underlying_price=150.0,
        )
        
        assert plan is not None
        assert plan.signal == signal
        assert plan.contract == contract
        assert plan.sleeve_type == SleeveType.WSB
        assert plan.base_size_percent == 0.20
        assert plan.final_size_dollars > 0
        assert plan.quantity > 0


class TestCapitalAllocator:
    """Tests for CapitalAllocator."""
    
    def test_allocate_to_sleeve(self, capital_allocator, portfolio_manager):
        """Test allocation to a sleeve."""
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.85,
            urgency=0.8,
            timestamp=datetime.utcnow(),
            signal_level=SignalConfidence.HIGH,
        )
        
        contract = OptionContract(
            symbol="AAPL 240621C00150000",
            underlying="AAPL",
            option_type=OptionType.CALL,
            strike=150.0,
            expiration=datetime(2024, 6, 21),
            dte=30,
            mid_price=1.50,
        )
        
        from src.market.options import ScoredContract
        scored_contract = ScoredContract(
            contract=contract,
            tier="TIER2_EXTREME",
            total_score=0.85,
        )
        
        plans = capital_allocator.allocate_to_sleeve(
            sleeve_type=SleeveType.WSB,
            signal=signal,
            contracts=[scored_contract],
        )
        
        assert len(plans) == 1
        assert plans[0].sleeve_type == SleeveType.WSB
    
    def test_check_floor_constraint(self, capital_allocator, portfolio_manager):
        """Test floor constraint checking."""
        portfolio_manager.total_equity = 50000
        portfolio_manager.total_open_risk = 10000
        
        from src.models import TradePlan, TradeSignal, OptionContract
        from src.models import SignalSource, SignalDirection, SleeveType
        
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.8,
            urgency=0.8,
            timestamp=datetime.utcnow(),
        )
        
        contract = OptionContract(
            symbol="AAPL 240621C00150000",
            underlying="AAPL",
            option_type=OptionType.CALL,
            strike=150.0,
            expiration=datetime(2024, 6, 21),
            dte=30,
        )
        
        plan = TradePlan(
            signal=signal,
            contract=contract,
            sleeve_type=SleeveType.WSB,
            final_size_dollars=5000,
            max_loss_if_wrong=5000,
            worst_case_equity=35000,
            quantity=10,
        )
        
        is_allowed = capital_allocator.check_floor_constraint(plan)
        
        assert is_allowed is True
    
    def test_resize_to_floor(self, capital_allocator, portfolio_manager):
        """Test resizing to floor."""
        portfolio_manager.total_equity = 40000
        portfolio_manager.total_open_risk = 5000
        
        from src.models import TradePlan, TradeSignal, OptionContract
        from src.models import SignalSource, SignalDirection, SleeveType
        
        signal = TradeSignal(
            source=SignalSource.WSB,
            ticker="AAPL",
            direction=SignalDirection.CALL,
            confidence=0.8,
            urgency=0.8,
            timestamp=datetime.utcnow(),
        )
        
        contract = OptionContract(
            symbol="AAPL 240621C00150000",
            underlying="AAPL",
            option_type=OptionType.CALL,
            strike=150.0,
            expiration=datetime(2024, 6, 21),
            dte=30,
        )
        
        plan = TradePlan(
            signal=signal,
            contract=contract,
            sleeve_type=SleeveType.WSB,
            final_size_dollars=10000,
            max_loss_if_wrong=10000,
            worst_case_equity=25000,
            quantity=20,
        )
        
        resized = capital_allocator.resize_to_floor(plan)
        
        assert resized is not None
        assert resized.final_size_dollars < 10000
