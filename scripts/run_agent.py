#!/usr/bin/env python3
"""
Run script for Project DEGENERATE agent.

Usage:
    python scripts/run_agent.py [--config config.yaml] [--continuous] [--interval 1]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import DegenerateAgent, main
from src.config import init_config
from src.logging import init_logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Project DEGENERATE - Autonomous High-Convexity Options Agent"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one iteration and exit",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Interval in minutes for continuous mode",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (no actual trades)",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset the database before running",
    )
    
    return parser.parse_args()


def run():
    """Run the agent."""
    args = parse_args()
    
    # Initialize logging
    init_logging(level=args.log_level)
    
    # Initialize config
    config = init_config(args.config)
    
    # Reset database if requested
    if args.reset_db:
        from src.database import create_database_manager
        db = create_database_manager()
        db.reset()
        logging.info("Database reset complete")
    
    # Initialize agent
    agent = DegenerateAgent(config)
    
    if args.test:
        logging.info("Running in test mode - no actual trades will be executed")
        # In production, this would be controlled by config
    
    if args.once:
        agent.run_once()
    elif args.continuous:
        agent.run_continuous(interval_minutes=args.interval)
    else:
        # Default: run once
        agent.run_once()


if __name__ == "__main__":
    run()
