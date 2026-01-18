"""
Exchange data models for BDK Trading Bot.

This module defines data structures used across all exchange implementations,
providing a unified interface regardless of the underlying exchange.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


# ==================== Enums ====================


class ExchangeType(str, Enum):
    """Type of exchange."""

    CRYPTO_CEX = "crypto_cex"  # Centralized crypto exchange
    CRYPTO_DEX = "crypto_dex"  # Decentralized crypto exchange
    STOCK_US = "stock_us"  # US stock market
    STOCK_TR = "stock_tr"  # Turkish stock market (BIST)


class OrderSide(str, Enum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LOSS_LIMIT = "stop_loss_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(str, Enum):
    """Time in force for orders."""

    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill
    DAY = "day"  # Day order


# ==================== Data Classes ====================


@dataclass
class ExchangeInfo:
    """Information about an exchange."""

    id: str  # Exchange identifier (binance, alpaca, etc.)
    name: str  # Display name
    exchange_type: ExchangeType
    is_paper_trading: bool = True  # Whether using paper trading
    is_connected: bool = False
    supported_features: List[str] = field(
        default_factory=list
    )  # ['spot', 'futures', 'margin']
    rate_limits: Dict[str, int] = field(
        default_factory=dict
    )  # {'requests_per_minute': 1200}
    trading_fees: Dict[str, Decimal] = field(
        default_factory=dict
    )  # {'maker': 0.001, 'taker': 0.001}
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Ticker:
    """Real-time ticker data for a symbol."""

    exchange: str
    symbol: str  # Trading pair (BTC/USDT, AAPL)
    bid: Decimal  # Best bid price
    ask: Decimal  # Best ask price
    last: Decimal  # Last trade price
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None  # Base currency volume
    quote_volume_24h: Optional[Decimal] = None  # Quote currency volume
    change_24h: Optional[Decimal] = None  # Price change (absolute)
    change_percent_24h: Optional[Decimal] = None  # Price change (percentage)
    vwap_24h: Optional[Decimal] = None  # Volume weighted average price
    open_24h: Optional[Decimal] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        return self.ask - self.bid

    @property
    def spread_percent(self) -> Decimal:
        """Calculate spread as percentage of mid price."""
        mid = (self.bid + self.ask) / 2
        if mid == 0:
            return Decimal("0")
        return (self.spread / mid) * 100

    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.bid + self.ask) / 2


@dataclass
class OrderBookLevel:
    """Single level in order book."""

    price: Decimal
    quantity: Decimal

    @property
    def value(self) -> Decimal:
        """Total value at this level."""
        return self.price * self.quantity


@dataclass
class OrderBook:
    """Order book snapshot."""

    exchange: str
    symbol: str
    bids: List[OrderBookLevel]  # Sorted by price descending (best first)
    asks: List[OrderBookLevel]  # Sorted by price ascending (best first)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid."""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask."""
        return self.asks[0] if self.asks else None

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate spread between best bid and ask."""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return None

    def get_depth(self, levels: int = 10) -> Dict[str, Any]:
        """
        Get order book depth for specified levels.

        Args:
            levels: Number of levels to include

        Returns:
            Dict with bid/ask totals
        """
        return {
            "bids": self.bids[:levels],
            "asks": self.asks[:levels],
            "bid_total": sum(level.value for level in self.bids[:levels]),
            "ask_total": sum(level.value for level in self.asks[:levels]),
        }


@dataclass
class OHLCV:
    """Candlestick/OHLCV data."""

    exchange: str
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Optional[Decimal] = None
    trades_count: Optional[int] = None

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish."""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish."""
        return self.close < self.open

    @property
    def body_size(self) -> Decimal:
        """Calculate body size."""
        return abs(self.close - self.open)

    @property
    def range_size(self) -> Decimal:
        """Calculate full range size."""
        return self.high - self.low


@dataclass
class Trade:
    """Individual trade/execution."""

    exchange: str
    symbol: str
    trade_id: str
    price: Decimal
    quantity: Decimal
    side: OrderSide
    timestamp: datetime
    fee: Optional[Decimal] = None
    fee_currency: Optional[str] = None

    @property
    def value(self) -> Decimal:
        """Calculate trade value."""
        return self.price * self.quantity


