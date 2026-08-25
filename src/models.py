"""
Data models for Project DEGENERATE.

Defines the core data structures used throughout the system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Signal Models
# =============================================================================

class SignalSource(str, Enum):
    """Source of a trading signal."""
    WSB = "WSB"
    PELOSI = "PELOSI"
    INVERSE_CRAMER = "INVERSE_CRAMER"


class SignalDirection(str, Enum):
    """Direction of a trading signal."""
    CALL = "CALL"
    PUT = "PUT"
    NONE = "NONE"


class SignalConfidence(str, Enum):
    """Confidence level for a signal."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class TradeSignal(BaseModel):
    """
    Normalized trading signal from any source.
    
    All signal sources must output this format to keep data acquisition
    separate from trading logic.
    """
    source: SignalSource
    ticker: str
    direction: SignalDirection
    confidence: float  # 0.0 to 1.0
    urgency: float  # 0.0 to 1.0
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Computed fields
    score: float = 0.0
    signal_level: SignalConfidence = SignalConfidence.NORMAL
    
    def __hash__(self):
        return hash((self.source, self.ticker, self.direction, self.timestamp))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TradeSignal):
            return False
        return (
            self.source == other.source
            and self.ticker == other.ticker
            and self.direction == other.direction
            and self.timestamp == other.timestamp
        )


# =============================================================================
# WSB Signal Models
# =============================================================================

class WSBMentionData(BaseModel):
    """WSB ticker mention data."""
    ticker: str
    mentions_15m: int = 0
    mentions_1h: int = 0
    mentions_24h: int = 0
    mention_acceleration: float = 0.0
    post_score: float = 0.0
    comment_velocity: float = 0.0
    bullish_language: float = 0.0
    bearish_language: float = 0.0
    option_mentions: int = 0
    strike_mentions: list[float] = Field(default_factory=list)
    expiration_mentions: list[str] = Field(default_factory=list)
    price_momentum: float = 0.0
    volume_anomaly: float = 0.0
    option_volume: float = 0.0
    meme_intensity: float = 0.0


class WSBSignal(TradeSignal):
    """WSB-specific signal with additional metadata."""
    wsb_data: WSBMentionData = Field(default_factory=WSBMentionData)
    
    @classmethod
    def from_base(cls, signal: TradeSignal, wsb_data: WSBMentionData) -> "WSBSignal":
        return cls(
            source=signal.source,
            ticker=signal.ticker,
            direction=signal.direction,
            confidence=signal.confidence,
            urgency=signal.urgency,
            timestamp=signal.timestamp,
            metadata=signal.metadata,
            wsb_data=wsb_data,
        )


# =============================================================================
# Pelosi Signal Models
# =============================================================================

class TransactionType(str, Enum):
    """Type of congressional transaction."""
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    PARTIAL_SALE = "PARTIAL_SALE"


class PelosiDisclosure(BaseModel):
    """Raw Pelosi family disclosure data."""
    ticker: str
    asset: str
    transaction_type: TransactionType
    transaction_date: datetime
    disclosure_date: datetime
    value_range: tuple[float, float]  # (min, max) in USD
    
    @property
    def transaction_magnitude(self) -> float:
        """Estimated transaction size."""
        return (self.value_range[0] + self.value_range[1]) / 2


class PelosiSignal(TradeSignal):
    """Pelosi-specific signal with disclosure data."""
    disclosure: PelosiDisclosure
    disclosure_age_hours: float = 0.0
    post_disclosure_momentum: float = 0.0
    sector_momentum: float = 0.0
    
    @classmethod
    def from_base(
        cls, signal: TradeSignal, disclosure: PelosiDisclosure, **kwargs
    ) -> "PelosiSignal":
        return cls(
            source=signal.source,
            ticker=signal.ticker,
            direction=signal.direction,
            confidence=signal.confidence,
            urgency=signal.urgency,
            timestamp=signal.timestamp,
            metadata=signal.metadata,
            disclosure=disclosure,
            **kwargs,
        )


# =============================================================================
# Cramer Signal Models
# =============================================================================

