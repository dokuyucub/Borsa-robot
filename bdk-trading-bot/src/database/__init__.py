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
]
