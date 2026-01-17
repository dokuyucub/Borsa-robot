"""
Configuration management system for BDK Trading Bot.

This module provides a comprehensive configuration system that loads settings
from YAML files and environment variables, with Pydantic validation.

Example Usage:
    >>> from src.core import get_config
    >>>
    >>> # Get config singleton
    >>> config = get_config()
    >>>
    >>> # Access settings
    >>> print(config.paper_trading.initial_balance_usd)  # 10000.0
    >>> print(config.crypto.coins)  # ['BTC', 'ETH', ...]
    >>> print(config.telegram.language)  # 'tr'
    >>>
    >>> # Get exchange credentials
    >>> creds = config.get_exchange_credentials("binance")
    >>> print(creds["api_key"])
    >>>
    >>> # Check what's configured
    >>> enabled = config.get_enabled_exchanges()
    >>> print(enabled)  # ['binance', 'bybit'] etc.
"""

import os
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator

from .exceptions import BDKException, ConfigurationError

# Configure logger
logger = logging.getLogger(__name__)


class GeneralConfig(BaseModel):
    """General application configuration."""

    environment: str = "development"
    debug: bool = True
    timezone: str = "Europe/Istanbul"


class PaperTradingConfig(BaseModel):
    """Paper trading (simulation) configuration."""

    enabled: bool = True
    initial_balance_usd: float = 10000.0
    max_single_trade_usd: float = 500.0
    max_daily_loss_usd: float = 300.0
    max_open_positions: int = 5


class CryptoConfig(BaseModel):
    """Cryptocurrency trading configuration."""

    enabled: bool = True
    exchanges: list[str] = ["binance", "bybit", "okx", "kucoin", "gateio"]
    coins: list[str] = [
        "BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOGE",
        "DOT", "MATIC", "LINK", "UNI", "LTC", "ATOM", "NEAR", "APT"
    ]
    quote_currency: str = "USDT"

    @field_validator("exchanges", mode="after")
    @classmethod
    def validate_exchanges(cls, v: list[str]) -> list[str]:
        """Ensure all exchange names are lowercase."""
        return [exchange.lower() for exchange in v]

    @field_validator("coins", mode="after")
    @classmethod
    def validate_coins(cls, v: list[str]) -> list[str]:
        """Ensure all coin symbols are uppercase."""
        return [coin.upper() for coin in v]


class USStocksConfig(BaseModel):
    """US stocks trading configuration."""

    enabled: bool = True
    provider: str = "alpaca"
    stocks: list[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "TSLA", "META", "AMD", "NFLX", "CRM"
    ]
    etfs: list[str] = ["SPY", "QQQ", "IWM", "DIA", "VTI"]

    @field_validator("stocks", mode="after")
    @classmethod
    def validate_stocks(cls, v: list[str]) -> list[str]:
        """Ensure all stock symbols are uppercase."""
        return [symbol.upper() for symbol in v]

    @field_validator("etfs", mode="after")
    @classmethod
    def validate_etfs(cls, v: list[str]) -> list[str]:
        """Ensure all ETF symbols are uppercase."""
        return [etf.upper() for etf in v]


class BISTConfig(BaseModel):
    """BIST (Borsa Istanbul) trading configuration."""

    enabled: bool = True
    symbols: list[str] = [
        "THYAO", "SISE", "ASELS", "GARAN", "AKBNK",
        "KCHOL", "TUPRS", "EREGL", "BIMAS", "FROTO"
    ]

    @field_validator("symbols", mode="after")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        """Ensure all BIST symbols are uppercase."""
        return [symbol.upper() for symbol in v]


class ArbitrageConfig(BaseModel):
    """Arbitrage trading strategy configuration."""

    enabled: bool = True
    min_profit_percent: float = 0.15
    max_execution_time_seconds: int = 60
    min_confidence_score: int = 90

    @field_validator("min_profit_percent", mode="after")
    @classmethod
    def validate_min_profit(cls, v: float) -> float:
        """Ensure min_profit_percent is between 0.01 and 5.0."""
        if not 0.01 <= v <= 5.0:
            raise ValueError("min_profit_percent must be between 0.01 and 5.0")
        return v


