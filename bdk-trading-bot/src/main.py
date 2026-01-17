"""
BDK Trading Bot - Main Entry Point

AI-Powered Paper Trading Bot for Crypto, US Stocks & BIST
"""

from src import __version__
from src.core import get_config, get_logger, log_startup_banner, setup_logging


def main() -> None:
    """Main entry point for BDK Trading Bot."""
    # Load configuration
    config = get_config()

    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_format=config.logging.format,
        file_enabled=config.logging.file_enabled,
        max_file_size_mb=config.logging.max_file_size_mb,
        backup_count=config.logging.backup_count,
    )

    # Get logger
    logger = get_logger("bdk.main")

    # Log startup banner
    log_startup_banner(
        version=__version__,
        environment=config.general.environment,
        paper_trading=config.paper_trading.enabled,
    )

    # Log configuration summary
    logger.info(
        "Configuration loaded",
        crypto_enabled=config.crypto.enabled,
        us_stocks_enabled=config.us_stocks.enabled,
        bist_enabled=config.bist.enabled,
        exchanges=config.crypto.exchanges if config.crypto.enabled else [],
        initial_balance=config.paper_trading.initial_balance_usd,
    )

    # Validate configuration
    warnings = config.validate_all()
    for warning in warnings:
        logger.warning(warning)

    logger.info("⏳ Bot initialization not yet implemented...")
    logger.info(
        "📊 Paper Trading Mode: ${:,.2f} virtual balance".format(
            config.paper_trading.initial_balance_usd
        )
    )


if __name__ == "__main__":
    main()
