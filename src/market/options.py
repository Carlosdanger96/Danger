"""
Options analysis for Project DEGENERATE.

Provides contract scoring, selection, and convexity analysis.
"""

import logging
from datetime import datetime
from typing import Any

from src.config import init_config
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
# Contract Filtering
# =============================================================================

class ContractFilter:
    """Filters option contracts based on criteria."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def filter_by_dte(self, contracts: list[OptionContract], min_dte: int, max_dte: int) -> list[OptionContract]:
        """Filter contracts by days to expiration."""
        return [c for c in contracts if min_dte <= c.dte <= max_dte]
    
    def filter_by_delta(self, contracts: list[OptionContract], min_delta: float, max_delta: float) -> list[OptionContract]:
        """Filter contracts by delta."""
        return [c for c in contracts if min_delta <= c.delta <= max_delta]
    
    def filter_by_option_type(self, contracts: list[OptionContract], option_type: OptionType) -> list[OptionContract]:
        """Filter contracts by option type (CALL or PUT)."""
        return [c for c in contracts if c.option_type == option_type]
    
    def filter_by_tier(self, contracts: list[OptionContract], tier: ContractTier) -> list[OptionContract]:
        """Filter contracts by tier."""
        if tier == ContractTier.TIER1_AGGRESSIVE:
            return self.filter_by_dte(contracts, 14, 45)
        elif tier == ContractTier.TIER2_EXTREME:
            return self.filter_by_dte(contracts, 7, 21)
        elif tier == ContractTier.TIER3_ABSURD:
            return self.filter_by_dte(contracts, 3, 14)
        return contracts
    
    def filter_liquid(self, contracts: list[OptionContract], min_volume: int = 10, min_open_interest: int = 50) -> list[OptionContract]:
        """Filter contracts by liquidity criteria."""
        return [
            c for c in contracts
            if c.volume >= min_volume and c.open_interest >= min_open_interest
        ]
    
    def filter_otm(
        self, 
        contracts: list[OptionContract], 
        underlying_price: float,
        min_distance: float = 0.05
    ) -> list[OptionContract]:
        """
        Filter for out-of-the-money contracts.
        
        Args:
            contracts: List of contracts to filter
            underlying_price: Current price of underlying
            min_distance: Minimum distance from current price (as decimal)
            
        Returns:
            List of OTM contracts
        """
        result = []
        for contract in contracts:
            if contract.option_type == OptionType.CALL:
                # CALL is OTM if strike > underlying
                if contract.strike > underlying_price * (1 + min_distance):
                    result.append(contract)
            elif contract.option_type == OptionType.PUT:
                # PUT is OTM if strike < underlying
                if contract.strike < underlying_price * (1 - min_distance):
                    result.append(contract)
        return result


# =============================================================================
# Contract Scoring
# =============================================================================

class ContractScorer:
    """Scores option contracts for selection."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
    
    def calculate_convexity_score(
        self,
        contract: OptionContract,
        underlying_price: float,
        expected_move: float = 0.10,
    ) -> float:
        """
        Calculate convexity score for a contract.
        
        ConvexityScore = (ExpectedMove * Gamma * Leverage) / Premium
        
        Args:
            contract: The option contract
            underlying_price: Current underlying price
            expected_move: Expected price move (as decimal, e.g., 0.10 for 10%)
            
        Returns:
            Convexity score
        """
        if contract.premium <= 0:
            return 0.0
        
        # Gamma represents how much delta changes per $1 move in underlying
        # Higher gamma = more convexity
        gamma = contract.gamma if contract.gamma > 0 else 0.01
        
        # Leverage: underlying value / premium
        leverage = underlying_price / contract.premium if contract.premium > 0 else 1.0
        
        # Convexity score
        convexity = (expected_move * gamma * leverage) / contract.premium
        
        return convexity if convexity > 0 else 0.0
    
    def calculate_gamma_score(self, contract: OptionContract) -> float:
        """Calculate gamma score (normalized 0-1)."""
        # Normalize gamma based on typical ranges
        # Gamma can vary widely, so we cap it
        gamma = abs(contract.gamma) if contract.gamma else 0.0
        
        # Typical gamma range for near-term options: 0.01 to 0.5
        # Normalize to 0-1 scale
        if gamma >= 0.5:
            return 1.0
        elif gamma <= 0.01:
            return 0.0
        else:
            return (gamma - 0.01) / (0.5 - 0.01)
    
    def calculate_premium_efficiency(self, contract: OptionContract, underlying_price: float) -> float:
        """
        Calculate premium efficiency (how cheap the option is relative to underlying).
        
        Lower premium relative to underlying = higher score.
        """
        if contract.premium <= 0 or underlying_price <= 0:
            return 0.0
        
        premium_percent = contract.premium / underlying_price
        
        # Invert: lower premium percent = higher score
        # Typical range: 0.01 to 0.20 (1% to 20% of underlying)
        if premium_percent >= 0.20:
            return 0.0
        elif premium_percent <= 0.01:
            return 1.0
        else:
            return 1.0 - ((premium_percent - 0.01) / (0.20 - 0.01))
    
    def calculate_liquidity_score(self, contract: OptionContract) -> float:
        """Calculate liquidity score based on volume and open interest."""
        if contract.volume <= 0 and contract.open_interest <= 0:
            return 0.0
        
        # Normalize volume and open interest
        volume_score = min(contract.volume / 100, 1.0)
        oi_score = min(contract.open_interest / 1000, 1.0)
        
        # Combined score
        return (volume_score * 0.4) + (oi_score * 0.6)
    
    def calculate_catalyst_urgency(self, contract: OptionContract, signal: TradeSignal) -> float:
        """Calculate catalyst urgency score."""
        # Base urgency from signal
        urgency = signal.urgency
        
        # Adjust based on DTE (shorter DTE = more urgent)
        if contract.dte <= 7:
            urgency *= 1.2
        elif contract.dte <= 3:
            urgency *= 1.5
        elif contract.dte >= 30:
            urgency *= 0.8
        
        return min(urgency, 1.0)
    
    def score_contract(
        self,
        contract: OptionContract,
        signal: TradeSignal,
        underlying_price: float,
        expected_move: float = 0.10,
    ) -> ScoredContract:
        """
        Score a contract for selection.
        
        TotalContractScore =
            0.35 * ConvexityScore
            + 0.20 * SignalConfidence
            + 0.15 * GammaScore
            + 0.10 * PremiumEfficiency
            + 0.10 * Liquidity
            + 0.10 * CatalystUrgency
        
        Args:
            contract: The option contract
            signal: The trading signal
            underlying_price: Current underlying price
            expected_move: Expected price move
            
        Returns:
            ScoredContract with all scores
        """
        # Calculate individual scores
        convexity_score = self.calculate_convexity_score(contract, underlying_price, expected_move)
        signal_confidence = signal.confidence
        gamma_score = self.calculate_gamma_score(contract)
        premium_efficiency = self.calculate_premium_efficiency(contract, underlying_price)
        liquidity_score = self.calculate_liquidity_score(contract)
        catalyst_urgency = self.calculate_catalyst_urgency(contract, signal)
        
        # Total score
        total_score = (
            0.35 * convexity_score
            + 0.20 * signal_confidence
            + 0.15 * gamma_score
            + 0.10 * premium_efficiency
            + 0.10 * liquidity_score
            + 0.10 * catalyst_urgency
        )
        
        # Determine tier
        tier = self._determine_tier(contract)
        
        return ScoredContract(
            contract=contract,
            tier=tier,
            convexity_score=convexity_score,
            signal_confidence=signal_confidence,
            gamma_score=gamma_score,
            premium_efficiency=premium_efficiency,
            liquidity_score=liquidity_score,
            catalyst_urgency=catalyst_urgency,
            total_score=total_score,
        )
    
    def _determine_tier(self, contract: OptionContract) -> ContractTier:
        """Determine contract tier based on DTE and delta."""
        if contract.dte >= 14 and 0.30 <= contract.delta <= 0.40:
            return ContractTier.TIER1_AGGRESSIVE
        elif contract.dte >= 7 and 0.15 <= contract.delta <= 0.30:
            return ContractTier.TIER2_EXTREME
        elif contract.dte >= 3 and 0.05 <= contract.delta <= 0.15:
            return ContractTier.TIER3_ABSURD
        elif contract.dte >= 3 and contract.delta <= 0.15:
            return ContractTier.TIER3_ABSURD
        elif contract.dte >= 7 and contract.delta <= 0.30:
            return ContractTier.TIER2_EXTREME
        else:
            return ContractTier.TIER1_AGGRESSIVE


