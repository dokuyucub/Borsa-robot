"""
Database models for BDK Trading Bot.

This module defines all SQLAlchemy ORM models for storing trading data,
including portfolios, positions, trades, signals, and market data.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# ==================== Enums ====================


class MarketType(str, Enum):
    """Market type enumeration."""

    CRYPTO = "crypto"
    US_STOCK = "us_stock"
    BIST = "bist"


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class TradeStatus(str, Enum):
    """Trade status enumeration."""

    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class SignalType(str, Enum):
    """Signal type enumeration."""

    ARBITRAGE = "arbitrage"
    NEWS = "news"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"


class SignalAction(str, Enum):
    """Signal action enumeration."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


# ==================== Models ====================


class Portfolio(Base):
    """
    Tracks overall portfolio state and balance.
    Typically single row for paper trading portfolio.
    """

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="paper_trading")
    initial_balance_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    current_balance_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    total_pnl_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0")
    )
    total_pnl_percent: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0")
    )
    total_trades: Mapped[int] = mapped_column(default=0)
    winning_trades: Mapped[int] = mapped_column(default=0)
    losing_trades: Mapped[int] = mapped_column(default=0)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    positions: Mapped[List["Position"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[List["Trade"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    daily_reports: Mapped[List["DailyReport"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Position(Base):
    """
    Tracks open positions in any market.
    """

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    market_type: Mapped[MarketType]
    exchange: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(50))
    side: Mapped[OrderSide]
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    current_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    unrealized_pnl_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0")
    )
    unrealized_pnl_percent: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0")
    )
    stop_loss_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    take_profit_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), server_default=func.now()
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="positions")
    trades: Mapped[List["Trade"]] = relationship(back_populates="position")

    # Indexes
    __table_args__ = (
        Index("idx_positions_symbol", "symbol"),
        Index("idx_positions_market_exchange", "market_type", "exchange"),
    )


class Trade(Base):
    """
    Records all trade executions (paper trades).
    """

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[str] = mapped_column(String(50), unique=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("positions.id"), nullable=True
    )
    market_type: Mapped[MarketType]
    exchange: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(50))
    side: Mapped[OrderSide]
    order_type: Mapped[OrderType]
    status: Mapped[TradeStatus]
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    value_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    fee_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0"))
    pnl_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    pnl_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    signal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("signals.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="trades")
    position: Mapped[Optional["Position"]] = relationship(back_populates="trades")
    signal: Mapped[Optional["Signal"]] = relationship(back_populates="trades")

    # Indexes
    __table_args__ = (
        Index("idx_trades_trade_id", "trade_id", unique=True),
        Index("idx_trades_symbol", "symbol"),
        Index("idx_trades_executed_at", "executed_at"),
        Index("idx_trades_market_exchange", "market_type", "exchange"),
    )


class Signal(Base):
    """
    Records trading signals generated by strategies.
    """

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(50), unique=True)
    signal_type: Mapped[SignalType]
    market_type: Mapped[MarketType]
    symbol: Mapped[str] = mapped_column(String(50))
    action: Mapped[SignalAction]
    confidence_score: Mapped[int]
    price_at_signal: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    target_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    stop_loss_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    expected_profit_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    reasoning: Mapped[str] = mapped_column(String(1000))
    source_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_executed: Mapped[bool] = mapped_column(default=False)
    execution_result: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    trades: Mapped[List["Trade"]] = relationship(back_populates="signal")

    # Indexes
    __table_args__ = (
        Index("idx_signals_signal_id", "signal_id", unique=True),
        Index("idx_signals_symbol", "symbol"),
        Index("idx_signals_type_action", "signal_type", "action"),
        Index("idx_signals_created_at", "created_at"),
    )


class PriceHistory(Base):
    """
    Stores historical price data for analysis.
    TimescaleDB hypertable candidate.
    """

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_type: Mapped[MarketType]
    exchange: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime]
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    quote_volume: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    trades_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Indexes and constraints
    __table_args__ = (
        Index("idx_price_history_symbol_timestamp", "symbol", "timestamp"),
        Index("idx_price_history_market_exchange", "market_type", "exchange"),
        UniqueConstraint(
            "exchange", "symbol", "timestamp", name="uq_price_history"
        ),
    )


class ArbitrageOpportunity(Base):
    """
    Records detected arbitrage opportunities.
    """

    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(50))
    buy_exchange: Mapped[str] = mapped_column(String(50))
    sell_exchange: Mapped[str] = mapped_column(String(50))
    buy_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    sell_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    spread_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    estimated_profit_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    net_profit_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    is_executed: Mapped[bool] = mapped_column(default=False)
    execution_result: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Indexes
    __table_args__ = (
        Index("idx_arbitrage_symbol", "symbol"),
        Index("idx_arbitrage_detected_at", "detected_at"),
    )


class NewsItem(Base):
    """
    Stores news articles and their analysis.
    """

    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[Optional[str]] = mapped_column(nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    published_at: Mapped[datetime]
    symbols: Mapped[list] = mapped_column(JSONB, default=list)
    sentiment_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    impact_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_processed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Indexes
    __table_args__ = (
        Index("idx_news_source_external", "source", "external_id"),
        Index("idx_news_published_at", "published_at"),
        Index("idx_news_sentiment", "sentiment_score"),
    )


class DailyReport(Base):
    """
    Stores daily performance reports.
    """

    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    report_date: Mapped[date]
    starting_balance_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    ending_balance_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    daily_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    daily_pnl_percent: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    total_trades: Mapped[int] = mapped_column(default=0)
    winning_trades: Mapped[int] = mapped_column(default=0)
    losing_trades: Mapped[int] = mapped_column(default=0)
    largest_win_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    largest_loss_usd: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    arbitrage_opportunities: Mapped[int] = mapped_column(default=0)
    arbitrage_executed: Mapped[int] = mapped_column(default=0)
    news_signals: Mapped[int] = mapped_column(default=0)
    report_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="daily_reports")

    # Indexes
    __table_args__ = (
        Index("idx_daily_reports_date", "portfolio_id", "report_date", unique=True),
    )


class BotSettings(Base):
    """
    Stores runtime bot settings (can be changed without restart).
    """

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(String(1000))
    value_type: Mapped[str] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    # Indexes
    __table_args__ = (Index("idx_bot_settings_key", "key", unique=True),)
