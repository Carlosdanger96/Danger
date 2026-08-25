"""
Database layer for Project DEGENERATE.

Handles SQLite storage for signals, trades, positions, and performance data.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import create_engine, orm
from sqlalchemy.ext.declarative import declarative_base

from src.models import (
    ContractTier,
    PerformanceRecord,
    Position,
    SignalDirection,
    SignalSource,
    SleeveType,
    TradeExecution,
    TradeSignal,
)

logger = logging.getLogger(__name__)

Base = declarative_base()


# =============================================================================
# Database Models
# =============================================================================

class DBSignal(Base):
    """Database model for trade signals."""
    __tablename__ = "signals"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    signal_id = sa.Column(sa.String(64), unique=True, index=True)
    source = sa.Column(sa.String(32), nullable=False, index=True)
    ticker = sa.Column(sa.String(16), nullable=False, index=True)
    direction = sa.Column(sa.String(16), nullable=False)
    confidence = sa.Column(sa.Float, nullable=False)
    urgency = sa.Column(sa.Float, nullable=False)
    score = sa.Column(sa.Float, nullable=False, default=0.0)
    signal_level = sa.Column(sa.String(16), nullable=False, default="NORMAL")
    timestamp = sa.Column(sa.DateTime, nullable=False, index=True)
    metadata = sa.Column(sa.JSON, nullable=False, default={})
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    processed = sa.Column(sa.Boolean, nullable=False, default=False)
    processed_at = sa.Column(sa.DateTime, nullable=True)


class DBTrade(Base):
    """Database model for trade executions."""
    __tablename__ = "trades"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    trade_id = sa.Column(sa.String(64), unique=True, index=True)
    signal_id = sa.Column(sa.String(64), sa.ForeignKey("signals.signal_id"), index=True)
    
    # Signal info
    signal_source = sa.Column(sa.String(32), nullable=False)
    sleeve_type = sa.Column(sa.String(32), nullable=False)
    ticker = sa.Column(sa.String(16), nullable=False)
    direction = sa.Column(sa.String(16), nullable=False)
    
    # Contract info
    contract_symbol = sa.Column(sa.String(64), nullable=False)
    underlying = sa.Column(sa.String(16), nullable=False)
    option_type = sa.Column(sa.String(16), nullable=False)
    strike = sa.Column(sa.Float, nullable=False)
    expiration = sa.Column(sa.DateTime, nullable=False)
    
    # Order info
    order_id = sa.Column(sa.String(64), nullable=True)
    order_type = sa.Column(sa.String(16), nullable=False)
    side = sa.Column(sa.String(16), nullable=False)
    quantity = sa.Column(sa.Integer, nullable=False)
    limit_price = sa.Column(sa.Float, nullable=True)
    
    # Sizing
    base_size_percent = sa.Column(sa.Float, nullable=False)
    consensus_multiplier = sa.Column(sa.Float, nullable=False, default=1.0)
    desperation_multiplier = sa.Column(sa.Float, nullable=False, default=1.0)
    final_size_dollars = sa.Column(sa.Float, nullable=False)
    
    # Execution
    execution_timestamp = sa.Column(sa.DateTime, nullable=True)
    filled_quantity = sa.Column(sa.Integer, nullable=False, default=0)
    filled_price = sa.Column(sa.Float, nullable=False, default=0.0)
    total_cost = sa.Column(sa.Float, nullable=False, default=0.0)
    
    # Status
    status = sa.Column(sa.String(32), nullable=False, default="PENDING")
    
    # Timestamps
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DBPosition(Base):
    """Database model for current positions."""
    __tablename__ = "positions"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    symbol = sa.Column(sa.String(64), unique=True, index=True)
    underlying = sa.Column(sa.String(16), nullable=False)
    option_type = sa.Column(sa.String(16), nullable=False)
    strike = sa.Column(sa.Float, nullable=False)
    expiration = sa.Column(sa.DateTime, nullable=False)
    quantity = sa.Column(sa.Integer, nullable=False)
    entry_price = sa.Column(sa.Float, nullable=False)
    entry_timestamp = sa.Column(sa.DateTime, nullable=False)
    current_price = sa.Column(sa.Float, nullable=False, default=0.0)
    
    # Source tracking
    signal_source = sa.Column(sa.String(32), nullable=True)
    sleeve_type = sa.Column(sa.String(32), nullable=True)
    trade_id = sa.Column(sa.String(64), nullable=True)
    
    # Status
    is_open = sa.Column(sa.Boolean, nullable=False, default=True)
    closed_at = sa.Column(sa.DateTime, nullable=True)
    exit_price = sa.Column(sa.Float, nullable=True)
    
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class DBPerformance(Base):
    """Database model for performance records."""
    __tablename__ = "performance"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    trade_id = sa.Column(sa.String(64), unique=True, index=True)
    signal_source = sa.Column(sa.String(32), nullable=False)
    sleeve_type = sa.Column(sa.String(32), nullable=False)
    ticker = sa.Column(sa.String(16), nullable=False)
    contract_symbol = sa.Column(sa.String(64), nullable=False)
    
    # Timing
    entry_timestamp = sa.Column(sa.DateTime, nullable=False)
    exit_timestamp = sa.Column(sa.DateTime, nullable=True)
    
    # Pricing
    entry_price = sa.Column(sa.Float, nullable=False)
    exit_price = sa.Column(sa.Float, nullable=True)
    quantity = sa.Column(sa.Integer, nullable=False)
    
    # Results
    max_gain = sa.Column(sa.Float, nullable=False, default=0.0)
    max_loss = sa.Column(sa.Float, nullable=False, default=0.0)
    final_return = sa.Column(sa.Float, nullable=False, default=0.0)
    return_percent = sa.Column(sa.Float, nullable=False, default=0.0)
    
    # Classification
    contract_tier = sa.Column(sa.String(32), nullable=True)
    signal_confidence = sa.Column(sa.String(16), nullable=True)
    
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)


class DBSleeveState(Base):
    """Database model for sleeve state snapshots."""
    __tablename__ = "sleeve_states"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    sleeve_type = sa.Column(sa.String(32), nullable=False, index=True)
    snapshot_timestamp = sa.Column(sa.DateTime, nullable=False, index=True)
    available_cash = sa.Column(sa.Float, nullable=False)
    open_risk = sa.Column(sa.Float, nullable=False)
    realized_profit = sa.Column(sa.Float, nullable=False)
    realized_loss = sa.Column(sa.Float, nullable=False)
    total_equity = sa.Column(sa.Float, nullable=False)
    
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)


class DBPortfolioSnapshot(Base):
    """Database model for portfolio snapshots."""
    __tablename__ = "portfolio_snapshots"
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    snapshot_timestamp = sa.Column(sa.DateTime, nullable=False, index=True)
    total_equity = sa.Column(sa.Float, nullable=False)
    hard_floor = sa.Column(sa.Float, nullable=False)
    max_drawdown = sa.Column(sa.Float, nullable=False)
    current_drawdown = sa.Column(sa.Float, nullable=False)
    
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)


# =============================================================================
# Database Manager
# =============================================================================

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_path: str | Path = "data/trades.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.Session = orm.sessionmaker(bind=self.engine)
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the database with all tables."""
        if self._initialized:
            return
        
        logger.info(f"Initializing database at {self.db_path}")
        Base.metadata.create_all(self.engine)
        self._initialized = True
        logger.info("Database initialization complete")
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def reset(self) -> None:
        """Reset the database (DANGEROUS - for testing only)."""
        logger.warning("Resetting database - ALL DATA WILL BE LOST")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        logger.info("Database reset complete")


