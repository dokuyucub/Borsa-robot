"""
Repository pattern for database operations.

This module provides repository classes for each model, implementing
common CRUD operations and specialized queries.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Generic, List, Optional, TypeVar

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger

from .models import (
    ArbitrageOpportunity,
    DailyReport,
    MarketType,
    NewsItem,
    OrderSide,
    OrderType,
    Portfolio,
    Position,
    PriceHistory,
    Signal,
    SignalAction,
    SignalType,
    Trade,
    TradeStatus,
)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations.

    Type parameter T represents the model class.
    """

    def __init__(self, session: AsyncSession, model: type[T]):
        """
        Initialize repository.

        Args:
            session: Async database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
        self.logger = get_logger(f"bdk.repository.{model.__tablename__}")

    async def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID."""
        result = await self.session.get(self.model, id)
        return result

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> T:
        """Create new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        instance = await self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            await self.session.flush()
            await self.session.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        instance = await self.get_by_id(id)
        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True
        return False

    async def count(self) -> int:
        """Count total entities."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0


# ==================== Specialized Repositories ====================


class PortfolioRepository(BaseRepository[Portfolio]):
    """Repository for Portfolio operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Portfolio)

    async def get_default(self) -> Portfolio:
        """
        Get or create default paper trading portfolio.

        Returns:
            Portfolio: Default portfolio
        """
        stmt = select(Portfolio).where(Portfolio.name == "paper_trading")
        result = await self.session.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if portfolio is None:
            # Create default portfolio
            from src.core.config import get_config

            config = get_config()
            initial_balance = Decimal(str(config.paper_trading.initial_balance_usd))

            portfolio = await self.create(
                name="paper_trading",
                initial_balance_usd=initial_balance,
                current_balance_usd=initial_balance,
                total_value_usd=initial_balance,
            )
            self.logger.info(
                "Created default portfolio",
                initial_balance=float(initial_balance),
            )

        return portfolio

    async def update_balance(
        self, portfolio_id: int, new_balance: Decimal
    ) -> Portfolio:
        """
        Update portfolio balance.

        Args:
            portfolio_id: Portfolio ID
            new_balance: New balance amount

        Returns:
            Portfolio: Updated portfolio
        """
        portfolio = await self.update(
            portfolio_id, current_balance_usd=new_balance
        )
        return portfolio

    async def update_stats(
        self, portfolio_id: int, pnl: Decimal, is_win: bool
    ) -> Portfolio:
        """
        Update portfolio statistics after trade.

        Args:
            portfolio_id: Portfolio ID
            pnl: Profit/loss amount
            is_win: Whether trade was profitable

        Returns:
            Portfolio: Updated portfolio
        """
        portfolio = await self.get_by_id(portfolio_id)
        if portfolio:
            portfolio.total_pnl_usd += pnl
            portfolio.total_trades += 1

            if is_win:
                portfolio.winning_trades += 1
            else:
                portfolio.losing_trades += 1

            # Calculate win rate
            if portfolio.total_trades > 0:
                portfolio.win_rate = Decimal(
                    (portfolio.winning_trades / portfolio.total_trades) * 100
                )

            # Calculate P&L percentage
            if portfolio.initial_balance_usd > 0:
                portfolio.total_pnl_percent = (
                    portfolio.total_pnl_usd / portfolio.initial_balance_usd
                ) * Decimal("100")

            await self.session.flush()
            await self.session.refresh(portfolio)

        return portfolio


class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Trade)

    async def create_trade(
        self,
        portfolio_id: int,
        market_type: MarketType,
        exchange: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Decimal,
        fee_usd: Decimal = Decimal("0"),
        signal_id: Optional[int] = None,
        position_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Trade:
        """
        Create a new trade.

        Args:
            portfolio_id: Portfolio ID
            market_type: Market type (crypto, us_stock, bist)
            exchange: Exchange name
            symbol: Trading symbol
            side: Order side (buy/sell)
            order_type: Order type
            quantity: Trade quantity
            price: Execution price
            fee_usd: Trading fee
            signal_id: Related signal ID
            position_id: Related position ID
            notes: Trade notes

        Returns:
            Trade: Created trade
        """
        # Generate trade ID
        now = datetime.utcnow()
        trade_id = f"TRD-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S%f')[:9]}"

        value_usd = quantity * price

        trade = await self.create(
            trade_id=trade_id,
            portfolio_id=portfolio_id,
            position_id=position_id,
            market_type=market_type,
            exchange=exchange,
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=TradeStatus.OPEN,
            quantity=quantity,
            price=price,
            value_usd=value_usd,
            fee_usd=fee_usd,
            signal_id=signal_id,
            notes=notes,
            executed_at=now,
        )

        self.logger.info(
            "Trade created",
            trade_id=trade_id,
            symbol=symbol,
            side=side.value,
            quantity=float(quantity),
            price=float(price),
        )

        return trade

    async def get_by_trade_id(self, trade_id: str) -> Optional[Trade]:
        """Get trade by trade ID."""
        stmt = select(Trade).where(Trade.trade_id == trade_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent(self, limit: int = 50) -> List[Trade]:
        """
        Get recent trades.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trades
        """
        stmt = (
            select(Trade)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbol(self, symbol: str, limit: int = 50) -> List[Trade]:
        """
        Get trades for a specific symbol.

        Args:
            symbol: Trading symbol
            limit: Maximum number of trades

        Returns:
            List of trades
        """
        stmt = (
            select(Trade)
            .where(Trade.symbol == symbol)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Trade]:
        """
        Get trades within date range.

        Args:
            start_date: Start datetime
            end_date: End datetime

        Returns:
            List of trades
        """
        stmt = (
            select(Trade)
            .where(
                and_(
                    Trade.executed_at >= start_date,
                    Trade.executed_at <= end_date,
                )
            )
            .order_by(Trade.executed_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_daily_summary(self, date: date) -> dict:
        """
        Get trade summary for a specific date.

        Args:
            date: Date to summarize

        Returns:
            Dictionary with summary statistics
        """
        start_datetime = datetime.combine(date, datetime.min.time())
        end_datetime = datetime.combine(date, datetime.max.time())

        stmt = select(Trade).where(
            and_(
                Trade.executed_at >= start_datetime,
                Trade.executed_at <= end_datetime,
            )
        )
        result = await self.session.execute(stmt)
        trades = list(result.scalars().all())

        total_trades = len(trades)
        total_volume = sum(float(t.value_usd) for t in trades)
        winning_trades = sum(1 for t in trades if t.pnl_usd and t.pnl_usd > 0)
        losing_trades = sum(1 for t in trades if t.pnl_usd and t.pnl_usd < 0)

        return {
            "date": date,
            "total_trades": total_trades,
            "total_volume_usd": total_volume,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (
                (winning_trades / total_trades * 100) if total_trades > 0 else 0
            ),
        }


class PositionRepository(BaseRepository[Position]):
    """Repository for Position operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Position)

    async def get_open_positions(self, portfolio_id: int) -> List[Position]:
        """
        Get all open positions for a portfolio.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            List of open positions
        """
        stmt = select(Position).where(Position.portfolio_id == portfolio_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbol(
        self, portfolio_id: int, symbol: str
    ) -> Optional[Position]:
        """
        Get position by symbol.

        Args:
            portfolio_id: Portfolio ID
            symbol: Trading symbol

        Returns:
            Position or None
        """
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def open_position(
        self,
        portfolio_id: int,
        market_type: MarketType,
        exchange: str,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        entry_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Position:
        """
        Open a new position.

        Args:
            portfolio_id: Portfolio ID
            market_type: Market type
            exchange: Exchange name
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Position size
            entry_price: Entry price
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price

        Returns:
            Position: Created position
        """
        position = await self.create(
            portfolio_id=portfolio_id,
            market_type=market_type,
            exchange=exchange,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
        )

        self.logger.info(
            "Position opened",
            symbol=symbol,
            side=side.value,
            quantity=float(quantity),
            entry_price=float(entry_price),
        )

        return position

    async def update_price(
        self, position_id: int, current_price: Decimal
    ) -> Position:
        """
        Update position with current market price.

        Args:
            position_id: Position ID
            current_price: Current market price

        Returns:
            Position: Updated position
        """
        position = await self.get_by_id(position_id)
        if position:
            position.current_price = current_price

            # Calculate unrealized P&L
            if position.side == OrderSide.BUY:
                pnl = (current_price - position.entry_price) * position.quantity
                pnl_percent = (
                    (current_price - position.entry_price) / position.entry_price
                ) * Decimal("100")
            else:  # SELL (short)
                pnl = (position.entry_price - current_price) * position.quantity
                pnl_percent = (
                    (position.entry_price - current_price) / position.entry_price
                ) * Decimal("100")

            position.unrealized_pnl_usd = pnl
            position.unrealized_pnl_percent = pnl_percent

            await self.session.flush()
            await self.session.refresh(position)

        return position

    async def close_position(self, position_id: int) -> Position:
        """
        Close a position.

        Args:
            position_id: Position ID

        Returns:
            Position: The closed position (before deletion)
        """
        position = await self.get_by_id(position_id)
        if position:
            self.logger.info(
                "Position closed",
                symbol=position.symbol,
                pnl_usd=float(position.unrealized_pnl_usd),
                pnl_percent=float(position.unrealized_pnl_percent),
            )
            # Note: In production, you might want to archive instead of delete
            await self.delete(position_id)

        return position


class SignalRepository(BaseRepository[Signal]):
    """Repository for Signal operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Signal)

    async def create_signal(
        self,
        signal_type: SignalType,
        market_type: MarketType,
        symbol: str,
        action: SignalAction,
        confidence_score: int,
        price_at_signal: Decimal,
        reasoning: str,
        source_data: dict,
        target_price: Optional[Decimal] = None,
        stop_loss_price: Optional[Decimal] = None,
        expected_profit_percent: Optional[Decimal] = None,
        expires_at: Optional[datetime] = None,
    ) -> Signal:
        """
        Create a new trading signal.

        Args:
            signal_type: Type of signal (arbitrage, news, etc.)
            market_type: Market type
            symbol: Trading symbol
            action: Signal action (buy/sell/hold)
            confidence_score: Confidence score (0-100)
            price_at_signal: Price when signal generated
            reasoning: Why signal was generated
            source_data: Raw data that generated signal
            target_price: Optional target price
            stop_loss_price: Optional stop loss price
            expected_profit_percent: Expected profit percentage
            expires_at: Signal expiration time

        Returns:
            Signal: Created signal
        """
        # Generate signal ID
        now = datetime.utcnow()
        signal_id = f"SIG-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S%f')[:9]}"

        signal = await self.create(
            signal_id=signal_id,
            signal_type=signal_type,
            market_type=market_type,
            symbol=symbol,
            action=action,
            confidence_score=confidence_score,
            price_at_signal=price_at_signal,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            expected_profit_percent=expected_profit_percent,
            reasoning=reasoning,
            source_data=source_data,
            expires_at=expires_at,
        )

        self.logger.info(
            "Signal created",
            signal_id=signal_id,
            signal_type=signal_type.value,
            symbol=symbol,
            action=action.value,
            confidence=confidence_score,
        )

        return signal

    async def get_pending_signals(self, min_confidence: int = 0) -> List[Signal]:
        """
        Get pending (not executed) signals.

        Args:
            min_confidence: Minimum confidence score

        Returns:
            List of pending signals
        """
        stmt = (
            select(Signal)
            .where(
                and_(
                    Signal.is_executed == False,
                    Signal.confidence_score >= min_confidence,
                    or_(
                        Signal.expires_at.is_(None),
                        Signal.expires_at > datetime.utcnow(),
                    ),
                )
            )
            .order_by(Signal.confidence_score.desc(), Signal.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_executed(self, signal_id: int, result: str) -> Signal:
        """
        Mark signal as executed.

        Args:
            signal_id: Signal ID
            result: Execution result

        Returns:
            Signal: Updated signal
        """
        signal = await self.update(
            signal_id, is_executed=True, execution_result=result
        )
        return signal

    async def get_by_symbol(
        self, symbol: str, signal_type: Optional[SignalType] = None
    ) -> List[Signal]:
        """
        Get signals for a symbol.

        Args:
            symbol: Trading symbol
            signal_type: Optional signal type filter

        Returns:
            List of signals
        """
        conditions = [Signal.symbol == symbol]
        if signal_type:
            conditions.append(Signal.signal_type == signal_type)

        stmt = (
            select(Signal)
            .where(and_(*conditions))
            .order_by(Signal.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ArbitrageRepository(BaseRepository[ArbitrageOpportunity]):
    """Repository for ArbitrageOpportunity operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ArbitrageOpportunity)

    async def record_opportunity(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: Decimal,
        sell_price: Decimal,
        spread_percent: Decimal,
        estimated_profit_usd: Decimal,
        net_profit_percent: Decimal,
    ) -> ArbitrageOpportunity:
        """
        Record a new arbitrage opportunity.

        Args:
            symbol: Trading symbol
            buy_exchange: Exchange to buy from
            sell_exchange: Exchange to sell to
            buy_price: Buy price
            sell_price: Sell price
            spread_percent: Price spread percentage
            estimated_profit_usd: Estimated profit in USD
            net_profit_percent: Net profit percentage after fees

        Returns:
            ArbitrageOpportunity: Created opportunity
        """
        opportunity = await self.create(
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_percent=spread_percent,
            estimated_profit_usd=estimated_profit_usd,
            net_profit_percent=net_profit_percent,
        )

        self.logger.info(
            "Arbitrage opportunity recorded",
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            spread_percent=float(spread_percent),
            profit_usd=float(estimated_profit_usd),
        )

        return opportunity

    async def get_recent_opportunities(
        self, symbol: Optional[str] = None, limit: int = 50
    ) -> List[ArbitrageOpportunity]:
        """
        Get recent arbitrage opportunities.

        Args:
            symbol: Optional symbol filter
            limit: Maximum number to return

        Returns:
            List of opportunities
        """
        stmt = select(ArbitrageOpportunity).order_by(
            ArbitrageOpportunity.detected_at.desc()
        )

        if symbol:
            stmt = stmt.where(ArbitrageOpportunity.symbol == symbol)

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_executed(
        self, opportunity_id: int, result: str
    ) -> ArbitrageOpportunity:
        """
        Mark opportunity as executed.

        Args:
            opportunity_id: Opportunity ID
            result: Execution result

        Returns:
            ArbitrageOpportunity: Updated opportunity
        """
        opportunity = await self.update(
            opportunity_id, is_executed=True, execution_result=result
        )
        return opportunity


class PriceHistoryRepository(BaseRepository[PriceHistory]):
    """Repository for PriceHistory operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PriceHistory)

    async def save_candle(
        self,
        market_type: MarketType,
        exchange: str,
        symbol: str,
        timestamp: datetime,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
    ) -> PriceHistory:
        """
        Save a single price candle.

        Args:
            market_type: Market type
            exchange: Exchange name
            symbol: Trading symbol
            timestamp: Candle timestamp
            open: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume

        Returns:
            PriceHistory: Created candle
        """
        candle = await self.create(
            market_type=market_type,
            exchange=exchange,
            symbol=symbol,
            timestamp=timestamp,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
        return candle

    async def save_candles_bulk(self, candles: List[dict]) -> int:
        """
        Bulk insert candles.

        Args:
            candles: List of candle dictionaries

        Returns:
            int: Number of candles inserted
        """
        if not candles:
            return 0

        instances = [PriceHistory(**candle) for candle in candles]
        self.session.add_all(instances)
        await self.session.flush()

        self.logger.debug(f"Bulk inserted {len(candles)} candles")
        return len(candles)

    async def get_candles(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[PriceHistory]:
        """
        Get candles within time range.

        Args:
            symbol: Trading symbol
            exchange: Exchange name
            start_time: Start datetime
            end_time: End datetime
            limit: Maximum candles to return

        Returns:
            List of price candles
        """
        stmt = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.symbol == symbol,
                    PriceHistory.exchange == exchange,
                    PriceHistory.timestamp >= start_time,
                    PriceHistory.timestamp <= end_time,
                )
            )
            .order_by(PriceHistory.timestamp.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_price(
        self, symbol: str, exchange: str
    ) -> Optional[PriceHistory]:
        """
        Get latest price for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange name

        Returns:
            PriceHistory or None
        """
        stmt = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.symbol == symbol,
                    PriceHistory.exchange == exchange,
                )
            )
            .order_by(PriceHistory.timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