class CramerRecommendation(str, Enum):
    """Cramer's explicit recommendation classification."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class CramerStatement(BaseModel):
    """Raw Cramer statement data."""
    ticker: str
    recommendation: CramerRecommendation
    statement: str
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    source: str  # e.g., "Mad Money", "CNBC Interview"
    polarity: float  # -1.0 (bearish) to 1.0 (bullish)


class CramerSignal(TradeSignal):
    """Cramer-specific signal with statement data."""
    cramer_statement: CramerStatement
    price_momentum_against_cramer: float = 0.0
    market_regime: float = 0.0
    
    @classmethod
    def from_base(
        cls, signal: TradeSignal, cramer_statement: CramerStatement, **kwargs
    ) -> "CramerSignal":
        return cls(
            source=signal.source,
            ticker=signal.ticker,
            direction=signal.direction,
            confidence=signal.confidence,
            urgency=signal.urgency,
            timestamp=signal.timestamp,
            metadata=signal.metadata,
            cramer_statement=cramer_statement,
            **kwargs,
        )


# =============================================================================
# Options Models
# =============================================================================

class OptionType(str, Enum):
    """Type of option contract."""
    CALL = "CALL"
    PUT = "PUT"


class OptionContract(BaseModel):
    """Option contract data from Alpaca."""
    symbol: str
    underlying: str
    option_type: OptionType
    strike: float
    expiration: datetime
    dte: int  # Days to expiration
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    iv: float = 0.0  # Implied volatility
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    volume: int = 0
    open_interest: int = 0
    in_the_money: bool = False
    
    @property
    def mid_price(self) -> float:
        """Midpoint between bid and ask."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last if self.last > 0 else 0.0
    
    @property
    def spread(self) -> float:
        """Bid-ask spread."""
        if self.bid > 0 and self.ask > 0:
            return self.ask - self.bid
        return 0.0
    
    @property
    def spread_percent(self) -> float:
        """Bid-ask spread as percentage of mid price."""
        mid = self.mid_price
        if mid > 0:
            return (self.spread / mid) * 100
        return 0.0


class ContractTier(str, Enum):
    """Contract tier classification."""
    TIER1_AGGRESSIVE = "TIER1_AGGRESSIVE"
    TIER2_EXTREME = "TIER2_EXTREME"
    TIER3_ABSURD = "TIER3_ABSURD"


class ScoredContract(BaseModel):
    """Option contract with scoring for selection."""
    contract: OptionContract
    tier: ContractTier
    convexity_score: float = 0.0
    signal_confidence: float = 0.0
    gamma_score: float = 0.0
    premium_efficiency: float = 0.0
    liquidity_score: float = 0.0
    catalyst_urgency: float = 0.0
    total_score: float = 0.0
    
    @property
    def upside_potential(self) -> float:
        """Estimated upside potential based on scoring."""
        return self.total_score * 100  # Scale for percentage


# =============================================================================
# Portfolio Models
# =============================================================================

class SleeveType(str, Enum):
    """Portfolio sleeve type."""
    WSB = "WSB"
    PELOSI = "PELOSI"
    INVERSE_CRAMER = "INVERSE_CRAMER"


class SleeveState(BaseModel):
    """State of a portfolio sleeve."""
    sleeve_type: SleeveType
    allocation: float  # Target allocation (e.g., 0.25 for 25%)
    available_cash: float = 0.0
    open_risk: float = 0.0  # Total premium at risk
    realized_profit: float = 0.0
    realized_loss: float = 0.0
    active_signals: list[TradeSignal] = Field(default_factory=list)
    open_positions: list[str] = Field(default_factory=list)  # Contract symbols
    
    @property
    def used_capital(self) -> float:
        """Capital currently deployed."""
        return self.allocation * 100000 - self.available_cash
    
    @property
    def pnl(self) -> float:
        """Realized P&L for this sleeve."""
        return self.realized_profit - self.realized_loss


class PortfolioState(BaseModel):
    """Overall portfolio state."""
    total_equity: float = 100000.0
    hard_floor: float = 30000.0
    max_drawdown: float = 0.70
    sleeves: dict[SleeveType, SleeveState] = Field(default_factory=dict)
    all_positions: list[str] = Field(default_factory=list)
    
    @property
    def current_drawdown(self) -> float:
        """Current drawdown from starting equity."""
        if self.total_equity >= 100000:
            return 0.0
        return (100000 - self.total_equity) / 100000
    
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


# =============================================================================
# Order Models
# =============================================================================