# =============================================================================
# Signal Repository
# =============================================================================

class SignalRepository:
    """Repository for signal operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def save_signal(self, signal: TradeSignal) -> str:
        """Save a signal to the database."""
        import uuid
        
        signal_id = str(uuid.uuid4())
        
        with self.db.get_session() as session:
            db_signal = DBSignal(
                signal_id=signal_id,
                source=signal.source.value,
                ticker=signal.ticker,
                direction=signal.direction.value,
                confidence=signal.confidence,
                urgency=signal.urgency,
                score=signal.score,
                signal_level=signal.signal_level.value,
                timestamp=signal.timestamp,
                metadata=signal.metadata,
            )
            session.add(db_signal)
            session.flush()
            logger.debug(f"Saved signal {signal_id} for {signal.ticker}")
            return signal_id
    
    def get_signal(self, signal_id: str) -> Optional[TradeSignal]:
        """Get a signal by ID."""
        with self.db.get_session() as session:
            db_signal = session.query(DBSignal).filter_by(signal_id=signal_id).first()
            if db_signal:
                return TradeSignal(
                    source=SignalSource(db_signal.source),
                    ticker=db_signal.ticker,
                    direction=SignalDirection(db_signal.direction),
                    confidence=db_signal.confidence,
                    urgency=db_signal.urgency,
                    timestamp=db_signal.timestamp,
                    metadata=db_signal.metadata,
                    score=db_signal.score,
                    signal_level=db_signal.signal_level,
                )
            return None
    
    def get_unprocessed_signals(self) -> list[TradeSignal]:
        """Get all unprocessed signals."""
        with self.db.get_session() as session:
            db_signals = session.query(DBSignal).filter_by(processed=False).all()
            signals = []
            for db_signal in db_signals:
                signal = TradeSignal(
                    source=SignalSource(db_signal.source),
                    ticker=db_signal.ticker,
                    direction=SignalDirection(db_signal.direction),
                    confidence=db_signal.confidence,
                    urgency=db_signal.urgency,
                    timestamp=db_signal.timestamp,
                    metadata=db_signal.metadata,
                    score=db_signal.score,
                    signal_level=db_signal.signal_level,
                )
                signals.append(signal)
            return signals
    
    def mark_signal_processed(self, signal_id: str) -> None:
        """Mark a signal as processed."""
        with self.db.get_session() as session:
            db_signal = session.query(DBSignal).filter_by(signal_id=signal_id).first()
            if db_signal:
                db_signal.processed = True
                db_signal.processed_at = datetime.utcnow()
                session.add(db_signal)
                logger.debug(f"Marked signal {signal_id} as processed")
    
    def get_signals_by_ticker(self, ticker: str, limit: int = 100) -> list[TradeSignal]:
        """Get recent signals for a specific ticker."""
        with self.db.get_session() as session:
            db_signals = (
                session.query(DBSignal)
                .filter_by(ticker=ticker)
                .order_by(DBSignal.timestamp.desc())
                .limit(limit)
                .all()
            )
            signals = []
            for db_signal in db_signals:
                signal = TradeSignal(
                    source=SignalSource(db_signal.source),
                    ticker=db_signal.ticker,
                    direction=SignalDirection(db_signal.direction),
                    confidence=db_signal.confidence,
                    urgency=db_signal.urgency,
                    timestamp=db_signal.timestamp,
                    metadata=db_signal.metadata,
                    score=db_signal.score,
                    signal_level=db_signal.signal_level,
                )
                signals.append(signal)
            return signals


# =============================================================================
# Trade Repository
# =============================================================================

class TradeRepository:
    """Repository for trade operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def save_trade(self, trade: TradeExecution) -> str:
        """Save a trade execution to the database."""
        import uuid
        
        trade_id = trade.trade_id if trade.trade_id else str(uuid.uuid4())
        
        with self.db.get_session() as session:
            db_trade = DBTrade(
                trade_id=trade_id,
                signal_id=trade.trade_plan.signal.metadata.get("signal_id", ""),
                signal_source=trade.trade_plan.signal.source.value,
                sleeve_type=trade.trade_plan.sleeve_type.value,
                ticker=trade.trade_plan.signal.ticker,
                direction=trade.trade_plan.signal.direction.value,
                contract_symbol=trade.trade_plan.contract.symbol,
                underlying=trade.trade_plan.contract.underlying,
                option_type=trade.trade_plan.contract.option_type.value,
                strike=trade.trade_plan.contract.strike,
                expiration=trade.trade_plan.contract.expiration,
                order_id=trade.order.order_id,
                order_type=trade.order.order_type.value,
                side=trade.order.side.value,
                quantity=trade.order.quantity,
                limit_price=trade.order.limit_price,
                base_size_percent=trade.trade_plan.base_size_percent,
                consensus_multiplier=trade.trade_plan.consensus_multiplier,
                desperation_multiplier=trade.trade_plan.desperation_multiplier,
                final_size_dollars=trade.trade_plan.final_size_dollars,
                execution_timestamp=trade.execution_timestamp,
                filled_quantity=trade.filled_quantity,
                filled_price=trade.filled_price,
                total_cost=trade.total_cost,
                status=trade.order.status.value,
            )
            session.add(db_trade)
            session.flush()
            logger.info(f"Saved trade {trade_id} for {trade.trade_plan.signal.ticker}")
            return trade_id
    
    def get_trade(self, trade_id: str) -> Optional[TradeExecution]:
        """Get a trade by ID."""
        with self.db.get_session() as session:
            db_trade = session.query(DBTrade).filter_by(trade_id=trade_id).first()
            if db_trade:
                # Reconstruct TradeExecution from DBTrade
                # This is a simplified reconstruction
                from src.models import Order, OrderStatus, OrderType, OrderSide
                
                order = Order(
                    order_id=db_trade.order_id or "",
                    symbol=db_trade.contract_symbol,
                    order_type=OrderType(db_trade.order_type),
                    side=OrderSide(db_trade.side),
                    quantity=db_trade.quantity,
                    limit_price=db_trade.limit_price,
                    status=OrderStatus(db_trade.status),
                    filled_quantity=db_trade.filled_quantity,
                    filled_price=db_trade.filled_price,
                )
                
                # Note: This is a simplified reconstruction
                # In production, you'd need to properly reconstruct TradePlan
                return TradeExecution(
                    trade_id=db_trade.trade_id,
                    trade_plan=None,  # Would need proper reconstruction
                    order=order,
                    execution_timestamp=db_trade.execution_timestamp,
                    filled_quantity=db_trade.filled_quantity,
                    filled_price=db_trade.filled_price,
                    total_cost=db_trade.total_cost,
                )
            return None
    
    def get_open_trades(self) -> list[TradeExecution]:
        """Get all open trades."""
        with self.db.get_session() as session:
            db_trades = session.query(DBTrade).filter(
                DBTrade.status.in_(["PENDING", "PARTIALLY_FILLED"])
            ).all()
            trades = []
            for db_trade in db_trades:
                from src.models import Order, OrderStatus, OrderType, OrderSide
                order = Order(
                    order_id=db_trade.order_id or "",
                    symbol=db_trade.contract_symbol,
                    order_type=OrderType(db_trade.order_type),
                    side=OrderSide(db_trade.side),
                    quantity=db_trade.quantity,
                    limit_price=db_trade.limit_price,
                    status=OrderStatus(db_trade.status),
                    filled_quantity=db_trade.filled_quantity,
                    filled_price=db_trade.filled_price,
                )
                trades.append(TradeExecution(
                    trade_id=db_trade.trade_id,
                    trade_plan=None,
                    order=order,
                    execution_timestamp=db_trade.execution_timestamp,
                    filled_quantity=db_trade.filled_quantity,
                    filled_price=db_trade.filled_price,
                    total_cost=db_trade.total_cost,
                ))
            return trades