# =============================================================================
# Contract Selector
# =============================================================================

class ContractSelector:
    """Selects the best option contracts for a given signal."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.filter = ContractFilter(config)
        self.scorer = ContractScorer(config)
    
    def select_contracts(
        self,
        signal: TradeSignal,
        underlying_price: float,
        option_chain: list[OptionContract],
        limit: int = 5,
    ) -> list[ScoredContract]:
        """
        Select the best contracts for a signal.
        
        Args:
            signal: The trading signal
            underlying_price: Current underlying price
            option_chain: All available option contracts
            limit: Maximum number of contracts to return
            
        Returns:
            List of scored contracts, sorted by score
        """
        # Filter by signal direction
        direction = signal.direction
        if direction == SignalDirection.CALL:
            contracts = self.filter.filter_by_option_type(option_chain, OptionType.CALL)
        elif direction == SignalDirection.PUT:
            contracts = self.filter.filter_by_option_type(option_chain, OptionType.PUT)
        else:
            contracts = option_chain
        
        # Filter by DTE range from config
        config = self.config
        min_dte = config.options.min_dte
        max_dte = config.options.max_dte
        contracts = self.filter.filter_by_dte(contracts, min_dte, max_dte)
        
        # Filter by preferred delta range
        preferred_min = config.options.preferred_delta_min
        preferred_max = config.options.preferred_delta_max
        contracts = self.filter.filter_by_delta(contracts, preferred_min, preferred_max)
        
        # Prefer OTM contracts
        if config.options.prefer_otm:
            contracts = self.filter.filter_otm(contracts, underlying_price)
        
        # Filter by liquidity
        contracts = self.filter.filter_liquid(contracts)
        
        # Score remaining contracts
        scored_contracts = []
        for contract in contracts:
            scored = self.scorer.score_contract(
                contract=contract,
                signal=signal,
                underlying_price=underlying_price,
            )
            scored_contracts.append(scored)
        
        # Sort by total score (descending)
        scored_contracts.sort(key=lambda x: x.total_score, reverse=True)
        
        # Return top N
        return scored_contracts[:limit]
    
    def select_best_contract(
        self,
        signal: TradeSignal,
        underlying_price: float,
        option_chain: list[OptionContract],
    ) -> ScoredContract | None:
        """Select the single best contract for a signal."""
        contracts = self.select_contracts(signal, underlying_price, option_chain, limit=1)
        return contracts[0] if contracts else None
    
    def select_by_tier(
        self,
        signal: TradeSignal,
        underlying_price: float,
        option_chain: list[OptionContract],
        tier: ContractTier,
        limit: int = 3,
    ) -> list[ScoredContract]:
        """Select contracts from a specific tier."""
        # Filter by tier first
        filtered = self.filter.filter_by_tier(option_chain, tier)
        
        # Then apply other filters
        direction = signal.direction
        if direction == SignalDirection.CALL:
            filtered = self.filter.filter_by_option_type(filtered, OptionType.CALL)
        elif direction == SignalDirection.PUT:
            filtered = self.filter.filter_by_option_type(filtered, OptionType.PUT)
        
        # Filter by DTE
        config = self.config
        filtered = self.filter.filter_by_dte(filtered, config.options.min_dte, config.options.max_dte)
        
        # Score and sort
        scored_contracts = []
        for contract in filtered:
            scored = self.scorer.score_contract(
                contract=contract,
                signal=signal,
                underlying_price=underlying_price,
            )
            scored_contracts.append(scored)
        
        scored_contracts.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored_contracts[:limit]


# =============================================================================
# Greeks Calculation (Placeholder)
# =============================================================================

class GreeksCalculator:
    """
    Calculates option Greeks.
    
    Note: This is a placeholder. In production, we'd use:
    1. Alpaca's built-in Greeks
    2. Black-Scholes calculation
    3. External pricing service
    """
    
    def __init__(self):
        pass
    
    def calculate_delta(
        self,
        underlying_price: float,
        strike: float,
        dte: int,
        iv: float,
        option_type: OptionType,
        risk_free_rate: float = 0.05,
    ) -> float:
        """Calculate delta using Black-Scholes (simplified)."""
        # This is a placeholder - use proper Black-Scholes in production
        if option_type == OptionType.CALL:
            if underlying_price > strike:
                return min(1.0, max(0.0, underlying_price - strike) / underlying_price)
            else:
                return max(0.0, 0.5 - (strike - underlying_price) / (2 * underlying_price))
        else:  # PUT
            if underlying_price < strike:
                return min(1.0, max(0.0, strike - underlying_price) / strike)
            else:
                return max(0.0, 0.5 - (underlying_price - strike) / (2 * strike))
    
    def calculate_gamma(
        self,
        underlying_price: float,
        strike: float,
        dte: int,
        iv: float,
    ) -> float:
        """Calculate gamma (simplified)."""
        # Placeholder - gamma is highest for ATM options with short DTE
        if dte <= 7:
            distance = abs(underlying_price - strike) / underlying_price
            if distance < 0.1:  # Near ATM
                return 0.3 / (dte ** 0.5)
            elif distance < 0.2:
                return 0.15 / (dte ** 0.5)
            else:
                return 0.05 / (dte ** 0.5)
        elif dte <= 30:
            return 0.1 / (dte ** 0.5)
        else:
            return 0.05 / (dte ** 0.5)
    
    def calculate_theta(
        self,
        underlying_price: float,
        strike: float,
        dte: int,
        iv: float,
        option_type: OptionType,
    ) -> float:
        """Calculate theta (time decay)."""
        # Placeholder - theta increases as expiration approaches
        if option_type == OptionType.CALL:
            if underlying_price > strike:
                return -0.01 * (1 + (30 / dte) if dte > 0 else 1)
            else:
                return -0.005 * (1 + (30 / dte) if dte > 0 else 1)
        else:  # PUT
            if underlying_price < strike:
                return -0.01 * (1 + (30 / dte) if dte > 0 else 1)
            else:
                return -0.005 * (1 + (30 / dte) if dte > 0 else 1)
    
    def calculate_vega(
        self,
        underlying_price: float,
        strike: float,
        dte: int,
    ) -> float:
        """Calculate vega (sensitivity to IV)."""
        # Placeholder - vega is higher for longer-dated options
        if dte >= 30:
            return 0.2
        elif dte >= 14:
            return 0.15
        elif dte >= 7:
            return 0.1
        else:
            return 0.05
    
    def calculate_rho(
        self,
        underlying_price: float,
        strike: float,
        dte: int,
        option_type: OptionType,
    ) -> float:
        """Calculate rho (sensitivity to interest rates)."""
        # Placeholder
        if option_type == OptionType.CALL:
            return 0.05 * (dte / 365)
        else:
            return -0.05 * (dte / 365)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ContractFilter",
    "ContractScorer",
    "ContractSelector",
    "GreeksCalculator",
]
