"""
Logging configuration for Project DEGENERATE.

Provides structured logging for the autonomous trading agent.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import colorlog


# =============================================================================
# Custom Formatter
# =============================================================================

class DegenerateFormatter(colorlog.ColoredFormatter):
    """Custom formatter for Project DEGENERATE logs."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(
            "%(log_color)s[%(asctime)s] %(levelname)-8s%(reset)s "
            "%(cyan)s%(name)s%(reset)s:%(cyan)s%(lineno)d%(reset)s - "
            "%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            *args,
            **kwargs
        )


# =============================================================================
# Logger Setup
# =============================================================================

def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    console: bool = True,
) -> logging.Logger:
    """
    Configure logging for Project DEGENERATE.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file, or None for no file logging
        console: Whether to log to console
        
    Returns:
        The root logger
    """
    # Convert level string to logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    logger = logging.getLogger("project_degenerate")
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = DegenerateFormatter()
    
    # Add console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Configure third-party loggers
    configure_third_party_loggers(log_level)
    
    return logger


def configure_third_party_loggers(level: int) -> None:
    """Configure logging for third-party libraries."""
    # Reduce noise from third-party libraries
    noisy_loggers = [
        "urllib3",
        "requests",
        "alpaca",
        "sqlalchemy",
        "pydantic",
        "httpcore",
        "httpx",
    ]
    
    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)


# =============================================================================
# Structured Logging
# =============================================================================

def log_signal(
    logger: logging.Logger,
    signal_source: str,
    ticker: str,
    direction: str,
    confidence: float,
    score: float,
    **kwargs,
) -> None:
    """Log a trading signal with structured data."""
    extra = {
        "signal_source": signal_source,
        "ticker": ticker,
        "direction": direction,
        "confidence": confidence,
        "score": score,
        **kwargs,
    }
    logger.info(
        f"Signal: {signal_source} -> {direction} {ticker} (confidence: {confidence:.2f}, score: {score:.2f})",
        extra=extra,
    )


def log_trade(
    logger: logging.Logger,
    trade_id: str,
    ticker: str,
    contract: str,
    side: str,
    quantity: int,
    price: float,
    sleeve: str,
    **kwargs,
) -> None:
    """Log a trade execution with structured data."""
    extra = {
        "trade_id": trade_id,
        "ticker": ticker,
        "contract": contract,
        "side": side,
        "quantity": quantity,
        "price": price,
        "sleeve": sleeve,
        **kwargs,
    }
    logger.info(
        f"Trade: {side} {quantity} {contract} @ ${price:.2f} (sleeve: {sleeve})",
        extra=extra,
    )


def log_position(
    logger: logging.Logger,
    symbol: str,
    quantity: int,
    entry_price: float,
    current_price: float,
    pnl: float,
    **kwargs,
) -> None:
    """Log a position with structured data."""
    extra = {
        "symbol": symbol,
        "quantity": quantity,
        "entry_price": entry_price,
        "current_price": current_price,
        "pnl": pnl,
        **kwargs,
    }
    logger.info(
        f"Position: {quantity} {symbol} (entry: ${entry_price:.2f}, current: ${current_price:.2f}, P&L: ${pnl:+.2f})",
        extra=extra,
    )


def log_portfolio(
    logger: logging.Logger,
    total_equity: float,
    drawdown: float,
    hard_floor: float,
    open_positions: int,
    **kwargs,
) -> None:
    """Log portfolio state with structured data."""
    extra = {
        "total_equity": total_equity,
        "drawdown": drawdown,
        "hard_floor": hard_floor,
        "open_positions": open_positions,
        **kwargs,
    }
    logger.info(
        f"Portfolio: ${total_equity:,.2f} (drawdown: {drawdown:.2%}, floor: ${hard_floor:,.2f}, positions: {open_positions})",
        extra=extra,
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str,
    **kwargs,
) -> None:
    """Log an error with structured data."""
    extra = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        **kwargs,
    }
    logger.error(
        f"Error in {context}: {type(error).__name__}: {error}",
        extra=extra,
        exc_info=True,
    )


def log_warning(
    logger: logging.Logger,
    message: str,
    context: str,
    **kwargs,
) -> None:
    """Log a warning with structured data."""
    extra = {
        "context": context,
        **kwargs,
    }
    logger.warning(f"Warning in {context}: {message}", extra=extra)


# =============================================================================
# Performance Logging
# =============================================================================

def log_performance(
    logger: logging.Logger,
    trade_id: str,
    pnl: float,
    return_percent: float,
    duration_minutes: float,
    **kwargs,
) -> None:
    """Log a completed trade's performance."""
    extra = {
        "trade_id": trade_id,
        "pnl": pnl,
        "return_percent": return_percent,
        "duration_minutes": duration_minutes,
        **kwargs,
    }
    if pnl > 0:
        logger.info(
            f"Win: ${pnl:+.2f} ({return_percent:+.2%}) in {duration_minutes:.1f}m",
            extra=extra,
        )
    else:
        logger.warning(
            f"Loss: ${pnl:+.2f} ({return_percent:+.2%}) in {duration_minutes:.1f}m",
            extra=extra,
        )


# =============================================================================
# Metrics Tracking
# =============================================================================

class MetricsTracker:
    """Track and log performance metrics."""
    
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("project_degenerate.metrics")
        self.metrics: dict[str, Any] = {}
    
    def increment(self, key: str, value: float = 1.0) -> None:
        """Increment a metric."""
        self.metrics[key] = self.metrics.get(key, 0.0) + value
    
    def set(self, key: str, value: Any) -> None:
        """Set a metric value."""
        self.metrics[key] = value
    
    def get(self, key: str, default: Any = 0.0) -> Any:
        """Get a metric value."""
        return self.metrics.get(key, default)
    
    def log_all(self) -> None:
        """Log all metrics."""
        if not self.metrics:
            return
        
        self.logger.info("Metrics: " + ", ".join(
            f"{k}={v}" for k, v in self.metrics.items()
        ))
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()


# =============================================================================
# Global Logger
# =============================================================================

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def init_logging(level: str = "INFO", log_file: str | Path | None = None) -> logging.Logger:
    """Initialize and return the global logger."""
    global _logger
    if _logger is None:
        _logger = setup_logging(level=level, log_file=log_file)
    return _logger
