#!/usr/bin/env python3
"""
Dry run script for Project DEGENERATE.

Runs the agent in simulation mode without executing actual trades.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import DegenerateAgent
from src.config import init_config
from src.logging import init_logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Project DEGENERATE - Dry Run Mode"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations to run",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    
    return parser.parse_args()


def run_dry_run():
    """Run the agent in dry run mode."""
    args = parse_args()
    
    # Initialize logging
    init_logging(level=args.log_level)
    
    # Initialize config
    config = init_config(args.config)
    
    logging.info("Starting dry run simulation...")
    logging.info(f"Running {args.iterations} iterations")
    
    # Initialize agent
    agent = DegenerateAgent(config)
    
    # Run multiple iterations
    for i in range(args.iterations):
        logging.info(f"\n=== Iteration {i + 1}/{args.iterations} ===")
        try:
            agent.run_once()
        except Exception as e:
            logging.error(f"Iteration {i + 1} failed: {e}")
            break
    
    logging.info("\nDry run simulation complete")


if __name__ == "__main__":
    run_dry_run()
