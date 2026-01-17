"""Database management module for BDK Trading Bot."""

# Base
from .models import Base

# Enums
from .models import (
    MarketType,
    OrderSide,
    OrderType,
    SignalAction,
    SignalType,
    TradeStatus,
)

# Models
from .models import (
    ArbitrageOpportunity,
    BotSettings,
    DailyReport,
    NewsItem,
    Portfolio,
    Position,
    PriceHistory,
    Signal,
    Trade,
)

# Connection
from .connection import DatabaseManager, close_database, get_database

# Repositories
from .repository import (
    ArbitrageRepository,
    BaseRepository,
    PortfolioRepository,
    PositionRepository,
    PriceHistoryRepository,
    SignalRepository,
    TradeRepository,
)

# Redis
from .redis_client import RedisManager, close_redis, get_redis

# Cache
from .cache import (
    ArbitrageCache,
    CacheManager,
    DistributedLock,
    PriceCache,
    RateLimiter,
    cached,
    get_cache_manager,
)

# Cache constants
from .cache import (
    ARBITRAGE_PREFIX,
    ARBITRAGE_TTL,
    LOCK_PREFIX,
    NEWS_PREFIX,
    NEWS_TTL,
    ORDER_BOOK_PREFIX,
    ORDER_BOOK_TTL,
    PRICE_PREFIX,
    PRICE_TTL,
    RATE_LIMIT_PREFIX,
    SESSION_PREFIX,
    SESSION_TTL,
    SIGNAL_PREFIX,
    SIGNAL_TTL,
    TICKER_PREFIX,
    TICKER_TTL,
)

__all__ = [
    # Base
    "Base",
    # Enums
    "MarketType",
    "OrderSide",
    "OrderType",
    "TradeStatus",
    "SignalType",
    "SignalAction",
    # Models
    "Portfolio",
    "Position",
    "Trade",
    "Signal",
    "PriceHistory",
    "ArbitrageOpportunity",
    "NewsItem",
    "DailyReport",
    "BotSettings",
    # Connection
    "DatabaseManager",
    "get_database",
    "close_database",
    # Repositories
    "BaseRepository",
    "PortfolioRepository",
    "TradeRepository",
    "PositionRepository",
    "SignalRepository",
    "ArbitrageRepository",
    "PriceHistoryRepository",
    # Redis
    "RedisManager",
    "get_redis",
    "close_redis",
    # Cache
    "CacheManager",
    "get_cache_manager",
    "PriceCache",
    "ArbitrageCache",
    "RateLimiter",
    "DistributedLock",
    "cached",
    # Cache constants
    "PRICE_PREFIX",
    "ARBITRAGE_PREFIX",
    "TICKER_PREFIX",
    "ORDER_BOOK_PREFIX",
    "NEWS_PREFIX",
    "SIGNAL_PREFIX",
    "RATE_LIMIT_PREFIX",
    "SESSION_PREFIX",
    "LOCK_PREFIX",
    "PRICE_TTL",
    "TICKER_TTL",
    "ORDER_BOOK_TTL",
    "ARBITRAGE_TTL",
    "NEWS_TTL",
    "SIGNAL_TTL",
    "SESSION_TTL",
]
