"""Core module for BDK Trading Bot."""

from src.core.config import Config, get_config, reload_config
from src.core.exceptions import (
    BDKException,
    ConfigurationError,
    DataFetchError,
    ExchangeError,
    InsufficientBalanceError,
    RiskLimitExceededError,
    StrategyError,
)
from src.core.logger import (
    LogContext,
    get_exchange_logger,
    get_logger,
    get_strategy_logger,
    get_trade_logger,
    log_exception,
    log_performance,
    log_startup_banner,
    log_trade,
    setup_logging,
)

__all__ = [
    # Configuration
    "Config",
    "get_config",
    "reload_config",
    # Exceptions
    "BDKException",
    "ConfigurationError",
    "DataFetchError",
    "ExchangeError",
    "InsufficientBalanceError",
    "RiskLimitExceededError",
    "StrategyError",
    # Logging
    "setup_logging",
    "get_logger",
    "get_trade_logger",
    "get_exchange_logger",
    "get_strategy_logger",
    "LogContext",
    "log_exception",
    "log_trade",
    "log_performance",
    "log_startup_banner",
]
