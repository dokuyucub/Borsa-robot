"""
Exchange factory for BDK Trading Bot.

This module provides a factory pattern for creating and managing exchange
instances. It handles registration, instantiation, and lifecycle management
of all exchange implementations.
"""

from typing import Any, Callable, Dict, List, Optional, Type

from src.core.config import get_config
from src.core.logger import get_logger

from .base import BaseExchange

logger = get_logger("bdk.exchanges.factory")


# ==================== Exchange Registry ====================

_exchange_registry: Dict[str, Type[BaseExchange]] = {}


def register_exchange(exchange_id: str) -> Callable:
    """
    Decorator to register an exchange implementation.

    Usage:
        >>> @register_exchange("binance")
        ... class BinanceExchange(BaseExchange):
        ...     EXCHANGE_ID = "binance"
        ...     # Implementation
        ...     pass

    Args:
        exchange_id: Unique exchange identifier

    Returns:
        Decorator function
    """

    def decorator(cls: Type[BaseExchange]) -> Type[BaseExchange]:
        if exchange_id in _exchange_registry:
            logger.warning(
                f"Overwriting existing exchange registration: {exchange_id}"
            )

        _exchange_registry[exchange_id] = cls
        logger.debug(f"Registered exchange: {exchange_id}", exchange_class=cls.__name__)
        return cls

    return decorator


def get_registered_exchanges() -> List[str]:
    """
    Get list of all registered exchange IDs.

    Returns:
        List of exchange IDs
    """
    return list(_exchange_registry.keys())


def is_exchange_registered(exchange_id: str) -> bool:
    """
    Check if an exchange is registered.

    Args:
        exchange_id: Exchange identifier

    Returns:
        True if registered
    """
    return exchange_id in _exchange_registry


# ==================== Exchange Factory ====================


