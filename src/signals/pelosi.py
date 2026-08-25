"""
Pelosi signal processing for Project DEGENERATE.

Monitors congressional disclosure data and generates trading signals.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.config import init_config
from src.models import (
    PelosiDisclosure,
    PelosiSignal,
    SignalDirection,
    SignalSource,
    TransactionType,
    TradeSignal,
)
from src.signals.base import BaseSignalGenerator, SignalNormalizer, SignalScorer

logger = logging.getLogger(__name__)


# =============================================================================
# Pelosi Disclosure Parser
# =============================================================================

class PelosiDisclosureParser:
    """
    Parses Pelosi family disclosure data from official sources.
    
    Note: The official House disclosure database has usage restrictions.
    This implementation is designed for educational/hackathon use only.
    """
    
    # Known Pelosi family members to track
    PELOSI_FAMILY_MEMBERS = [
        "Nancy Pelosi",
        "Paul Pelosi",
        "Christine Pelosi",
        "Jacqueline Pelosi",
        "Paul Pelosi Jr.",
    ]
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.api_url = self.config.signal_sources.pelosi.api_url
    
    def parse_disclosure(self, disclosure_data: dict[str, Any]) -> PelosiDisclosure | None:
        """
        Parse a raw disclosure record.
        
        Args:
            disclosure_data: Raw disclosure data from API
            
        Returns:
            PelosiDisclosure or None if not a Pelosi family disclosure
        """
        # Check if this is a Pelosi family disclosure
        reporter = disclosure_data.get("reporter", "")
        if not any(member in reporter for member in self.PELOSI_FAMILY_MEMBERS):
            return None
        
        # Extract transaction details
        try:
            ticker = self._extract_ticker(disclosure_data)
            asset = disclosure_data.get("asset_description", "")
            transaction_type = self._parse_transaction_type(disclosure_data.get("transaction_type", ""))
            transaction_date = self._parse_date(disclosure_data.get("transaction_date", ""))
            disclosure_date = self._parse_date(disclosure_data.get("disclosure_date", ""))
            value_range = self._parse_value_range(disclosure_data.get("amount", ""))
            
            if not ticker or not transaction_type:
                return None
            
            return PelosiDisclosure(
                ticker=ticker,
                asset=asset,
                transaction_type=transaction_type,
                transaction_date=transaction_date,
                disclosure_date=disclosure_date,
                value_range=value_range,
            )
        except Exception as e:
            logger.error(f"Failed to parse Pelosi disclosure: {e}")
            return None
    
    def _extract_ticker(self, data: dict[str, Any]) -> str | None:
        """Extract ticker from disclosure data."""
        # Try different fields
        ticker = data.get("ticker") or data.get("symbol") or data.get("asset_symbol")
        
        if ticker:
            return str(ticker).upper()
        
        # Try to extract from asset description
        asset = data.get("asset_description", "")
        if asset:
            # Common patterns: "APPLE INC (AAPL)", "AAPL", "Apple - Common Stock"
            import re
            
            # Pattern: (TICKER)
            match = re.search(r'\(([A-Z]{1,5})\)', asset)
            if match:
                return match.group(1)
            
            # Pattern: TICKER at start
            match = re.match(r'^[A-Z]{2,5}', asset)
            if match:
                return match.group(0)
        
        return None
    
    def _parse_transaction_type(self, transaction_str: str) -> TransactionType:
        """Parse transaction type string."""
        transaction_str = str(transaction_str).upper()
        
        if "PURCHASE" in transaction_str:
            return TransactionType.PURCHASE
        elif "SALE" in transaction_str:
            if "PARTIAL" in transaction_str:
                return TransactionType.PARTIAL_SALE
            return TransactionType.SALE
        else:
            return TransactionType.PURCHASE  # Default
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string into datetime."""
        if not date_str:
            return datetime.utcnow()
        
        try:
            # Try different date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%b %d, %Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Fallback to today
            return datetime.utcnow()
        except:
            return datetime.utcnow()
    
    def _parse_value_range(self, value_str: str) -> tuple[float, float]:
        """Parse value range string into tuple of floats."""
        if not value_str:
            return (0.0, 0.0)
        
        try:
            # Common format: "$1,000,001 - $5,000,000"
            import re
            
            # Pattern: $X - $Y
            match = re.search(r'\$([\d,]+)\s*-\s*\$([\d,]+)', value_str)
            if match:
                min_val = float(match.group(1).replace(",", ""))
                max_val = float(match.group(2).replace(",", ""))
                return (min_val, max_val)
            
            # Pattern: $X or more
            match = re.search(r'\$([\d,]+)\s*or more', value_str)
            if match:
                min_val = float(match.group(1).replace(",", ""))
                return (min_val, min_val * 2)  # Estimate range
            
            # Pattern: Over $X
            match = re.search(r'Over\s*\$([\d,]+)', value_str)
            if match:
                min_val = float(match.group(1).replace(",", ""))
                return (min_val, min_val * 2)
            
            # Pattern: $X
            match = re.search(r'\$([\d,]+)', value_str)
            if match:
                val = float(match.group(1).replace(",", ""))
                return (val, val)
            
            return (0.0, 0.0)
        except:
            return (0.0, 0.0)


