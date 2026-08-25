"""
Tests for hard floor constraint.
"""

import pytest
from src.risk.floor import FloorMonitor, FloorAlertLevel
from src.risk.governor import HardFloorEnforcer
from src.state import PortfolioManager
from src.config import init_config


@pytest.fixture
def config():
    return init_config()


@pytest.fixture
def portfolio_manager(config):
    return PortfolioManager(config)


@pytest.fixture
def floor_monitor(config):
    return FloorMonitor(config)


@pytest.fixture
def floor_enforcer(config):
    return HardFloorEnforcer(config)


class TestFloorMonitor:
    """Tests for FloorMonitor."""
    
    def test_check_floor_above(self, floor_monitor, portfolio_manager):
        """Test floor check when above floor."""
        portfolio_manager.total_equity = 50000
        assert floor_monitor.check_floor() is True
    
    def test_check_floor_at(self, floor_monitor, portfolio_manager):
        """Test floor check when at floor."""
        portfolio_manager.total_equity = 30000
        assert floor_monitor.check_floor() is False
    
    def test_check_floor_below(self, floor_monitor, portfolio_manager):
        """Test floor check when below floor."""
        portfolio_manager.total_equity = 20000
        assert floor_monitor.check_floor() is False
    
    def test_get_floor_status(self, floor_monitor, portfolio_manager):
        """Test floor status retrieval."""
        portfolio_manager.total_equity = 40000
        status = floor_monitor.get_floor_status()
        
        assert status["current_equity"] == 40000
        assert status["hard_floor"] == 30000
        assert status["is_above_floor"] is True
        assert status["distance_to_floor"] == 10000
    
    def test_check_worst_case_safe(self, floor_monitor, portfolio_manager):
        """Test worst case check when safe."""
        portfolio_manager.total_equity = 50000
        portfolio_manager.total_open_risk = 10000
        
        is_safe, worst_case, max_allowed = floor_monitor.check_worst_case(5000)
        
        assert is_safe is True
        assert worst_case == 35000
        assert max_allowed == 15000
    
    def test_check_worst_case_unsafe(self, floor_monitor, portfolio_manager):
        """Test worst case check when unsafe."""
        portfolio_manager.total_equity = 35000
        portfolio_manager.total_open_risk = 5000
        
        is_safe, worst_case, max_allowed = floor_monitor.check_worst_case(10000)
        
        assert is_safe is False
        assert worst_case == 20000
        assert max_allowed == 0


class TestFloorAlertLevel:
    """Tests for FloorAlertLevel."""
    
    def test_critical_level(self):
        """Test critical alert level."""
        assert FloorAlertLevel.get_level(-1000, 30000) == FloorAlertLevel.CRITICAL
    
    def test_warning_level(self):
        """Test warning alert level."""
        assert FloorAlertLevel.get_level(2000, 30000) == FloorAlertLevel.WARNING
    
    def test_info_level(self):
        """Test info alert level."""
        assert FloorAlertLevel.get_level(8000, 30000) == FloorAlertLevel.INFO
    
    def test_normal_level(self):
        """Test normal alert level."""
        assert FloorAlertLevel.get_level(20000, 30000) == FloorAlertLevel.NORMAL


class TestHardFloorEnforcer:
    """Tests for HardFloorEnforcer."""
    
    def test_validate_trade_safe(self, floor_enforcer, portfolio_manager):
        """Test trade validation when safe."""
        portfolio_manager.total_equity = 50000
        portfolio_manager.total_open_risk = 10000
        
        from src.models import TradePlan, TradeSignal, OptionContract
        from src.models import SignalSource, SignalDirection, SleeveType
        from datetime import datetime
        
        # Create mock trade plan
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
            option_type="CALL",
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
            worst_case_equity=45000,
            quantity=10,
        )
        
        is_valid, reason = floor_enforcer.validate_trade(plan)
        assert is_valid is True
    
    def test_validate_trade_unsafe(self, floor_enforcer, portfolio_manager):
        """Test trade validation when unsafe."""
        portfolio_manager.total_equity = 35000
        portfolio_manager.total_open_risk = 5000
        
        from src.models import TradePlan, TradeSignal, OptionContract
        from src.models import SignalSource, SignalDirection, SleeveType
        from datetime import datetime
        
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
            option_type="CALL",
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
            worst_case_equity=20000,
            quantity=20,
        )
        
        is_valid, reason = floor_enforcer.validate_trade(plan)
        assert is_valid is False
        assert "violate hard floor" in reason
    
    def test_resize_trade(self, floor_enforcer, portfolio_manager):
        """Test trade resizing."""
        portfolio_manager.total_equity = 40000
        portfolio_manager.total_open_risk = 5000
        
        from src.models import TradePlan, TradeSignal, OptionContract
        from src.models import SignalSource, SignalDirection, SleeveType
        from datetime import datetime
        
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
            option_type="CALL",
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
        
        resized = floor_enforcer.resize_trade(plan)
        
        assert resized is not None
        assert resized.final_size_dollars < 10000
        assert resized.max_loss_if_wrong <= 5000  # 40000 - 30000 - 5000 = 5000 max
