"""
Signal processing module for Project DEGENERATE.

Provides signal ingestion, normalization, and scoring for:
- WallStreetBets
- Pelosi Tracker
- Inverse Cramer
"""

from src.signals.base import TradeSignal, SignalNormalizer, SignalScorer
from src.signals.wsb import WSBAnalyzer, WSBSignalGenerator
from src.signals.pelosi import PelosiAnalyzer, PelosiSignalGenerator
from src.signals.cramer import CramerAnalyzer, CramerSignalGenerator
from src.signals.consensus import ConsensusEngine

__all__ = [
    "TradeSignal",
    "SignalNormalizer",
    "SignalScorer",
    "WSBAnalyzer",
    "WSBSignalGenerator",
    "PelosiAnalyzer",
    "PelosiSignalGenerator",
    "CramerAnalyzer",
    "CramerSignalGenerator",
    "ConsensusEngine",
]
