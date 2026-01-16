"""
Helper utility functions for BDK Trading Bot.

This module provides common utility functions used throughout the application
for formatting, time conversion, calculations, and more.
"""

import asyncio
import functools
from datetime import datetime, time
from typing import Any, Callable, Iterator, TypeVar

import pytz

# Type variable for generic list chunking
T = TypeVar('T')


def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """
    Format monetary amounts with appropriate currency symbols.

    Supports multiple currencies with their native formatting conventions.
    Turkish Lira uses comma as decimal separator and dot as thousands separator.

    Args:
        amount: The monetary amount to format
        currency: Currency code (USD, TRY, EUR, BTC, ETH)
        decimals: Number of decimal places (default: 2)

    Returns:
        Formatted currency string with symbol

    Examples:
        >>> format_currency(1234.56, "USD")
        '$1,234.56'
        >>> format_currency(1234.56, "TRY")
        '₺1.234,56'
        >>> format_currency(0.00123456, "BTC", 8)
        '₿0.00123456'
    """
    # Currency symbols mapping
    symbols = {
        "USD": "$",
        "TRY": "₺",
        "EUR": "€",
        "BTC": "₿",
        "ETH": "Ξ",
        "USDT": "$",
    }

    symbol = symbols.get(currency.upper(), currency)

    # Turkish Lira uses different formatting (1.234,56 instead of 1,234.56)
    if currency.upper() == "TRY":
        # Format with dots as thousands separator and comma as decimal
        formatted = f"{amount:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{symbol}{formatted}"

    # Standard formatting for other currencies
    formatted = f"{amount:,.{decimals}f}"
    return f"{symbol}{formatted}"


def format_percent(value: float, decimals: int = 2, with_sign: bool = True) -> str:
    """
    Format percentage values with optional sign prefix.

    Args:
        value: The percentage value to format (as a number, not decimal)
        decimals: Number of decimal places (default: 2)
        with_sign: Include +/- sign prefix (default: True)

    Returns:
        Formatted percentage string

    Examples:
        >>> format_percent(12.345)
        '+12.35%'
        >>> format_percent(-5.678, decimals=1)
        '-5.7%'
        >>> format_percent(3.14, with_sign=False)
        '3.14%'
    """
    formatted = f"{value:.{decimals}f}"

    if with_sign:
        if value > 0:
            return f"+{formatted}%"
        return f"{formatted}%"

    return f"{formatted}%"


def format_number(value: float, decimals: int = 2) -> str:
    """
    Format large numbers with K, M, B suffixes for readability.

    Args:
        value: The number to format
        decimals: Number of decimal places (default: 2)

    Returns:
        Formatted number string with appropriate suffix

    Examples:
        >>> format_number(1500)
        '1.50K'
        >>> format_number(2300000)
        '2.30M'
        >>> format_number(4500000000)
        '4.50B'
        >>> format_number(999)
        '999'
    """
    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.{decimals}f}B"
    elif abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.{decimals}f}M"
    elif abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.{decimals}f}K"
    else:
        return f"{sign}{abs_value:.{decimals}f}" if decimals > 0 else f"{sign}{int(abs_value)}"


def timestamp_to_datetime(timestamp_ms: int, tz: str = "Europe/Istanbul") -> datetime:
    """
    Convert millisecond timestamp to timezone-aware datetime object.

    Args:
        timestamp_ms: Unix timestamp in milliseconds
        tz: Target timezone name (default: Europe/Istanbul)

    Returns:
        Timezone-aware datetime object

    Examples:
        >>> dt = timestamp_to_datetime(1704067200000)  # 2024-01-01 00:00:00 UTC
        >>> dt.tzinfo.zone
        'Europe/Istanbul'
    """
    timezone = pytz.timezone(tz)
    dt_utc = datetime.fromtimestamp(timestamp_ms / 1000, tz=pytz.UTC)
    return dt_utc.astimezone(timezone)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime object to millisecond timestamp.

    Args:
        dt: Datetime object (can be naive or timezone-aware)

    Returns:
        Unix timestamp in milliseconds

    Examples:
        >>> dt = datetime(2024, 1, 1, tzinfo=pytz.UTC)
        >>> datetime_to_timestamp(dt)
        1704067200000
    """
    return int(dt.timestamp() * 1000)


def calculate_percent_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.

    Args:
        old_value: The original value
        new_value: The new value

    Returns:
        Percentage change (positive for increase, negative for decrease)

    Raises:
        ValueError: If old_value is zero

    Examples:
        >>> calculate_percent_change(100, 150)
        50.0
        >>> calculate_percent_change(200, 150)
        -25.0
    """
    if old_value == 0:
        raise ValueError("old_value cannot be zero")

    return ((new_value - old_value) / old_value) * 100


