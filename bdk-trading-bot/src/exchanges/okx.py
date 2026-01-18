"""
OKX exchange implementation for BDK Trading Bot.

This module provides OKX exchange integration using the CCXT library,
supporting both real and paper trading modes. OKX requires a passphrase
for API authentication.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

import ccxt.async_support as ccxt

from src.core.exceptions import ExchangeError
from src.core.logger import get_exchange_logger

from .base import BaseExchange
from .factory import register_exchange
from .models import (
    Balance,
    ExchangeType,
    MarketInfo,
    OHLCV,
    Order,
    OrderBook,
    OrderBookLevel,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Ticker,
    TimeInForce,
    Trade,
)


@register_exchange("okx")
class OKXExchange(BaseExchange):
    """
    OKX exchange implementation using CCXT.

    OKX specific features:
    - Requires passphrase for API authentication
    - Unified account system
    - High liquidity for major pairs

    Usage:
        >>> exchange = OKXExchange(
        ...     api_key="your_key",
        ...     api_secret="your_secret",
        ...     passphrase="your_passphrase",
        ...     paper_trading=True
        ... )
        >>> await exchange.connect()
        >>>
        >>> ticker = await exchange.fetch_ticker("BTC/USDT")
        >>> print(f"BTC Price: {ticker.last}")
    """

    EXCHANGE_ID = "okx"
    EXCHANGE_NAME = "OKX"
    EXCHANGE_TYPE = ExchangeType.CRYPTO_CEX

    # OKX rate limits
    RATE_LIMIT_REQUESTS = 600  # Per minute
    RATE_LIMIT_ORDERS = 60  # Per 2 seconds

    # Supported timeframes
    TIMEFRAMES = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "2h": "2H",
        "4h": "4H",
        "6h": "6H",
        "12h": "12H",
        "1d": "1D",
        "1w": "1W",
        "1M": "1M",
    }

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",
        paper_trading: bool = True,
        demo_trading: bool = False,
        **kwargs,
    ):
        """
        Initialize OKX exchange.

        Args:
            api_key: OKX API key
            api_secret: OKX API secret
            passphrase: OKX API passphrase (required for private endpoints)
            paper_trading: If True, simulate orders locally
            demo_trading: If True, use OKX demo trading environment
        """
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            paper_trading=paper_trading,
            **kwargs,
        )

        self.demo_trading = demo_trading
        self._client: Optional[ccxt.okx] = None

        # Paper trading state
        self._paper_balances: Dict[str, Balance] = {}
        self._paper_orders: Dict[str, Order] = {}
        self._paper_order_counter: int = 0

        # WebSocket state
        self._ws_task: Optional[asyncio.Task] = None

        self.logger = get_exchange_logger(self.EXCHANGE_ID)

    # ==================== Connection Methods ====================

    async def connect(self) -> bool:
        """Connect to OKX API."""
        try:
            self.logger.info("Connecting to OKX...")

            # Configure CCXT client
            config: Dict[str, Any] = {
                "apiKey": self.api_key if self.api_key else None,
                "secret": self.api_secret if self.api_secret else None,
                "password": self.passphrase if self.passphrase else None,
                "enableRateLimit": True,
                "rateLimit": 100,
                "options": {"defaultType": "spot", "adjustForTimeDifference": True},
            }

            # OKX demo trading
            if self.demo_trading:
                config["sandbox"] = True

            config = {k: v for k, v in config.items() if v is not None}

            self._client = ccxt.okx(config)

            # Test connection
            await self.load_markets()

            # Initialize paper trading
            if self.paper_trading:
                await self._init_paper_trading()

            self._connected = True
            self.logger.info(
                "Connected to OKX",
                paper_trading=self.paper_trading,
                demo_trading=self.demo_trading,
                markets_loaded=len(self._markets),
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to OKX: {e}")
            raise ExchangeError(
                message=f"Connection failed: {e}", exchange=self.EXCHANGE_ID
            )

    async def disconnect(self) -> None:
        """Disconnect from OKX."""
        try:
            if self._ws_task:
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except asyncio.CancelledError:
                    pass
                self._ws_task = None

            if self._client:
                await self._client.close()
                self._client = None

            self._connected = False
            self.logger.info("Disconnected from OKX")

        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")

    async def health_check(self) -> bool:
        """Check if OKX is accessible."""
        try:
            if not self._client:
                return False
            await self._client.fetch_time()
            return True
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False

    # ==================== Market Data Methods ====================

    async def load_markets(self) -> Dict[str, MarketInfo]:
        """Load all OKX spot markets."""
        try:
            await self._enforce_rate_limit()

            raw_markets = await self._client.load_markets()

            for symbol, market in raw_markets.items():
                if market.get("spot", False):
                    # Parse limits with proper error handling
                    limits = market.get("limits", {})
                    amount_limits = limits.get("amount", {})
                    price_limits = limits.get("price", {})
                    cost_limits = limits.get("cost", {})
                    precision = market.get("precision", {})

                    self._markets[symbol] = MarketInfo(
                        exchange=self.EXCHANGE_ID,
                        symbol=symbol,
                        base_currency=market.get("base", ""),
                        quote_currency=market.get("quote", ""),
                        exchange_symbol=market.get("id", ""),
                        is_active=market.get("active", True),
                        is_spot=True,
                        is_margin=market.get("margin", False),
                        is_futures=False,
                        min_quantity=Decimal(str(amount_limits.get("min", 0) or 0)),
                        max_quantity=(
                            Decimal(str(amount_limits.get("max", 0)))
                            if amount_limits.get("max")
                            else None
                        ),
                        quantity_step=Decimal(str(10 ** -precision.get("amount", 8))),
                        min_price=Decimal(str(price_limits.get("min", 0) or 0)),
                        max_price=(
                            Decimal(str(price_limits.get("max", 0)))
                            if price_limits.get("max")
                            else None
                        ),
                        price_step=Decimal(str(10 ** -precision.get("price", 8))),
                        min_notional=Decimal(str(cost_limits.get("min", 0) or 0)),
                        maker_fee=Decimal(str(market.get("maker", 0.001))),
                        taker_fee=Decimal(str(market.get("taker", 0.0015))),
                        metadata=market,
                    )

            self.logger.info(f"Loaded {len(self._markets)} markets")
            return self._markets

        except Exception as e:
            self._handle_error(e, "load_markets")

    async def fetch_ticker(self, symbol: str) -> Ticker:
        """Fetch current ticker for a symbol."""
        try:
            await self._enforce_rate_limit()

            raw = await self._client.fetch_ticker(symbol)

            return Ticker(
                exchange=self.EXCHANGE_ID,
                symbol=symbol,
                bid=Decimal(str(raw.get("bid", 0) or 0)),
                ask=Decimal(str(raw.get("ask", 0) or 0)),
                last=Decimal(str(raw.get("last", 0) or 0)),
                high_24h=Decimal(str(raw.get("high", 0) or 0)),
                low_24h=Decimal(str(raw.get("low", 0) or 0)),
                volume_24h=Decimal(str(raw.get("baseVolume", 0) or 0)),
                quote_volume_24h=Decimal(str(raw.get("quoteVolume", 0) or 0)),
                change_24h=Decimal(str(raw.get("change", 0) or 0)),
                change_percent_24h=Decimal(str(raw.get("percentage", 0) or 0)),
                vwap_24h=(
                    Decimal(str(raw.get("vwap", 0)))
                    if raw.get("vwap") is not None
                    else None
                ),
                open_24h=Decimal(str(raw.get("open", 0) or 0)),
                timestamp=datetime.fromtimestamp(
                    raw.get("timestamp", 0) / 1000, tz=timezone.utc
                ),
            )

        except Exception as e:
            self._handle_error(e, f"fetch_ticker({symbol})")

    async def fetch_tickers(
        self, symbols: Optional[List[str]] = None
    ) -> Dict[str, Ticker]:
        """Fetch tickers for multiple symbols."""
        try:
            await self._enforce_rate_limit()

            raw_tickers = await self._client.fetch_tickers(symbols)

            tickers = {}
            for symbol, raw in raw_tickers.items():
                if symbols is None or symbol in symbols:
                    tickers[symbol] = Ticker(
                        exchange=self.EXCHANGE_ID,
                        symbol=symbol,
                        bid=Decimal(str(raw.get("bid", 0) or 0)),
                        ask=Decimal(str(raw.get("ask", 0) or 0)),
                        last=Decimal(str(raw.get("last", 0) or 0)),
                        high_24h=Decimal(str(raw.get("high", 0) or 0)),
                        low_24h=Decimal(str(raw.get("low", 0) or 0)),
                        volume_24h=Decimal(str(raw.get("baseVolume", 0) or 0)),
                        quote_volume_24h=Decimal(str(raw.get("quoteVolume", 0) or 0)),
                        change_24h=Decimal(str(raw.get("change", 0) or 0)),
                        change_percent_24h=Decimal(str(raw.get("percentage", 0) or 0)),
                        open_24h=Decimal(str(raw.get("open", 0) or 0)),
                        timestamp=datetime.fromtimestamp(
                            raw.get("timestamp", 0) / 1000, tz=timezone.utc
                        ),
                    )

            return tickers

        except Exception as e:
            self._handle_error(e, "fetch_tickers")

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """Fetch order book for a symbol."""
        try:
            await self._enforce_rate_limit()

            raw = await self._client.fetch_order_book(symbol, limit)

            bids = [
                OrderBookLevel(price=Decimal(str(bid[0])), quantity=Decimal(str(bid[1])))
                for bid in raw.get("bids", [])
            ]

            asks = [
                OrderBookLevel(price=Decimal(str(ask[0])), quantity=Decimal(str(ask[1])))
                for ask in raw.get("asks", [])
            ]

            return OrderBook(
                exchange=self.EXCHANGE_ID,
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=(
                    datetime.fromtimestamp(raw.get("timestamp", 0) / 1000, tz=timezone.utc)
                    if raw.get("timestamp")
                    else datetime.now(timezone.utc)
                ),
            )

        except Exception as e:
            self._handle_error(e, f"fetch_order_book({symbol})")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[OHLCV]:
        """Fetch OHLCV data."""
        try:
            await self._enforce_rate_limit()

            tf = self.TIMEFRAMES.get(timeframe, timeframe)
            since_ts = int(since.timestamp() * 1000) if since else None

            raw = await self._client.fetch_ohlcv(symbol, tf, since_ts, limit)

            ohlcv_list = []
            for candle in raw:
                ohlcv_list.append(
                    OHLCV(
                        exchange=self.EXCHANGE_ID,
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(
                            candle[0] / 1000, tz=timezone.utc
                        ),
                        open=Decimal(str(candle[1])),
                        high=Decimal(str(candle[2])),
                        low=Decimal(str(candle[3])),
                        close=Decimal(str(candle[4])),
                        volume=Decimal(str(candle[5])),
                    )
                )

            return ohlcv_list

        except Exception as e:
            self._handle_error(e, f"fetch_ohlcv({symbol})")

    async def fetch_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Fetch recent public trades."""
        try:
            await self._enforce_rate_limit()

            raw = await self._client.fetch_trades(symbol, limit=limit)

            trades = []
            for t in raw:
                trades.append(
                    Trade(
                        exchange=self.EXCHANGE_ID,
                        symbol=symbol,
                        trade_id=str(t.get("id", "")),
                        price=Decimal(str(t.get("price", 0))),
                        quantity=Decimal(str(t.get("amount", 0))),
                        side=(
                            OrderSide.BUY
                            if t.get("side") == "buy"
                            else OrderSide.SELL
                        ),
                        timestamp=datetime.fromtimestamp(
                            t.get("timestamp", 0) / 1000, tz=timezone.utc
                        ),
                    )
                )

            return trades

        except Exception as e:
            self._handle_error(e, f"fetch_recent_trades({symbol})")

    # ==================== Account Methods ====================

    async def fetch_balance(self) -> Dict[str, Balance]:
        """Fetch account balances."""
        if self.paper_trading:
            return self._paper_balances.copy()

        try:
            await self._enforce_rate_limit()

            raw = await self._client.fetch_balance()

            balances = {}
            for currency, data in raw.get("total", {}).items():
                if float(data) > 0:
                    balances[currency] = Balance(
                        currency=currency,
                        free=Decimal(str(raw.get("free", {}).get(currency, 0))),
                        locked=Decimal(str(raw.get("used", {}).get(currency, 0))),
                        total=Decimal(str(data)),
                    )

            return balances

        except Exception as e:
            self._handle_error(e, "fetch_balance")

    async def fetch_positions(self) -> List[Position]:
        """Fetch open positions."""
        return []

    # ==================== Order Methods ====================

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
        """Create an order."""
        if self.paper_trading:
            return await self._create_paper_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
                client_order_id=client_order_id,
            )

        raise ExchangeError(
            message="Real trading not implemented. Use paper_trading=True",
            exchange=self.EXCHANGE_ID,
        )

    async def _create_paper_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        client_order_id: Optional[str] = None,
    ) -> Order:
        """Simulate order creation."""
        ticker = await self.fetch_ticker(symbol)
        execution_price = price if order_type == OrderType.LIMIT else ticker.last

        market = await self.get_market(symbol)
        if not market:
            raise ExchangeError(f"Market not found: {symbol}", self.EXCHANGE_ID)

        base_currency = market.base_currency
        quote_currency = market.quote_currency
        order_value = quantity * execution_price

        # Check balance
        if side == OrderSide.BUY:
            required_currency = quote_currency
            required_amount = order_value
        else:
            required_currency = base_currency
            required_amount = quantity

        balance = self._paper_balances.get(required_currency)
        if not balance or balance.free < required_amount:
            raise ExchangeError(
                f"Insufficient balance: need {required_amount} {required_currency}, have {balance.free if balance else 0}",
                self.EXCHANGE_ID,
            )

        # Generate order ID
        self._paper_order_counter += 1
        order_id = f"PAPER-{self.EXCHANGE_ID.upper()}-{self._paper_order_counter:06d}"

        # Fee (0.15% taker for OKX)
        fee_rate = Decimal("0.0015")
        fee = order_value * fee_rate

        now = datetime.now(timezone.utc)
        order = Order(
            exchange=self.EXCHANGE_ID,
            symbol=symbol,
            order_id=order_id,
            client_order_id=client_order_id,
            side=side,
            order_type=order_type,
            status=(
                OrderStatus.FILLED
                if order_type == OrderType.MARKET
                else OrderStatus.OPEN
            ),
            quantity=quantity,
            filled_quantity=(
                quantity if order_type == OrderType.MARKET else Decimal("0")
            ),
            price=price,
            stop_price=stop_price,
            average_price=(
                execution_price if order_type == OrderType.MARKET else None
            ),
            time_in_force=time_in_force,
            created_at=now,
            updated_at=now,
            filled_at=now if order_type == OrderType.MARKET else None,
            fee=fee if order_type == OrderType.MARKET else Decimal("0"),
            fee_currency=quote_currency,
            metadata={"paper_trading": True},
        )

        if order_type == OrderType.MARKET:
            await self._execute_paper_order(order, execution_price, fee)

        self._paper_orders[order_id] = order

        self.logger.info(
            "Paper order created",
            order_id=order_id,
            symbol=symbol,
            side=side.value,
            type=order_type.value,
            quantity=str(quantity),
            price=str(execution_price),
        )

        return order

    async def _execute_paper_order(
        self, order: Order, execution_price: Decimal, fee: Decimal
    ) -> None:
        """Execute paper order."""
        market = await self.get_market(order.symbol)
        base_currency = market.base_currency
        quote_currency = market.quote_currency
        order_value = order.quantity * execution_price

        if order.side == OrderSide.BUY:
            self._paper_balances[quote_currency].free -= order_value + fee
            self._paper_balances[quote_currency].total -= order_value + fee

            if base_currency not in self._paper_balances:
                self._paper_balances[base_currency] = Balance(
                    currency=base_currency,
                    free=Decimal("0"),
                    locked=Decimal("0"),
                    total=Decimal("0"),
                )
            self._paper_balances[base_currency].free += order.quantity
            self._paper_balances[base_currency].total += order.quantity
        else:
            self._paper_balances[base_currency].free -= order.quantity
            self._paper_balances[base_currency].total -= order.quantity
            self._paper_balances[quote_currency].free += order_value - fee
            self._paper_balances[quote_currency].total += order_value - fee

        self.logger.info(
            "Paper order executed",
            order_id=order.order_id,
            side=order.side.value,
            quantity=str(order.quantity),
            price=str(execution_price),
            fee=str(fee),
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        """Cancel an order."""
        if self.paper_trading:
            if order_id not in self._paper_orders:
                raise ExchangeError(f"Order not found: {order_id}", self.EXCHANGE_ID)

            order = self._paper_orders[order_id]
            if not order.is_open:
                raise ExchangeError(f"Order not open: {order_id}", self.EXCHANGE_ID)

            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now(timezone.utc)

            self.logger.info("Paper order cancelled", order_id=order_id)
            return order

        raise ExchangeError("Real trading not implemented", self.EXCHANGE_ID)

    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """Fetch order status."""
        if self.paper_trading:
            if order_id not in self._paper_orders:
                raise ExchangeError(f"Order not found: {order_id}", self.EXCHANGE_ID)
            return self._paper_orders[order_id]

        raise ExchangeError("Real trading not implemented", self.EXCHANGE_ID)

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Fetch open orders."""
        if self.paper_trading:
            orders = [o for o in self._paper_orders.values() if o.is_open]
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]
            return orders

        raise ExchangeError("Real trading not implemented", self.EXCHANGE_ID)

    async def fetch_order_history(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Order]:
        """Fetch order history."""
        if self.paper_trading:
            orders = list(self._paper_orders.values())
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]
            if since:
                orders = [o for o in orders if o.created_at >= since]
            orders.sort(key=lambda o: o.created_at, reverse=True)
            return orders[:limit]

        raise ExchangeError("Real trading not implemented", self.EXCHANGE_ID)

    # ==================== Paper Trading Init ====================

    async def _init_paper_trading(self) -> None:
        """Initialize paper trading."""
        from src.core.config import get_config

        config = get_config()

        initial_balance = Decimal(str(config.paper_trading.initial_balance_usd))

        self._paper_balances = {
            "USDT": Balance(
                currency="USDT",
                free=initial_balance,
                locked=Decimal("0"),
                total=initial_balance,
            )
        }

        self.logger.info(
            "Paper trading initialized", initial_balance=str(initial_balance)
        )

    # ==================== WebSocket ====================

    async def subscribe_ticker(
        self, symbols: List[str], callback: Callable[[Ticker], Any]
    ) -> None:
        """Subscribe to ticker updates."""
        self._ticker_callbacks.append(callback)

        if not self._ws_task:
            self._ws_task = asyncio.create_task(self._ticker_polling_loop(symbols))

        self.logger.info(f"Subscribed to tickers: {symbols}")

    async def _ticker_polling_loop(self, symbols: List[str]) -> None:
        """Poll tickers."""
        while self._connected:
            try:
                tickers = await self.fetch_tickers(symbols)
                for ticker in tickers.values():
                    for callback in self._ticker_callbacks:
                        try:
                            await callback(ticker)
                        except Exception as e:
                            self.logger.error(f"Ticker callback error: {e}")

                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ticker polling error: {e}")
                await asyncio.sleep(5)

    # ==================== Utility Methods ====================

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert unified symbol to OKX format."""
        return symbol.replace("/", "-")

    def _parse_symbol(self, exchange_symbol: str) -> str:
        """Convert OKX symbol to unified format."""
        return exchange_symbol.replace("-", "/")
