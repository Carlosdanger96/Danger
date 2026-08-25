"""
State management for Project DEGENERATE.

Maintains portfolio state, sleeve allocations, and trading context.
"""

import logging
from datetime import datetime
from typing import Any

from src.config import init_config
from src.models import (
    Order,
    OrderStatus,
    Position,
    PortfolioState,
    SignalDirection,
    SignalSource,
    SleeveState,
    SleeveType,
    TradeSignal,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Sleeve Management
# =============================================================================

class SleeveManager:
    """Manages individual portfolio sleeves."""
    
    def __init__(self, sleeve_type: SleeveType, allocation: float, config: Any = None):
        self.sleeve_type = sleeve_type
        self.allocation = allocation
        self.config = config or init_config()
        
        # State
        self.available_cash: float = allocation * 100000  # Starting allocation
        self.open_risk: float = 0.0
        self.realized_profit: float = 0.0
        self.realized_loss: float = 0.0
        self.active_signals: list[TradeSignal] = []
        self.open_positions: list[str] = []
    
    @property
    def total_allocation(self) -> float:
        """Total allocation for this sleeve."""
        return self.allocation * 100000
    
    @property
    def used_capital(self) -> float:
        """Capital currently deployed."""
        return self.total_allocation - self.available_cash
    
    @property
    def utilization(self) -> float:
        """Percentage of allocation currently used."""
        return self.used_capital / self.total_allocation if self.total_allocation > 0 else 0.0
    
    @property
    def pnl(self) -> float:
        """Realized P&L for this sleeve."""
        return self.realized_profit - self.realized_loss
    
    @property
    def total_value(self) -> float:
        """Total value (cash + open positions)."""
        return self.available_cash + self.open_risk
    
    def allocate_for_signal(self, signal: TradeSignal, premium: float) -> float:
        """
        Allocate capital for a signal based on confidence.
        
        Args:
            signal: The trading signal
            premium: Premium per contract
            
        Returns:
            Dollar amount to allocate
        """
        # Get sizing from config
        thresholds = self.config.strategy.sizing
        
        # Determine size percentage based on signal confidence
        if signal.score >= self.config.strategy.signal_thresholds.get("extreme", 0.90):
            size_percent = thresholds.get("extreme", 0.30)
        elif signal.score >= self.config.strategy.signal_thresholds.get("high", 0.80):
            size_percent = thresholds.get("high", 0.20)
        elif signal.score >= self.config.strategy.signal_thresholds.get("minimum", 0.75):
            size_percent = thresholds.get("normal", 0.10)
        else:
            size_percent = thresholds.get("low", 0.05)
        
        # Calculate dollar amount
        dollar_amount = self.total_allocation * size_percent
        
        # Ensure we don't exceed available cash
        dollar_amount = min(dollar_amount, self.available_cash)
        
        return dollar_amount
    
    def reserve_capital(self, amount: float) -> bool:
        """
        Reserve capital for a trade.
        
        Args:
            amount: Amount to reserve
            
        Returns:
            True if successful, False if insufficient capital
        """
        if amount > self.available_cash:
            logger.warning(f"Insufficient capital in {self.sleeve_type} sleeve: {amount} > {self.available_cash}")
            return False
        
        self.available_cash -= amount
        self.open_risk += amount
        logger.debug(f"Reserved {amount} from {self.sleeve_type} sleeve")
        return True
    
    def release_capital(self, amount: float) -> None:
        """
        Release reserved capital.
        
        Args:
            amount: Amount to release
        """
        self.available_cash += amount
        self.open_risk = max(0, self.open_risk - amount)
        logger.debug(f"Released {amount} to {self.sleeve_type} sleeve")
    
    def add_signal(self, signal: TradeSignal) -> None:
        """Add an active signal."""
        if signal not in self.active_signals:
            self.active_signals.append(signal)
            logger.debug(f"Added signal to {self.sleeve_type}: {signal.ticker} {signal.direction}")
    
    def remove_signal(self, signal: TradeSignal) -> None:
        """Remove an active signal."""
        if signal in self.active_signals:
            self.active_signals.remove(signal)
            logger.debug(f"Removed signal from {self.sleeve_type}: {signal.ticker} {signal.direction}")
    
    def add_position(self, position: Position) -> None:
        """Add an open position."""
        if position.symbol not in self.open_positions:
            self.open_positions.append(position.symbol)
            logger.debug(f"Added position to {self.sleeve_type}: {position.symbol}")
    
    def remove_position(self, symbol: str) -> None:
        """Remove an open position."""
        if symbol in self.open_positions:
            self.open_positions.remove(symbol)
            logger.debug(f"Removed position from {self.sleeve_type}: {symbol}")
    
    def record_profit(self, amount: float) -> None:
        """Record realized profit."""
        self.realized_profit += amount
        logger.debug(f"Recorded profit in {self.sleeve_type}: {amount}")
    
    def record_loss(self, amount: float) -> None:
        """Record realized loss."""
        self.realized_loss += amount
        logger.debug(f"Recorded loss in {self.sleeve_type}: {amount}")
    
    def get_state(self) -> SleeveState:
        """Get current sleeve state."""
        return SleeveState(
            sleeve_type=self.sleeve_type,
            allocation=self.allocation,
            available_cash=self.available_cash,
            open_risk=self.open_risk,
            realized_profit=self.realized_profit,
            realized_loss=self.realized_loss,
            active_signals=self.active_signals,
            open_positions=self.open_positions,
        )


# =============================================================================
# Portfolio Manager
# =============================================================================

class PortfolioManager:
    """Manages the overall portfolio state."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        
        # Initialize sleeves
        self.sleeves: dict[SleeveType, SleeveManager] = {}
        sleeves_config = self.config.sleeves
        
        if sleeves_config.wsb.enabled:
            self.sleeves[SleeveType.WSB] = SleeveManager(
                SleeveType.WSB,
                sleeves_config.wsb.allocation,
                self.config,
            )
        
        if sleeves_config.pelosi.enabled:
            self.sleeves[SleeveType.PELOSI] = SleeveManager(
                SleeveType.PELOSI,
                sleeves_config.pelosi.allocation,
                self.config,
            )
        
        if sleeves_config.inverse_cramer.enabled:
            self.sleeves[SleeveType.INVERSE_CRAMER] = SleeveManager(
                SleeveType.INVERSE_CRAMER,
                sleeves_config.inverse_cramer.allocation,
                self.config,
            )
        
        # Portfolio state
        self.total_equity: float = 100000.0
        self.starting_equity: float = 100000.0
        self.hard_floor: float = self.config.account.hard_floor
        self.max_drawdown: float = self.config.account.max_drawdown
    
    @property
    def current_drawdown(self) -> float:
        """Current drawdown from starting equity."""
        if self.total_equity >= self.starting_equity:
            return 0.0
        return (self.starting_equity - self.total_equity) / self.starting_equity
    
    @property
    def drawdown_percent(self) -> float:
        """Drawdown as percentage."""
        return self.current_drawdown * 100
    
    @property
    def is_above_floor(self) -> bool:
        """Check if equity is above hard floor."""
        return self.total_equity >= self.hard_floor
    
    @property
    def max_allowed_loss(self) -> float:
        """Maximum allowed loss from current equity."""
        return self.total_equity - self.hard_floor
    
    @property
    def total_open_risk(self) -> float:
        """Total open risk across all sleeves."""
        return sum(sleeve.open_risk for sleeve in self.sleeves.values())
    
    @property
    def total_available_cash(self) -> float:
        """Total available cash across all sleeves."""
        return sum(sleeve.available_cash for sleeve in self.sleeves.values())
    
    def get_sleeve(self, sleeve_type: SleeveType) -> SleeveManager | None:
        """Get a specific sleeve manager."""
        return self.sleeves.get(sleeve_type)
    
    def update_equity(self, new_equity: float) -> None:
        """Update total portfolio equity."""
        old_equity = self.total_equity
        self.total_equity = new_equity
        
        if new_equity < old_equity:
            logger.info(f"Equity decreased: ${old_equity:,.2f} -> ${new_equity:,.2f}")
        else:
            logger.info(f"Equity increased: ${old_equity:,.2f} -> ${new_equity:,.2f}")
    
    def get_portfolio_state(self) -> PortfolioState:
        """Get current portfolio state."""
        sleeves_state = {}
        all_positions = []
        
        for sleeve_type, sleeve in self.sleeves.items():
            sleeves_state[sleeve_type] = sleeve.get_state()
            all_positions.extend(sleeve.open_positions)
        
        return PortfolioState(
            total_equity=self.total_equity,
            hard_floor=self.hard_floor,
            max_drawdown=self.max_drawdown,
            sleeves=sleeves_state,
            all_positions=all_positions,
        )
    
    def get_desperation_multiplier(self) -> float:
        """
        Get the desperation multiplier based on current drawdown.
        
        Returns:
            Multiplier to apply to position sizes
        """
        if not self.config.strategy.desperation.get("enabled", True):
            return 1.0
        
        drawdown = self.current_drawdown
        
        if drawdown >= 0.70:  # At or below 30k floor
            return 0.0  # Should not trade
        elif drawdown >= 0.65:
            return self.config.strategy.desperation.get("drawdown_65_70", 2.0)
        elif drawdown >= 0.55:
            return self.config.strategy.desperation.get("drawdown_55_65", 1.75)
        elif drawdown >= 0.40:
            return self.config.strategy.desperation.get("drawdown_40_55", 1.50)
        elif drawdown >= 0.20:
            return self.config.strategy.desperation.get("drawdown_20_40", 1.25)
        else:
            return self.config.strategy.desperation.get("drawdown_0_20", 1.0)
    
    def is_last_chance_mode(self) -> bool:
        """Check if in last-chance mode (65-70% drawdown)."""
        return self.current_drawdown >= 0.65 and self.current_drawdown < 0.70
    
    def check_floor_constraint(self, potential_loss: float) -> bool:
        """
        Check if a potential trade would violate the hard floor.
        
        Args:
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            True if trade is allowed, False if it would violate the floor
        """
        worst_case_equity = self.total_equity - potential_loss - self.total_open_risk
        return worst_case_equity >= self.hard_floor
    
    def resize_to_floor(self, potential_loss: float) -> float:
        """
        Calculate maximum allowed position size to stay above floor.
        
        Args:
            potential_loss: Maximum potential loss from the new trade
            
        Returns:
            Maximum allowed position size
        """
        max_total_loss = self.total_equity - self.hard_floor
        max_new_loss = max_total_loss - self.total_open_risk
        
        if max_new_loss <= 0:
            return 0.0
        
        # Scale down proportionally
        if potential_loss <= 0:
            return 0.0
        
        return (max_new_loss / potential_loss) * potential_loss


# =============================================================================
# Signal Aggregator
# =============================================================================

class SignalAggregator:
    """Aggregates and normalizes signals from multiple sources."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.signals: list[TradeSignal] = []
    
    def add_signal(self, signal: TradeSignal) -> None:
        """Add a signal for aggregation."""
        self.signals.append(signal)
    
    def get_consensus_multiplier(self, ticker: str, direction: SignalDirection) -> float:
        """
        Get consensus multiplier for a ticker and direction.
        
        Args:
            ticker: Stock ticker
            direction: Signal direction
            
        Returns:
            Multiplier based on number of agreeing sources
        """
        agreeing_sources = 0
        
        for signal in self.signals:
            if signal.ticker == ticker and signal.direction == direction:
                agreeing_sources += 1
        
        if agreeing_sources >= 3:
            return self.config.strategy.consensus.get("three_sources", 2.0)
        elif agreeing_sources >= 2:
            return self.config.strategy.consensus.get("two_sources", 1.5)
        else:
            return self.config.strategy.consensus.get("one_source", 1.0)
    
    def get_signals_by_ticker(self, ticker: str) -> list[TradeSignal]:
        """Get all signals for a specific ticker."""
        return [s for s in self.signals if s.ticker == ticker]
    
    def get_signals_by_direction(self, direction: SignalDirection) -> list[TradeSignal]:
        """Get all signals with a specific direction."""
        return [s for s in self.signals if s.direction == direction]
    
    def get_highest_confidence_signal(self, ticker: str) -> TradeSignal | None:
        """Get the highest confidence signal for a ticker."""
        signals = self.get_signals_by_ticker(ticker)
        if not signals:
            return None
        return max(signals, key=lambda x: x.confidence)
    
    def clear_signals(self) -> None:
        """Clear all aggregated signals."""
        self.signals.clear()
    
    def clear_old_signals(self, max_age_minutes: int = 60) -> None:
        """Clear signals older than a certain age."""
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        self.signals = [s for s in self.signals if s.timestamp >= cutoff]


# =============================================================================
# Global State
# =============================================================================

_portfolio_manager: PortfolioManager | None = None
_signal_aggregator: SignalAggregator | None = None


def get_portfolio_manager() -> PortfolioManager:
    """Get the global portfolio manager."""
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = PortfolioManager()
    return _portfolio_manager


def get_signal_aggregator() -> SignalAggregator:
    """Get the global signal aggregator."""
    global _signal_aggregator
    if _signal_aggregator is None:
        _signal_aggregator = SignalAggregator()
    return _signal_aggregator


def init_state() -> tuple[PortfolioManager, SignalAggregator]:
    """Initialize global state objects."""
    global _portfolio_manager, _signal_aggregator
    _portfolio_manager = PortfolioManager()
    _signal_aggregator = SignalAggregator()
    return _portfolio_manager, _signal_aggregator


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "SleeveManager",
    "PortfolioManager",
    "SignalAggregator",
    "get_portfolio_manager",
    "get_signal_aggregator",
    "init_state",
]
