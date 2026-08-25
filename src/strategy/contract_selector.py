"""
Contract selection for Project DEGENERATE.

Selects the best option contracts based on:
- Convexity
- Gamma
- Premium efficiency
- Liquidity
- Catalyst urgency
"""

import logging
from datetime import datetime
from typing import Any

from src.config import init_config
from src.market.options import ContractSelector as MarketContractSelector
from src.models import (
    ContractTier,
    OptionContract,
    OptionType,
    ScoredContract,
    SignalDirection,
    TradeSignal,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enhanced Contract Selector
# =============================================================================

class ContractSelector:
    """
    Selects the best option contracts for trading signals.
    
    Uses the market ContractSelector for base functionality and adds
    DEGENERATE-specific logic.
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.market_selector = MarketContractSelector(config)
    
    def select_contracts(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
        limit: int = 5,
    ) -> list[ScoredContract]:
        """
        Select the best contracts for a signal.
        
        Args:
            signal: The trading signal
            option_chain: All available option contracts
            underlying_price: Current underlying price
            limit: Maximum number of contracts to return
            
        Returns:
            List of scored contracts, sorted by score
        """
        return self.market_selector.select_contracts(
            signal=signal,
            underlying_price=underlying_price,
            option_chain=option_chain,
            limit=limit,
        )
    
    def select_by_tier(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
        tier: ContractTier,
        limit: int = 3,
    ) -> list[ScoredContract]:
        """
        Select contracts from a specific tier.
        
        Args:
            signal: The trading signal
            option_chain: All available option contracts
            underlying_price: Current underlying price
            tier: The contract tier to select from
            limit: Maximum number of contracts to return
            
        Returns:
            List of scored contracts from the specified tier
        """
        return self.market_selector.select_by_tier(
            signal=signal,
            underlying_price=underlying_price,
            option_chain=option_chain,
            tier=tier,
            limit=limit,
        )
    
    def select_best_contract(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
    ) -> ScoredContract | None:
        """
        Select the single best contract for a signal.
        
        Args:
            signal: The trading signal
            option_chain: All available option contracts
            underlying_price: Current underlying price
            
        Returns:
            The best scored contract or None
        """
        return self.market_selector.select_best_contract(
            signal=signal,
            underlying_price=underlying_price,
            option_chain=option_chain,
        )
    
    def select_for_high_convexity(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
        limit: int = 5,
    ) -> list[ScoredContract]:
        """
        Select contracts with the highest convexity.
        
        Primary objective: find contracts capable of nonlinear returns
        from relatively little premium.
        
        Args:
            signal: The trading signal
            option_chain: All available option contracts
            underlying_price: Current underlying price
            limit: Maximum number of contracts to return
            
        Returns:
            List of high-convexity contracts
        """
        # Filter for OTM contracts
        otm_contracts = []
        for contract in option_chain:
            if signal.direction == SignalDirection.CALL:
                if contract.strike > underlying_price:
                    otm_contracts.append(contract)
            else:  # PUT
                if contract.strike < underlying_price:
                    otm_contracts.append(contract)
        
        # Score contracts
        scored_contracts = []
        for contract in otm_contracts:
            scored = self.market_selector.scorer.score_contract(
                contract=contract,
                signal=signal,
                underlying_price=underlying_price,
                expected_move=0.20,  # Higher expected move for convexity
            )
            scored_contracts.append(scored)
        
        # Sort by convexity score (descending)
        scored_contracts.sort(key=lambda x: x.convexity_score, reverse=True)
        
        return scored_contracts[:limit]
    
    def select_for_last_chance_mode(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
        min_multiple: float = 5.0,
        limit: int = 3,
    ) -> list[ScoredContract]:
        """
        Select contracts for last-chance mode.
        
        Only very high-convexity positions qualify.
        Minimum target multiple = 5x
        
        Args:
            signal: The trading signal
            option_chain: All available option contracts
            underlying_price: Current underlying price
            min_multiple: Minimum target multiple (e.g., 5x)
            limit: Maximum number of contracts to return
            
        Returns:
            List of last-chance mode contracts
        """
        # Filter for Tier 2 and Tier 3 contracts
        tier2 = self.select_by_tier(signal, option_chain, underlying_price, ContractTier.TIER2_EXTREME, limit * 2)
        tier3 = self.select_by_tier(signal, option_chain, underlying_price, ContractTier.TIER3_ABSURD, limit * 2)
        
        # Combine and filter by upside potential
        all_contracts = tier2 + tier3
        
        # Filter for high upside potential
        high_potential = [
            c for c in all_contracts
            if c.upside_potential >= min_multiple * 100  # Convert to percentage
        ]
        
        # Sort by upside potential
        high_potential.sort(key=lambda x: x.upside_potential, reverse=True)
        
        return high_potential[:limit]
    
    def get_tier_preferences(self) -> dict[ContractTier, float]:
        """
        Get tier preferences for contract selection.
        
        The agent should disproportionately favor Tier 2 and occasionally
        allocate to Tier 3.
        
        Returns:
            Dictionary mapping tier to preference weight
        """
        return {
            ContractTier.TIER1_AGGRESSIVE: 0.30,
            ContractTier.TIER2_EXTREME: 0.50,
            ContractTier.TIER3_ABSURD: 0.20,
        }


# =============================================================================
# Contract Ranker
# =============================================================================

class ContractRanker:
    """Ranks contracts for selection."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.selector = ContractSelector(config)
    
    def rank_contracts(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
    ) -> list[ScoredContract]:
        """
        Rank all contracts for a signal.
        
        Args:
            signal: The trading signal
            option_chain: All available option contracts
            underlying_price: Current underlying price
            
        Returns:
            List of all contracts with scores, sorted by total score
        """
        # Score all contracts
        scored_contracts = []
        for contract in option_chain:
            scored = self.selector.market_selector.scorer.score_contract(
                contract=contract,
                signal=signal,
                underlying_price=underlying_price,
            )
            scored_contracts.append(scored)
        
        # Sort by total score (descending)
        scored_contracts.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored_contracts
    
    def rank_by_convexity(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
    ) -> list[ScoredContract]:
        """Rank contracts by convexity score."""
        scored_contracts = self.rank_contracts(signal, option_chain, underlying_price)
        scored_contracts.sort(key=lambda x: x.convexity_score, reverse=True)
        return scored_contracts
    
    def rank_by_gamma(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
    ) -> list[ScoredContract]:
        """Rank contracts by gamma score."""
        scored_contracts = self.rank_contracts(signal, option_chain, underlying_price)
        scored_contracts.sort(key=lambda x: x.gamma_score, reverse=True)
        return scored_contracts
    
    def rank_by_premium_efficiency(
        self,
        signal: TradeSignal,
        option_chain: list[OptionContract],
        underlying_price: float,
    ) -> list[ScoredContract]:
        """Rank contracts by premium efficiency."""
        scored_contracts = self.rank_contracts(signal, option_chain, underlying_price)
        scored_contracts.sort(key=lambda x: x.premium_efficiency, reverse=True)
        return scored_contracts


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ContractSelector",
    "ContractRanker",
]
