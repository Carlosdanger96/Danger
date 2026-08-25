#!/usr/bin/env python3
"""
Reset script for Project DEGENERATE competition.

Resets the database and state for a fresh competition run.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.database import create_database_manager
from src.logging import init_logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Reset Project DEGENERATE for competition"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/trades.db",
        help="Path to database file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm reset (required)",
    )
    
    return parser.parse_args()


def reset_competition():
    """Reset the competition state."""
    args = parse_args()
    
    # Initialize logging
    init_logging(level=args.log_level)
    
    if not args.confirm:
        logging.error("Reset not confirmed. Use --confirm to reset.")
        sys.exit(1)
    
    logging.warning("Resetting competition database - ALL DATA WILL BE LOST")
    
    # Reset database
    db = create_database_manager(args.db_path)
    db.reset()
    
    logging.info("Database reset complete")
    logging.info(f"Starting equity: $100,000")
    logging.info(f"Hard floor: $30,000")
    logging.info("Ready for new competition run")


if __name__ == "__main__":
    reset_competition()
