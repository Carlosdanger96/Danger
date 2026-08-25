"""
Capital allocation and position sizing for Project DEGENERATE.

Handles how much capital to allocate to each trade based on:
- Signal confidence
- Sleeve allocation
- Consensus multiplier
- Desperation multiplier
- Hard floor constraint
"""

import logging
from typing import Any

from src.config import init_config
from src.models import (
    ContractTier,
    OptionContract,
    Position,
    SignalConfidence,
    SignalDirection,
    SleeveType,
    TradePlan,
    TradeSignal,
)
from src.state import get_portfolio_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Position Sizer
# =============================================================================

class PositionSizer:
    """Calculates position size based on signal and constraints."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def calculate_base_size(
        self,
        signal: TradeSignal,
        sleeve_type: SleeveType,
    ) -> float:
        """
        Calculate base position size as percentage of sleeve.
        
        Initial sizing:
        LOW SIGNAL: 5% of sleeve
        NORMAL SIGNAL: 10% of sleeve
        HIGH SIGNAL: 20% of sleeve
        EXTREME SIGNAL: 30% of sleeve
        
        Args:
            signal: The trading signal
            sleeve_type: The sleeve type
            
        Returns:
            Base size as percentage of sleeve allocation
        """
        sizing = self.config.strategy.sizing
        
        if signal.signal_level == SignalConfidence.EXTREME:
            return sizing.get("extreme", 0.30)
        elif signal.signal_level == SignalConfidence.HIGH:
            return sizing.get("high", 0.20)
        elif signal.signal_level == SignalConfidence.NORMAL:
            return sizing.get("normal", 0.10)
        else:  # LOW
            return sizing.get("low", 0.05)
    
    def calculate_dollar_size(
        self,
        signal: TradeSignal,
        sleeve_type: SleeveType,
        contract: OptionContract,
    ) -> float:
        """
        Calculate dollar amount to allocate to a position.
        
        Args:
            signal: The trading signal
            sleeve_type: The sleeve type
            contract: The selected option contract
            
        Returns:
            Dollar amount to allocate
        """
        portfolio = get_portfolio_manager()
        sleeve = portfolio.get_sleeve(sleeve_type)
        
        if sleeve is None:
            logger.error(f"Sleeve {sleeve_type} not found")
            return 0.0
        
        # Base size as percentage of sleeve
        base_percent = self.calculate_base_size(signal, sleeve_type)
        base_dollars = sleeve.total_allocation * base_percent
        
        # Apply multipliers
        consensus_multiplier = signal.metadata.get("consensus_multiplier", 1.0)
        desperation_multiplier = portfolio.get_desperation_multiplier()
        
        # Calculate final size
        final_dollars = base_dollars * consensus_multiplier * desperation_multiplier
        
        # Ensure we don't exceed available cash
        final_dollars = min(final_dollars, sleeve.available_cash)
        
        # Ensure we don't exceed max order size
        max_order_size = self.config.execution.max_order_size
        final_dollars = min(final_dollars, max_order_size)
        
        return final_dollars
    
    def calculate_contract_count(
        self,
        dollar_amount: float,
        contract: OptionContract,
    ) -> int:
        """
        Calculate number of contracts to trade.
        
        Args:
            dollar_amount: Dollar amount to allocate
            contract: The option contract
            
        Returns:
            Number of contracts (integer)
        """
        if contract.mid_price <= 0:
            return 0
        
        # Number of contracts = dollar_amount / (contract_price * 100)
        # Options typically trade in contracts of 100 shares
        contracts = dollar_amount / (contract.mid_price * 100)
        
        # Round down to whole contracts
        return int(contracts)
    
    def create_trade_plan(
        self,
        signal: TradeSignal,
        contract: OptionContract,
        sleeve_type: SleeveType,
        underlying_price: float,
    ) -> TradePlan | None:
        """
        Create a complete trade plan.
        
        Args:
            signal: The trading signal
            contract: The selected option contract
            sleeve_type: The sleeve type
            underlying_price: Current underlying price
            
        Returns:
            TradePlan or None if trade is not viable
        """
        portfolio = get_portfolio_manager()
        sleeve = portfolio.get_sleeve(sleeve_type)
        
        if sleeve is None:
            logger.error(f"Sleeve {sleeve_type} not found")
            return None
        
        # Calculate dollar amount
        dollar_amount = self.calculate_dollar_size(signal, sleeve_type, contract)
        
        if dollar_amount <= 0:
            logger.warning(f"Zero or negative dollar amount for {signal.ticker}")
            return None
        
        # Calculate contract count
        contract_count = self.calculate_contract_count(dollar_amount, contract)
        
        if contract_count <= 0:
            logger.warning(f"Zero or negative contract count for {signal.ticker}")
            return None
        
        # Calculate actual dollar amount (contract_count * contract_price * 100)
        actual_dollar_amount = contract_count * contract.mid_price * 100
        
        # Determine direction
        if signal.direction == SignalDirection.CALL:
            side = "BUY_TO_OPEN"
        else:
            side = "SELL_TO_OPEN"
        
        # Get multipliers
        consensus_multiplier = signal.metadata.get("consensus_multiplier", 1.0)
        desperation_multiplier = portfolio.get_desperation_multiplier()
        
        # Calculate max loss (premium at risk)
        max_loss = actual_dollar_amount
        
        # Calculate worst case equity
        worst_case_equity = portfolio.total_equity - max_loss - portfolio.total_open_risk
        
        # Check floor constraint
        if worst_case_equity < portfolio.hard_floor:
            # Need to resize
            max_allowed_loss = portfolio.total_equity - portfolio.hard_floor - portfolio.total_open_risk
            if max_allowed_loss <= 0:
                logger.warning(f"Cannot trade {signal.ticker}: would violate hard floor")
                return None
            
            # Scale down proportionally
            scale_factor = max_allowed_loss / max_loss
            contract_count = max(1, int(contract_count * scale_factor))
            actual_dollar_amount = contract_count * contract.mid_price * 100
            max_loss = actual_dollar_amount
        
        # Create trade plan
        trade_plan = TradePlan(
            signal=signal,
            contract=contract,
            sleeve_type=sleeve_type,
            base_size_percent=self.calculate_base_size(signal, sleeve_type),
            consensus_multiplier=consensus_multiplier,
            desperation_multiplier=desperation_multiplier,
            final_size_dollars=actual_dollar_amount,
            max_loss_if_wrong=max_loss,
            worst_case_equity=portfolio.total_equity - max_loss - portfolio.total_open_risk,
            quantity=contract_count,
        )
        
        return trade_plan


# =============================================================================
# Capital Allocator
# =============================================================================

class CapitalAllocator:
    """Manages capital allocation across sleeves and trades."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.sizer = PositionSizer(config)
    
    def allocate_to_sleeve(
        self,
        sleeve_type: SleeveType,
        signal: TradeSignal,
        contracts: list[Any],  # List of ScoredContract
    ) -> list[TradePlan]:
        """
        Allocate capital to trades within a sleeve.
        
        Args:
            sleeve_type: The sleeve type
            signal: The trading signal
            contracts: List of scored contracts
            
        Returns:
            List of TradePlan objects
        """
        portfolio = get_portfolio_manager()
        sleeve = portfolio.get_sleeve(sleeve_type)
        
        if sleeve is None:
            return []
        
        trade_plans = []
        
        for scored_contract in contracts:
            contract = scored_contract.contract
            
            # Create trade plan
            plan = self.sizer.create_trade_plan(
                signal=signal,
                contract=contract,
                sleeve_type=sleeve_type,
                underlying_price=0.0,  # Would need actual price
            )
            
            if plan is not None:
                trade_plans.append(plan)
        
        return trade_plans
    
    def allocate_across_sleeves(
        self,
        signals: list[TradeSignal],
    ) -> dict[SleeveType, list[TradePlan]]:
        """
        Allocate capital to trades across all sleeves.
        
        Args:
            signals: List of signals to allocate
            
        Returns:
            Dictionary mapping sleeve type to list of trade plans
        """
        allocation: dict[SleeveType, list[TradePlan]] = {}
        
        for signal in signals:
            # Determine which sleeve this signal belongs to
            sleeve_type = self._get_sleeve_for_signal(signal)
            
            if sleeve_type not in allocation:
                allocation[sleeve_type] = []
            
            # For now, just create a placeholder allocation
            # In production, this would select contracts and create trade plans
            
        return allocation
    
    def _get_sleeve_for_signal(self, signal: TradeSignal) -> SleeveType:
        """Get the appropriate sleeve for a signal."""
        return SleeveType(signal.source.value)
    
    def check_floor_constraint(self, trade_plan: TradePlan) -> bool:
        """
        Check if a trade plan would violate the hard floor.
        
        Args:
            trade_plan: The trade plan to check
            
        Returns:
            True if trade is allowed, False if it would violate floor
        """
        portfolio = get_portfolio_manager()
        
        worst_case_equity = (
            portfolio.total_equity
            - trade_plan.max_loss_if_wrong
            - portfolio.total_open_risk
        )
        
        return worst_case_equity >= portfolio.hard_floor
    
    def resize_to_floor(self, trade_plan: TradePlan) -> TradePlan:
        """
        Resize a trade plan to comply with hard floor constraint.
        
        Args:
            trade_plan: The trade plan to resize
            
        Returns:
            Resized trade plan
        """
        portfolio = get_portfolio_manager()
        
        max_allowed_loss = (
            portfolio.total_equity
            - portfolio.hard_floor
            - portfolio.total_open_risk
        )
        
        if max_allowed_loss <= 0:
            # Cannot trade at all
            trade_plan.quantity = 0
            trade_plan.final_size_dollars = 0.0
            return trade_plan
        
        if trade_plan.max_loss_if_wrong <= max_allowed_loss:
            # Already compliant
            return trade_plan
        
        # Scale down proportionally
        scale_factor = max_allowed_loss / trade_plan.max_loss_if_wrong
        
        new_quantity = max(1, int(trade_plan.quantity * scale_factor))
        new_dollar_amount = new_quantity * trade_plan.contract.mid_price * 100
        new_max_loss = new_dollar_amount
        
        trade_plan.quantity = new_quantity
        trade_plan.final_size_dollars = new_dollar_amount
        trade_plan.max_loss_if_wrong = new_max_loss
        trade_plan.worst_case_equity = portfolio.total_equity - new_max_loss - portfolio.total_open_risk
        
        return trade_plan


