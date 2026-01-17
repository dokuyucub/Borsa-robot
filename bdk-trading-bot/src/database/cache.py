"""
Cache management for BDK Trading Bot.

This module provides specialized cache classes for different data types
including prices, arbitrage opportunities, rate limiting, and distributed locking.
"""

import asyncio
import time
from datetime import datetime
from decimal import Decimal
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from src.core.logger import get_logger

from .redis_client import RedisManager, get_redis

# ==================== Cache Key Prefixes ====================

PRICE_PREFIX = "price"
ARBITRAGE_PREFIX = "arb"
TICKER_PREFIX = "ticker"
ORDER_BOOK_PREFIX = "orderbook"
NEWS_PREFIX = "news"
SIGNAL_PREFIX = "signal"
RATE_LIMIT_PREFIX = "ratelimit"
SESSION_PREFIX = "session"
LOCK_PREFIX = "lock"

# ==================== Cache TTL Defaults ====================

PRICE_TTL = 5  # 5 seconds for real-time prices
TICKER_TTL = 10  # 10 seconds for ticker data
ORDER_BOOK_TTL = 5  # 5 seconds for order book
ARBITRAGE_TTL = 30  # 30 seconds for arb opportunities
NEWS_TTL = 300  # 5 minutes for news
SIGNAL_TTL = 60  # 1 minute for signals
SESSION_TTL = 86400  # 24 hours for sessions


# ==================== Price Cache ====================