def round_price(price: float, tick_size: float = 0.01) -> float:
    """
    Round price to the nearest tick size.

    Used to ensure prices conform to exchange requirements.
    Different exchanges and symbols may have different tick sizes.

    Args:
        price: The price to round
        tick_size: The minimum price increment (default: 0.01)

    Returns:
        Price rounded to nearest tick size

    Examples:
        >>> round_price(123.456, 0.01)
        123.46
        >>> round_price(123.456, 0.5)
        123.5
        >>> round_price(123.456, 1.0)
        123.0
    """
    return round(price / tick_size) * tick_size


def chunks(lst: list[T], n: int) -> Iterator[list[T]]:
    """
    Split a list into chunks of specified size.

    Useful for batch processing of large lists.

    Args:
        lst: The list to split
        n: Size of each chunk

    Yields:
        Iterator of list chunks

    Examples:
        >>> list(chunks([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
        >>> list(chunks(['a', 'b', 'c', 'd'], 3))
        [['a', 'b', 'c'], ['d']]
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying async functions with exponential backoff.

    Automatically retries failed async operations with configurable
    delay and backoff strategy.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for delay after each attempt (default: 2.0)
        exceptions: Tuple of exception types to catch and retry (default: (Exception,))

    Returns:
        Decorated async function with retry logic

    Examples:
        >>> @retry_async(max_attempts=3, delay=1.0, backoff=2.0)
        ... async def fetch_data():
        ...     # Function that might fail
        ...     pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        raise

                    # Log retry attempt (will be replaced with proper logging later)
                    print(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay}s..."
                    )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached, but satisfy type checker
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def get_current_time(tz: str = "Europe/Istanbul") -> datetime:
    """
    Get current time in specified timezone.

    Args:
        tz: Timezone name (default: Europe/Istanbul)

    Returns:
        Current datetime in specified timezone

    Examples:
        >>> now = get_current_time()
        >>> now.tzinfo.zone
        'Europe/Istanbul'
        >>> now = get_current_time("America/New_York")
        >>> now.tzinfo.zone
        'America/New_York'
    """
    timezone = pytz.timezone(tz)
    return datetime.now(tz=timezone)


def is_market_open(market: str) -> bool:
    """
    Check if a specific market is currently open for trading.

    Market hours (in Istanbul time):
    - crypto: 24/7 (always open)
    - us: Monday-Friday, 16:30-23:00 (NYSE/NASDAQ hours)
    - bist: Monday-Friday, 10:00-18:00 (Borsa Istanbul hours)

    Args:
        market: Market type ('crypto', 'us', 'bist')

    Returns:
        True if market is open, False otherwise

    Examples:
        >>> is_market_open('crypto')
        True
        >>> # Returns True/False based on current time for 'us' or 'bist'
    """
    market = market.lower()

    # Crypto markets are always open (24/7)
    if market == "crypto":
        return True

    # Get current time in Istanbul timezone
    now = get_current_time("Europe/Istanbul")
    current_time = now.time()
    is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4

    # US market hours (NYSE/NASDAQ in Istanbul time)
    if market == "us":
        if not is_weekday:
            return False
        market_open = time(16, 30)  # 9:30 AM ET = 4:30 PM Istanbul
        market_close = time(23, 0)   # 4:00 PM ET = 11:00 PM Istanbul
        return market_open <= current_time <= market_close

    # BIST (Borsa Istanbul) hours
    if market == "bist":
        if not is_weekday:
            return False
        market_open = time(10, 0)   # 10:00 AM Istanbul
        market_close = time(18, 0)   # 6:00 PM Istanbul
        return market_open <= current_time <= market_close

    # Unknown market type
    return False
