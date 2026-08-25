"""
Market data and execution module for Project DEGENERATE.

Provides interfaces for:
- Alpaca API integration (paper trading)
- Option chain retrieval
- Market data fetching
- Order execution
"""

from src.market.alpaca import (
    AlpacaClient,
    AlpacaMCPClient,
    get_alpaca_client,
    init_alpaca_client,
)

__all__ = [
    "AlpacaClient",
    "AlpacaMCPClient",
    "get_alpaca_client",
    "init_alpaca_client",
]