class PriceCache:
    """
    Specialized cache for price data.

    Key format: price:{exchange}:{symbol}
    Example: price:binance:BTC/USDT
    """

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self.logger = get_logger("bdk.cache.price")

    async def set_price(
        self,
        exchange: str,
        symbol: str,
        price: Decimal | float,
        volume_24h: Optional[Decimal | float] = None,
        change_24h: Optional[Decimal | float] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Cache current price for a symbol.

        Example:
            >>> await price_cache.set_price(
            ...     "binance", "BTC/USDT",
            ...     price=42000.50,
            ...     volume_24h=1234567890,
            ...     change_24h=2.5
            ... )
        """
        key = f"{PRICE_PREFIX}:{exchange}:{symbol}"
        data = {
            "price": float(price),
            "volume_24h": float(volume_24h) if volume_24h else None,
            "change_24h": float(change_24h) if change_24h else None,
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "exchange": exchange,
            "symbol": symbol,
        }
        await self.redis.set(key, data, ttl=PRICE_TTL)

    async def get_price(
        self, exchange: str, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached price."""
        key = f"{PRICE_PREFIX}:{exchange}:{symbol}"
        return await self.redis.get(key)

    async def get_all_prices(
        self, exchange: Optional[str] = None, symbol: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached prices, optionally filtered.

        Returns:
            Dict with keys as "exchange:symbol" and values as price data
        """
        if exchange and symbol:
            pattern = f"{PRICE_PREFIX}:{exchange}:{symbol}"
        elif exchange:
            pattern = f"{PRICE_PREFIX}:{exchange}:*"
        elif symbol:
            pattern = f"{PRICE_PREFIX}:*:{symbol}"
        else:
            pattern = f"{PRICE_PREFIX}:*"

        keys = await self.redis.keys(pattern)
        result = {}
        for key in keys:
            data = await self.redis.get(key)
            if data:
                # Extract exchange:symbol from key
                parts = key.replace(f"{PRICE_PREFIX}:", "").split(":", 1)
                if len(parts) == 2:
                    result[f"{parts[0]}:{parts[1]}"] = data
        return result

    async def get_price_comparison(
        self, symbol: str, exchanges: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get prices for same symbol across multiple exchanges.
        Useful for arbitrage detection.

        Returns:
            Dict with exchange names as keys
        """
        pattern = f"{PRICE_PREFIX}:*:{symbol}"
        keys = await self.redis.keys(pattern)
        result = {}
        for key in keys:
            data = await self.redis.get(key)
            if data:
                exchange = key.split(":")[1]
                if exchanges is None or exchange in exchanges:
                    result[exchange] = data
        return result


# ==================== Arbitrage Cache ====================


class ArbitrageCache:
    """
    Cache for arbitrage opportunities.

    Key format: arb:{symbol}:{buy_exchange}:{sell_exchange}
    """

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self.logger = get_logger("bdk.cache.arbitrage")

    async def set_opportunity(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: Decimal | float,
        sell_price: Decimal | float,
        spread_percent: Decimal | float,
        net_profit_percent: Decimal | float,
        estimated_profit_usd: Decimal | float,
    ) -> None:
        """Cache an arbitrage opportunity."""
        key = f"{ARBITRAGE_PREFIX}:{symbol}:{buy_exchange}:{sell_exchange}"
        data = {
            "symbol": symbol,
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "buy_price": float(buy_price),
            "sell_price": float(sell_price),
            "spread_percent": float(spread_percent),
            "net_profit_percent": float(net_profit_percent),
            "estimated_profit_usd": float(estimated_profit_usd),
            "detected_at": datetime.utcnow().isoformat(),
        }
        await self.redis.set(key, data, ttl=ARBITRAGE_TTL)

        # Also add to sorted set for easy retrieval by profit
        await self.redis.zadd(
            f"{ARBITRAGE_PREFIX}:ranked", {key: float(net_profit_percent)}
        )

    async def get_opportunity(
        self, symbol: str, buy_exchange: str, sell_exchange: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific arbitrage opportunity."""
        key = f"{ARBITRAGE_PREFIX}:{symbol}:{buy_exchange}:{sell_exchange}"
        return await self.redis.get(key)

    async def get_best_opportunities(
        self, limit: int = 10, min_profit_percent: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Get best arbitrage opportunities sorted by profit.

        Returns:
            List of opportunities sorted by net_profit_percent descending
        """
        # Get from sorted set (highest scores first)
        keys_with_scores = await self.redis.zrange(
            f"{ARBITRAGE_PREFIX}:ranked",
            0,
            limit - 1,
            withscores=True,
            desc=True,
        )

        result = []
        for item in keys_with_scores:
            if isinstance(item, tuple):
                key, score = item
            else:
                continue

            if score >= min_profit_percent:
                data = await self.redis.get(key)
                if data:
                    result.append(data)
        return result

    async def get_opportunities_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all opportunities for a symbol."""
        pattern = f"{ARBITRAGE_PREFIX}:{symbol}:*"
        keys = await self.redis.keys(pattern)
        result = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                result.append(data)
        return sorted(
            result, key=lambda x: x.get("net_profit_percent", 0), reverse=True
        )

    async def clear_expired(self) -> int:
        """Clear expired opportunities from ranked set."""
        keys = await self.redis.keys(f"{ARBITRAGE_PREFIX}:*:*:*")
        valid_keys = set()
        for key in keys:
            if await self.redis.exists(key):
                valid_keys.add(key)

        # Remove invalid keys from ranked set
        ranked_members = await self.redis.zrange(
            f"{ARBITRAGE_PREFIX}:ranked", 0, -1
        )
        removed = 0
        for member in ranked_members:
            if member not in valid_keys:
                await self.redis.zrem(f"{ARBITRAGE_PREFIX}:ranked", member)
                removed += 1
        return removed


# ==================== Rate Limiter ====================


class RateLimiter:
    """
    Redis-based rate limiter.

    Uses sliding window algorithm.
    """

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self.logger = get_logger("bdk.cache.ratelimit")

    async def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., "api:binance", "telegram:123")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            (is_allowed, remaining_requests)

        Example:
            >>> allowed, remaining = await limiter.is_allowed("api:binance", 100, 60)
            >>> if not allowed:
            ...     logger.warning(f"Rate limited, {remaining} requests remaining")
        """
        if not self.redis.client:
            return True, max_requests

        cache_key = f"{RATE_LIMIT_PREFIX}:{key}"
        now = time.time()
        window_start = now - window_seconds

        try:
            # Remove old entries
            await self.redis.client.zremrangebyscore(cache_key, 0, window_start)

            # Count current entries
            current_count = await self.redis.client.zcard(cache_key)

            if current_count < max_requests:
                # Add new entry
                await self.redis.client.zadd(cache_key, {str(now): now})
                await self.redis.expire(cache_key, window_seconds)
                return True, max_requests - current_count - 1

            return False, 0
        except Exception as e:
            self.logger.error("Rate limiter error", key=key, error=str(e))
            return True, max_requests  # Allow on error

    async def get_wait_time(self, key: str, window_seconds: int) -> float:
        """
        Get seconds until next request is allowed.

        Returns:
            Seconds to wait (0 if allowed now)
        """
        if not self.redis.client:
            return 0

        cache_key = f"{RATE_LIMIT_PREFIX}:{key}"
        try:
            oldest = await self.redis.client.zrange(
                cache_key, 0, 0, withscores=True
            )
            if oldest:
                if isinstance(oldest[0], tuple):
                    oldest_time = oldest[0][1]
                else:
                    return 0
                wait_time = (oldest_time + window_seconds) - time.time()
                return max(0, wait_time)
            return 0
        except Exception as e:
            self.logger.error("Get wait time error", key=key, error=str(e))
            return 0


# ==================== Distributed Lock ====================


class DistributedLock:
    """
    Redis-based distributed lock for preventing race conditions.

    Usage:
        >>> lock = DistributedLock(redis, "arbitrage:BTC")
        >>> if await lock.acquire(timeout=5):
        ...     try:
        ...         # Do work
        ...         pass
        ...     finally:
        ...         await lock.release()

    Or as context manager:
        >>> async with DistributedLock(redis, "arbitrage:BTC"):
        ...     # Do work
        ...     pass
    """

    def __init__(self, redis: RedisManager, name: str, ttl: int = 30):
        self.redis = redis
        self.name = f"{LOCK_PREFIX}:{name}"
        self.ttl = ttl
        self.logger = get_logger("bdk.cache.lock")
        self._lock_value: Optional[str] = None

    async def acquire(
        self, timeout: float = 10, retry_interval: float = 0.1
    ) -> bool:
        """
        Acquire the lock.

        Args:
            timeout: Max seconds to wait for lock
            retry_interval: Seconds between retry attempts

        Returns:
            True if lock acquired, False if timeout
        """
        import uuid

        self._lock_value = str(uuid.uuid4())
        start = time.time()

        while time.time() - start < timeout:
            if await self.redis.set(
                self.name, self._lock_value, ttl=self.ttl, nx=True
            ):
                self.logger.debug(f"Lock acquired: {self.name}")
                return True
            await asyncio.sleep(retry_interval)

        self.logger.warning(f"Lock timeout: {self.name}")
        return False

    async def release(self) -> bool:
        """Release the lock if we own it."""
        if self._lock_value is None:
            return False

        # Only release if we own the lock
        current = await self.redis.get(self.name)
        if current == self._lock_value:
            await self.redis.delete(self.name)
            self.logger.debug(f"Lock released: {self.name}")
            self._lock_value = None
            return True
        return False

    async def __aenter__(self) -> "DistributedLock":
        if not await self.acquire():
            raise TimeoutError(f"Could not acquire lock: {self.name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.release()


# ==================== Cache Decorator ====================

T = TypeVar("T")


def cached(
    prefix: str, ttl: int = 60, key_builder: Optional[Callable[..., str]] = None
):
    """
    Decorator for caching async function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Optional function to build cache key from args

    Example:
        >>> @cached("prices", ttl=10)
        ... async def get_price(exchange: str, symbol: str) -> dict:
        ...     # Expensive API call
        ...     return await api.fetch_price(symbol)
        >>>
        >>> # First call: fetches from API, caches result
        >>> price = await get_price("binance", "BTC/USDT")
        >>>
        >>> # Second call within 10s: returns cached result
        >>> price = await get_price("binance", "BTC/USDT")
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            redis = await get_redis()

            # Build cache key
            if key_builder:
                cache_key = f"{prefix}:{key_builder(*args, **kwargs)}"
            else:
                key_parts = [str(a) for a in args] + [
                    f"{k}={v}" for k, v in sorted(kwargs.items())
                ]
                cache_key = f"{prefix}:{':'.join(key_parts)}"

            # Try cache
            cached_result = await redis.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            await redis.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# ==================== Cache Manager ====================


class CacheManager:
    """
    Central cache manager providing access to all cache functionality.

    Usage:
        >>> cache = await get_cache_manager()
        >>>
        >>> # Price caching
        >>> await cache.prices.set_price("binance", "BTC/USDT", 42000)
        >>>
        >>> # Arbitrage caching
        >>> await cache.arbitrage.set_opportunity(...)
        >>>
        >>> # Rate limiting
        >>> allowed, remaining = await cache.rate_limiter.is_allowed("api:binance", 100, 60)
    """

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self.prices = PriceCache(redis)
        self.arbitrage = ArbitrageCache(redis)
        self.rate_limiter = RateLimiter(redis)
        self.logger = get_logger("bdk.cache")

    def lock(self, name: str, ttl: int = 30) -> DistributedLock:
        """Get a distributed lock."""
        return DistributedLock(self.redis, name, ttl)

    async def clear_all(self) -> int:
        """Clear all BDK cache keys."""
        patterns = [
            f"{PRICE_PREFIX}:*",
            f"{ARBITRAGE_PREFIX}:*",
            f"{TICKER_PREFIX}:*",
            f"{ORDER_BOOK_PREFIX}:*",
            f"{NEWS_PREFIX}:*",
            f"{SIGNAL_PREFIX}:*",
        ]
        total = 0
        for pattern in patterns:
            total += await self.redis.flush_pattern(pattern)
        self.logger.info(f"Cleared {total} cache keys")
        return total

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "prices": len(await self.redis.keys(f"{PRICE_PREFIX}:*")),
            "arbitrage": len(await self.redis.keys(f"{ARBITRAGE_PREFIX}:*")),
            "tickers": len(await self.redis.keys(f"{TICKER_PREFIX}:*")),
            "news": len(await self.redis.keys(f"{NEWS_PREFIX}:*")),
            "signals": len(await self.redis.keys(f"{SIGNAL_PREFIX}:*")),
        }
        stats["total"] = sum(stats.values())
        return stats


# ==================== Singleton ====================

_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get or create CacheManager singleton."""
    global _cache_manager
    if _cache_manager is None:
        redis = await get_redis()
        _cache_manager = CacheManager(redis)
    return _cache_manager
