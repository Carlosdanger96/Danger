"""
Alpaca API integration for Project DEGENERATE.

Handles market data, option chains, and paper trading execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.models import Order, OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import (
    GetOptionContractsRequest,
    MarketOrderRequest,
    LimitOrderRequest,
)
from pydantic import BaseModel

from src.config import get_alpaca_config
from src.models import (
    OptionContract,
    OptionType,
    Order as DegenerateOrder,
    OrderSide as DegenerateOrderSide,
    OrderStatus,
    OrderType as DegenerateOrderType,
    Position as DegeneratePosition,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Alpaca Client Wrapper
# =============================================================================

class AlpacaClient:
    """
    Wrapper around Alpaca TradingClient with paper trading support.
    
    Provides market data, option chains, and order execution.
    """
    
    def __init__(self, api_key: str | None = None, api_secret: str | None = None, paper: bool = True):
        """
        Initialize Alpaca client.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            paper: Use paper trading (default: True)
        """
        # Get config from environment if not provided
        if api_key is None or api_secret is None:
            config = get_alpaca_config()
            api_key = api_key or config.get("api_key", "")
            api_secret = api_secret or config.get("api_secret", "")
            paper = paper or config.get("paper", True)
        
        if not api_key or not api_secret:
            raise ValueError("Alpaca API key and secret are required")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper = paper
        
        # Initialize trading client
        self.client = TradingClient(
            api_key=api_key,
            secret_key=api_secret,
            paper=paper,
        )
        
        # Base URL for data API
        self.base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
        self.data_base_url = "https://paper-data.alpaca.markets" if paper else "https://data.alpaca.markets"
        
        logger.info(f"Alpaca client initialized (paper: {paper})")
    
    def get_account(self) -> dict[str, Any]:
        """Get account information."""
        try:
            account = self.client.get_account()
            return {
                "equity": float(account.equity),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "daytrade_count": account.daytrade_count,
                "pattern_day_trader": account.pattern_day_trader,
            }
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            raise
    
    def get_positions(self) -> list[DegeneratePosition]:
        """Get all current positions."""
        try:
            positions = self.client.get_all_positions()
            result = []
            for pos in positions:
                # Parse option symbol if it's an option
                if pos.symbol and len(pos.symbol) > 6 and pos.symbol[5] == ' ':
                    # Option symbol format: XYZ  240621C00123000
                    parts = pos.symbol.split()
                    if len(parts) >= 2:
                        underlying = parts[0]
                        option_code = parts[1]
                        # Parse option code (simplified)
                        # Full parsing would need more complex logic
                        result.append(DegeneratePosition(
                            symbol=pos.symbol,
                            underlying=underlying,
                            option_type=OptionType.CALL if 'C' in option_code else OptionType.PUT,
                            strike=0.0,  # Would need proper parsing
                            expiration=datetime.utcnow(),  # Would need proper parsing
                            quantity=int(pos.qty),
                            entry_price=float(pos.avg_entry_price),
                            current_price=float(pos.current_price) if pos.current_price else 0.0,
                        ))
                    else:
                        result.append(DegeneratePosition(
                            symbol=pos.symbol,
                            underlying=pos.symbol,
                            option_type=OptionType.CALL,
                            strike=0.0,
                            expiration=datetime.utcnow(),
                            quantity=int(pos.qty),
                            entry_price=float(pos.avg_entry_price),
                            current_price=float(pos.current_price) if pos.current_price else 0.0,
                        ))
                else:
                    # Regular stock position
                    result.append(DegeneratePosition(
                        symbol=pos.symbol,
                        underlying=pos.symbol,
                        option_type=OptionType.CALL,
                        strike=0.0,
                        expiration=datetime.utcnow(),
                        quantity=int(pos.qty),
                        entry_price=float(pos.avg_entry_price),
                        current_price=float(pos.current_price) if pos.current_price else 0.0,
                    ))
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    def get_position(self, symbol: str) -> Optional[DegeneratePosition]:
        """Get a specific position by symbol."""
        try:
            pos = self.client.get_position(symbol)
            if pos:
                return DegeneratePosition(
                    symbol=pos.symbol,
                    underlying=pos.symbol,
                    option_type=OptionType.CALL,
                    strike=0.0,
                    expiration=datetime.utcnow(),
                    quantity=int(pos.qty),
                    entry_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price) if pos.current_price else 0.0,
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get position {symbol}: {e}")
            return None


# =============================================================================
# Option Chain Retrieval
# =============================================================================

class OptionChainFetcher:
    """Fetches and processes option chain data from Alpaca."""
    
    def __init__(self, alpaca_client: AlpacaClient):
        self.client = alpaca_client
    
    def get_option_chain(self, underlying: str, expiration: datetime | None = None) -> list[OptionContract]:
        """
        Get option chain for an underlying symbol.
        
        Args:
            underlying: The underlying stock symbol (e.g., 'AAPL')
            expiration: Specific expiration date, or None for all
            
        Returns:
            List of OptionContract objects
        """
        try:
            # Build request
            request = GetOptionContractsRequest(
                symbol=underlying,
                expiration=expiration.isoformat() if expiration else None,
            )
            
            # Get contracts
            contracts = self.client.client.get_option_contracts(request)
            
            result = []
            for contract in contracts:
                # Parse expiration date
                try:
                    exp_date = datetime.fromisoformat(contract.expiration.replace('Z', '+00:00'))
                except:
                    exp_date = datetime.utcnow() + timedelta(days=30)
                
                # Calculate DTE
                dte = (exp_date - datetime.utcnow()).days
                if dte < 0:
                    continue  # Skip expired contracts
                
                # Determine if in-the-money
                # This would need current underlying price
                itm = False  # Placeholder
                
                option_contract = OptionContract(
                    symbol=contract.symbol,
                    underlying=underlying,
                    option_type=OptionType.CALL if contract.option_type == "call" else OptionType.PUT,
                    strike=float(contract.strike_price),
                    expiration=exp_date,
                    dte=dte,
                    delta=0.0,  # Would need Greeks
                    gamma=0.0,
                    theta=0.0,
                    vega=0.0,
                    rho=0.0,
                    iv=0.0,
                    bid=0.0,  # Would need market data
                    ask=0.0,
                    last=0.0,
                    bid_size=0,
                    ask_size=0,
                    volume=0,
                    open_interest=0,
                    in_the_money=itm,
                )
                result.append(option_contract)
            
            # Sort by expiration and strike
            result.sort(key=lambda x: (x.expiration, x.strike))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get option chain for {underlying}: {e}")
            raise
    
    def get_option_chain_with_greeks(self, underlying: str, expiration: datetime | None = None) -> list[OptionContract]:
        """
        Get option chain with Greeks data.
        
        Note: Alpaca's V2 API provides Greeks, but we may need to fetch
        them separately or calculate them.
        """
        contracts = self.get_option_chain(underlying, expiration)
        
        # For now, return contracts without Greeks
        # In production, we'd fetch Greeks from Alpaca or calculate them
        return contracts
    
    def get_near_term_expirations(self, underlying: str, max_dte: int = 45) -> list[datetime]:
        """Get near-term expiration dates for an underlying."""
        try:
            request = GetOptionContractsRequest(symbol=underlying)
            contracts = self.client.client.get_option_contracts(request)
            
            expirations = set()
            for contract in contracts:
                try:
                    exp_date = datetime.fromisoformat(contract.expiration.replace('Z', '+00:00'))
                    dte = (exp_date - datetime.utcnow()).days
                    if 0 <= dte <= max_dte:
                        expirations.add(exp_date)
                except:
                    continue
            
            return sorted(list(expirations))
            
        except Exception as e:
            logger.error(f"Failed to get expirations for {underlying}: {e}")
            return []


# =============================================================================
# Market Data
# =============================================================================

class MarketDataFetcher:
    """Fetches market data from Alpaca."""
    
    def __init__(self, alpaca_client: AlpacaClient):
        self.client = alpaca_client
        self.base_url = alpaca_client.data_base_url
    
    def get_underlying_price(self, symbol: str) -> float:
        """Get current price for an underlying."""
        try:
            # Use Alpaca's latest quote endpoint
            url = f"{self.base_url}/v2/stocks/{symbol}/quotes/latest"
            headers = {
                "APCA-API-KEY-ID": self.client.api_key,
                "APCA-API-SECRET-KEY": self.client.api_secret,
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'quote' in data:
                quote = data['quote']
                # Return ask price if available, otherwise last
                if quote.get('ask_price'):
                    return float(quote['ask_price'])
                elif quote.get('last_price'):
                    return float(quote['last_price'])
                elif quote.get('bid_price'):
                    return float(quote['bid_price'])
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return 0.0
    
    def get_option_quote(self, symbol: str) -> dict[str, Any]:
        """Get quote for an option contract."""
        try:
            url = f"{self.base_url}/v2/options/contracts/{symbol}/quotes/latest"
            headers = {
                "APCA-API-KEY-ID": self.client.api_key,
                "APCA-API-SECRET-KEY": self.client.api_secret,
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get option quote for {symbol}: {e}")
            return {}
    
    def get_option_chain_market_data(self, underlying: str) -> dict[str, Any]:
        """Get market data for an entire option chain."""
        try:
            url = f"{self.base_url}/v2/options/{underlying}"
            headers = {
                "APCA-API-KEY-ID": self.client.api_key,
                "APCA-API-SECRET-KEY": self.client.api_secret,
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get option chain market data for {underlying}: {e}")
            return {}


# =============================================================================
# Order Execution
# =============================================================================

class OrderExecutor:
    """Executes orders through Alpaca."""
    
    def __init__(self, alpaca_client: AlpacaClient):
        self.client = alpaca_client
    
    def execute_order(
        self,
        symbol: str,
        side: DegenerateOrderSide,
        quantity: int,
        order_type: DegenerateOrderType = DegenerateOrderType.MARKET,
        limit_price: float | None = None,
        time_in_force: str = "DAY",
        **kwargs,
    ) -> DegenerateOrder:
        """
        Execute an order.
        
        Args:
            symbol: Contract symbol
            side: BUY or SELL
            quantity: Number of contracts
            order_type: MARKET, LIMIT, etc.
            limit_price: For LIMIT orders
            time_in_force: DAY, GTC, etc.
            
        Returns:
            Order object with execution details
        """
        try:
            # Convert side
            alpaca_side = OrderSide.BUY if side in [DegenerateOrderSide.BUY, DegenerateOrderSide.BUY_TO_OPEN] else OrderSide.SELL
            
            # Build order request
            if order_type == DegenerateOrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY,
                )
            elif order_type == DegenerateOrderType.LIMIT:
                if limit_price is None:
                    raise ValueError("LIMIT orders require a limit_price")
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    limit_price=str(limit_price),
                    time_in_force=TimeInForce.DAY,
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Submit order
            order = self.client.client.submit_order(order_request)
            
            # Convert to DegenerateOrder
            return DegenerateOrder(
                order_id=order.id,
                symbol=order.symbol,
                order_type=order_type,
                side=side,
                quantity=order.qty,
                limit_price=limit_price,
                time_in_force=time_in_force,
                created_at=order.submitted_at,
                status=OrderStatus.PENDING,
            )
            
        except Exception as e:
            logger.error(f"Failed to execute order for {symbol}: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            self.client.client.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> DegenerateOrder | None:
        """Get status of an order."""
        try:
            order = self.client.client.get_order(order_id)
            if order:
                status = OrderStatus.PENDING
                if order.status == "filled":
                    status = OrderStatus.FILLED
                elif order.status == "partially_filled":
                    status = OrderStatus.PARTIALLY_FILLED
                elif order.status == "canceled":
                    status = OrderStatus.CANCELED
                elif order.status == "expired":
                    status = OrderStatus.EXPIRED
                elif order.status == "rejected":
                    status = OrderStatus.REJECTED
                
                return DegenerateOrder(
                    order_id=order.id,
                    symbol=order.symbol,
                    order_type=DegenerateOrderType.MARKET,
                    side=DegenerateOrderSide.BUY if order.side == "buy" else DegenerateOrderSide.SELL,
                    quantity=order.qty,
                    limit_price=order.limit_price,
                    time_in_force=order.time_in_force,
                    created_at=order.submitted_at,
                    status=status,
                    filled_quantity=order.filled_qty,
                    filled_price=order.filled_avg_price,
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    def get_open_orders(self) -> list[DegenerateOrder]:
        """Get all open orders."""
        try:
            orders = self.client.client.get_open_orders()
            result = []
            for order in orders:
                status = OrderStatus.PENDING
                if order.status == "filled":
                    status = OrderStatus.FILLED
                elif order.status == "partially_filled":
                    status = OrderStatus.PARTIALLY_FILLED
                
                result.append(DegenerateOrder(
                    order_id=order.id,
                    symbol=order.symbol,
                    order_type=DegenerateOrderType.MARKET,
                    side=DegenerateOrderSide.BUY if order.side == "buy" else DegenerateOrderSide.SELL,
                    quantity=order.qty,
                    limit_price=order.limit_price,
                    time_in_force=order.time_in_force,
                    created_at=order.submitted_at,
                    status=status,
                    filled_quantity=order.filled_qty,
                    filled_price=order.filled_avg_price,
                ))
            return result
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []


# =============================================================================
# Alpaca MCP Client (Simplified)
# =============================================================================

class AlpacaMCPClient:
    """
    Simplified MCP-like client for Alpaca.
    
    Provides a unified interface for option chain retrieval and order execution.
    """
    
    def __init__(self, api_key: str | None = None, api_secret: str | None = None, paper: bool = True):
        """
        Initialize Alpaca MCP client.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            paper: Use paper trading (default: True)
        """
        self.client = AlpacaClient(api_key, api_secret, paper)
        self.option_fetcher = OptionChainFetcher(self.client)
        self.market_data = MarketDataFetcher(self.client)
        self.order_executor = OrderExecutor(self.client)
    
    def get_account_info(self) -> dict[str, Any]:
        """Get account information."""
        return self.client.get_account()
    
    def get_option_chain(self, underlying: str, expiration: datetime | None = None) -> list[OptionContract]:
        """Get option chain for an underlying."""
        return self.option_fetcher.get_option_chain(underlying, expiration)
    
    def get_option_chain_with_greeks(self, underlying: str) -> list[OptionContract]:
        """Get option chain with Greeks."""
        return self.option_fetcher.get_option_chain_with_greeks(underlying)
    
    def get_underlying_price(self, symbol: str) -> float:
        """Get current price for an underlying."""
        return self.market_data.get_underlying_price(symbol)
    
    def execute_option_order(
        self,
        symbol: str,
        side: DegenerateOrderSide,
        quantity: int,
        order_type: DegenerateOrderType = DegenerateOrderType.MARKET,
        limit_price: float | None = None,
    ) -> DegenerateOrder:
        """Execute an option order."""
        return self.order_executor.execute_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
        )
    
    def get_positions(self) -> list[DegeneratePosition]:
        """Get all current positions."""
        return self.client.get_positions()
    
    def get_position(self, symbol: str) -> Optional[DegeneratePosition]:
        """Get a specific position."""
        return self.client.get_position(symbol)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.order_executor.cancel_order(order_id)
    
    def get_order_status(self, order_id: str) -> DegenerateOrder | None:
        """Get order status."""
        return self.order_executor.get_order_status(order_id)


# =============================================================================
# Singleton Client
# =============================================================================

_alpaca_client: AlpacaMCPClient | None = None


def get_alpaca_client() -> AlpacaMCPClient:
    """Get the global Alpaca MCP client."""
    global _alpaca_client
    if _alpaca_client is None:
        _alpaca_client = AlpacaMCPClient()
    return _alpaca_client


def init_alpaca_client(api_key: str | None = None, api_secret: str | None = None, paper: bool = True) -> AlpacaMCPClient:
    """Initialize the global Alpaca MCP client."""
    global _alpaca_client
    _alpaca_client = AlpacaMCPClient(api_key, api_secret, paper)
    return _alpaca_client
