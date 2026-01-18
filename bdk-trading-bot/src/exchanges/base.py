"""
Base exchange interface for BDK Trading Bot.

This module provides the abstract base class that all exchange
implementations must inherit from, ensuring a consistent interface.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.core.config import get_config
from src.core.exceptions import ExchangeError
from src.core.logger import get_exchange_logger, get_logger

from .models import (
    Balance,
    ExchangeInfo,
    ExchangeType,
    MarketInfo,
    OHLCV,
    Order,
    OrderBook,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Ticker,
    TimeInForce,
    Trade,
)


class BaseExchange(ABC):
    """
    Abstract base class for all exchange implementations.

    All exchanges (Binance, Alpaca, etc.) must implement this interface.
    This ensures consistent behavior across different exchanges.

    Features:
    - Paper trading support (simulated orders)
    - Rate limiting
    - Automatic reconnection
    - Unified data models

    Usage:
        >>> class BinanceExchange(BaseExchange):
        ...     async def connect(self):
        ...         # Implementation
        ...         pass
    """

    # Class attributes (override in subclasses)
    EXCHANGE_ID: str = "base"
    EXCHANGE_NAME: str = "Base Exchange"
    EXCHANGE_TYPE: ExchangeType = ExchangeType.CRYPTO_CEX

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        paper_trading: bool = True,
        **kwargs,
    ):
        """
        Initialize exchange.

        Args:
            api_key: API key (empty for public endpoints only)
            api_secret: API secret
            passphrase: API passphrase (required by some exchanges)
            paper_trading: If True, simulate orders instead of real execution
            **kwargs: Additional exchange-specific parameters
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.paper_trading = paper_trading

        self.logger = get_exchange_logger(self.EXCHANGE_ID)
        self.config = get_config()

        self._connected = False
        self._markets: Dict[str, MarketInfo] = {}
        self._balances: Dict[str, Balance] = {}
        self._last_request_time: float = 0

        # Rate limiting
        self._rate_limit_requests: int = 1200  # Per minute
        self._rate_limit_window: int = 60

        # Callbacks for real-time updates
        self._ticker_callbacks: List[Callable[[Ticker], Awaitable[None]]] = []
        self._trade_callbacks: List[Callable[[Trade], Awaitable[None]]] = []
        self._order_callbacks: List[Callable[[Order], Awaitable[None]]] = []

    # ==================== Connection Methods ====================

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to exchange.

        Returns:
            True if connection successful

        Raises:
            ExchangeError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from exchange."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if exchange connection is healthy.

        Returns:
            True if exchange is accessible
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._connected

    def get_info(self) -> ExchangeInfo:
        """
        Get exchange information.

        Returns:
            ExchangeInfo with current state
        """
        return ExchangeInfo(
            id=self.EXCHANGE_ID,
            name=self.EXCHANGE_NAME,
            exchange_type=self.EXCHANGE_TYPE,
            is_paper_trading=self.paper_trading,
            is_connected=self._connected,
            rate_limits={"requests_per_minute": self._rate_limit_requests},
        )

    # ==================== Market Data Methods ====================

    @abstractmethod
    async def load_markets(self) -> Dict[str, MarketInfo]:
        """
        Load all available markets/symbols.

        Returns:
            Dict mapping symbol to MarketInfo
        """
        pass

    async def get_markets(self) -> Dict[str, MarketInfo]:
        """
        Get cached markets or load if empty.

        Returns:
            Dict of markets
        """
        if not self._markets:
            self._markets = await self.load_markets()
        return self._markets

    async def get_market(self, symbol: str) -> Optional[MarketInfo]:
        """
        Get market info for a specific symbol.

        Args:
            symbol: Trading pair

        Returns:
            MarketInfo or None if not found
        """
        markets = await self.get_markets()
        return markets.get(symbol)

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """
        Fetch current ticker for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")

        Returns:
            Ticker data
        """
        pass

    @abstractmethod
    async def fetch_tickers(
        self, symbols: Optional[List[str]] = None
    ) -> Dict[str, Ticker]:
        """
        Fetch tickers for multiple symbols.

        Args:
            symbols: List of symbols. If None, fetch all.

        Returns:
            Dict mapping symbol to Ticker
        """
        pass

    @abstractmethod
    async def fetch_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """
        Fetch order book for a symbol.

        Args:
            symbol: Trading pair
            limit: Number of levels to fetch

        Returns:
            OrderBook data
        """
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[OHLCV]:
        """
        Fetch OHLCV (candlestick) data.

        Args:
            symbol: Trading pair
            timeframe: Candle interval ("1m", "5m", "15m", "1h", "4h", "1d")
            since: Start time (None = exchange default)
            limit: Number of candles

        Returns:
            List of OHLCV data
        """
        pass

    @abstractmethod
    async def fetch_recent_trades(
        self, symbol: str, limit: int = 100
    ) -> List[Trade]:
        """
        Fetch recent public trades.

        Args:
            symbol: Trading pair
            limit: Number of trades

        Returns:
            List of Trade data
        """
        pass

    # ==================== Account Methods ====================

    @abstractmethod
    async def fetch_balance(self) -> Dict[str, Balance]:
        """
        Fetch account balances.

        Returns:
            Dict mapping currency to Balance
        """
        pass

    async def get_balance(self, currency: str) -> Optional[Balance]:
        """
        Get balance for specific currency.

        Args:
            currency: Currency code

        Returns:
            Balance or None if not found
        """
        balances = await self.fetch_balance()
        return balances.get(currency)

    @abstractmethod
    async def fetch_positions(self) -> List[Position]:
        """
        Fetch open positions (for margin/futures).

        Returns:
            List of Position data
        """
        pass

    # ==================== Order Methods ====================

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        client_order_id: Optional[str] = None,
        **kwargs,
    ) -> Order:
        """
        Create a new order.

        Args:
            symbol: Trading pair
            side: Buy or sell
            order_type: Market, limit, etc.
            quantity: Order quantity
            price: Limit price (required for limit orders)
            stop_price: Stop trigger price
            time_in_force: Order time policy
            client_order_id: Custom order ID
            **kwargs: Additional parameters

        Returns:
            Order data

        Note:
            In paper trading mode, this simulates the order.
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        """
        Cancel an open order.

        Args:
            order_id: Exchange order ID
            symbol: Trading pair

        Returns:
            Updated Order data
        """
        pass

    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """
        Fetch order status.

        Args:
            order_id: Exchange order ID
            symbol: Trading pair

        Returns:
            Order data
        """
        pass

    @abstractmethod
    async def fetch_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[Order]:
        """
        Fetch all open orders.

        Args:
            symbol: Filter by symbol (None = all)

        Returns:
            List of open Order data
        """
        pass

    @abstractmethod
    async def fetch_order_history(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Order]:
        """
        Fetch order history.

        Args:
            symbol: Filter by symbol
            since: Start time
            limit: Max orders to return

        Returns:
            List of Order data
        """
        pass

    # ==================== Convenience Methods ====================

    async def create_market_buy(
        self, symbol: str, quantity: Decimal, **kwargs
    ) -> Order:
        """
        Create market buy order.

        Args:
            symbol: Trading pair
            quantity: Order quantity
            **kwargs: Additional parameters

        Returns:
            Order data
        """
        return await self.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
            **kwargs,
        )

    async def create_market_sell(
        self, symbol: str, quantity: Decimal, **kwargs
    ) -> Order:
        """
        Create market sell order.

        Args:
            symbol: Trading pair
            quantity: Order quantity
            **kwargs: Additional parameters

        Returns:
            Order data
        """
        return await self.create_order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            **kwargs,
        )

    async def create_limit_buy(
        self, symbol: str, quantity: Decimal, price: Decimal, **kwargs
    ) -> Order:
        """
        Create limit buy order.

        Args:
            symbol: Trading pair
            quantity: Order quantity
            price: Limit price
            **kwargs: Additional parameters

        Returns:
            Order data
        """
        return await self.create_order(
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            **kwargs,
        )

    async def create_limit_sell(
        self, symbol: str, quantity: Decimal, price: Decimal, **kwargs
    ) -> Order:
        """
        Create limit sell order.

        Args:
            symbol: Trading pair
            quantity: Order quantity
            price: Limit price
            **kwargs: Additional parameters

        Returns:
            Order data
        """
        return await self.create_order(
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            **kwargs,
        )

    # ==================== WebSocket / Streaming ====================

    async def subscribe_ticker(
        self, symbols: List[str], callback: Callable[[Ticker], Awaitable[None]]
    ) -> None:
        """
        Subscribe to real-time ticker updates.

        Args:
            symbols: List of symbols to subscribe
            callback: Async function called with Ticker data

        Note:
            Override in subclass if exchange supports WebSocket.
            Default implementation polls REST API.
        """
        self._ticker_callbacks.append(callback)
        self.logger.info(f"Subscribed to tickers: {symbols}")

    async def subscribe_trades(
        self, symbols: List[str], callback: Callable[[Trade], Awaitable[None]]
    ) -> None:
        """
        Subscribe to real-time trade updates.

        Args:
            symbols: List of symbols to subscribe
            callback: Async function called with Trade data
        """
        self._trade_callbacks.append(callback)
        self.logger.info(f"Subscribed to trades: {symbols}")

    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all streams."""
        self._ticker_callbacks.clear()
        self._trade_callbacks.clear()
        self._order_callbacks.clear()
        self.logger.info("Unsubscribed from all streams")

    # ==================== Helper Methods ====================

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to exchange format.
        Override in subclass if needed.

        Args:
            symbol: Unified symbol (BTC/USDT)

        Returns:
            Exchange-specific symbol (BTCUSDT)
        """
        return symbol.replace("/", "")

    def _parse_symbol(self, exchange_symbol: str) -> str:
        """
        Parse exchange symbol to unified format.
        Override in subclass if needed.

        Args:
            exchange_symbol: Exchange-specific symbol

        Returns:
            Unified symbol
        """
        return exchange_symbol

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        min_interval = self._rate_limit_window / self._rate_limit_requests
        elapsed = now - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def _handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle and log exchange errors.

        Args:
            error: Exception that occurred
            context: Context where error occurred

        Raises:
            ExchangeError: Wrapped error
        """
        self.logger.error(
            f"Exchange error: {context}",
            error=str(error),
            error_type=type(error).__name__,
        )
        raise ExchangeError(
            message=str(error), exchange=self.EXCHANGE_ID, details={"context": context}
        )