# =============================================================================
# Position Repository
# =============================================================================

class PositionRepository:
    """Repository for position operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def save_position(self, position: Position) -> None:
        """Save or update a position."""
        with self.db.get_session() as session:
            db_position = session.query(DBPosition).filter_by(symbol=position.symbol).first()
            
            if db_position:
                # Update existing position
                db_position.quantity = position.quantity
                db_position.entry_price = position.entry_price
                db_position.current_price = position.current_price
                db_position.is_open = True
                db_position.closed_at = None
                db_position.exit_price = None
                db_position.updated_at = datetime.utcnow()
            else:
                # Create new position
                db_position = DBPosition(
                    symbol=position.symbol,
                    underlying=position.underlying,
                    option_type=position.option_type.value,
                    strike=position.strike,
                    expiration=position.expiration,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    entry_timestamp=position.entry_timestamp,
                    current_price=position.current_price,
                    signal_source=position.signal_source.value if position.signal_source else None,
                    sleeve_type=position.sleeve_type.value if position.sleeve_type else None,
                    is_open=True,
                )
                session.add(db_position)
            
            session.flush()
            logger.info(f"Saved position {position.symbol} with quantity {position.quantity}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a position by symbol."""
        with self.db.get_session() as session:
            db_position = session.query(DBPosition).filter_by(symbol=symbol, is_open=True).first()
            if db_position:
                return Position(
                    symbol=db_position.symbol,
                    underlying=db_position.underlying,
                    option_type=db_position.option_type,
                    strike=db_position.strike,
                    expiration=db_position.expiration,
                    quantity=db_position.quantity,
                    entry_price=db_position.entry_price,
                    entry_timestamp=db_position.entry_timestamp,
                    current_price=db_position.current_price,
                    signal_source=db_position.signal_source,
                    sleeve_type=db_position.sleeve_type,
                )
            return None
    
    def get_all_open_positions(self) -> list[Position]:
        """Get all open positions."""
        with self.db.get_session() as session:
            db_positions = session.query(DBPosition).filter_by(is_open=True).all()
            positions = []
            for db_position in db_positions:
                position = Position(
                    symbol=db_position.symbol,
                    underlying=db_position.underlying,
                    option_type=db_position.option_type,
                    strike=db_position.strike,
                    expiration=db_position.expiration,
                    quantity=db_position.quantity,
                    entry_price=db_position.entry_price,
                    entry_timestamp=db_position.entry_timestamp,
                    current_price=db_position.current_price,
                    signal_source=db_position.signal_source,
                    sleeve_type=db_position.sleeve_type,
                )
                positions.append(position)
            return positions
    
    def close_position(self, symbol: str, exit_price: float) -> None:
        """Close a position."""
        with self.db.get_session() as session:
            db_position = session.query(DBPosition).filter_by(symbol=symbol, is_open=True).first()
            if db_position:
                db_position.is_open = False
                db_position.closed_at = datetime.utcnow()
                db_position.exit_price = exit_price
                db_position.updated_at = datetime.utcnow()
                session.add(db_position)
                logger.info(f"Closed position {symbol} at {exit_price}")


