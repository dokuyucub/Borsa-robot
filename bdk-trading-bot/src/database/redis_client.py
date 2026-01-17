"""
Redis client management for BDK Trading Bot.

This module provides async Redis operations including caching,
pub/sub messaging, and distributed locking.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

import redis.asyncio as redis

from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger("bdk.redis")


class RedisManager:
    """
    Manages async Redis connections for caching and pub/sub.

    Features:
    - Connection pooling
    - Automatic reconnection
    - JSON serialization
    - Pub/Sub support

    Usage:
        >>> redis_mgr = RedisManager()
        >>> await redis_mgr.initialize()
        >>>
        >>> # Basic operations
        >>> await redis_mgr.set("key", {"data": "value"}, ttl=60)
        >>> data = await redis_mgr.get("key")
        >>>
        >>> # Pub/Sub
        >>> await redis_mgr.publish("channel", {"event": "price_update"})
        >>>
        >>> await redis_mgr.close()
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis manager.

        Args:
            redis_url: Redis connection URL. If None, loaded from config.
        """
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.logger = get_logger("bdk.redis")
        self._subscribers: Dict[str, List[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        Initialize Redis connection.

        - Get URL from config if not provided
        - Create connection pool
        - Test connection with PING
        - Log success/failure
        """
        # Get URL from config if not provided
        if self.redis_url is None:
            config = get_config()
            self.redis_url = config.redis_url

        if not self.redis_url:
            self.logger.warning(
                "Redis URL not configured. Redis features will be disabled."
            )
            return

        try:
            # Create Redis client with connection pool
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )

            # Test connection
            await self.client.ping()

            self.logger.info("Redis connection established")

        except Exception as e:
            self.logger.error(
                "Failed to connect to Redis",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            self.client = None

    async def close(self) -> None:
        """
        Close Redis connections gracefully.

        - Cancel listener task if running
        - Close pubsub
        - Close client connection
        """
        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        # Close pubsub
        if self.pubsub:
            await self.pubsub.close()

        # Close client
        if self.client:
            await self.client.close()
            self.logger.info("Redis connections closed")

    async def health_check(self) -> bool:
        """
        Check if Redis is accessible.

        Returns:
            True if PING successful, False otherwise
        """
        if not self.client:
            return False

        try:
            await self.client.ping()
            return True
        except Exception as e:
            self.logger.error(
                "Redis health check failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False

    # ==================== Basic Operations ====================

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set a key-value pair with optional TTL.

        Args:
            key: Cache key
            value: Value (will be JSON serialized if dict/list)
            ttl: Time to live in seconds (None = no expiry)
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if set successfully

        Example:
            >>> await redis_mgr.set("price:BTC", {"price": 42000}, ttl=10)
        """
        if not self.client:
            return False

        try:
            serialized = self._serialize(value)
            result = await self.client.set(
                key, serialized, ex=ttl, nx=nx, xx=xx
            )
            return bool(result)
        except Exception as e:
            self.logger.error(
                "Redis SET failed",
                key=key,
                error=str(e),
            )
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value by key.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Deserialized value or default

        Example:
            >>> price = await redis_mgr.get("price:BTC", default={})
        """
        if not self.client:
            return default

        try:
            value = await self.client.get(key)
            if value is None:
                return default
            return self._deserialize(value)
        except Exception as e:
            self.logger.error(
                "Redis GET failed",
                key=key,
                error=str(e),
            )
            return default

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Returns:
            Number of keys deleted
        """
        if not self.client or not keys:
            return 0

        try:
            return await self.client.delete(*keys)
        except Exception as e:
            self.logger.error("Redis DELETE failed", keys=keys, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            return False

        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            self.logger.error("Redis EXISTS failed", key=key, error=str(e))
            return False

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        if not self.client:
            return -2

        try:
            return await self.client.ttl(key)
        except Exception as e:
            self.logger.error("Redis TTL failed", key=key, error=str(e))
            return -2

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        if not self.client:
            return False

        try:
            return bool(await self.client.expire(key, ttl))
        except Exception as e:
            self.logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "price:*", "arb:BTC:*")

        Returns:
            List of matching keys
        """
        if not self.client:
            return []

        try:
            keys = await self.client.keys(pattern)
            return [k for k in keys]
        except Exception as e:
            self.logger.error("Redis KEYS failed", pattern=pattern, error=str(e))
            return []

    # ==================== Hash Operations ====================

    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set hash field."""
        if not self.client:
            return 0

        try:
            serialized = self._serialize(value)
            return await self.client.hset(name, key, serialized)
        except Exception as e:
            self.logger.error("Redis HSET failed", name=name, error=str(e))
            return 0

    async def hget(self, name: str, key: str, default: Any = None) -> Any:
        """Get hash field."""
        if not self.client:
            return default

        try:
            value = await self.client.hget(name, key)
            if value is None:
                return default
            return self._deserialize(value)
        except Exception as e:
            self.logger.error("Redis HGET failed", name=name, error=str(e))
            return default

    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all hash fields."""
        if not self.client:
            return {}

        try:
            data = await self.client.hgetall(name)
            return {k: self._deserialize(v) for k, v in data.items()}
        except Exception as e:
            self.logger.error("Redis HGETALL failed", name=name, error=str(e))
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        if not self.client or not keys:
            return 0

        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            self.logger.error("Redis HDEL failed", name=name, error=str(e))
            return 0

    async def hmset(self, name: str, mapping: Dict[str, Any]) -> bool:
        """Set multiple hash fields."""
        if not self.client:
            return False

        try:
            serialized = {k: self._serialize(v) for k, v in mapping.items()}
            await self.client.hset(name, mapping=serialized)
            return True
        except Exception as e:
            self.logger.error("Redis HMSET failed", name=name, error=str(e))
            return False

    # ==================== List Operations ====================

    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to left of list."""
        if not self.client or not values:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return await self.client.lpush(key, *serialized)
        except Exception as e:
            self.logger.error("Redis LPUSH failed", key=key, error=str(e))
            return 0

    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to right of list."""
        if not self.client or not values:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return await self.client.rpush(key, *serialized)
        except Exception as e:
            self.logger.error("Redis RPUSH failed", key=key, error=str(e))
            return 0

    async def lpop(self, key: str) -> Any:
        """Pop from left of list."""
        if not self.client:
            return None

        try:
            value = await self.client.lpop(key)
            if value is None:
                return None
            return self._deserialize(value)
        except Exception as e:
            self.logger.error("Redis LPOP failed", key=key, error=str(e))
            return None

    async def rpop(self, key: str) -> Any:
        """Pop from right of list."""
        if not self.client:
            return None

        try:
            value = await self.client.rpop(key)
            if value is None:
                return None
            return self._deserialize(value)
        except Exception as e:
            self.logger.error("Redis RPOP failed", key=key, error=str(e))
            return None

    async def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """Get list range."""
        if not self.client:
            return []

        try:
            values = await self.client.lrange(key, start, stop)
            return [self._deserialize(v) for v in values]
        except Exception as e:
            self.logger.error("Redis LRANGE failed", key=key, error=str(e))
            return []

    async def llen(self, key: str) -> int:
        """Get list length."""
        if not self.client:
            return 0

        try:
            return await self.client.llen(key)
        except Exception as e:
            self.logger.error("Redis LLEN failed", key=key, error=str(e))
            return 0

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        """Trim list to specified range."""
        if not self.client:
            return False

        try:
            await self.client.ltrim(key, start, stop)
            return True
        except Exception as e:
            self.logger.error("Redis LTRIM failed", key=key, error=str(e))
            return False

    # ==================== Sorted Set Operations ====================

    async def zadd(
        self,
        key: str,
        mapping: Dict[str, float],
        nx: bool = False,
        xx: bool = False,
    ) -> int:
        """
        Add members to sorted set with scores.

        Args:
            key: Sorted set key
            mapping: {member: score} dict

        Example:
            >>> await redis_mgr.zadd("leaderboard", {"user1": 100, "user2": 200})
        """
        if not self.client or not mapping:
            return 0

        try:
            return await self.client.zadd(key, mapping, nx=nx, xx=xx)
        except Exception as e:
            self.logger.error("Redis ZADD failed", key=key, error=str(e))
            return 0

    async def zrange(
        self,
        key: str,
        start: int,
        stop: int,
        withscores: bool = False,
        desc: bool = False,
    ) -> List[Any]:
        """Get sorted set range."""
        if not self.client:
            return []

        try:
            if desc:
                result = await self.client.zrevrange(
                    key, start, stop, withscores=withscores
                )
            else:
                result = await self.client.zrange(
                    key, start, stop, withscores=withscores
                )

            if withscores:
                # Return list of tuples (member, score)
                return list(result)
            return list(result)
        except Exception as e:
            self.logger.error("Redis ZRANGE failed", key=key, error=str(e))
            return []

    async def zrem(self, key: str, *members: str) -> int:
        """Remove members from sorted set."""
        if not self.client or not members:
            return 0

        try:
            return await self.client.zrem(key, *members)
        except Exception as e:
            self.logger.error("Redis ZREM failed", key=key, error=str(e))
            return 0

    async def zscore(self, key: str, member: str) -> Optional[float]:
        """Get score of member."""
        if not self.client:
            return None

        try:
            return await self.client.zscore(key, member)
        except Exception as e:
            self.logger.error("Redis ZSCORE failed", key=key, error=str(e))
            return None

    # ==================== Pub/Sub Operations ====================

    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to channel.

        Args:
            channel: Channel name
            message: Message (will be JSON serialized)

        Returns:
            Number of subscribers that received the message

        Example:
            >>> await redis_mgr.publish("price_updates", {
            ...     "symbol": "BTC/USDT",
            ...     "price": 42000,
            ...     "exchange": "binance"
            ... })
        """
        if not self.client:
            return 0

        try:
            serialized = self._serialize(message)
            return await self.client.publish(channel, serialized)
        except Exception as e:
            self.logger.error(
                "Redis PUBLISH failed", channel=channel, error=str(e)
            )
            return 0

    async def subscribe(
        self, channel: str, callback: Callable[[str, Any], Awaitable[None]]
    ) -> None:
        """
        Subscribe to channel with callback.

        Args:
            channel: Channel name (supports patterns like "price:*")
            callback: Async function called with (channel, message)

        Example:
            >>> async def on_price(channel, data):
            ...     print(f"Price update on {channel}: {data}")
            >>>
            >>> await redis_mgr.subscribe("price:*", on_price)
        """
        if not self.client:
            return

        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

        # Create pubsub if needed
        if self.pubsub is None:
            self.pubsub = self.client.pubsub()

        # Subscribe to channel
        if "*" in channel or "?" in channel or "[" in channel:
            await self.pubsub.psubscribe(channel)
        else:
            await self.pubsub.subscribe(channel)

        # Start listener if not running
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._start_listener())

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from channel."""
        if not self.pubsub:
            return

        if channel in self._subscribers:
            del self._subscribers[channel]

        if "*" in channel or "?" in channel or "[" in channel:
            await self.pubsub.punsubscribe(channel)
        else:
            await self.pubsub.unsubscribe(channel)

    async def _start_listener(self) -> None:
        """Start background task to listen for pub/sub messages."""
        if not self.pubsub:
            return

        try:
            async for message in self.pubsub.listen():
                if message["type"] in ["message", "pmessage"]:
                    channel = message["channel"]
                    data = self._deserialize(message["data"])

                    # Call all callbacks for this channel
                    for pattern, callbacks in self._subscribers.items():
                        # Check if channel matches pattern
                        if pattern == channel or self._match_pattern(
                            pattern, channel
                        ):
                            for callback in callbacks:
                                try:
                                    await callback(channel, data)
                                except Exception as e:
                                    self.logger.error(
                                        "Pub/Sub callback error",
                                        channel=channel,
                                        error=str(e),
                                    )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error("Pub/Sub listener error", error=str(e))

    def _match_pattern(self, pattern: str, channel: str) -> bool:
        """Check if channel matches pattern (simple implementation)."""
        import fnmatch

        return fnmatch.fnmatch(channel, pattern)

    # ==================== Utility Methods ====================

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment integer value."""
        if not self.client:
            return 0

        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            self.logger.error("Redis INCR failed", key=key, error=str(e))
            return 0

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement integer value."""
        if not self.client:
            return 0

        try:
            return await self.client.decrby(key, amount)
        except Exception as e:
            self.logger.error("Redis DECR failed", key=key, error=str(e))
            return 0

    async def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Returns:
            Number of keys deleted

        Example:
            >>> await redis_mgr.flush_pattern("price:*")  # Clear all prices
        """
        if not self.client:
            return 0

        try:
            keys = await self.keys(pattern)
            if keys:
                return await self.delete(*keys)
            return 0
        except Exception as e:
            self.logger.error(
                "Redis FLUSH_PATTERN failed", pattern=pattern, error=str(e)
            )
            return 0

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    def _deserialize(self, value: Union[str, bytes, None]) -> Any:
        """Deserialize value from Redis."""
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


# ==================== Singleton Functions ====================

_redis_manager: Optional[RedisManager] = None


async def get_redis() -> RedisManager:
    """Get or create Redis manager singleton."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
        await _redis_manager.initialize()
    return _redis_manager


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None