class NewsTradingConfig(BaseModel):
    """News-based trading strategy configuration."""

    enabled: bool = True
    min_sentiment_score: int = 75
    sources: list[str] = ["newsapi", "cryptopanic", "finnhub", "reddit"]

    @field_validator("min_sentiment_score", mode="after")
    @classmethod
    def validate_sentiment_score(cls, v: int) -> int:
        """Ensure min_sentiment_score is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("min_sentiment_score must be between 0 and 100")
        return v


class RiskManagementConfig(BaseModel):
    """Risk management configuration."""

    stop_loss_percent: float = 2.0
    take_profit_percent: float = 5.0
    trailing_stop_enabled: bool = True
    trailing_stop_percent: float = 1.5

    @model_validator(mode="after")
    def validate_stop_loss_vs_take_profit(self) -> "RiskManagementConfig":
        """Ensure stop_loss is less than take_profit."""
        if self.stop_loss_percent >= self.take_profit_percent:
            raise ValueError(
                f"stop_loss_percent ({self.stop_loss_percent}) must be less than "
                f"take_profit_percent ({self.take_profit_percent})"
            )
        return self


class NightModeConfig(BaseModel):
    """Night mode configuration for automated trading during off-hours."""

    enabled: bool = True
    start_time: str = "23:00"
    end_time: str = "07:00"
    auto_trade: bool = True
    wake_up_threshold_usd: float = 1000.0

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Ensure time format is HH:MM."""
        import re
        if not re.match(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError(f"Time format must be HH:MM, got: {v}")
        return v


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    enabled: bool = True
    language: str = "tr"
    daily_report_time: str = "08:00"
    night_mode: NightModeConfig = NightModeConfig()

    @field_validator("language", mode="after")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Ensure language is either 'tr' or 'en'."""
        if v not in ["tr", "en"]:
            raise ValueError(f"language must be 'tr' or 'en', got: {v}")
        return v


class DatabaseConfig(BaseModel):
    """Database configuration."""

    type: str = "postgresql"
    pool_size: int = 10
    echo: bool = False


class RedisConfig(BaseModel):
    """Redis cache configuration."""

    enabled: bool = True
    cache_ttl_seconds: int = 60


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    file_enabled: bool = True
    max_file_size_mb: int = 100
    backup_count: int = 5

    @field_validator("level", mode="after")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Ensure logging level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"level must be one of {valid_levels}, got: {v}"
            )
        return v_upper


class Config(BaseModel):
    """
    Main configuration class that combines all config sections.

    This class loads configuration from YAML files and environment variables,
    providing a unified interface for accessing all application settings.
    """

    # Configuration sections
    general: GeneralConfig = GeneralConfig()
    paper_trading: PaperTradingConfig = PaperTradingConfig()
    crypto: CryptoConfig = CryptoConfig()
    us_stocks: USStocksConfig = USStocksConfig()
    bist: BISTConfig = BISTConfig()
    arbitrage: ArbitrageConfig = ArbitrageConfig()
    news_trading: NewsTradingConfig = NewsTradingConfig()
    risk_management: RiskManagementConfig = RiskManagementConfig()
    telegram: TelegramConfig = TelegramConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    logging: LoggingConfig = LoggingConfig()

    # Environment variables (API keys and secrets)
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # Exchange API credentials
    binance_api_key: str = Field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_api_secret: str = Field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    bybit_api_key: str = Field(default_factory=lambda: os.getenv("BYBIT_API_KEY", ""))
    bybit_api_secret: str = Field(default_factory=lambda: os.getenv("BYBIT_API_SECRET", ""))
    okx_api_key: str = Field(default_factory=lambda: os.getenv("OKX_API_KEY", ""))
    okx_api_secret: str = Field(default_factory=lambda: os.getenv("OKX_API_SECRET", ""))
    okx_passphrase: str = Field(default_factory=lambda: os.getenv("OKX_PASSPHRASE", ""))
    kucoin_api_key: str = Field(default_factory=lambda: os.getenv("KUCOIN_API_KEY", ""))
    kucoin_api_secret: str = Field(default_factory=lambda: os.getenv("KUCOIN_API_SECRET", ""))
    kucoin_passphrase: str = Field(default_factory=lambda: os.getenv("KUCOIN_PASSPHRASE", ""))
    gateio_api_key: str = Field(default_factory=lambda: os.getenv("GATEIO_API_KEY", ""))
    gateio_api_secret: str = Field(default_factory=lambda: os.getenv("GATEIO_API_SECRET", ""))
    alpaca_api_key: str = Field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    alpaca_api_secret: str = Field(default_factory=lambda: os.getenv("ALPACA_API_SECRET", ""))

    # News API credentials
    news_api_key: str = Field(default_factory=lambda: os.getenv("NEWS_API_KEY", ""))
    cryptopanic_api_key: str = Field(default_factory=lambda: os.getenv("CRYPTOPANIC_API_KEY", ""))
    finnhub_api_key: str = Field(default_factory=lambda: os.getenv("FINNHUB_API_KEY", ""))

    # AI API credentials
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "Config":
        """
        Load configuration from a YAML file.

        The YAML configuration is merged with environment variables,
        with environment variables taking precedence for API keys and secrets.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Config instance with loaded settings

        Raises:
            ConfigurationError: If file not found or parsing fails
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                details={"path": str(config_path)}
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            if yaml_data is None:
                yaml_data = {}

            logger.info(f"Loaded configuration from {config_path}")
            return cls(**yaml_data)

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML configuration: {e}",
                details={"path": str(config_path), "error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                details={"path": str(config_path), "error": str(e)}
            )

    def get_exchange_credentials(self, exchange: str) -> dict[str, str]:
        """
        Get API credentials for a specific exchange.

        Args:
            exchange: Exchange name (binance, bybit, okx, kucoin, gateio, alpaca)

        Returns:
            Dictionary containing api_key, api_secret, and passphrase (if applicable)

        Raises:
            ConfigurationError: If exchange is not recognized
        """
        exchange = exchange.lower()

        credentials_map = {
            "binance": {
                "api_key": self.binance_api_key,
                "api_secret": self.binance_api_secret,
            },
            "bybit": {
                "api_key": self.bybit_api_key,
                "api_secret": self.bybit_api_secret,
            },
            "okx": {
                "api_key": self.okx_api_key,
                "api_secret": self.okx_api_secret,
                "passphrase": self.okx_passphrase,
            },
            "kucoin": {
                "api_key": self.kucoin_api_key,
                "api_secret": self.kucoin_api_secret,
                "passphrase": self.kucoin_passphrase,
            },
            "gateio": {
                "api_key": self.gateio_api_key,
                "api_secret": self.gateio_api_secret,
            },
            "alpaca": {
                "api_key": self.alpaca_api_key,
                "api_secret": self.alpaca_api_secret,
            },
        }

        if exchange not in credentials_map:
            raise ConfigurationError(
                f"Unknown exchange: {exchange}",
                details={
                    "exchange": exchange,
                    "supported_exchanges": list(credentials_map.keys())
                }
            )

        return credentials_map[exchange]

    def is_exchange_configured(self, exchange: str) -> bool:
        """
        Check if an exchange has API credentials configured.

        Args:
            exchange: Exchange name

        Returns:
            True if the exchange has API key configured, False otherwise
        """
        try:
            creds = self.get_exchange_credentials(exchange)
            # Check if api_key is not empty
            return bool(creds.get("api_key", "").strip())
        except ConfigurationError:
            return False

    def get_enabled_exchanges(self) -> list[str]:
        """
        Get list of exchanges that are both enabled in config AND have API keys.

        Returns:
            List of exchange names that are ready to use
        """
        enabled = []

        # Check crypto exchanges
        if self.crypto.enabled:
            for exchange in self.crypto.exchanges:
                if self.is_exchange_configured(exchange):
                    enabled.append(exchange)

        # Check US stocks provider
        if self.us_stocks.enabled and self.is_exchange_configured(self.us_stocks.provider):
            enabled.append(self.us_stocks.provider)

        return enabled

    def validate_all(self) -> list[str]:
        """
        Validate entire configuration and return warnings.

        This method performs comprehensive validation checks beyond
        field-level validation, checking logical consistency and
        completeness of the configuration.

        Returns:
            List of warning messages (empty list if all validations pass)
        """
        warnings = []

        # Check that at least one market is enabled
        markets_enabled = (
            self.crypto.enabled or
            self.us_stocks.enabled or
            self.bist.enabled
        )
        if not markets_enabled:
            warnings.append("No markets enabled (crypto, us_stocks, bist all disabled)")

        # Check paper trading settings
        if self.paper_trading.enabled:
            if self.paper_trading.max_single_trade_usd > self.paper_trading.initial_balance_usd:
                warnings.append(
                    f"max_single_trade_usd ({self.paper_trading.max_single_trade_usd}) "
                    f"exceeds initial_balance_usd ({self.paper_trading.initial_balance_usd})"
                )

            if self.paper_trading.max_daily_loss_usd > self.paper_trading.initial_balance_usd:
                warnings.append(
                    f"max_daily_loss_usd ({self.paper_trading.max_daily_loss_usd}) "
                    f"exceeds initial_balance_usd ({self.paper_trading.initial_balance_usd})"
                )

        # Check if any exchanges are configured
        enabled_exchanges = self.get_enabled_exchanges()
        if self.crypto.enabled and not any(ex in enabled_exchanges for ex in self.crypto.exchanges):
            warnings.append(
                "Crypto trading enabled but no crypto exchanges have API keys configured"
            )

        if self.us_stocks.enabled and self.us_stocks.provider not in enabled_exchanges:
            warnings.append(
                f"US stocks enabled but {self.us_stocks.provider} has no API keys configured"
            )

        # Check Telegram configuration
        if self.telegram.enabled:
            if not self.telegram_bot_token:
                warnings.append("Telegram enabled but TELEGRAM_BOT_TOKEN not set")
            if not self.telegram_chat_id:
                warnings.append("Telegram enabled but TELEGRAM_CHAT_ID not set")

        # Check database configuration
        if not self.database_url:
            warnings.append("DATABASE_URL not set")

        # Check Redis configuration
        if self.redis.enabled and not self.redis_url:
            warnings.append("Redis enabled but REDIS_URL not set")

        # Check news trading configuration
        if self.news_trading.enabled:
            news_sources_configured = (
                bool(self.news_api_key) or
                bool(self.cryptopanic_api_key) or
                bool(self.finnhub_api_key)
            )
            if not news_sources_configured:
                warnings.append(
                    "News trading enabled but no news API keys configured "
                    "(NEWS_API_KEY, CRYPTOPANIC_API_KEY, FINNHUB_API_KEY)"
                )

        # Check AI API key
        if not self.anthropic_api_key:
            warnings.append("ANTHROPIC_API_KEY not set")

        return warnings


@lru_cache()
def get_config(config_path: str | None = None) -> Config:
    """
    Get singleton Config instance.

    This function uses LRU cache to ensure only one Config instance
    is created and reused throughout the application lifecycle.

    Args:
        config_path: Optional path to config.yaml.
                    If None, looks for config/config.yaml

    Returns:
        Config instance loaded from YAML file or defaults

    Example:
        >>> config = get_config()
        >>> config = get_config("custom/path/config.yaml")
    """
    # Load environment variables from .env file
    load_dotenv()

    # Determine config file path
    if config_path is None:
        config_path = "config/config.yaml"

    config_file = Path(config_path)

    # Load from YAML if exists, otherwise use defaults
    if config_file.exists():
        logger.info(f"Loading configuration from {config_file}")
        config = Config.from_yaml(config_file)
    else:
        logger.warning(
            f"Configuration file not found at {config_file}, using defaults"
        )
        config = Config()

    # Run validation and log warnings
    warnings = config.validate_all()
    if warnings:
        logger.warning(
            f"Configuration validation warnings:\n" +
            "\n".join(f"  - {w}" for w in warnings)
        )

    return config


def reload_config(config_path: str | None = None) -> Config:
    """
    Force reload configuration (clears cache).

    This is useful for testing or when you need to reload
    configuration at runtime after changes.

    Args:
        config_path: Optional path to config.yaml

    Returns:
        Freshly loaded Config instance

    Example:
        >>> config = reload_config()
        >>> config = reload_config("custom/path/config.yaml")
    """
    # Clear the LRU cache to force reload
    get_config.cache_clear()
    return get_config(config_path)