class ExchangeFactory:
    """
    Factory for creating and managing exchange instances.

    This class handles:
    - Creating exchange instances with proper configuration
    - Caching instances for reuse
    - Managing exchange lifecycle (creation, retrieval, cleanup)
    - Loading credentials from config

    Usage:
        >>> factory = ExchangeFactory()
        >>> exchange = await factory.create("binance")
        >>> # Later...
        >>> same_exchange = factory.get("binance")
        >>> await factory.close_all()
    """

    def __init__(self):
        """Initialize exchange factory."""
        self._instances: Dict[str, BaseExchange] = {}
        self.config = get_config()
        self.logger = get_logger("bdk.exchanges.factory")

    async def create(
        self,
        exchange_id: str,
        paper_trading: Optional[bool] = None,
        auto_connect: bool = True,
        **kwargs,
    ) -> BaseExchange:
        """
        Create or retrieve an exchange instance.

        Args:
            exchange_id: Exchange identifier (binance, alpaca, etc.)
            paper_trading: Override paper trading mode (None = use config)
            auto_connect: Automatically connect after creation
            **kwargs: Additional exchange-specific parameters

        Returns:
            Exchange instance

        Raises:
            ValueError: If exchange not registered
            ExchangeError: If connection fails

        Example:
            >>> factory = ExchangeFactory()
            >>> exchange = await factory.create("binance", paper_trading=True)
            >>> ticker = await exchange.fetch_ticker("BTC/USDT")
        """
        # Return cached instance if exists
        if exchange_id in self._instances:
            self.logger.debug(f"Returning cached exchange: {exchange_id}")
            return self._instances[exchange_id]

        # Check if exchange is registered
        if not is_exchange_registered(exchange_id):
            available = ", ".join(get_registered_exchanges())
            raise ValueError(
                f"Exchange '{exchange_id}' not registered. "
                f"Available exchanges: {available or 'none'}"
            )

        # Get exchange class
        exchange_class = _exchange_registry[exchange_id]

        # Get credentials from config
        credentials = self._get_credentials(exchange_id)

        # Determine paper trading mode
        if paper_trading is None:
            paper_trading = self.config.paper_trading.enabled

        # Merge credentials with kwargs (kwargs take precedence)
        params = {**credentials, "paper_trading": paper_trading, **kwargs}

        # Create instance
        self.logger.info(
            f"Creating exchange: {exchange_id}",
            paper_trading=paper_trading,
            auto_connect=auto_connect,
        )

        exchange = exchange_class(**params)

        # Auto-connect if requested
        if auto_connect:
            try:
                connected = await exchange.connect()
                if not connected:
                    self.logger.warning(
                        f"Exchange {exchange_id} creation succeeded but connection failed"
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to connect to exchange: {exchange_id}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise

        # Cache instance
        self._instances[exchange_id] = exchange

        self.logger.info(
            f"Exchange {exchange_id} created successfully",
            is_connected=exchange.is_connected,
        )

        return exchange

    async def create_all(
        self,
        exchange_ids: Optional[List[str]] = None,
        paper_trading: Optional[bool] = None,
        auto_connect: bool = True,
        **kwargs,
    ) -> Dict[str, BaseExchange]:
        """
        Create multiple exchange instances.

        Args:
            exchange_ids: List of exchange IDs (None = all enabled in config)
            paper_trading: Override paper trading mode
            auto_connect: Automatically connect after creation
            **kwargs: Additional parameters for all exchanges

        Returns:
            Dict mapping exchange_id to exchange instance

        Example:
            >>> factory = ExchangeFactory()
            >>> exchanges = await factory.create_all(["binance", "alpaca"])
            >>> for exchange_id, exchange in exchanges.items():
            ...     print(f"{exchange_id}: {exchange.is_connected}")
        """
        # Determine which exchanges to create
        if exchange_ids is None:
            # Get enabled exchanges from config
            exchange_ids = self._get_enabled_exchanges()

        if not exchange_ids:
            self.logger.warning("No exchanges to create")
            return {}

        self.logger.info(f"Creating {len(exchange_ids)} exchanges", exchanges=exchange_ids)

        # Create all exchanges
        exchanges = {}
        for exchange_id in exchange_ids:
            try:
                exchange = await self.create(
                    exchange_id=exchange_id,
                    paper_trading=paper_trading,
                    auto_connect=auto_connect,
                    **kwargs,
                )
                exchanges[exchange_id] = exchange
            except Exception as e:
                self.logger.error(
                    f"Failed to create exchange: {exchange_id}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                # Continue creating other exchanges

        self.logger.info(
            f"Created {len(exchanges)}/{len(exchange_ids)} exchanges successfully"
        )

        return exchanges

    def get(self, exchange_id: str) -> Optional[BaseExchange]:
        """
        Get cached exchange instance.

        Args:
            exchange_id: Exchange identifier

        Returns:
            Exchange instance or None if not created

        Example:
            >>> factory = ExchangeFactory()
            >>> exchange = factory.get("binance")
            >>> if exchange:
            ...     print(f"Binance is connected: {exchange.is_connected}")
        """
        return self._instances.get(exchange_id)

    def get_all(self) -> Dict[str, BaseExchange]:
        """
        Get all cached exchange instances.

        Returns:
            Dict mapping exchange_id to exchange instance
        """
        return self._instances.copy()

    def has(self, exchange_id: str) -> bool:
        """
        Check if exchange instance exists in cache.

        Args:
            exchange_id: Exchange identifier

        Returns:
            True if instance exists
        """
        return exchange_id in self._instances

    async def close(self, exchange_id: str) -> None:
        """
        Close and remove specific exchange.

        Args:
            exchange_id: Exchange identifier

        Example:
            >>> factory = ExchangeFactory()
            >>> await factory.close("binance")
        """
        if exchange_id in self._instances:
            exchange = self._instances[exchange_id]
            try:
                await exchange.disconnect()
                self.logger.info(f"Closed exchange: {exchange_id}")
            except Exception as e:
                self.logger.error(
                    f"Error closing exchange: {exchange_id}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            finally:
                del self._instances[exchange_id]

    async def close_all(self) -> None:
        """
        Close all exchange connections and clear cache.

        Example:
            >>> factory = ExchangeFactory()
            >>> # Create some exchanges...
            >>> await factory.close_all()
        """
        if not self._instances:
            self.logger.debug("No exchanges to close")
            return

        self.logger.info(f"Closing {len(self._instances)} exchanges")

        # Close all exchanges
        for exchange_id in list(self._instances.keys()):
            await self.close(exchange_id)

        self.logger.info("All exchanges closed")

    def _get_credentials(self, exchange_id: str) -> Dict[str, str]:
        """
        Get exchange credentials from config.

        Args:
            exchange_id: Exchange identifier

        Returns:
            Dict with api_key, api_secret, passphrase
        """
        try:
            credentials = self.config.get_exchange_credentials(exchange_id)
            self.logger.debug(
                f"Loaded credentials for {exchange_id}",
                has_api_key=bool(credentials.get("api_key")),
                has_api_secret=bool(credentials.get("api_secret")),
                has_passphrase=bool(credentials.get("passphrase")),
            )
            return credentials
        except Exception as e:
            self.logger.warning(
                f"Failed to load credentials for {exchange_id}: {str(e)}"
            )
            return {"api_key": "", "api_secret": "", "passphrase": ""}

    def _get_enabled_exchanges(self) -> List[str]:
        """
        Get list of enabled exchanges from config.

        Returns:
            List of exchange IDs that are enabled
        """
        enabled = []

        # Check crypto exchanges
        if self.config.crypto.binance.enabled:
            enabled.append("binance")
        if self.config.crypto.coinbase.enabled:
            enabled.append("coinbase")

        # Check stock exchanges
        if self.config.stocks.alpaca.enabled:
            enabled.append("alpaca")

        return enabled


# ==================== Singleton Instance ====================

_factory: Optional[ExchangeFactory] = None


def get_exchange_factory() -> ExchangeFactory:
    """
    Get or create exchange factory singleton.

    Returns:
        ExchangeFactory instance

    Example:
        >>> factory = get_exchange_factory()
        >>> exchange = await factory.create("binance")
    """
    global _factory
    if _factory is None:
        _factory = ExchangeFactory()
        logger.debug("Created exchange factory singleton")
    return _factory


async def get_exchange(
    exchange_id: str,
    paper_trading: Optional[bool] = None,
    auto_connect: bool = True,
    **kwargs,
) -> BaseExchange:
    """
    Convenience function to get or create an exchange.

    This is a shortcut for get_exchange_factory().create()

    Args:
        exchange_id: Exchange identifier
        paper_trading: Override paper trading mode
        auto_connect: Automatically connect after creation
        **kwargs: Additional exchange-specific parameters

    Returns:
        Exchange instance

    Example:
        >>> # Simple usage
        >>> exchange = await get_exchange("binance")
        >>>
        >>> # With parameters
        >>> exchange = await get_exchange(
        ...     "binance",
        ...     paper_trading=True,
        ...     testnet=True
        ... )
    """
    factory = get_exchange_factory()
    return await factory.create(
        exchange_id=exchange_id,
        paper_trading=paper_trading,
        auto_connect=auto_connect,
        **kwargs,
    )


async def close_all_exchanges() -> None:
    """
    Close all exchanges and cleanup factory.

    Example:
        >>> # At application shutdown
        >>> await close_all_exchanges()
    """
    global _factory
    if _factory:
        await _factory.close_all()
        _factory = None
        logger.debug("Closed all exchanges and cleared factory")