# =============================================================================
# Performance Repository
# =============================================================================

class PerformanceRepository:
    """Repository for performance tracking."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def save_performance_record(self, record: PerformanceRecord) -> None:
        """Save a performance record."""
        with self.db.get_session() as session:
            db_record = DBPerformance(
                trade_id=record.trade_id,
                signal_source=record.signal_source.value,
                sleeve_type=record.sleeve_type.value,
                ticker=record.ticker,
                contract_symbol=record.contract_symbol,
                entry_timestamp=record.entry_timestamp,
                exit_timestamp=record.exit_timestamp,
                entry_price=record.entry_price,
                exit_price=record.exit_price if record.exit_price else None,
                quantity=record.quantity,
                max_gain=record.max_gain,
                max_loss=record.max_loss,
                final_return=record.final_return,
                return_percent=record.return_percent,
                contract_tier=record.contract_tier.value if record.contract_tier else None,
                signal_confidence=record.signal_confidence.value if record.signal_confidence else None,
            )
            session.add(db_record)
            session.flush()
            logger.info(f"Saved performance record for trade {record.trade_id}")
    
    def get_performance_summary(self) -> dict[str, Any]:
        """Get a summary of performance metrics."""
        with self.db.get_session() as session:
            # Get all completed trades
            completed_trades = session.query(DBPerformance).filter(
                DBPerformance.exit_timestamp.isnot(None)
            ).all()
            
            if not completed_trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "max_win": 0.0,
                    "max_loss": 0.0,
                }
            
            winning_trades = [t for t in completed_trades if t.final_return > 0]
            losing_trades = [t for t in completed_trades if t.final_return < 0]
            
            wins = [t.final_return for t in winning_trades]
            losses = [abs(t.final_return) for t in losing_trades]
            
            total_pnl = sum(t.final_return for t in completed_trades)
            
            return {
                "total_trades": len(completed_trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": len(winning_trades) / len(completed_trades) if completed_trades else 0.0,
                "total_pnl": total_pnl,
                "avg_win": sum(wins) / len(wins) if wins else 0.0,
                "avg_loss": sum(losses) / len(losses) if losses else 0.0,
                "max_win": max(wins) if wins else 0.0,
                "max_loss": max(losses) if losses else 0.0,
            }


# =============================================================================
# Database Factory
# =============================================================================

def create_database_manager(db_path: str | Path = "data/trades.db") -> DatabaseManager:
    """Create and initialize a database manager."""
    manager = DatabaseManager(db_path)
    manager.initialize()
    return manager


def create_repositories(db_manager: DatabaseManager):
    """Create all repositories for a database manager."""
    return {
        "signals": SignalRepository(db_manager),
        "trades": TradeRepository(db_manager),
        "positions": PositionRepository(db_manager),
        "performance": PerformanceRepository(db_manager),
    }


# Global database instance (lazy initialized)
_db_manager: DatabaseManager | None = None
_repositories: dict[str, Any] | None = None


def init_database(db_path: str | Path = "data/trades.db") -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager, _repositories
    if _db_manager is None:
        _db_manager = create_database_manager(db_path)
        _repositories = create_repositories(_db_manager)
    return _db_manager


def get_repositories() -> dict[str, Any]:
    """Get the global repositories."""
    global _repositories
    if _repositories is None:
        init_database()
    return _repositories


def get_signal_repository() -> SignalRepository:
    """Get the signal repository."""
    return get_repositories()["signals"]


def get_trade_repository() -> TradeRepository:
    """Get the trade repository."""
    return get_repositories()["trades"]


def get_position_repository() -> PositionRepository:
    """Get the position repository."""
    return get_repositories()["positions"]


def get_performance_repository() -> PerformanceRepository:
    """Get the performance repository."""
    return get_repositories()["performance"]
