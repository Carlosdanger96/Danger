"""
Scheduler for Project DEGENERATE.

Handles scheduled tasks and market hours.
"""

import logging
import time
from datetime import datetime, time as dt_time
from typing import Any, Callable

import pytz

from src.config import init_config

logger = logging.getLogger(__name__)


# =============================================================================
# Market Hours
# =============================================================================

class MarketHours:
    """Manages market hours and trading windows."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.timezone = pytz.timezone(self.config.market.timezone)
        self.open_time = self._parse_time(self.config.market.open_time)
        self.close_time = self._parse_time(self.config.market.close_time)
    
    def _parse_time(self, time_str: str) -> dt_time:
        """Parse time string into time object."""
        return datetime.strptime(time_str, "%H:%M").time()
    
    def is_market_open(self) -> bool:
        """
        Check if market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        now = datetime.now(self.timezone)
        current_time = now.time()
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check if within market hours
        return self.open_time <= current_time <= self.close_time
    
    def is_market_closed(self) -> bool:
        """Check if market is currently closed."""
        return not self.is_market_open()
    
    def get_time_until_open(self) -> int:
        """
        Get seconds until market opens.
        
        Returns:
            Seconds until open (0 if already open)
        """
        now = datetime.now(self.timezone)
        current_time = now.time()
        
        if self.is_market_open():
            return 0
        
        # If before open time today
        if current_time < self.open_time:
            open_datetime = datetime.combine(now.date(), self.open_time)
            delta = open_datetime - now
            return delta.total_seconds()
        
        # If after close time today, calculate until tomorrow
        tomorrow = now.date() + timedelta(days=1)
        open_datetime = datetime.combine(tomorrow, self.open_time)
        delta = open_datetime - now
        return delta.total_seconds()
    
    def get_time_until_close(self) -> int:
        """
        Get seconds until market closes.
        
        Returns:
            Seconds until close (0 if already closed)
        """
        now = datetime.now(self.timezone)
        current_time = now.time()
        
        if not self.is_market_open():
            return 0
        
        close_datetime = datetime.combine(now.date(), self.close_time)
        delta = close_datetime - now
        return delta.total_seconds()
    
    def wait_until_open(self) -> None:
        """Wait until market opens."""
        seconds = self.get_time_until_open()
        if seconds > 0:
            logger.info(f"Market closed - waiting {seconds:.0f} seconds until open")
            time.sleep(seconds)


# =============================================================================
# Task Scheduler
# =============================================================================

class TaskScheduler:
    """Schedules and runs periodic tasks."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.market_hours = MarketHours(config)
        self.tasks: list[tuple[Callable, int, str]] = []  # (task, interval_seconds, name)
        self.running = False
    
    def add_task(
        self,
        task: Callable,
        interval_seconds: int,
        name: str,
    ) -> None:
        """
        Add a periodic task.
        
        Args:
            task: The task function to call
            interval_seconds: Interval between executions
            name: Task name for logging
        """
        self.tasks.append((task, interval_seconds, name))
        logger.info(f"Added task: {name} (interval: {interval_seconds}s)")
    
    def remove_task(self, name: str) -> bool:
        """
        Remove a task by name.
        
        Args:
            name: The task name
            
        Returns:
            True if removed, False if not found
        """
        for i, (task, interval, task_name) in enumerate(self.tasks):
            if task_name == name:
                del self.tasks[i]
                logger.info(f"Removed task: {name}")
                return True
        return False
    
    def run_once(self) -> None:
        """Run all tasks once."""
        for task, interval, name in self.tasks:
            try:
                logger.debug(f"Running task: {name}")
                task()
            except Exception as e:
                logger.error(f"Task {name} failed: {e}")
    
    def run_continuous(self) -> None:
        """Run tasks continuously."""
        self.running = True
        
        try:
            while self.running:
                # Only run if market is open
                if self.market_hours.is_market_open():
                    self.run_once()
                
                # Sleep for a short interval
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler crashed: {e}", exc_info=True)
            raise
    
    def start(self) -> None:
        """Start the scheduler in a background thread."""
        import threading
        self.running = True
        self.thread = threading.Thread(target=self.run_continuous, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")


# =============================================================================
# Scheduled Tasks
# =============================================================================

class ScheduledTasks:
    """Defines scheduled tasks for the agent."""
    
    def __init__(self, agent: Any):
        self.agent = agent
        self.scheduler = TaskScheduler()
        
        # Add scheduled tasks
        self._add_tasks()
    
    def _add_tasks(self) -> None:
        """Add all scheduled tasks."""
        # Run main trading loop every minute
        self.scheduler.add_task(
            task=self.agent.run_once,
            interval_seconds=60,
            name="main_trading_loop",
        )
        
        # Check positions every 30 seconds
        self.scheduler.add_task(
            task=self._check_positions,
            interval_seconds=30,
            name="position_monitor",
        )
        
        # Check exits every 30 seconds
        self.scheduler.add_task(
            task=self._check_exits,
            interval_seconds=30,
            name="exit_checker",
        )
        
        # Log status every 5 minutes
        self.scheduler.add_task(
            task=self._log_status,
            interval_seconds=300,
            name="status_logger",
        )
    
    def _check_positions(self) -> None:
        """Check all positions."""
        self.agent._monitor_positions()
    
    def _check_exits(self) -> None:
        """Check for exit signals."""
        self.agent._process_exits()
    
    def _log_status(self) -> None:
        """Log agent status."""
        self.agent._log_status()
    
    def start(self) -> None:
        """Start all scheduled tasks."""
        self.scheduler.start()
    
    def stop(self) -> None:
        """Stop all scheduled tasks."""
        self.scheduler.stop()


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "MarketHours",
    "TaskScheduler",
    "ScheduledTasks",
]