@dataclass
class Order:
    """Order information."""

    exchange: str
    symbol: str
    order_id: str
    client_order_id: Optional[str] = None
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    quantity: Decimal = Decimal("0")
    filled_quantity: Decimal = Decimal("0")
    price: Optional[Decimal] = None  # Limit price
    stop_price: Optional[Decimal] = None  # Stop trigger price
    average_price: Optional[Decimal] = None  # Average fill price
    time_in_force: TimeInForce = TimeInForce.GTC
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    fee: Decimal = Decimal("0")
    fee_currency: Optional[str] = None
    trades: List[Trade] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        """Check if order is still open."""
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        )

    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining quantity."""
        return self.quantity - self.filled_quantity

    @property
    def fill_percent(self) -> Decimal:
        """Calculate fill percentage."""
        if self.quantity == 0:
            return Decimal("0")
        return (self.filled_quantity / self.quantity) * 100

    @property
    def value(self) -> Decimal:
        """Calculate order value."""
        price = self.average_price or self.price or Decimal("0")
        return self.filled_quantity * price


@dataclass
class Balance:
    """Account balance for a currency."""

    currency: str
    free: Decimal  # Available balance
    locked: Decimal  # In orders/positions
    total: Decimal  # Free + locked
    usd_value: Optional[Decimal] = None  # Estimated USD value

    @classmethod
    def from_total(
        cls, currency: str, total: Decimal, locked: Decimal = Decimal("0")
    ) -> "Balance":
        """Create Balance from total and locked amounts."""
        return cls(
            currency=currency, free=total - locked, locked=locked, total=total
        )


@dataclass
class Position:
    """Open position (for margin/futures)."""

    exchange: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    liquidation_price: Optional[Decimal] = None
    leverage: Decimal = Decimal("1")
    unrealized_pnl: Decimal = Decimal("0")
    unrealized_pnl_percent: Decimal = Decimal("0")
    margin: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def notional_value(self) -> Decimal:
        """Calculate notional value."""
        return self.quantity * self.current_price

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.side == OrderSide.BUY

    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.side == OrderSide.SELL


@dataclass
class MarketInfo:
    """Information about a trading market/symbol."""

    exchange: str
    symbol: str  # Unified symbol (BTC/USDT)
    base_currency: str  # Base (BTC)
    quote_currency: str  # Quote (USDT)
    exchange_symbol: str  # Exchange-specific symbol (BTCUSDT)
    is_active: bool = True
    is_spot: bool = True
    is_margin: bool = False
    is_futures: bool = False
    min_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    quantity_step: Optional[Decimal] = None  # Lot size
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    price_step: Optional[Decimal] = None  # Tick size
    min_notional: Optional[Decimal] = None  # Min order value
    maker_fee: Optional[Decimal] = None
    taker_fee: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def round_quantity(self, quantity: Decimal) -> Decimal:
        """
        Round quantity to valid step size.

        Args:
            quantity: Quantity to round

        Returns:
            Rounded quantity
        """
        if self.quantity_step:
            return (quantity // self.quantity_step) * self.quantity_step
        return quantity

    def round_price(self, price: Decimal) -> Decimal:
        """
        Round price to valid tick size.

        Args:
            price: Price to round

        Returns:
            Rounded price
        """
        if self.price_step:
            return (price // self.price_step) * self.price_step
        return price

    def validate_order(
        self, quantity: Decimal, price: Optional[Decimal] = None
    ) -> List[str]:
        """
        Validate order parameters.

        Args:
            quantity: Order quantity
            price: Order price (for limit orders)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if self.min_quantity and quantity < self.min_quantity:
            errors.append(f"Quantity {quantity} below minimum {self.min_quantity}")

        if self.max_quantity and quantity > self.max_quantity:
            errors.append(f"Quantity {quantity} above maximum {self.max_quantity}")

        if price:
            if self.min_price and price < self.min_price:
                errors.append(f"Price {price} below minimum {self.min_price}")

            if self.max_price and price > self.max_price:
                errors.append(f"Price {price} above maximum {self.max_price}")

            if self.min_notional:
                notional = quantity * price
                if notional < self.min_notional:
                    errors.append(
                        f"Notional {notional} below minimum {self.min_notional}"
                    )

        return errors
