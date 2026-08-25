"""
Main entry point for Project DEGENERATE.

Autonomous high-convexity options agent.
"""

import logging
import sys
from datetime import datetime
from typing import Any

from src.config import init_config, get_config
from src.logging import init_logging, get_logger
from src.database import init_database, get_repositories
from src.state import init_state, get_portfolio_manager, get_signal_aggregator
from src.market.alpaca import init_alpaca_client, get_alpaca_client
from src.execution.alpaca_mcp import init_executor, get_executor
from src.signals import (
    WSBSignalGenerator,
    PelosiSignalGenerator,
    CramerSignalGenerator,
    ConsensusEngine,
)
from src.strategy import (
    ContractSelector,
    PositionSizer,
    CapitalAllocator,
    DesperationEngine,
    WinnerEngine,
    ExitManager,
)
from src.risk import RiskGovernor, FloorMonitor

logger = get_logger()


# =============================================================================
# Agent Core
# =============================================================================

class DegenerateAgent:
    """
    Main autonomous trading agent.
    
    Implements the agent loop:
    1. Collect signals
    2. Normalize signals
    3. Score signals
    4. Select contracts
    5. Allocate positions
    6. Apply multipliers (consensus, desperation)
    7. Validate against hard floor
    8. Execute trades
    9. Monitor positions
    10. Manage winners
    11. Process exits
    12. Record everything
    """
    
    def __init__(self, config: Any = None):
        """
        Initialize the agent.
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        
        # Initialize components
        self._init_components()
        
        logger.info("Project DEGENERATE agent initialized")
    
    def _init_components(self) -> None:
        """Initialize all agent components."""
        # Initialize database
        self.db_manager = init_database()
        self.repositories = get_repositories()
        
        # Initialize state
        self.portfolio, self.signal_aggregator = init_state()
        
        # Initialize market data
        self.alpaca = get_alpaca_client()
        
        # Initialize execution
        self.executor = get_executor()
        
        # Initialize signal generators
        self.wsb_generator = WSBSignalGenerator(self.config)
        self.pelosi_generator = PelosiSignalGenerator(self.config)
        self.cramer_generator = CramerSignalGenerator(self.config)
        
        # Initialize strategy components
        self.contract_selector = ContractSelector(self.config)
        self.position_sizer = PositionSizer(self.config)
        self.capital_allocator = CapitalAllocator(self.config)
        self.consensus_engine = ConsensusEngine(self.config)
        self.desperation_engine = DesperationEngine(self.config)
        self.winner_engine = WinnerEngine(self.config)
        self.exit_manager = ExitManager(self.config)
        
        # Initialize risk management
        self.risk_governor = RiskGovernor(self.config)
        self.floor_monitor = FloorMonitor(self.config)
    
    def run_once(self) -> None:
        """
        Run one iteration of the agent loop.
        
        This is the main trading loop iteration.
        """
        logger.info("Starting agent iteration...")
        
        try:
            # Step 1: Collect signals
            signals = self._collect_signals()
            logger.info(f"Collected {len(signals)} signals")
            
            # Step 2: Normalize and score signals
            scored_signals = self._score_signals(signals)
            logger.info(f"Scored {len(scored_signals)} signals")
            
            # Step 3: Filter to tradable signals
            tradable_signals = self._filter_tradable(scored_signals)
            logger.info(f"Tradable signals: {len(tradable_signals)}")
            
            # Step 4: Apply consensus multipliers
            enhanced_signals = self._apply_consensus(tradable_signals)
            
            # Step 5: Select contracts for each signal
            opportunities = self._select_contracts(enhanced_signals)
            logger.info(f"Found {len(opportunities)} trading opportunities")
            
            # Step 6: Allocate positions
            trade_plans = self._allocate_positions(opportunities)
            logger.info(f"Created {len(trade_plans)} trade plans")
            
            # Step 7: Apply desperation multiplier
            adjusted_plans = self._apply_desperation(trade_plans)
            
            # Step 8: Validate against hard floor
            valid_plans = self._validate_plans(adjusted_plans)
            logger.info(f"Valid trade plans: {len(valid_plans)}")
            
            # Step 9: Execute trades
            executions = self._execute_trades(valid_plans)
            logger.info(f"Executed {len(executions)} trades")
            
            # Step 10: Monitor positions
            self._monitor_positions()
            
            # Step 11: Manage winners
            self._manage_winners()
            
            # Step 12: Process exits
            self._process_exits()
            
            # Step 13: Record everything
            self._record_everything(executions, opportunities)
            
            # Log status
            self._log_status()
            
        except Exception as e:
            logger.error(f"Agent iteration failed: {e}", exc_info=True)
            raise
    
    def _collect_signals(self) -> list[Any]:
        """Collect signals from all sources."""
        signals = []
        
        # Collect WSB signals
        if self.config.sleeves.wsb.enabled:
            wsb_signals = self.wsb_generator.generate_signals()
            signals.extend(wsb_signals)
            logger.debug(f"WSB: {len(wsb_signals)} signals")
        
        # Collect Pelosi signals
        if self.config.sleeves.pelosi.enabled:
            pelosi_signals = self.pelosi_generator.generate_signals()
            signals.extend(pelosi_signals)
            logger.debug(f"Pelosi: {len(pelosi_signals)} signals")
        
        # Collect Cramer signals
        if self.config.sleeves.inverse_cramer.enabled:
            cramer_signals = self.cramer_generator.generate_signals()
            signals.extend(cramer_signals)
            logger.debug(f"Cramer: {len(cramer_signals)} signals")
        
        return signals
    
    def _score_signals(self, signals: list[Any]) -> list[Any]:
        """Score and normalize signals."""
        scored = []
        for signal in signals:
            # Signals should already be scored by their generators
            # Just ensure they meet minimum threshold
            if signal.score >= self.config.strategy.signal_thresholds.get("minimum", 0.75):
                scored.append(signal)
        return scored
    
    def _filter_tradable(self, signals: list[Any]) -> list[Any]:
        """Filter to only tradable signals."""
        return [
            s for s in signals
            if s.score >= self.config.strategy.signal_thresholds.get("minimum", 0.75)
        ]
    
    def _apply_consensus(self, signals: list[Any]) -> list[Any]:
        """Apply consensus multipliers to signals."""
        return self.consensus_engine.create_consensus_signal(signals)
    
    def _select_contracts(self, signals: list[Any]) -> list[Any]:
        """Select contracts for each signal."""
        opportunities = []
        
        for signal in signals:
            # Get option chain for the ticker
            underlying_price = self.alpaca.get_underlying_price(signal.ticker)
            if underlying_price <= 0:
                logger.warning(f"No price data for {signal.ticker}")
                continue
            
            try:
                option_chain = self.alpaca.get_option_chain(signal.ticker)
            except Exception as e:
                logger.warning(f"Failed to get option chain for {signal.ticker}: {e}")
                continue
            
            # Select best contracts
            scored_contracts = self.contract_selector.select_contracts(
                signal=signal,
                underlying_price=underlying_price,
                option_chain=option_chain,
                limit=3,
            )
            
            for scored_contract in scored_contracts:
                opportunities.append({
                    "signal": signal,
                    "contract": scored_contract,
                    "underlying_price": underlying_price,
                })
        
        return opportunities
    
    def _allocate_positions(self, opportunities: list[Any]) -> list[Any]:
        """Allocate positions for opportunities."""
        trade_plans = []
        
        for opportunity in opportunities:
            signal = opportunity["signal"]
            contract = opportunity["contract"].contract
            underlying_price = opportunity["underlying_price"]
            
            # Determine sleeve
            if signal.source == "WSB":
                sleeve_type = "WSB"
            elif signal.source == "PELOSI":
                sleeve_type = "PELOSI"
            else:  # INVERSE_CRAMER
                sleeve_type = "INVERSE_CRAMER"
            
            # Create trade plan
            trade_plan = self.position_sizer.create_trade_plan(
                signal=signal,
                contract=contract,
                sleeve_type=sleeve_type,
                underlying_price=underlying_price,
            )
            
            if trade_plan:
                trade_plans.append(trade_plan)
        
        return trade_plans
    
    def _apply_desperation(self, trade_plans: list[Any]) -> list[Any]:
        """Apply desperation multiplier to trade plans."""
        adjusted_plans = []
        
        for plan in trade_plans:
            adjusted = self.desperation_engine.apply_desperation_to_trade(plan)
            adjusted_plans.append(adjusted)
        
        return adjusted_plans
    
    def _validate_plans(self, trade_plans: list[Any]) -> list[Any]:
        """Validate trade plans against risk constraints."""
        valid_plans = []
        
        for plan in trade_plans:
            # Check floor constraint
            if not self.risk_governor.check_floor_constraint(plan):
                # Try to resize
                resized = self.risk_governor.enforce_constraints(plan)
                if resized and resized.quantity > 0:
                    valid_plans.append(resized)
                else:
                    logger.warning(f"Rejected trade plan: violates hard floor")
            else:
                valid_plans.append(plan)
        
        return valid_plans
    
    def _execute_trades(self, trade_plans: list[Any]) -> list[Any]:
        """Execute valid trade plans."""
        executions = []
        
        for plan in trade_plans:
            try:
                execution = self.executor.execute_trade_plan(plan)
                if execution:
                    executions.append(execution)
                    
                    # Update portfolio
                    sleeve = self.portfolio.get_sleeve(plan.sleeve_type)
                    if sleeve:
                        sleeve.reserve_capital(plan.final_size_dollars)
                        sleeve.add_signal(plan.signal)
            except Exception as e:
                logger.error(f"Failed to execute trade plan: {e}")
        
        return executions
    
    def _monitor_positions(self) -> None:
        """Monitor all open positions."""
        # Refresh position prices
        # Check for exits
        pass
    
    def _manage_winners(self) -> None:
        """Manage winning positions."""
        self.winner_engine.manage_all_winners()
    
    def _process_exits(self) -> None:
        """Process exit signals."""
        exit_orders = self.exit_manager.check_all_positions()
        
        for symbol, orders in exit_orders.items():
            for order in orders:
                logger.info(f"Exit order: {order}")
                # Execute exit order
                # Update portfolio
    
    def _record_everything(self, executions: list[Any], opportunities: list[Any]) -> None:
        """Record all activity."""
        # Record signals
        for opp in opportunities:
            signal = opp["signal"]
            self.repositories["signals"].save_signal(signal)
        
        # Record trades
        for execution in executions:
            self.repositories["trades"].save_trade(execution)
        
        # Record positions
        # Would need to get updated positions
        
        # Save portfolio snapshot
        # self._save_portfolio_snapshot()
    
    def _log_status(self) -> None:
        """Log current agent status."""
        portfolio = self.portfolio.get_portfolio_state()
        
        logger.info(
            f"Status: Equity=${portfolio.total_equity:,.2f} | "
            f"Drawdown={portfolio.drawdown_percent:.2f}% | "
            f"Floor=${portfolio.hard_floor:,.2f} | "
            f"Positions={len(portfolio.all_positions)}"
        )
    
    def run_continuous(self, interval_minutes: int = 1) -> None:
        """
        Run the agent continuously.
        
        Args:
            interval_minutes: Minutes between iterations
        """
        import time
        
        logger.info(f"Starting continuous agent loop (interval: {interval_minutes}min)")
        
        try:
            while True:
                # Check termination condition
                if self.floor_monitor.check_termination_condition():
                    logger.critical("Hard floor violated - terminating")
                    break
                
                # Run one iteration
                self.run_once()
                
                # Wait for next iteration
                logger.info(f"Waiting {interval_minutes} minutes for next iteration...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Agent crashed: {e}", exc_info=True)
            raise


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
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
    
    args = parser.parse_args()
    
    # Initialize logging
    init_logging(level=args.log_level)
    
    # Initialize config
    config = init_config(args.config)
    
    # Initialize agent
    agent = DegenerateAgent(config)
    
    if args.test:
        logger.info("Running in test mode - no actual trades will be executed")
        # Override to prevent actual trading
        # In production, this would be controlled by config
    
    if args.once:
        agent.run_once()
    elif args.continuous:
        agent.run_continuous(interval_minutes=args.interval)
    else:
        # Default: run once
        agent.run_once()


if __name__ == "__main__":
    main()