class OrderType(str, Enum):
    """Type of order."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(str, Enum):
    """Side of an order."""
    BUY = "BUY"
    SELL = "SELL"
    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"


class OrderStatus(str, Enum):
    """Status of an order."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class Order(BaseModel):
    """Order model for execution."""
    order_id: str
    symbol: str
    order_type: OrderType = OrderType.MARKET
    side: OrderSide
    quantity: int
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: str = "DAY"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    
    # Source tracking
    signal_source: SignalSource | None = None
    sleeve_type: SleeveType | None = None
    
    @property
    def is_open(self) -> bool:
        """Check if order is still open."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_completed(self) -> bool:
        """Check if order is completed."""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
            OrderStatus.REJECTED,
        ]


class Position(BaseModel):
    """Position model for tracking."""
    symbol: str
    underlying: str
    option_type: OptionType
    strike: float
    expiration: datetime
    quantity: int  # Positive for long, negative for short
    entry_price: float = 0.0
    entry_timestamp: datetime = Field(default_factory=datetime.utcnow)
    current_price: float = 0.0
    
    # Source tracking
    signal_source: SignalSource | None = None
    sleeve_type: SleeveType | None = None
    
    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.quantity < 0
    
    @property
    def absolute_quantity(self) -> int:
        """Absolute value of quantity."""
        return abs(self.quantity)
    
    @property
    def cost_basis(self) -> float:
        """Total cost basis for the position."""
        return self.entry_price * self.absolute_quantity
    
    @property
    def mark_to_market(self) -> float:
        """Current market value."""
        return self.current_price * self.absolute_quantity
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L."""
        if self.is_long:
            return self.mark_to_market - self.cost_basis
        else:
            return self.cost_basis - self.mark_to_market


# =============================================================================
# Trade Execution Models
# =============================================================================

class TradePlan(BaseModel):
    """Planned trade before execution."""
    signal: TradeSignal
    contract: OptionContract
    sleeve_type: SleeveType
    
    # Sizing
    base_size_percent: float = 0.0  # % of sleeve allocation
    consensus_multiplier: float = 1.0
    desperation_multiplier: float = 1.0
    final_size_dollars: float = 0.0
    
    # Validation
    max_loss_if_wrong: float = 0.0  # Max loss if position goes to zero
    worst_case_equity: float = 0.0
    
    # Execution
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    limit_price: float | None = None
    
    @property
    def premium_risk(self) -> float:
        """Total premium at risk."""
        return self.final_size_dollars
    
    @property
    def contract_count(self) -> int:
        """Number of contracts to trade."""
        if self.contract.mid_price > 0:
            return int(self.final_size_dollars / self.contract.mid_price)
        return 0


class TradeExecution(BaseModel):
    """Executed trade record."""
    trade_id: str
    trade_plan: TradePlan
    order: Order
    execution_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Results
    filled_quantity: int = 0
    filled_price: float = 0.0
    total_cost: float = 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if trade was executed successfully."""
        return self.filled_quantity > 0


# =============================================================================
# Performance Tracking Models
# =============================================================================

class PerformanceRecord(BaseModel):
    """Performance record for a completed trade."""
    trade_id: str
    signal_source: SignalSource
    sleeve_type: SleeveType
    ticker: str
    contract_symbol: str
    entry_timestamp: datetime
    exit_timestamp: datetime | None = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: int = 0
    
    # Results
    max_gain: float = 0.0
    max_loss: float = 0.0
    final_return: float = 0.0
    return_percent: float = 0.0
    
    # Classification
    contract_tier: ContractTier | None = None
    signal_confidence: SignalConfidence | None = None
    
    @property
    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.exit_timestamp is None
    
    @property
    def duration_seconds(self) -> float:
        """Duration of trade in seconds."""
        if self.exit_timestamp is None:
            return 0.0
        return (self.exit_timestamp - self.entry_timestamp).total_seconds()
    
    @property
    def duration_minutes(self) -> float:
        """Duration of trade in minutes."""
        return self.duration_seconds / 60


class PerformanceSummary(BaseModel):
    """Summary of performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    sharpe_ratio: float = 0.0  # Not an optimization target, but tracked
    
    # By sleeve
    sleeve_performance: dict[SleeveType, dict[str, float]] = Field(default_factory=dict)
    
    # By source
    source_performance: dict[SignalSource, dict[str, float]] = Field(default_factory=dict)
    
    @property
    def profit_factor(self) -> float:
        """Profit factor (gross wins / gross losses)."""
        if self.avg_loss == 0:
            return float('inf') if self.avg_win > 0 else 0.0
        return self.avg_win / abs(self.avg_loss)
