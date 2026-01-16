"""
Core exception classes for BDK Trading Bot.

This module defines custom exceptions used throughout the application
for better error handling and debugging.
"""

from typing import Any


class BDKException(Exception):
    """
    Base exception class for all BDK Trading Bot exceptions.

    All custom exceptions should inherit from this class to provide
    consistent error handling and logging capabilities.

    Attributes:
        message: Human-readable error message
        details: Additional context about the error as a dictionary
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize the BDK exception.

        Args:
            message: Error message describing what went wrong
            details: Optional dictionary containing additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(BDKException):
    """
    Exception raised for configuration-related errors.

    This exception is raised when there are issues with loading,
    parsing, or validating configuration files or environment variables.

    Examples:
        - Missing required configuration keys
        - Invalid configuration values
        - Unable to load configuration files
    """
    pass


class ExchangeError(BDKException):
    """
    Exception raised for exchange-related errors.

    This exception is raised when there are issues communicating with
    cryptocurrency or stock exchanges.

    Attributes:
        exchange: Name of the exchange that caused the error
    """

    def __init__(
        self,
        message: str,
        exchange: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the exchange error.

        Args:
            message: Error message describing what went wrong
            exchange: Name of the exchange (e.g., 'binance', 'alpaca')
            details: Optional dictionary containing additional error context
        """
        self.exchange = exchange
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        base_msg = f"[{self.exchange}] {self.message}"
        if self.details:
            return f"{base_msg} | Details: {self.details}"
        return base_msg


class InsufficientBalanceError(BDKException):
    """
    Exception raised when attempting to trade with insufficient balance.

    This exception is raised when a trade cannot be executed because
    the account balance is insufficient for the requested operation.

    Attributes:
        required: Amount required for the operation
        available: Currently available balance
        currency: Currency or asset symbol (e.g., 'USD', 'BTC')
    """

    def __init__(
        self,
        message: str,
        required: float,
        available: float,
        currency: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the insufficient balance error.

        Args:
            message: Error message describing what went wrong
            required: Amount required for the operation
            available: Currently available balance
            currency: Currency or asset symbol
            details: Optional dictionary containing additional error context
        """
        self.required = required
        self.available = available
        self.currency = currency
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return (
            f"{self.message} | Required: {self.required} {self.currency}, "
            f"Available: {self.available} {self.currency}"
        )


class RiskLimitExceededError(BDKException):
    """
    Exception raised when a trading operation exceeds risk management limits.

    This exception is raised when a trade or operation would violate
    configured risk management rules (e.g., max position size, daily loss limit).

    Attributes:
        limit_type: Type of limit that was exceeded (e.g., 'max_single_trade', 'daily_loss')
        limit_value: The configured limit value
        attempted_value: The value that was attempted which exceeded the limit
    """

    def __init__(
        self,
        message: str,
        limit_type: str,
        limit_value: float,
        attempted_value: float,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the risk limit exceeded error.

        Args:
            message: Error message describing what went wrong
            limit_type: Type of limit that was exceeded
            limit_value: The configured limit value
            attempted_value: The value that was attempted
            details: Optional dictionary containing additional error context
        """
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.attempted_value = attempted_value
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return (
            f"{self.message} | Limit Type: {self.limit_type}, "
            f"Limit: {self.limit_value}, Attempted: {self.attempted_value}"
        )


class DataFetchError(BDKException):
    """
    Exception raised when data fetching operations fail.

    This exception is raised when there are issues retrieving data from
    external sources like exchanges, news APIs, or data providers.

    Attributes:
        source: Name of the data source that failed (e.g., 'binance', 'newsapi')
    """

    def __init__(
        self,
        message: str,
        source: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the data fetch error.

        Args:
            message: Error message describing what went wrong
            source: Name of the data source
            details: Optional dictionary containing additional error context
        """
        self.source = source
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        base_msg = f"[{self.source}] {self.message}"
        if self.details:
            return f"{base_msg} | Details: {self.details}"
        return base_msg


class StrategyError(BDKException):
    """
    Exception raised when trading strategy execution fails.

    This exception is raised when there are issues with strategy
    initialization, execution, or signal generation.

    Attributes:
        strategy: Name of the strategy that caused the error
    """

    def __init__(
        self,
        message: str,
        strategy: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the strategy error.

        Args:
            message: Error message describing what went wrong
            strategy: Name of the strategy
            details: Optional dictionary containing additional error context
        """
        self.strategy = strategy
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        base_msg = f"[Strategy: {self.strategy}] {self.message}"
        if self.details:
            return f"{base_msg} | Details: {self.details}"
        return base_msg
