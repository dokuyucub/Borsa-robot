"""
Logging system for BDK Trading Bot.

This module provides structured logging using structlog with both console
and file output, supporting JSON and pretty formats.

Example Usage:
    >>> from src.core.logger import setup_logging, get_logger
    >>>
    >>> # Setup logging system
    >>> setup_logging(level="INFO", log_format="pretty")
    >>>
    >>> # Get logger
    >>> logger = get_logger("bdk.strategies")
    >>> logger.info("Strategy started", pairs=["BTC/USDT", "ETH/USDT"])
    >>>
    >>> # Use context manager
    >>> with LogContext(trade_id="TRD-001"):
    >>>     logger.info("Processing trade")
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Optional

import structlog
from datetime import datetime

# Constants
LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = LOG_DIR / "bdk.log"
TRADE_LOG_FILE = LOG_DIR / "trades.log"
ERROR_LOG_FILE = LOG_DIR / "errors.log"


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: str | Path | None = None,
    file_enabled: bool = True,
    max_file_size_mb: int = 100,
    backup_count: int = 5,
    console_enabled: bool = True,
) -> None:
    """
    Initialize the logging system for BDK Trading Bot.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "pretty")
        log_file: Path to main log file (default: logs/bdk.log)
        file_enabled: Enable file logging
        max_file_size_mb: Max size per log file before rotation
        backup_count: Number of backup files to keep
        console_enabled: Enable console output

    Example:
        >>> setup_logging(level="DEBUG", log_format="pretty")
    """
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(exist_ok=True)

    # Set log file path
    if log_file is None:
        log_file = DEFAULT_LOG_FILE
    else:
        log_file = Path(log_file)

    # Convert level string to logging level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure structlog processors based on format
    if log_format == "json":
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.ExtraAdder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
        )
    else:  # pretty format
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.ExtraAdder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
        )

    # Configure structlog to use stdlib
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if file_enabled:
        max_bytes = max_file_size_mb * 1024 * 1024
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Error file handler (only ERROR and above)
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

        # Trade file handler
        trade_handler = logging.handlers.RotatingFileHandler(
            TRADE_LOG_FILE,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        trade_handler.setLevel(logging.INFO)
        trade_handler.setFormatter(formatter)
        trade_logger = logging.getLogger("bdk.trades")
        trade_logger.addHandler(trade_handler)

    # Set third-party loggers to WARNING to reduce noise
    third_party_loggers = [
        "ccxt",
        "urllib3",
        "asyncio",
        "websockets",
        "httpx",
        "telegram",
    ]
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str = "bdk") -> structlog.BoundLogger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (e.g., "bdk.exchanges.binance")

    Returns:
        Configured structlog BoundLogger

    Example:
        >>> logger = get_logger("bdk.strategies.arbitrage")
        >>> logger.info("Strategy started", pairs=["BTC/USDT", "ETH/USDT"])
    """
    return structlog.get_logger(name)


def get_trade_logger() -> structlog.BoundLogger:
    """
    Get a logger specifically for trade operations.
    Logs to both main log and trades.log

    Returns:
        Logger configured for trade logging

    Example:
        >>> trade_logger = get_trade_logger()
        >>> trade_logger.info(
        ...     "Trade executed",
        ...     trade_id="TRD-001",
        ...     symbol="BTC/USDT",
        ...     side="buy",
        ...     amount=0.1,
        ...     price=42000.0
        ... )
    """
    return structlog.get_logger("bdk.trades")


def get_exchange_logger(exchange: str) -> structlog.BoundLogger:
    """
    Get a logger for a specific exchange.

    Args:
        exchange: Exchange name (binance, bybit, etc.)

    Returns:
        Logger bound with exchange context

    Example:
        >>> logger = get_exchange_logger("binance")
        >>> logger.info("Connected to exchange")
    """
    return structlog.get_logger(f"bdk.exchanges.{exchange}").bind(exchange=exchange)


def get_strategy_logger(strategy: str) -> structlog.BoundLogger:
    """
    Get a logger for a specific strategy.

    Args:
        strategy: Strategy name (arbitrage, news_trading, etc.)

    Returns:
        Logger bound with strategy context

    Example:
        >>> logger = get_strategy_logger("arbitrage")
        >>> logger.info("Opportunity found", profit_percent=0.25)
    """
    return structlog.get_logger(f"bdk.strategies.{strategy}").bind(strategy=strategy)


class LogContext:
    """
    Context manager for adding temporary context to logs.

    Example:
        >>> with LogContext(trade_id="TRD-001", symbol="BTC/USDT"):
        ...     logger.info("Processing trade")  # Includes trade_id and symbol
        >>> logger.info("Outside context")  # No trade_id or symbol
    """

    def __init__(self, **kwargs: Any):
        """
        Initialize LogContext.

        Args:
            **kwargs: Context key-value pairs to add to logs
        """
        self.context = kwargs
        self.token = None

    def __enter__(self) -> "LogContext":
        """Enter context and bind variables."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and unbind variables."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_exception(
    logger: structlog.BoundLogger,
    exc: Exception,
    message: str = "An error occurred",
    **extra: Any,
) -> None:
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance
        exc: Exception to log
        message: Error message
        **extra: Additional context

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, e, "Operation failed", operation="fetch_price")
    """
    logger.exception(
        message,
        error_type=type(exc).__name__,
        error_message=str(exc),
        **extra,
    )


def log_trade(
    action: str,
    symbol: str,
    side: str,
    amount: float,
    price: float,
    **extra: Any,
) -> None:
    """
    Convenience function to log trade operations.

    Args:
        action: Trade action (open, close, cancel)
        symbol: Trading pair
        side: buy or sell
        amount: Trade amount
        price: Trade price
        **extra: Additional context (trade_id, exchange, pnl, etc.)

    Example:
        >>> log_trade(
        ...     action="open",
        ...     symbol="BTC/USDT",
        ...     side="buy",
        ...     amount=0.1,
        ...     price=42000.0,
        ...     exchange="binance",
        ...     trade_id="TRD-001"
        ... )
    """
    trade_logger = get_trade_logger()
    trade_logger.info(
        f"Trade {action}",
        action=action,
        symbol=symbol,
        side=side,
        amount=amount,
        price=price,
        value=amount * price,
        **extra,
    )


def log_performance(
    logger: structlog.BoundLogger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **extra: Any,
) -> None:
    """
    Log performance metrics for operations.

    Args:
        logger: Logger instance
        operation: Name of operation
        duration_ms: Duration in milliseconds
        success: Whether operation succeeded
        **extra: Additional metrics

    Example:
        >>> import time
        >>> start = time.time()
        >>> result = fetch_prices()
        >>> duration = (time.time() - start) * 1000
        >>> log_performance(logger, "fetch_prices", duration, count=len(result))
    """
    logger.info(
        f"Performance: {operation}",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        success=success,
        **extra,
    )


def log_startup_banner(version: str, environment: str, paper_trading: bool) -> None:
    """
    Log a startup banner with bot information.

    Args:
        version: Bot version
        environment: Running environment (development, production)
        paper_trading: Whether paper trading is enabled
    """
    logger = get_logger("bdk.main")

    logger.info("=" * 50)
    logger.info("🚀 BDK Trading Bot Starting")
    logger.info("=" * 50)
    logger.info(f"Version: {version}")
    logger.info(f"Environment: {environment}")
    logger.info(f"Paper Trading: {'✅ Enabled' if paper_trading else '❌ Disabled'}")
    logger.info("=" * 50)