# =============================================================================
# Tier Allocator
# =============================================================================

class TierAllocator:
    """Allocates capital across contract tiers."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def get_tier_weights(self) -> dict[ContractTier, float]:
        """Get allocation weights for each tier."""
        tiers = self.config.strategy.contract_tiers
        return {
            ContractTier.TIER1_AGGRESSIVE: tiers.tier1.weight,
            ContractTier.TIER2_EXTREME: tiers.tier2.weight,
            ContractTier.TIER3_ABSURD: tiers.tier3.weight,
        }
    
    def allocate_by_tier(
        self,
        signal: TradeSignal,
        contracts_by_tier: dict[ContractTier, list[Any]],
        sleeve_type: SleeveType,
    ) -> dict[ContractTier, TradePlan]:
        """
        Allocate capital across contract tiers.
        
        The agent should disproportionately favor Tier 2 and occasionally
        allocate to Tier 3.
        
        Args:
            signal: The trading signal
            contracts_by_tier: Dictionary mapping tier to list of contracts
            sleeve_type: The sleeve type
            
        Returns:
            Dictionary mapping tier to TradePlan
        """
        weights = self.get_tier_weights()
        sizer = PositionSizer(self.config)
        
        allocation: dict[ContractTier, TradePlan] = {}
        
        for tier, contracts in contracts_by_tier.items():
            if not contracts:
                continue
            
            # Get the best contract from this tier
            best_contract = contracts[0].contract
            
            # Calculate weight for this tier
            weight = weights.get(tier, 0.0)
            
            # Create trade plan with tier-specific allocation
            plan = sizer.create_trade_plan(
                signal=signal,
                contract=best_contract,
                sleeve_type=sleeve_type,
                underlying_price=0.0,
            )
            
            if plan:
                # Scale by tier weight
                plan.final_size_dollars *= weight
                plan.quantity = sizer.calculate_contract_count(
                    plan.final_size_dollars, best_contract
                )
                allocation[tier] = plan
        
        return allocation


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "PositionSizer",
    "CapitalAllocator",
    "TierAllocator",
]