# =============================================================================
# Pelosi Data Fetcher
# =============================================================================

class PelosiDataFetcher:
    """
    Fetches Pelosi disclosure data from various sources.
    
    Note: This is a simplified implementation. In production, you would:
    1. Use the official House disclosure API
    2. Respect rate limits and usage restrictions
    3. Cache data appropriately
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.parser = PelosiDisclosureParser(config)
    
    def fetch_recent_disclosures(self, lookback_days: int = 30) -> list[PelosiDisclosure]:
        """
        Fetch recent Pelosi family disclosures.
        
        Args:
            lookback_days: Number of days to look back
            
        Returns:
            List of PelosiDisclosure objects
        """
        # Placeholder - in production, this would call the official API
        # For now, return empty list
        
        logger.info(f"Fetching Pelosi disclosures from last {lookback_days} days")
        
        # This would be implemented with actual API calls
        # Example sources:
        # - https://disclosures.clerk.house.gov/
        # - https://www.house.gov/representatives#find-your-rep
        
        return []
    
    def fetch_from_api(self) -> list[dict[str, Any]]:
        """
        Fetch raw disclosure data from API.
        
        Returns:
            List of raw disclosure records
        """
        # Placeholder for API integration
        return []
    
    def get_new_disclosures(self) -> list[PelosiDisclosure]:
        """
        Get new disclosures since last check.
        
        Returns:
            List of new PelosiDisclosure objects
        """
        # In production, track last fetch time and only return new disclosures
        return self.fetch_recent_disclosures(self.config.signal_sources.pelosi.lookback_days)


# =============================================================================
# Pelosi Analyzer
# =============================================================================

class PelosiAnalyzer:
    """Analyzes Pelosi disclosures and extracts trading signals."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.fetcher = PelosiDataFetcher(config)
        self.parser = PelosiDisclosureParser(config)
    
    def analyze_disclosure(self, disclosure: PelosiDisclosure) -> dict[str, Any]:
        """
        Analyze a Pelosi disclosure.
        
        Args:
            disclosure: The disclosure to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Calculate disclosure age
        disclosure_age = datetime.utcnow() - disclosure.disclosure_date
        disclosure_age_hours = disclosure_age.total_seconds() / 3600
        
        # Calculate transaction magnitude
        transaction_magnitude = disclosure.transaction_magnitude
        
        # Determine direction
        if disclosure.transaction_type == TransactionType.PURCHASE:
            direction = SignalDirection.CALL
        elif disclosure.transaction_type == TransactionType.SALE:
            direction = SignalDirection.PUT
        else:
            direction = SignalDirection.NONE
        
        return {
            "disclosure": disclosure,
            "direction": direction,
            "disclosure_age_hours": disclosure_age_hours,
            "transaction_magnitude": transaction_magnitude,
            "post_disclosure_momentum": 0.0,  # Would need price data
            "sector_momentum": 0.0,  # Would need sector data
        }
    
    def calculate_pelosi_score(self, analysis: dict[str, Any]) -> float:
        """
        Calculate PELOSI_SCORE for a disclosure.
        
        PELOSI_SCORE =
            0.30 * TransactionMagnitude
            + 0.25 * PostDisclosureMomentum
            + 0.20 * SectorMomentum
            + 0.15 * DisclosureFreshness
            + 0.10 * OptionConvexity
        
        Args:
            analysis: Analysis results from analyze_disclosure
            
        Returns:
            Pelosi score (0-1)
        """
        disclosure = analysis["disclosure"]
        
        # Normalize transaction magnitude (cap at $15M)
        magnitude = min(disclosure.transaction_magnitude / 15000000, 1.0)
        
        # Disclosure freshness (newer = better, cap at 7 days)
        age_hours = analysis["disclosure_age_hours"]
        freshness = max(0, 1.0 - (age_hours / (7 * 24)))
        
        # Placeholder for other factors
        post_disclosure_momentum = analysis.get("post_disclosure_momentum", 0.5)
        sector_momentum = analysis.get("sector_momentum", 0.5)
        option_convexity = 0.5  # Placeholder
        
        score = (
            0.30 * magnitude
            + 0.25 * post_disclosure_momentum
            + 0.20 * sector_momentum
            + 0.15 * freshness
            + 0.10 * option_convexity
        )
        
        return min(max(score, 0.0), 1.0)


# =============================================================================
# Pelosi Signal Generator
# =============================================================================

class PelosiSignalGenerator(BaseSignalGenerator):
    """Generates trading signals from Pelosi disclosures."""
    
    def __init__(self, config: Any = None):
        super().__init__(SignalSource.PELOSI)
        self.config = config or init_config()
        self.analyzer = PelosiAnalyzer(config)
        self.fetcher = PelosiDataFetcher(config)
        
        # Cache of processed disclosures
        self.processed_disclosures: set[str] = set()
    
    def add_disclosure(self, disclosure: PelosiDisclosure) -> None:
        """
        Add a disclosure for processing.
        
        Args:
            disclosure: The Pelosi disclosure to process
        """
        disclosure_id = f"{disclosure.ticker}_{disclosure.transaction_date.isoformat()}"
        if disclosure_id not in self.processed_disclosures:
            self.processed_disclosures.add(disclosure_id)
            # Store for processing
            self._disclosure_queue.append(disclosure)
    
    def process_disclosure(self, disclosure: PelosiDisclosure) -> TradeSignal | None:
        """
        Process a single disclosure into a signal.
        
        Args:
            disclosure: The disclosure to process
            
        Returns:
            TradeSignal or None if not actionable
        """
        # Analyze the disclosure
        analysis = self.analyzer.analyze_disclosure(disclosure)
        
        direction = analysis["direction"]
        if direction == SignalDirection.NONE:
            return None
        
        # Calculate score
        score = self.analyzer.calculate_pelosi_score(analysis)
        
        # Calculate urgency (newer disclosures = more urgent)
        disclosure_age_hours = analysis["disclosure_age_hours"]
        urgency = max(0, 1.0 - (disclosure_age_hours / (14 * 24)))
        
        # Create normalized signal
        signal = SignalNormalizer.normalize_to_trade_signal(
            source=SignalSource.PELOSI,
            ticker=disclosure.ticker,
            direction=direction,
            confidence=score,
            urgency=urgency,
            timestamp=disclosure.disclosure_date,
            metadata={
                "disclosure_date": disclosure.disclosure_date.isoformat(),
                "transaction_date": disclosure.transaction_date.isoformat(),
                "transaction_type": disclosure.transaction_type.value,
                "value_range": disclosure.value_range,
                "transaction_magnitude": disclosure.transaction_magnitude,
                "disclosure_age_hours": disclosure_age_hours,
            },
        )
        
        # Score the signal
        return self.scorer.score_signal(signal)
    
    def generate_signals(self) -> list[TradeSignal]:
        """Generate signals from queued disclosures."""
        signals = []
        
        # Fetch new disclosures
        new_disclosures = self.fetcher.get_new_disclosures()
        
        for disclosure in new_disclosures:
            signal = self.process_disclosure(disclosure)
            if signal:
                signals.append(signal)
        
        return self.score_and_filter(signals)
    
    def get_latest_signal(self, ticker: str | None = None) -> TradeSignal | None:
        """Get the latest signal."""
        signals = self.generate_signals()
        
        if ticker:
            signals = [s for s in signals if s.ticker == ticker]
        
        if signals:
            return max(signals, key=lambda x: x.timestamp)
        return None
    
    def clear_cache(self) -> None:
        """Clear processed disclosures cache."""
        self.processed_disclosures.clear()


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "PelosiDisclosureParser",
    "PelosiDataFetcher",
    "PelosiAnalyzer",
    "PelosiSignalGenerator",
]
