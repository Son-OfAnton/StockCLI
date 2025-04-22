"""
CLI commands for the stock application.
"""

import csv
import json
import click
import time
import threading
import logging
from typing import List, Optional, Union
from datetime import date, datetime, timedelta
from pathlib import Path

from app.api.twelve_data import TwelveDataAPIError, client
# from app.main import cli
# from app.main import analysts_group
from app.models.bond import Bond
from app.models.commodity import CommodityGroup, CommodityPair
from app.models.etf import ETF
from app.models.stock import Quote
from app.models.symbol import Symbol
from app.utils.display import create_progress_spinner, display_bonds, display_bonds_detailed, display_commodity_groups, display_commodity_pairs, display_commodity_pairs_detailed, display_company_profile, display_cross_listed_symbols, display_eod_price, display_etfs, display_etfs_detailed, display_fund_families, display_fund_family_detail, display_funds_table, display_market_movers, display_mutual_fund_profile, display_mutual_fund_type_detail, display_mutual_fund_types, display_mutual_funds_detailed
from app.utils.helpers import (
    display_quotes_table, clear_screen
)
from app.utils.export import (
    ensure_directory, export_dividend_calendar, export_dividend_comparison, export_dividend_history, export_quotes, export_splits_calendar, export_stock_splits, export_stock_splits_comparison, get_default_export_dir, get_home_export_dir
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_cli.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Shared state for tracking refresh thread
_refresh_thread = None
_stop_refresh = threading.Event()
_last_quotes = []  # Store the last fetched quotes for export


@click.group()
def stock():
    """Commands for interacting with stock data."""
    pass


@stock.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option("--refresh", "-r", is_flag=True, help="Enable auto-refresh of quotes")
@click.option("--interval", "-i", default=10, help="Refresh interval in seconds (default: 10)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed quote information")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export quotes to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files (default: project's exports directory)")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def quote(symbols: List[str], refresh: bool, interval: int, detailed: bool, debug: bool,
          export: Optional[str], output_dir: Optional[str], use_home_dir: bool):
    """Get current stock quotes for one or more SYMBOLS.

    Examples:
    \b
    # Get a single quote
    stockcli stock quote AAPL

    # Get multiple quotes
    stockcli stock quote AAPL MSFT GOOG

    # Get quotes with auto-refresh every 5 seconds
    stockcli stock quote AAPL MSFT --refresh --interval 5

    # Get detailed quotes
    stockcli stock quote AAPL MSFT --detailed

    # Export quotes to JSON (saves to project's exports directory by default)
    stockcli stock quote AAPL MSFT --export json

    # Export quotes to both JSON and CSV to a specific directory
    stockcli stock quote AAPL MSFT --export both --output-dir ~/stock_data

    # Export quotes to user's home directory
    stockcli stock quote AAPL MSFT --export both --use-home-dir
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    logger.info(
        f"Quote command called with symbols: {symbols}, refresh: {refresh}, interval: {interval}")

    if interval < 1:
        raise click.BadParameter("Interval must be at least 1 second")

    symbols = [s.upper() for s in symbols]

    # Process export format
    export_formats = []
    if export == 'json':
        export_formats = ['json']
    elif export == 'csv':
        export_formats = ['csv']
    elif export == 'both':
        export_formats = ['json', 'csv']

    # Handle output directory
    export_output_dir = None
    if output_dir:
        # If a custom output directory is provided, use it
        export_output_dir = Path(output_dir).expanduser().resolve()
        logger.debug(f"Using custom export directory: {export_output_dir}")
    elif use_home_dir:
        # If --use-home-dir flag is set, use home directory
        export_output_dir = get_home_export_dir()
        logger.debug(f"Using home directory for exports: {export_output_dir}")
    else:
        # Otherwise, use the default (project) directory
        export_output_dir = get_default_export_dir()
        logger.debug(
            f"Using default project export directory: {export_output_dir}")

    if refresh:
        # Start auto-refresh in background thread
        refresh_quotes(symbols, interval, detailed, debug,
                       export_formats, export_output_dir)
    else:
        # Fetch quotes once
        quotes = fetch_and_display_quotes(symbols, detailed, debug)

        # Export if requested and quotes were fetched successfully
        if export and quotes:
            export_results = export_quotes(
                quotes, export_formats, export_output_dir)

            if export_results:
                click.echo("\nExported quotes to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")


@stock.command()
def stop():
    """Stop any running auto-refresh processes."""
    global _refresh_thread, _stop_refresh

    if _refresh_thread and _refresh_thread.is_alive():
        _stop_refresh.set()
        _refresh_thread.join(timeout=1.0)
        click.echo("Quote refresh stopped.")
    else:
        click.echo("No active quote refresh to stop.")


@stock.command()
@click.option("--format", "-f", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              default='both', help="Export format (default: both)")
@click.option("--output-dir", "-o", type=click.Path(file_okay=False),
              help="Directory to save exported files (default: project's exports directory)")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def export_last(format: str, output_dir: Optional[str], use_home_dir: bool):
    """Export the most recently fetched quotes.

    Examples:
    \b
    # Export last quotes to default formats (JSON and CSV)
    stockcli stock export-last

    # Export last quotes to JSON only
    stockcli stock export-last --format json

    # Export to a specific directory
    stockcli stock export-last --output-dir ~/stock_data

    # Export to user's home directory
    stockcli stock export-last --use-home-dir
    """
    global _last_quotes

    if not _last_quotes:
        click.echo(
            "No quotes available to export. Fetch quotes first using 'quote' command.")
        return

    # Process export format
    export_formats = []
    if format == 'json':
        export_formats = ['json']
    elif format == 'csv':
        export_formats = ['csv']
    elif format == 'both':
        export_formats = ['json', 'csv']

    # Handle output directory
    export_output_dir = None
    if output_dir:
        # If a custom output directory is provided, use it
        export_output_dir = Path(output_dir).expanduser().resolve()
        logger.debug(f"Using custom export directory: {export_output_dir}")
    elif use_home_dir:
        # If --use-home-dir flag is set, use home directory
        export_output_dir = get_home_export_dir()
        logger.debug(f"Using home directory for exports: {export_output_dir}")
    else:
        # Otherwise, use the default (project) directory
        export_output_dir = get_default_export_dir()
        logger.debug(
            f"Using default project export directory: {export_output_dir}")

    # Export the quotes
    export_results = export_quotes(
        _last_quotes, export_formats, export_output_dir)

    if export_results:
        click.echo("Exported quotes to:")
        for fmt, path in export_results.items():
            click.echo(f"  {fmt.upper()}: {path}")
    else:
        click.echo("Failed to export quotes. Check logs for details.")


def fetch_and_display_quotes(symbols: List[str], detailed: bool = False, debug: bool = False) -> List[Quote]:
    """Fetch and display quotes for the given symbols."""
    global _last_quotes

    try:
        # Get quotes for all symbols
        if debug:
            click.echo(f"Fetching quotes for: {symbols}")

        response = client.get_quotes(symbols)

        if debug:
            click.echo(f"API response: {response}")

        # Handle both single and multiple quote responses
        quotes = []
        if isinstance(response, dict):
            if 'symbol' in response:
                # Single quote response
                quotes = [Quote.from_api_response(response)]
            elif 'status' in response and response.get('status') == 'error':
                # API returned an error
                click.echo(
                    f"API Error: {response.get('message', 'Unknown error')}")
                logger.error(f"API Error: {response}")
                return []
            else:
                # Response might be a dictionary of quotes
                for symbol, quote_data in response.items():
                    if isinstance(quote_data, dict) and 'symbol' in quote_data:
                        try:
                            quotes.append(Quote.from_api_response(quote_data))
                        except Exception as e:
                            logger.error(
                                f"Error parsing quote for {symbol}: {e}")
                            if debug:
                                click.echo(
                                    f"Error parsing quote for {symbol}: {e}")
        elif isinstance(response, list):
            # Multiple quotes response
            for item in response:
                try:
                    quotes.append(Quote.from_api_response(item))
                except Exception as e:
                    if 'symbol' in item:
                        symbol = item['symbol']
                    else:
                        symbol = "unknown"
                    logger.error(f"Error parsing quote for {symbol}: {e}")
                    if debug:
                        click.echo(f"Error parsing quote for {symbol}: {e}")

        if not quotes:
            click.echo(
                f"No valid quotes found for symbols: {', '.join(symbols)}")
            if debug:
                click.echo(
                    "Please check if the API key is valid and the symbols are correct")
            return []

        # Display the quotes
        display_quotes_table(quotes, detailed)

        # Store the quotes for later export
        _last_quotes = quotes

        return quotes

    except Exception as e:
        logger.error(f"Error fetching quotes: {e}", exc_info=True)
        click.echo(f"Error fetching quotes: {e}")
        if debug:
            import traceback
            click.echo(traceback.format_exc())
        return []


def refresh_quotes(symbols: List[str], interval: int, detailed: bool, debug: bool = False,
                   export_formats: List[str] = None, output_dir: Optional[Union[str, Path]] = None) -> None:
    """Start a background thread to refresh quotes periodically."""
    global _refresh_thread, _stop_refresh

    # Stop any existing refresh thread
    if _refresh_thread and _refresh_thread.is_alive():
        _stop_refresh.set()
        _refresh_thread.join(timeout=1.0)

    # Reset the stop event
    _stop_refresh = threading.Event()

    # Create and start the new refresh thread
    _refresh_thread = threading.Thread(
        target=_refresh_worker,
        args=(symbols, interval, detailed, debug, export_formats, output_dir),
        daemon=True
    )
    _refresh_thread.start()

    click.echo(
        f"Auto-refresh started for {', '.join(symbols)} every {interval} seconds.")
    if export_formats:
        click.echo(f"Auto-exporting to: {', '.join(export_formats)}")
        click.echo(f"Export directory: {output_dir}")
    click.echo("Press Ctrl+C to stop, or run 'stockcli stock stop'")


def _refresh_worker(symbols: List[str], interval: int, detailed: bool, debug: bool = False,
                    export_formats: List[str] = None, output_dir: Optional[Union[str, Path]] = None) -> None:
    """Worker function for the refresh thread."""
    try:
        while not _stop_refresh.is_set():
            clear_screen()
            click.echo(
                f"Auto-refreshing quotes for {', '.join(symbols)} every {interval} seconds.")
            click.echo(
                f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if export_formats:
                click.echo(f"Auto-exporting to: {', '.join(export_formats)}")
                click.echo(f"Export directory: {output_dir}")
            click.echo("Press Ctrl+C to stop")
            click.echo()

            # Fetch and display the quotes
            quotes = fetch_and_display_quotes(symbols, detailed, debug)

            # Export if requested and quotes were fetched
            if export_formats and quotes:
                export_results = export_quotes(
                    quotes, export_formats, output_dir)
                if export_results:
                    click.echo("\nExported to:")
                    for fmt, path in export_results.items():
                        click.echo(f"  {fmt.upper()}: {path}")

            # Sleep until next refresh or until stopped
            _stop_refresh.wait(interval)
    except Exception as e:
        logger.error(f"Error in refresh thread: {e}")
        if debug:
            click.echo(f"Error in refresh thread: {e}")
            import traceback
            click.echo(traceback.format_exc())


@stock.command()
@click.argument("symbol")
@click.option("--interval", "-i", default="1day", help="Time interval between data points")
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
def history(symbol, interval, start, end):
    """Get historical price data for SYMBOL."""
    click.echo(f"Fetching historical data for {symbol} (Not yet implemented)")


@stock.command()
@click.argument("symbol")
@click.argument("indicator")
@click.option("--period", "-p", default=14, help="Period for the indicator calculation")
def indicator(symbol, indicator, period):
    """Calculate technical indicator for SYMBOL."""
    click.echo(f"Calculating {indicator} for {symbol} (Not yet implemented)")


@stock.group()
def symbols():
    """Commands for exploring available symbols."""
    pass


@symbols.command(name="list")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ')")
@click.option("--type", "-t", help="Filter by type (e.g., 'stock', 'etf')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of symbols to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_symbols(exchange, type, country, search, limit, detailed,
                 export, output_dir, use_home_dir):
    """
    List available symbols with optional filtering.

    Examples:
    \b
    # List all symbols (limited to 100 by default)
    stockcli stock symbols list

    # List all NASDAQ stocks
    stockcli stock symbols list --exchange NASDAQ --type stock

    # Search for a specific symbol or name
    stockcli stock symbols list --search "Apple"

    # Show more details for each symbol
    stockcli stock symbols list --detailed

    # List all symbols (no limit)
    stockcli stock symbols list --limit 0

    # Export the symbols to CSV
    stockcli stock symbols list --export csv
    """
    from app.utils.display import display_symbols_table, create_progress_spinner
    from app.models.symbol import Symbol

    try:
        # Show a spinner while fetching symbols (can take a while)
        with create_progress_spinner(description="Fetching symbols...") as progress:
            task = progress.add_task("Fetching symbols...", total=None)

            # Fetch symbols with provided filters
            response = client.get_symbols(
                exchange=exchange,
                type=type,
                country=country,
                symbol=search
            )

        # Convert API response to Symbol objects
        symbols = [Symbol.from_api_response(item) for item in response]

        # Apply display limit if specified and non-zero
        display_limit = None if limit == 0 else limit

        # Display the symbols
        display_symbols_table(symbols, display_limit, detailed)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Use all symbols for export regardless of display limit
            from app.utils.export import export_symbols
            export_results = export_symbols(symbols, export_formats, output_dir,
                                            "symbols", use_home_dir)

            if export_results:
                click.echo("\nExported symbols to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo(
                    "\nFailed to export symbols. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching symbols: {e}", exc_info=True)
        click.echo(f"Error fetching symbols: {e}")


@symbols.command(name="types")
def list_symbol_types():
    """
    List available symbol types.
    """

    try:
        # Get symbol types
        types = client.get_symbol_types()

        # Display the types
        click.echo("\nAvailable Symbol Types:")
        for type_name in types:
            click.echo(f"- {type_name}")

    except Exception as e:
        logger.error(f"Error fetching symbol types: {e}", exc_info=True)
        click.echo(f"Error fetching symbol types: {e}")


@symbols.command(name="exchanges")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_exchanges(export, output_dir, use_home_dir):
    """
    List available exchanges.

    Examples:
    \b
    # List all exchanges
    stockcli stock symbols exchanges

    # Export exchanges to JSON
    stockcli stock symbols exchanges --export json
    """
    from app.utils.display import display_exchanges_table, create_progress_spinner
    from app.models.symbol import Exchange

    try:
        # Show a spinner while fetching exchanges
        with create_progress_spinner(description="Fetching exchanges...") as progress:
            task = progress.add_task("Fetching exchanges...", total=None)

            # Fetch exchanges
            response = client.get_exchanges()

        # Convert API response to Exchange objects
        exchanges = [Exchange.from_api_response(item) for item in response]

        # Display the exchanges
        display_exchanges_table(exchanges)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            from app.utils.export import export_symbols
            export_results = export_symbols(exchanges, export_formats, output_dir,
                                            "exchanges", use_home_dir)

            if export_results:
                click.echo("\nExported exchanges to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo(
                    "\nFailed to export exchanges. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching exchanges: {e}", exc_info=True)
        click.echo(f"Error fetching exchanges: {e}")


@stock.group()
def forex():
    """Commands for exploring forex currency pairs."""
    pass


@forex.command(name="pairs")
@click.option("--base", "-b", help="Filter by base currency (e.g., 'USD')")
@click.option("--quote", "-q", help="Filter by quote currency (e.g., 'EUR')")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of pairs to display (default: 100, 0 for all)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_forex_pairs(base, quote, limit, export, output_dir, use_home_dir):
    """
    List available forex currency pairs with optional filtering.

    Examples:
    \b
    # List all forex pairs (limited to 100 by default)
    stockcli stock forex pairs

    # List forex pairs with USD as base currency
    stockcli stock forex pairs --base USD

    # List forex pairs with EUR as quote currency
    stockcli stock forex pairs --quote EUR

    # Export all forex pairs to CSV
    stockcli stock forex pairs --export csv --limit 0
    """
    from app.utils.display import display_forex_pairs_table, create_progress_spinner
    from app.models.forex import ForexPair

    try:
        # Show a spinner while fetching forex pairs
        with create_progress_spinner(description="Fetching forex pairs...") as progress:
            task = progress.add_task("Fetching forex pairs...", total=None)

            # Fetch forex pairs with provided filters
            response = client.get_forex_pairs(
                currency_base=base,
                currency_quote=quote
            )

        # Convert API response to ForexPair objects
        forex_pairs = [ForexPair.from_api_response(item) for item in response]

        # Apply display limit if specified and non-zero
        display_limit = None if limit == 0 else limit

        # Display the forex pairs
        display_forex_pairs_table(forex_pairs, display_limit)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Use all forex pairs for export regardless of display limit
            from app.utils.export import export_symbols
            export_results = export_symbols(forex_pairs, export_formats, output_dir,
                                            "forex_pairs", use_home_dir)

            if export_results:
                click.echo("\nExported forex pairs to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo(
                    "\nFailed to export forex pairs. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching forex pairs: {e}", exc_info=True)
        click.echo(f"Error fetching forex pairs: {e}")


@forex.command(name="currencies")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_currencies(export, output_dir, use_home_dir):
    """
    List available currencies.

    Examples:
    \b
    # List all currencies
    stockcli stock forex currencies

    # Export all currencies to JSON
    stockcli stock forex currencies --export json
    """
    from app.utils.display import display_currencies_table, create_progress_spinner
    from app.models.symbol import Currency

    try:
        # Show a spinner while fetching currencies
        with create_progress_spinner(description="Fetching currencies...") as progress:
            task = progress.add_task("Fetching currencies...", total=None)

            # Fetch currencies
            response = client.get_currencies()

        # Convert API response to Currency objects
        currencies = [Currency.from_api_response(item) for item in response]

        # Display the currencies
        display_currencies_table(currencies)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            from app.utils.export import export_symbols
            export_results = export_symbols(currencies, export_formats, output_dir,
                                            "currencies", use_home_dir)

            if export_results:
                click.echo("\nExported currencies to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo(
                    "\nFailed to export currencies. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching currencies: {e}", exc_info=True)
        click.echo(f"Error fetching currencies: {e}")


@stock.group()
def crypto():
    """Commands for exploring cryptocurrency data."""
    pass


@crypto.command(name="list")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'Binance')")
@click.option("--base", "-b", help="Filter by base currency (e.g., 'BTC')")
@click.option("--quote", "-q", help="Filter by quote currency (e.g., 'USD')")
@click.option("--search", "-s", help="Search by symbol")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of pairs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_crypto_pairs(exchange, base, quote, search, limit, detailed,
                      export, output_dir, use_home_dir):
    """
    List available cryptocurrency pairs with optional filtering.

    Examples:
    \b
    # List all cryptocurrency pairs (limited to 100 by default)
    stockcli stock crypto list

    # List all Bitcoin pairs on Binance
    stockcli stock crypto list --base BTC --exchange Binance

    # List all pairs with USD as quote currency
    stockcli stock crypto list --quote USD

    # Search for a specific symbol
    stockcli stock crypto list --search "BTC/USD"

    # Show more details for each pair
    stockcli stock crypto list --detailed

    # List all pairs (no limit)
    stockcli stock crypto list --limit 0

    # Export the cryptocurrency data to CSV
    stockcli stock crypto list --export csv
    """
    from app.utils.display import display_crypto_pairs_table, create_progress_spinner
    from app.models.cryptocurrency import CryptoPair

    try:
        # Show a spinner while fetching crypto data
        with create_progress_spinner(description="Fetching cryptocurrency data...") as progress:
            task = progress.add_task(
                "Fetching cryptocurrency data...", total=None)

            # Fetch cryptocurrency pairs with provided filters
            response = client.get_cryptocurrencies(
                symbol=search,
                exchange=exchange,
                currency_base=base,
                currency_quote=quote
            )

        # Convert API response to CryptoPair objects
        crypto_pairs = [CryptoPair.from_api_response(
            item) for item in response]

        # Apply display limit if specified and non-zero
        display_limit = None if limit == 0 else limit

        # Display the cryptocurrency pairs
        display_crypto_pairs_table(crypto_pairs, display_limit, detailed)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Use all crypto pairs for export regardless of display limit
            from app.utils.export import export_symbols
            export_results = export_symbols(crypto_pairs, export_formats, output_dir,
                                            "crypto_pairs", use_home_dir)

            if export_results:
                click.echo("\nExported cryptocurrency pairs to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo(
                    "\nFailed to export cryptocurrency data. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching cryptocurrency data: {e}", exc_info=True)
        click.echo(f"Error fetching cryptocurrency data: {e}")


@crypto.command(name="exchanges")
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_crypto_exchanges(export, output_dir, use_home_dir):
    """
    List available cryptocurrency exchanges.

    Examples:
    \b
    # List all cryptocurrency exchanges
    stockcli stock crypto exchanges

    # Export the list of exchanges to a file
    stockcli stock crypto exchanges --export json
    """
    from app.utils.display import display_crypto_exchanges_list, create_progress_spinner

    try:
        # Show a spinner while fetching exchanges
        with create_progress_spinner(description="Fetching cryptocurrency exchanges...") as progress:
            task = progress.add_task(
                "Fetching cryptocurrency exchanges...", total=None)

            # Fetch cryptocurrency exchanges
            exchanges = client.get_crypto_exchanges()

        # Display the exchanges
        display_crypto_exchanges_list(exchanges)

        # Export if requested
        if export:
            # Convert the list of strings to a format that can be exported
            exchange_objects = [
                {'name': exchange}
                for exchange in exchanges
            ]

            from app.utils.export import export_to_json

            if export.lower() == 'json':
                if output_dir:
                    export_dir = Path(output_dir)
                elif use_home_dir:
                    export_dir = Path.home() / '.stock_cli' / 'exports'
                else:
                    export_dir = Path('stock_cli') / 'exports'

                # Ensure directory exists
                export_dir.mkdir(parents=True, exist_ok=True)

                # Generate timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # Create filepath
                filepath = export_dir / f"crypto_exchanges_{timestamp}.json"

                # Export
                if export_to_json(exchange_objects, filepath):
                    click.echo(
                        f"\nExported cryptocurrency exchanges to: {filepath}")
                else:
                    click.echo(
                        "\nFailed to export cryptocurrency exchanges. Check logs for details.")

    except Exception as e:
        logger.error(
            f"Error fetching cryptocurrency exchanges: {e}", exc_info=True)
        click.echo(f"Error fetching cryptocurrency exchanges: {e}")


@stock.group()
def funds():
    """Commands for exploring available funds (ETFs and mutual funds)."""
    pass


@funds.command(name="list")
@click.option("--type", "-t", type=click.Choice(['etf', 'mutual_fund', 'both'], case_sensitive=False),
              default='both', help="Type of funds to list (default: both)")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of funds to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_funds(type, exchange, country, search, limit, detailed,
               export, output_dir, use_home_dir):
    """
    List available funds with optional filtering.

    Examples:
    \b
    # List all funds (limited to 100 by default)
    stockcli stock funds list

    # List ETFs only
    stockcli stock funds list --type etf

    # List mutual funds only
    stockcli stock funds list --type mutual_fund

    # List ETFs from a specific exchange
    stockcli stock funds list --type etf --exchange NASDAQ

    # Search for a specific fund
    stockcli stock funds list --search "Vanguard"

    # Show more details for each fund
    stockcli stock funds list --detailed

    # List all funds (no limit)
    stockcli stock funds list --limit 0

    # Export the funds to CSV
    stockcli stock funds list --export csv
    """
    from app.utils.display import display_funds_table, create_progress_spinner
    from app.models.fund import Fund

    try:
        # Show a spinner while fetching funds
        with create_progress_spinner(description="Fetching funds...") as progress:
            task = progress.add_task("Fetching funds...", total=None)

            # Determine which type of funds to fetch
            fund_type = None
            if type.lower() == 'etf':
                fund_type = 'etf'
            elif type.lower() == 'mutual_fund':
                fund_type = 'mutual_fund'

            # Fetch funds with provided filters
            response = client.get_funds(
                fund_type=fund_type,
                exchange=exchange,
                country=country,
                symbol=search
            )

        # Convert API response to Fund objects
        funds = [Fund.from_symbol(item) for item in response]

        # Apply display limit if specified and non-zero
        display_limit = None if limit == 0 else limit

        # Display the funds
        display_funds_table(funds, display_limit, detailed)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Use all funds for export regardless of display limit
            from app.utils.export import export_symbols
            export_results = export_symbols(funds, export_formats, output_dir,
                                            "funds", use_home_dir)

            if export_results:
                click.echo("\nExported funds to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo("\nFailed to export funds. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching funds: {e}", exc_info=True)
        click.echo(f"Error fetching funds: {e}")


@funds.command(name="etfs")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of ETFs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_etfs(exchange, country, search, limit, detailed,
              export, output_dir, use_home_dir):
    """
    List available ETFs with optional filtering.

    Examples:
    \b
    # List all ETFs (limited to 100 by default)
    stockcli stock funds etfs

    # List ETFs from a specific exchange
    stockcli stock funds etfs --exchange NASDAQ

    # Search for a specific ETF
    stockcli stock funds etfs --search "S&P 500"
    """
    from app.utils.display import display_funds_table, create_progress_spinner
    from app.models.fund import Fund

    try:
        # Show a spinner while fetching ETFs
        with create_progress_spinner(description="Fetching ETFs...") as progress:
            task = progress.add_task("Fetching ETFs...", total=None)

            # Fetch ETFs with provided filters
            response = client.get_etfs(
                exchange=exchange,
                country=country,
                symbol=search
            )

        # Convert API response to Fund objects
        etfs = [Fund.from_symbol(item) for item in response]

        # Apply display limit if specified and non-zero
        display_limit = None if limit == 0 else limit

        # Display the ETFs
        display_funds_table(etfs, display_limit, detailed)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Use all ETFs for export regardless of display limit
            from app.utils.export import export_symbols
            export_results = export_symbols(etfs, export_formats, output_dir,
                                            "etfs", use_home_dir)

            if export_results:
                click.echo("\nExported ETFs to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo("\nFailed to export ETFs. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching ETFs: {e}", exc_info=True)
        click.echo(f"Error fetching ETFs: {e}")


@funds.command(name="mutual")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of mutual funds to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_mutual_funds(exchange, country, search, limit, detailed,
                      export, output_dir, use_home_dir):
    """
    List available mutual funds with optional filtering.

    Examples:
    \b
    # List all mutual funds (limited to 100 by default)
    stockcli stock funds mutual

    # List mutual funds from a specific country
    stockcli stock funds mutual --country "United States"

    # Search for a specific mutual fund
    stockcli stock funds mutual --search "Vanguard"
    """
    from app.utils.display import display_funds_table, create_progress_spinner
    from app.models.fund import Fund

    try:
        # Show a spinner while fetching mutual funds
        with create_progress_spinner(description="Fetching mutual funds...") as progress:
            task = progress.add_task("Fetching mutual funds...", total=None)

            # Fetch mutual funds with provided filters
            response = client.get_mutual_funds(
                exchange=exchange,
                country=country,
                symbol=search
            )

        # Convert API response to Fund objects
        mutual_funds = [Fund.from_symbol(item) for item in response]

        # Apply display limit if specified and non-zero
        display_limit = None if limit == 0 else limit

        # Display the mutual funds
        display_funds_table(mutual_funds, display_limit, detailed)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Use all mutual funds for export regardless of display limit
            from app.utils.export import export_symbols
            export_results = export_symbols(mutual_funds, export_formats, output_dir,
                                            "mutual_funds", use_home_dir)

            if export_results:
                click.echo("\nExported mutual funds to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo(
                    "\nFailed to export mutual funds. Check logs for details.")

    except Exception as e:
        logger.error(f"Error fetching mutual funds: {e}", exc_info=True)
        click.echo(f"Error fetching mutual funds: {e}")


@stock.group(name="bonds")
def bonds():
    """Commands for exploring available bonds."""
    pass


@bonds.command(name="list")
@click.option("--type", "-t", help="Filter by bond type (e.g., 'government', 'corporate')")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NYSE')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of bonds to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_bonds(type, exchange, country, search, limit, detailed,
               export, output_dir, use_home_dir):
    """List available bonds with optional filtering."""
    try:
        # Fetch bond data with filters
        bond_data = client.get_bonds(
            bond_type=type,
            exchange=exchange,
            country=country,
            symbol=search
        )

        # Convert API data to Bond objects
        bonds = [Bond.from_api_response(data) for data in bond_data]

        # Apply limit if specified
        if limit > 0 and len(bonds) > limit:
            bonds = bonds[:limit]

        if not bonds:
            click.echo("No bonds found matching the criteria.")
            return

        # Display bonds
        if detailed:
            display_bonds_detailed(bonds)
        else:
            display_bonds(bonds)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Handle output directory
            export_output_dir = None
            if output_dir:
                # If a custom output directory is provided, use it
                export_output_dir = Path(output_dir).expanduser().resolve()
                logger.debug(
                    f"Using custom export directory: {export_output_dir}")
            elif use_home_dir:
                # If --use-home-dir flag is set, use home directory
                export_output_dir = get_home_export_dir()
                logger.debug(
                    f"Using home directory for exports: {export_output_dir}")
            else:
                # Otherwise, use the default (project) directory
                export_output_dir = get_default_export_dir()
                logger.debug(
                    f"Using default project export directory: {export_output_dir}")

            from app.utils.export import export_items
            export_results = export_items(
                bonds, export_formats, export_output_dir, "bonds"
            )

            if export_results:
                click.echo("\nExported bonds to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        logger.error(f"API error fetching bonds: {e}", exc_info=True)
        click.echo(f"Error from TwelveData API: {e}")
        click.echo("If the bonds endpoint is not available in your API plan, "
                   "you may need to upgrade your subscription.")
    except Exception as e:
        logger.error(f"Error fetching bonds: {e}", exc_info=True)
        click.echo(f"Error fetching bonds: {e}")


@bonds.command(name="types")
def list_bond_types():
    """List available bond types.

    Examples:
    \b
    # List bond types
    stockcli stock bonds types
    """
    try:
        bond_types = client.get_bond_types()

        # Display bond types
        if bond_types:
            click.echo("Available Bond Types:")
            for bond_type in bond_types:
                click.echo(f"  - {bond_type}")
        else:
            click.echo("No bond types found.")

    except Exception as e:
        logger.error(f"Error fetching bond types: {e}", exc_info=True)
        click.echo(f"Error fetching bond types: {e}")


@bonds.command(name="government")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NYSE')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of bonds to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_government_bonds(exchange, country, search, limit, detailed,
                          export, output_dir, use_home_dir):
    """List government bonds with optional filtering.

    Examples:
    \b
    # List all government bonds
    stockcli stock bonds government

    # Filter by country
    stockcli stock bonds government --country "United States"
    """
    # Call the general list_bonds function with 'government' type
    ctx = click.get_current_context()
    ctx.invoke(
        list_bonds,
        type="government",
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@bonds.command(name="corporate")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NYSE')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of bonds to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_corporate_bonds(exchange, country, search, limit, detailed,
                         export, output_dir, use_home_dir):
    """List corporate bonds with optional filtering.

    Examples:
    \b
    # List all corporate bonds
    stockcli stock bonds corporate

    # Filter by country
    stockcli stock bonds corporate --country "United States"
    """
    # Call the general list_bonds function with 'corporate' type
    ctx = click.get_current_context()
    ctx.invoke(
        list_bonds,
        type="corporate",
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="etfs")
def etfs():
    """Commands for exploring available ETFs (Exchange-Traded Funds)."""
    pass


@etfs.command(name="list")
@click.option("--asset-class", "-a", help="Filter by asset class (e.g., 'equity', 'fixed_income')")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NYSE')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of ETFs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--sort-by", type=click.Choice(['symbol', 'expense_ratio', 'managed_assets', 'dividend_yield']),
              default='symbol', help="Sort results by this field")
@click.option("--descending", is_flag=True, help="Sort in descending order")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_etfs(asset_class, exchange, country, search, limit, detailed, sort_by, descending,
              export, output_dir, use_home_dir):
    """List available ETFs with optional filtering and sorting.

    Examples:
    \b
    # List all ETFs
    stockcli stock etfs list

    # Filter by asset class
    stockcli stock etfs list --asset-class equity

    # Filter by exchange
    stockcli stock etfs list --exchange NYSE

    # Search by name or symbol
    stockcli stock etfs list --search Vanguard

    # Sort by expense ratio (lowest first)
    stockcli stock etfs list --sort-by expense_ratio

    # Sort by managed assets (highest first)
    stockcli stock etfs list --sort-by managed_assets --descending

    # Show detailed information
    stockcli stock etfs list --detailed

    # Export to JSON
    stockcli stock etfs list --export json
    """
    try:
        # Fetch ETF data with filters
        etf_data = client.get_etfs(
            asset_class=asset_class,
            exchange=exchange,
            country=country,
            symbol=search
        )

        # Convert API data to ETF objects
        etfs = [ETF.from_api_response(data) for data in etf_data]

        # Sort ETFs based on user criteria
        if sort_by == 'expense_ratio':
            # Sort by expense ratio, handling None values
            etfs.sort(key=lambda e: e.expense_ratio if e.expense_ratio is not None else float('inf'),
                      reverse=descending)
        elif sort_by == 'managed_assets':
            # Sort by managed assets, handling None values
            etfs.sort(key=lambda e: e.managed_assets if e.managed_assets is not None else 0.0,
                      reverse=descending)
        elif sort_by == 'dividend_yield':
            # Sort by dividend yield, handling None values
            etfs.sort(key=lambda e: e.dividend_yield if e.dividend_yield is not None else 0.0,
                      reverse=descending)
        else:
            # Default sort by symbol
            etfs.sort(key=lambda e: e.symbol,
                      reverse=descending)

        # Apply limit if specified
        if limit > 0 and len(etfs) > limit:
            etfs = etfs[:limit]

        if not etfs:
            click.echo("No ETFs found matching the criteria.")
            return

        # Display ETFs
        if detailed:
            display_etfs_detailed(etfs)
        else:
            display_etfs(etfs)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Handle output directory
            export_output_dir = None
            if output_dir:
                # If a custom output directory is provided, use it
                export_output_dir = Path(output_dir).expanduser().resolve()
                logger.debug(
                    f"Using custom export directory: {export_output_dir}")
            elif use_home_dir:
                # If --use-home-dir flag is set, use home directory
                export_output_dir = get_home_export_dir()
                logger.debug(
                    f"Using home directory for exports: {export_output_dir}")
            else:
                # Otherwise, use the default (project) directory
                export_output_dir = get_default_export_dir()
                logger.debug(
                    f"Using default project export directory: {export_output_dir}")

            from app.utils.export import export_items
            export_results = export_items(
                etfs, export_formats, export_output_dir, "etfs"
            )

            if export_results:
                click.echo("\nExported ETFs to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        logger.error(f"API error fetching ETFs: {e}", exc_info=True)
        click.echo(f"Error from TwelveData API: {e}")
        click.echo("If the ETFs endpoint is not available in your API plan, "
                   "the command will try to use the stocks endpoint as a fallback.")
    except Exception as e:
        logger.error(f"Error fetching ETFs: {e}", exc_info=True)
        click.echo(f"Error fetching ETFs: {e}")


@etfs.command(name="asset-classes")
def list_etf_asset_classes():
    """List available ETF asset classes.

    Examples:
    \b
    # List ETF asset classes
    stockcli stock etfs asset-classes
    """
    try:
        asset_classes = client.get_etf_asset_classes()

        # Display asset classes
        if asset_classes:
            click.echo("Available ETF Asset Classes:")
            for asset_class in asset_classes:
                click.echo(f"  - {asset_class}")
        else:
            click.echo("No asset classes found.")

    except Exception as e:
        logger.error(f"Error fetching ETF asset classes: {e}", exc_info=True)
        click.echo(f"Error fetching ETF asset classes: {e}")


@etfs.command(name="equity")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NYSE')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of ETFs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--sort-by", type=click.Choice(['symbol', 'expense_ratio', 'managed_assets', 'dividend_yield']),
              default='symbol', help="Sort results by this field")
@click.option("--descending", is_flag=True, help="Sort in descending order")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_equity_etfs(exchange, country, search, limit, detailed, sort_by, descending,
                     export, output_dir, use_home_dir):
    """List equity ETFs with optional filtering.

    Examples:
    \b
    # List all equity ETFs
    stockcli stock etfs equity

    # Filter by country
    stockcli stock etfs equity --country "United States"
    """
    # Call the general list_etfs function with 'equity' asset class
    ctx = click.get_current_context()
    ctx.invoke(
        list_etfs,
        asset_class="equity",
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        sort_by=sort_by,
        descending=descending,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@etfs.command(name="fixed-income")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NYSE')")
@click.option("--country", "-c", help="Filter by country")
@click.option("--search", "-s", help="Search by symbol or name")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of ETFs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--sort-by", type=click.Choice(['symbol', 'expense_ratio', 'managed_assets', 'dividend_yield']),
              default='symbol', help="Sort results by this field")
@click.option("--descending", is_flag=True, help="Sort in descending order")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_fixed_income_etfs(exchange, country, search, limit, detailed, sort_by, descending,
                           export, output_dir, use_home_dir):
    """List fixed income ETFs (bond ETFs) with optional filtering.

    Examples:
    \b
    # List all fixed income ETFs
    stockcli stock etfs fixed-income

    # Filter by country
    stockcli stock etfs fixed-income --country "United States"
    """
    # Call the general list_etfs function with 'fixed_income' asset class
    ctx = click.get_current_context()
    ctx.invoke(
        list_etfs,
        asset_class="fixed_income",
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        sort_by=sort_by,
        descending=descending,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@etfs.command(name="info")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_etf_info(symbol, export, output_dir, use_home_dir):
    """Get detailed information for a specific ETF by symbol.

    Examples:
    \b
    # Show detailed information for an ETF
    stockcli stock etfs info SPY

    # Export ETF information
    stockcli stock etfs info QQQ --export json
    """
    try:
        # Fetch ETF data for the specific symbol
        etf_data = client.get_etfs(symbol=symbol)

        # Check if we found an ETF with this symbol
        if not etf_data:
            click.echo(f"No ETF found with symbol: {symbol}")
            return

        # Convert API data to ETF object (use the first match)
        etf = ETF.from_api_response(etf_data[0])

        # Display the ETF
        display_etfs_detailed([etf])

        # Export if requested
        if export:
            export_formats = [export]

            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()

            from app.utils.export import export_items
            export_results = export_items(
                [etf], export_formats, export_output_dir, f"etf_{symbol.lower()}"
            )

            if export_results:
                click.echo("\nExported ETF information to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except Exception as e:
        logger.error(f"Error fetching ETF information: {e}", exc_info=True)
        click.echo(f"Error fetching ETF information: {e}")


@stock.group(name="commodities")
def commodities():
    """Commands for exploring available commodity trading pairs."""
    pass


@commodities.command(name="list")
@click.option("--group", "-g", help="Filter by commodity group (e.g., 'precious_metals', 'energy')")
@click.option("--exchange", "-e", help="Filter by exchange")
@click.option("--search", "-s", help="Search by symbol")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of pairs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_commodity_pairs(group, exchange, search, limit, detailed,
                         export, output_dir, use_home_dir):
    """List available commodity trading pairs with optional filtering.

    Examples:
    \b
    # List all commodity pairs
    stockcli stock commodities list

    # Filter by commodity group
    stockcli stock commodities list --group precious_metals

    # Filter by exchange
    stockcli stock commodities list --exchange COMEX

    # Search by symbol
    stockcli stock commodities list --search "GOLD"

    # Show detailed information
    stockcli stock commodities list --detailed

    # Export to JSON
    stockcli stock commodities list --export json
    """
    try:
        # Fetch commodity pair data with filters
        commodities_data = client.get_commodity_pairs(
            commodity_group=group,
            exchange=exchange,
            symbol=search
        )

        # Convert API data to CommodityPair objects
        commodity_pairs = [CommodityPair.from_api_response(
            data) for data in commodities_data]

        # Apply limit if specified
        if limit > 0 and len(commodity_pairs) > limit:
            commodity_pairs = commodity_pairs[:limit]

        if not commodity_pairs:
            click.echo("No commodity pairs found matching the criteria.")
            return

        # Display commodity pairs
        if detailed:
            display_commodity_pairs_detailed(commodity_pairs)
        else:
            display_commodity_pairs(commodity_pairs)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']

            # Handle output directory
            export_output_dir = None
            if output_dir:
                # If a custom output directory is provided, use it
                export_output_dir = Path(output_dir).expanduser().resolve()
                logger.debug(
                    f"Using custom export directory: {export_output_dir}")
            elif use_home_dir:
                # If --use-home-dir flag is set, use home directory
                export_output_dir = get_home_export_dir()
                logger.debug(
                    f"Using home directory for exports: {export_output_dir}")
            else:
                # Otherwise, use the default (project) directory
                export_output_dir = get_default_export_dir()
                logger.debug(
                    f"Using default project export directory: {export_output_dir}")

            from app.utils.export import export_items
            export_results = export_items(
                commodity_pairs, export_formats, export_output_dir, "commodities"
            )

            if export_results:
                click.echo("\nExported commodity pairs to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        logger.error(f"API error fetching commodity pairs: {e}", exc_info=True)
        click.echo(f"Error from TwelveData API: {e}")
    except Exception as e:
        logger.error(f"Error fetching commodity pairs: {e}", exc_info=True)
        click.echo(f"Error fetching commodity pairs: {e}")


@commodities.command(name="groups")
def list_commodity_groups():
    """List available commodity groups with descriptions.

    Examples:
    \b
    # List commodity groups
    stockcli stock commodities groups
    """
    try:
        commodity_groups_data = client.get_commodity_groups()

        # Display commodity groups
        if commodity_groups_data:
            # Create CommodityGroup objects
            commodity_groups = [
                CommodityGroup(
                    name=data['name'],
                    description=data['description'],
                    examples=data['examples']
                ) for data in commodity_groups_data
            ]

            display_commodity_groups(commodity_groups)
        else:
            click.echo("No commodity groups found.")

    except Exception as e:
        logger.error(f"Error fetching commodity groups: {e}", exc_info=True)
        click.echo(f"Error fetching commodity groups: {e}")


@commodities.command(name="precious-metals")
@click.option("--exchange", "-e", help="Filter by exchange")
@click.option("--search", "-s", help="Search by symbol")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of pairs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_precious_metals(exchange, search, limit, detailed,
                         export, output_dir, use_home_dir):
    """List precious metals commodity pairs with optional filtering.

    Examples:
    \b
    # List all precious metals pairs
    stockcli stock commodities precious-metals

    # Search for gold specifically
    stockcli stock commodities precious-metals --search gold
    """
    # Call the general list_commodity_pairs function with 'precious_metals' group
    ctx = click.get_current_context()
    ctx.invoke(
        list_commodity_pairs,
        group="precious_metals",
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@commodities.command(name="energy")
@click.option("--exchange", "-e", help="Filter by exchange")
@click.option("--search", "-s", help="Search by symbol")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of pairs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_energy_commodities(exchange, search, limit, detailed,
                            export, output_dir, use_home_dir):
    """List energy commodity pairs with optional filtering.

    Examples:
    \b
    # List all energy commodity pairs
    stockcli stock commodities energy

    # Search for oil specifically
    stockcli stock commodities energy --search oil
    """
    # Call the general list_commodity_pairs function with 'energy' group
    ctx = click.get_current_context()
    ctx.invoke(
        list_commodity_pairs,
        group="energy",
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@commodities.command(name="agriculture")
@click.option("--exchange", "-e", help="Filter by exchange")
@click.option("--search", "-s", help="Search by symbol")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of pairs to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_agricultural_commodities(exchange, search, limit, detailed,
                                  export, output_dir, use_home_dir):
    """List agricultural commodity pairs with optional filtering.

    Examples:
    \b
    # List all agricultural commodity pairs
    stockcli stock commodities agriculture

    # Search for wheat specifically
    stockcli stock commodities agriculture --search wheat
    """
    # Call the general list_commodity_pairs function with 'agriculture' group
    ctx = click.get_current_context()
    ctx.invoke(
        list_commodity_pairs,
        group="agriculture",
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="symbols")
def symbols():
    """Commands for exploring available financial symbols."""
    pass


@symbols.command(name="cross-list")
@click.option("--symbol", "-s", help="Filter by specific symbol (e.g., 'AAPL')")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_cross_listed_symbols(symbol, export, output_dir, use_home_dir):
    """List symbols that are cross-listed on multiple exchanges."""
    from app.utils.display import display_cross_listed_symbols, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from app.models.symbol import Symbol

    try:
        click.echo("Fetching cross-listed symbols...")
        with create_progress_spinner("Fetching cross-listed symbols") as progress:
            task = progress.add_task("Downloading...", total=1)
            cross_listed = client.get_cross_listed_symbols(symbol=symbol)
            progress.update(task, advance=1)

        if not cross_listed:
            click.echo("No cross-listed symbols found.")
            return

        # Convert API response to Symbol objects if possible
        symbols_list = []
        raw_data = None
        try:
            for item in cross_listed:
                # Check if the item is a dictionary or a string
                if isinstance(item, dict):
                    symbols_list.append(Symbol.from_api_response(item))
                else:
                    logger.warning(f"Unexpected data format: {item}")

            # If we couldn't parse any symbols, keep the raw data for display
            if not symbols_list:
                raw_data = cross_listed
        except (KeyError, ValueError, TypeError) as e:
            click.echo(
                f"Warning: Could not parse all cross-listed symbols: {e}")
            raw_data = cross_listed

        # Display the symbols or raw data
        # Display the symbols or raw data
        if symbols_list:
            display_cross_listed_symbols(symbols_list)
        elif raw_data:
            from app.utils.display import display_raw_cross_listed_data
            display_raw_cross_listed_data(raw_data)
        else:
            click.echo("No cross-listed symbols data available.")
            return

        # Export if requested
        if export:
            export_formats = []
            if export == "json":
                export_formats = ["json"]
            elif export == "csv":
                export_formats = ["csv"]
            else:  # both
                export_formats = ["json", "csv"]

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Export the symbols or raw data
            from app.utils.export import export_items

            if symbols_list:
                exported_files = export_items(
                    symbols_list, export_formats, export_dir,
                    filename_prefix="cross_listed_symbols"
                )
            elif raw_data:
                # Fallback export for raw data
                import json
                import csv
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                exported_files = {}

                # Export as JSON
                if "json" in export_formats:
                    json_file = export_dir / \
                        f"cross_listed_symbols_{timestamp}.json"
                    export_dir.mkdir(parents=True, exist_ok=True)

                    with open(json_file, 'w') as f:
                        json.dump(raw_data, f, indent=2)

                    exported_files["json"] = str(json_file)

                # Export as CSV (if possible)
                if "csv" in export_formats and isinstance(raw_data, list):
                    csv_file = export_dir / \
                        f"cross_listed_symbols_{timestamp}.csv"
                    export_dir.mkdir(parents=True, exist_ok=True)

                    # Try to extract field names from the first item
                    fieldnames = []
                    if raw_data and isinstance(raw_data[0], dict):
                        fieldnames = list(raw_data[0].keys())

                    with open(csv_file, 'w', newline='') as f:
                        if fieldnames:
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            for item in raw_data:
                                if isinstance(item, dict):
                                    writer.writerow(item)
                        else:
                            writer = csv.writer(f)
                            for item in raw_data:
                                writer.writerow([item])

                    exported_files["csv"] = str(csv_file)

            if exported_files:
                click.echo("\nExported cross-listed symbols to:")
                for fmt, path in exported_files.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)


@symbols.command(name="exchanges")
@click.option("--type", "-t", help="Filter by exchange type (e.g., 'stock', 'etf')")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_exchanges(type, export, output_dir, use_home_dir):
    """List available exchanges with optional filtering by type."""
    from app.utils.display import display_exchanges_table, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from app.models.symbol import Exchange

    try:
        # Show a spinner while fetching exchanges
        with create_progress_spinner(description="Fetching exchanges...") as progress:
            task = progress.add_task("Fetching exchanges...", total=None)

            # Fetch exchanges with type filter if provided
            if type:
                click.echo(f"Fetching exchanges of type: {type}")
                exchanges_data = client.get_exchanges_by_type(type)
            else:
                exchanges_data = client.get_exchanges()

            progress.update(task, completed=True)

        exchanges = []
        for exchange_data in exchanges_data:
            try:
                exchanges.append(Exchange.from_api_response(exchange_data))
            except (KeyError, ValueError) as e:
                logger.warning(f"Could not parse exchange data: {e}")

        if not exchanges:
            click.echo("No exchanges found matching the criteria.")
            return

        # Display the exchanges
        display_exchanges_table(exchanges)
        click.echo(f"Total exchanges: {len(exchanges)}")

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            else:  # both
                export_formats = ['json', 'csv']

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Export the exchanges
            from app.utils.export import export_items

            prefix = 'exchanges'
            if type:
                prefix = f"{type}_exchanges"

            export_results = export_items(
                exchanges, export_formats, export_dir,
                filename_prefix=prefix
            )

            if export_results:
                click.echo("\nExported exchanges to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)


@symbols.command(name="exchange-schedule")
@click.argument("code", required=True)
@click.option("--date", "-d", help="Specific date in YYYY-MM-DD format")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_exchange_schedule(code, date, export, output_dir, use_home_dir):
    """Get exchange schedule, including details and trading hours."""
    from app.utils.display import display_exchange_schedule, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from app.models.exchange_details import ExchangeSchedule

    try:
        # Show a spinner while fetching data
        with create_progress_spinner(description=f"Fetching schedule for {code}...") as progress:
            task = progress.add_task("Downloading...", total=1)

            # Fetch exchange schedule
            exchange_data = client.get_exchange_schedule(code, date)
            progress.update(task, completed=True)

        # Create ExchangeSchedule object
        exchange_schedule = ExchangeSchedule.from_api_response(exchange_data)

        # Display the exchange schedule
        display_exchange_schedule(exchange_schedule)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            else:  # both
                export_formats = ['json', 'csv']

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Export the exchange schedule
            from app.utils.export import export_items

            filename_prefix = f"exchange_schedule_{code.lower()}"
            if date:
                filename_prefix += f"_{date}"

            export_results = export_items(
                [exchange_schedule], export_formats, export_dir,
                filename_prefix=filename_prefix
            )

            if export_results:
                click.echo("\nExported exchange schedule to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)


# Create aliases for backward compatibility
@symbols.command(name="exchange-details")
@click.argument("code", required=True)
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_exchange_details_alias(code, export, output_dir, use_home_dir):
    """Get detailed information about a specific exchange (alias for exchange-schedule)."""
    ctx = click.get_current_context()
    click.echo("Note: 'exchange-details' is now an alias for 'exchange-schedule'")
    ctx.invoke(
        get_exchange_schedule,
        code=code,
        date=None,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols.command(name="trading-hours")
@click.argument("code", required=True)
@click.option("--date", "-d", help="Specific date in YYYY-MM-DD format")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_exchange_trading_hours_alias(code, date, export, output_dir, use_home_dir):
    """Get trading hours for a specific exchange (alias for exchange-schedule)."""
    ctx = click.get_current_context()
    click.echo("Note: 'trading-hours' is now an alias for 'exchange-schedule'")
    ctx.invoke(
        get_exchange_schedule,
        code=code,
        date=date,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols.command(name="all-trading-hours")
@click.option("--type", "-t", help="Filter by exchange type (e.g., 'stock', 'etf')")
@click.option("--limit", "-l", type=int, help="Limit the number of exchanges to fetch")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_exchanges_with_hours(type, limit, export, output_dir, use_home_dir):
    """
    List all available exchanges with their opening and closing times.

    This command fetches all exchanges and their trading hours information.

    Examples:
    \b
    # List all exchanges with their trading hours
    stockcli symbols all-trading-hours

    # List stock exchanges with their trading hours
    stockcli symbols all-trading-hours --type stock

    # List a limited number of exchanges (for testing)
    stockcli symbols all-trading-hours --limit 10

    # Export results to JSON
    stockcli symbols all-trading-hours --export json
    """
    from app.utils.display import display_exchanges_with_hours_table, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from app.models.exchange_details import ExchangeSchedule
    from pathlib import Path

    try:
        # Show a spinner while fetching data
        with create_progress_spinner(description="Fetching all exchanges with trading hours...") as progress:
            task_id = progress.add_task("Downloading...", total=None)

            # Fetch exchanges with trading hours
            exchanges_data = client.get_all_exchanges_with_hours(
                limit=limit, exchange_type=type)

            progress.update(task_id, completed=True)

        # Convert API response to ExchangeSchedule objects
        exchange_schedules = []
        for data in exchanges_data:
            try:
                schedule = ExchangeSchedule.from_api_response(data)
                exchange_schedules.append(schedule)
            except (KeyError, ValueError) as e:
                logger.warning(f"Could not parse exchange schedule data: {e}")

        # Display the exchanges with trading hours
        display_exchanges_with_hours_table(exchange_schedules)

        # Export if requested
        # if export:
        #     export_formats = []
        #     if export == 'json':
        #         export_formats = ['json']
        #     elif export == 'csv':
        #         export_formats = ['csv']
        #     else:  # both
        #         export_formats = ['json', 'csv']

        #     # Determine output directory
        #     if output_dir:
        #         export_dir = Path(output_dir).expanduser().resolve()
        #     elif use_home_dir:
        #         export_dir = get_home_export_dir()
        #     else:
        #         export_dir = get_default_export_dir()

        #     # Export the exchange schedules
        #     filename_prefix = "exchanges_with_hours"
        #     if type:
        #         filename_prefix += f"_{type.lower()}"

        #     export_results = export_items(
        #         exchange_schedules, export_formats, export_dir,
        #         filename_prefix=filename_prefix
        #     )

        #     if export_results:
        #         click.echo("\nExported exchanges with trading hours to:")
        #         for fmt, path in export_results.items():
        #             click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(
            f"Unexpected error fetching exchanges with trading hours: {e}")
        click.echo(f"Unexpected error: {e}", err=True)


@symbols.command(name="instrument-types")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_instrument_types(export, output_dir, use_home_dir):
    """
    List available instrument types from the TwelveData API.

    Instrument types are categories of financial instruments that can be used
    for filtering in other API endpoints.

    Examples:
    \b
    # List all instrument types
    stockcli symbols instrument-types

    # Export instrument types to JSON
    stockcli symbols instrument-types --export json
    """
    from app.utils.display import display_instrument_types_table, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from pathlib import Path

    try:
        # Show a spinner while fetching data
        with create_progress_spinner(description="Fetching instrument types...") as progress:
            task_id = progress.add_task("Downloading...", total=None)

            # Fetch instrument types
            instrument_types = client.get_instrument_types()

            progress.update(task_id, completed=True)

        # Display the instrument types
        display_instrument_types_table(instrument_types)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            else:  # both
                export_formats = ['json', 'csv']

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Create a list of dictionaries for export
            export_data = []
            for instrument_type in instrument_types:
                if isinstance(instrument_type, dict):
                    export_data.append({
                        'id': instrument_type.get('id', ''),
                        'name': instrument_type.get('name', '')
                    })
                else:
                    # Handle string format for backwards compatibility
                    export_data.append({
                        'id': instrument_type,
                        'name': instrument_type.capitalize()
                    })

            # Export the instrument types
            from app.utils.export import export_to_json, export_to_csv
            export_results = {}

            filename_prefix = "instrument_types"
            if 'json' in export_formats:
                json_path = export_dir / f"{filename_prefix}.json"
                export_to_json(export_data, json_path)
                export_results['json'] = json_path

            if 'csv' in export_formats:
                csv_path = export_dir / f"{filename_prefix}.csv"
                with open(csv_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=['id', 'name'])
                    writer.writeheader()
                    writer.writerows(export_data)
                export_results['csv'] = csv_path

            if export_results:
                click.echo("\nExported instrument types to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error fetching instrument types: {e}")
        click.echo(f"Unexpected error: {e}", err=True)


@stock.command(name="earliest-data")
@click.argument("symbol", required=True)
@click.option("--interval", "-i", default="1day",
              help="Time interval (e.g., '1min', '5min', '1h', '1day', '1week', '1month')")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_earliest_data(symbol, interval, export, output_dir, use_home_dir):
    """
    Get the first available datetime for a given instrument at a specific interval.

    This command helps determine the historical data range available for a specific
    symbol and interval in the TwelveData API.

    Examples:
    \b
    # Get earliest available data for Apple stock with daily interval
    stockcli stock earliest-data AAPL --interval 1day

    # Get earliest available data for Bitcoin with hourly interval
    stockcli stock earliest-data BTC/USD --interval 1h

    # Get earliest data and export to JSON
    stockcli stock earliest-data AAPL --interval 1day --export json
    """
    from app.utils.display import display_earliest_data_info, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from pathlib import Path

    try:
        # Show a spinner while fetching data
        with create_progress_spinner(description=f"Fetching earliest data for {symbol}...") as progress:
            task_id = progress.add_task("Downloading...", total=None)

            # Fetch earliest available timestamp
            earliest_data = client.get_earliest_timestamp(symbol, interval)

            progress.update(task_id, completed=True)

        # Display the earliest data information
        display_earliest_data_info(earliest_data)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            else:  # both
                export_formats = ['json', 'csv']

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Export the earliest data info
            from app.utils.export import export_to_json, export_to_csv

            # Create a clean export object with the relevant data
            export_data = {
                'symbol': symbol,
                'interval': interval,
                'earliest_datetime': earliest_data.get('earliest_datetime'),
                'first_data_point': earliest_data.get('data', {})
            }

            export_results = {}
            filename_prefix = f"earliest_data_{symbol.replace('/', '_')}_{interval}"

            # Export to JSON if requested
            if 'json' in export_formats:
                json_path = export_dir / f"{filename_prefix}.json"
                export_to_json(export_data, json_path)
                export_results['json'] = json_path

            # Export to CSV if requested
            if 'csv' in export_formats:
                csv_path = export_dir / f"{filename_prefix}.csv"

                # Create a flattened representation for CSV
                flat_data = {
                    'symbol': symbol,
                    'interval': interval,
                    'earliest_datetime': earliest_data.get('earliest_datetime', 'N/A')
                }

                # Add the first data point fields if available
                if 'data' in earliest_data and earliest_data['data']:
                    for key, value in earliest_data['data'].items():
                        flat_data[f"data_{key}"] = value

                # Write to CSV
                with open(csv_path, 'w', newline='') as csvfile:
                    # Determine the fieldnames
                    fieldnames = list(flat_data.keys())

                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerow(flat_data)

                export_results['csv'] = csv_path

            if export_results:
                click.echo("\nExported earliest data info to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error fetching earliest data: {e}")
        click.echo(f"Unexpected error: {e}", err=True)


@symbols.command(name="search")
@click.argument("query", required=True)
@click.option("--limit", "-l", type=int, default=10,
              help="Maximum number of results to display (default: 10)")
@click.option("--type", "-t", multiple=True,
              help="Filter by instrument type(s) (can specify multiple)")
@click.option("--exchange", "-e", help="Filter by exchange")
@click.option("--country", "-c", help="Filter by country")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def search_symbols(query, limit, type, exchange, country, export, output_dir, use_home_dir):
    """
    Search for symbols matching a query.

    Examples:
    \b
    # Search for Apple
    stockcli symbols search "Apple"

    # Search for Bitcoin with limit of 5 results
    stockcli symbols search "Bitcoin" --limit 5

    # Search for stocks on NASDAQ
    stockcli symbols search "tech" --type stock --exchange NASDAQ

    # Search for ETFs and export results
    stockcli symbols search "S&P" --type etf --export json
    """
    from app.utils.display import display_symbol_search_results, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from pathlib import Path

    try:
        # Process instrument types filter
        instrument_types = list(type) if type else None

        # Show a spinner while fetching data
        with create_progress_spinner(description=f"Searching for '{query}'...") as progress:
            task_id = progress.add_task("Searching...", total=None)

            # Search for symbols
            symbols = client.search_symbols(
                query=query,
                outputsize=limit,
                instrument_types=instrument_types,
                exchange=exchange,
                country=country
            )

            progress.update(task_id, completed=True)

        # Display the search results
        display_symbol_search_results(symbols, query)

        # Export if requested
        if export and symbols:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            else:  # both
                export_formats = ['json', 'csv']

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Export the search results
            from app.utils.export import export_to_json, export_to_csv

            export_results = {}
            filename_query = query.replace(' ', '_').replace('/', '_')[:30]
            filename_prefix = f"symbol_search_{filename_query}"

            # Export to JSON if requested
            if 'json' in export_formats:
                json_path = export_dir / f"{filename_prefix}.json"
                export_to_json(symbols, json_path)
                export_results['json'] = json_path

            # Export to CSV if requested
            if 'csv' in export_formats:
                csv_path = export_dir / f"{filename_prefix}.csv"

                with open(csv_path, 'w', newline='') as csvfile:
                    # Define the fieldnames
                    fieldnames = ['symbol', 'instrument_name',
                                  'type', 'exchange', 'country', 'currency']

                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    # Write each symbol data
                    for symbol in symbols:
                        writer.writerow({
                            'symbol': symbol.get('symbol', ''),
                            'instrument_name': symbol.get('instrument_name', symbol.get('name', '')),
                            'type': symbol.get('type', ''),
                            'exchange': symbol.get('exchange', ''),
                            'country': symbol.get('country', ''),
                            'currency': symbol.get('currency', '')
                        })

                export_results['csv'] = csv_path

            if export_results:
                click.echo("\nExported search results to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error searching symbols: {e}")
        click.echo(f"Unexpected error: {e}", err=True)


@stock.command(name="time-series")
@click.argument("symbol", required=True)
@click.option("--interval", "-i", default="1day",
              help="Time interval (e.g., '1min', '5min', '1h', '1day', '1week', '1month')")
@click.option("--outputsize", "-n", type=int, default=30,
              help="Number of data points to fetch (default: 30, max: 5000)")
@click.option("--start-date", "-s",
              help="Start date in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format")
@click.option("--end-date", "-e",
              help="End date in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format")
@click.option("--order", "-o", type=click.Choice(['asc', 'desc'], case_sensitive=False),
              default='desc', help="Order of results ('asc' for oldest first, 'desc' for newest first)")
@click.option("--include-ext", is_flag=True,
              help="Include extended hours data (pre/post market) for stocks")
@click.option("--limit", "-l", type=int, default=10,
              help="Maximum number of data points to display (default: 10, 0 for all)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_time_series(symbol, interval, outputsize, start_date, end_date, order, include_ext,
                    limit, export, output_dir, use_home_dir):
    """
    Fetch meta and time series data for the requested instrument.

    This command will fetch historical price data for the specified symbol
    using the 'time_series' endpoint of the TwelveData API.

    Examples:
    \b
    # Get daily time series for Apple stock (last 30 days by default)
    stockcli stock time-series AAPL --interval 1day

    # Get hourly data for Bitcoin with 100 data points
    stockcli stock time-series BTC/USD --interval 1h --outputsize 100

    # Get data for a specific date range
    stockcli stock time-series MSFT --start-date 2023-01-01 --end-date 2023-01-31

    # Display more data points in the terminal
    stockcli stock time-series AAPL --limit 20

    # Export the time series data to CSV
    stockcli stock time-series AAPL --export csv
    """
    from app.utils.display import display_time_series_response, create_progress_spinner
    from app.utils.export import export_to_json, export_time_series_to_csv, get_default_export_dir, get_home_export_dir
    from app.models.stock import TimeSeries
    from pathlib import Path

    try:
        # Determine display limit
        display_limit = None if limit == 0 else limit

        # Show a spinner while fetching data
        with create_progress_spinner(description=f"Fetching time series for {symbol}...") as progress:
            task_id = progress.add_task("Downloading...", total=None)

            # Fetch time series data
            response = client.get_time_series(
                symbol=symbol,
                interval=interval,
                outputsize=outputsize,
                start_date=start_date,
                end_date=end_date,
                order=order,
                include_ext_premarket=include_ext
            )

            progress.update(task_id, completed=True)

        # Display the time series data
        display_time_series_response(response, display_limit)

        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            else:  # both
                export_formats = ['json', 'csv']

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Create TimeSeries object for export
            time_series = TimeSeries.from_api_response(response)

            # Generate filename with symbol and interval
            clean_symbol = symbol.replace('/', '_')
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_prefix = f"time_series_{clean_symbol}_{interval}_{date_str}"

            export_results = {}

            if 'json' in export_formats:
                json_path = export_dir / f"{filename_prefix}.json"
                export_to_json(response, json_path)
                export_results['json'] = json_path

            if 'csv' in export_formats:
                csv_path = export_dir / f"{filename_prefix}.csv"
                export_time_series_to_csv(time_series, csv_path)
                export_results['csv'] = csv_path

            if export_results:
                click.echo("\nExported time series data to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error fetching time series: {e}")
        click.echo(f"Unexpected error: {e}", err=True)


@stock.group()
def forex():
    """Commands for exploring forex data."""
    pass


@forex.command(name="rate")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(["json", "csv", "both"], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_exchange_rate(symbol, export, output_dir, use_home_dir):
    """
    Get real-time exchange rate for a currency pair.

    This command fetches the current exchange rate for the specified forex pair
    using the TwelveData API.

    SYMBOL should be in the format BASE/QUOTE (e.g., EUR/USD, GBP/JPY).

    Examples:
    \b
    # Get the exchange rate for EUR/USD
    stockcli stock forex rate EUR/USD

    # Get the exchange rate for GBP/JPY and export to JSON
    stockcli stock forex rate GBP/JPY --export json
    """
    from app.utils.display import display_forex_rate, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir, export_to_json
    from app.models.forex import ForexRate
    from pathlib import Path
    from datetime import datetime
    import csv

    try:
        # Show a spinner while fetching data
        with create_progress_spinner(description=f"Fetching exchange rate for {symbol}...") as progress:
            task_id = progress.add_task("Downloading...", total=None)
            # Fetch exchange rate
            response = client.get_exchange_rate(symbol)
            progress.update(task_id, completed=True)

        # Create ForexRate object
        forex_rate = ForexRate.from_api_response(response)

        # Display the forex rate
        display_forex_rate(forex_rate)

        # Export if requested
        if export:
            if export == "json":
                export_formats = ["json"]
            elif export == "csv":
                export_formats = ["csv"]
            else:  # both
                export_formats = ["json", "csv"]

            # Determine output directory
            if output_dir:
                export_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_dir = get_home_export_dir()
            else:
                export_dir = get_default_export_dir()

            # Generate filename with symbol
            clean_symbol = symbol.replace("/", "_")
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"forex_rate_{clean_symbol}_{date_str}"

            export_results = {}

            # Export to JSON if requested
            if "json" in export_formats:
                json_path = export_dir / f"{filename_prefix}.json"
                export_to_json(forex_rate.to_dict(), json_path)
                export_results["json"] = json_path

            # Export to CSV if requested
            if "csv" in export_formats:
                csv_path = export_dir / f"{filename_prefix}.csv"
                # Write CSV data
                with open(csv_path, "w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=ForexRate.get_csv_header())
                    writer.writeheader()
                    writer.writerow(forex_rate.to_csv_row())
                export_results["csv"] = csv_path

            if export_results:
                click.echo("\nExported exchange rate to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")

    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error fetching exchange rate: {e}")
        click.echo(f"Unexpected error: {e}", err=True)

@stock.command(name="latest-quote")
@click.argument("symbol", required=True)
@click.option("--refresh", "-r", is_flag=True, help="Enable auto-refresh")
@click.option("--interval", "-i", default=10, help="Refresh interval in seconds (default: 10)")
@click.option("--simple", "-s", is_flag=True, help="Show simplified view (less detail)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_latest_quote(symbol, refresh, interval, simple, export, output_dir, use_home_dir):
    """
    Get the latest quote for a specific instrument.
    
    This command fetches the most current pricing data for a specified financial instrument
    and displays detailed information, including price, changes, volume, and 52-week highs/lows.
    
    Examples:
    \b
    # Get latest quote for Apple stock
    stockcli stock latest-quote AAPL
    
    # Get latest quote for Bitcoin/USD with auto-refresh every 5 seconds
    stockcli stock latest-quote BTC/USD --refresh --interval 5
    
    # Get simplified view of the latest quote
    stockcli stock latest-quote AAPL --simple
    
    # Export the latest quote to JSON
    stockcli stock latest-quote AAPL --export json
    """
    from app.utils.display import display_detailed_quote, create_progress_spinner
    from app.utils.export import get_default_export_dir, get_home_export_dir
    from app.models.stock import Quote
    from pathlib import Path
    import time
    
    # Convert symbol to uppercase (except for crypto pairs that use slashes)
    if '/' not in symbol:
        symbol = symbol.upper()
    
    # Process export format
    export_formats = []
    if export == 'json':
        export_formats = ['json']
    elif export == 'csv':
        export_formats = ['csv']
    elif export == 'both':
        export_formats = ['json', 'csv']
    
    # Handle output directory
    export_output_dir = None
    if output_dir:
        # If a custom output directory is provided, use it
        export_output_dir = Path(output_dir).expanduser().resolve()
        logger.debug(f"Using custom export directory: {export_output_dir}")
    elif use_home_dir:
        # If --use-home-dir flag is set, use home directory
        export_output_dir = get_home_export_dir()
        logger.debug(f"Using home directory for exports: {export_output_dir}")
    else:
        # Otherwise, use the default (project) directory
        export_output_dir = get_default_export_dir()
        logger.debug(f"Using default project export directory: {export_output_dir}")
    
    # If refresh is enabled, set up auto-refresh loop
    if refresh:
        click.echo(f"Auto-refreshing quote for {symbol} every {interval} seconds. Press Ctrl+C to stop.")
        try:
            while True:
                fetch_and_display_single_quote(symbol, simple, export_formats, export_output_dir)
                time.sleep(interval)
        except KeyboardInterrupt:
            click.echo("\nAuto-refresh stopped.")
    else:
        # Just fetch once
        fetch_and_display_single_quote(symbol, simple, export_formats, export_output_dir)


def fetch_and_display_single_quote(symbol, simple=False, export_formats=None, output_dir=None):
    """Helper function to fetch and display a single quote with detailed view."""
    from app.utils.display import display_detailed_quote, create_progress_spinner
    from app.utils.export import export_quotes
    from app.models.stock import Quote
    
    try:
        # Show a spinner while fetching data
        with create_progress_spinner(description=f"Fetching quote for {symbol}...") as progress:
            task_id = progress.add_task("Downloading...", total=None)
            
            # Fetch the quote
            quote_data = client.get_quote(symbol)
            
            progress.update(task_id, completed=True)
        
        # Convert API response to Quote object
        quote = Quote.from_api_response(quote_data)
        
        # Display the quote with detailed view
        display_detailed_quote(quote, simplified=simple)
        
        # Export if requested
        if export_formats and output_dir:
            export_results = export_quotes([quote], export_formats, output_dir)
            
            if export_results:
                click.echo("\nExported quote to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
        # Return the quote for potential further processing
        return quote
        
    except TwelveDataAPIError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        logger.exception(f"Unexpected error fetching latest quote: {e}")
        click.echo(f"Unexpected error: {e}", err=True)

@stock.command(name="eod")
@click.argument("symbol", required=True)
@click.option("--date", "-d", help="Specific date in YYYY-MM-DD format (defaults to latest available)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export EOD data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def eod_command(symbol: str, date: str, export: str, output_dir: str, use_home_dir: bool):
    """
    Get the latest End of Day (EOD) price for a symbol.
    
    SYMBOL is the ticker symbol to get EOD data for (e.g., AAPL)
    """
    try:
        # Create a progress spinner
        with create_progress_spinner(f"Fetching EOD data for {symbol}...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get the EOD data
            eod_data = client.get_eod_price(symbol.upper(), date)
            
        # Display the EOD data
        display_eod_price(eod_data, symbol.upper())
        
        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']
            
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
            
            # Export the data
            from app.utils.export import export_to_json
            
            result_paths = {}
            if 'json' in export_formats:
                filename = f"eod_{symbol.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = export_output_dir / filename
                if export_to_json(eod_data, filepath):
                    result_paths['json'] = str(filepath)
            
            if 'csv' in export_formats:
                filename = f"eod_{symbol.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = export_output_dir / filename
                
                # Create CSV file manually as we don't have a dedicated EOD model with csv export
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(eod_data.keys()))
                    writer.writeheader()
                    writer.writerow({k: v for k, v in eod_data.items()})
                    result_paths['csv'] = str(filepath)
            
            # Display export results
            if result_paths:
                click.echo("\nExported EOD data to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error fetching EOD data: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)

@stock.command(name="gainers")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ', 'NYSE')")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of stocks to display")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def gainers_command(exchange: str, limit: int, export: str, output_dir: str, use_home_dir: bool):
    """
    Get the top gaining stocks for the day.
    """
    _fetch_and_display_market_movers("gainers", exchange, limit, export, output_dir, use_home_dir)
    
    
@stock.command(name="losers")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ', 'NYSE')")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of stocks to display")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def losers_command(exchange: str, limit: int, export: str, output_dir: str, use_home_dir: bool):
    """
    Get the top losing stocks for the day.
    """
    _fetch_and_display_market_movers("losers", exchange, limit, export, output_dir, use_home_dir)


def _fetch_and_display_market_movers(direction: str, exchange: Optional[str], limit: int, 
                                    export: Optional[str], output_dir: Optional[str], 
                                    use_home_dir: bool) -> None:
    """
    Helper function to fetch and display market movers.
    
    Args:
        direction: "gainers" for top gainers, "losers" for top losers
        exchange: Optional exchange to filter by
        limit: Maximum number of stocks to display
        export: Export format choice
        output_dir: Output directory for export
        use_home_dir: Whether to use the home directory for export
    """
    try:
        # Create a progress spinner
        direction_name = "gainers" if direction == "gainers" else "losers"
        with create_progress_spinner(f"Fetching top {direction_name}...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get the market movers
            movers = client.get_market_movers(direction, exchange, limit)
            
        # Display the movers
        display_market_movers(movers, direction_name)
        
        # Export if requested
        if export and movers:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']
            
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Current timestamp for filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            result_paths = {}
            
            # Export to JSON
            if 'json' in export_formats:
                filename = f"market_{direction_name}_{current_time}.json"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w') as f:
                        json.dump(movers, f, indent=2, default=str)
                    result_paths['json'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to JSON: {e}")
                    click.echo(f"Error exporting to JSON: {e}", err=True)
            
            # Export to CSV
            if 'csv' in export_formats:
                filename = f"market_{direction_name}_{current_time}.csv"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w', newline='') as f:
                        if movers:
                            fieldnames = movers[0].keys()
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            for mover in movers:
                                writer.writerow(mover)
                            result_paths['csv'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to CSV: {e}")
                    click.echo(f"Error exporting to CSV: {e}", err=True)
            
            # Display export results
            if result_paths:
                click.echo("\nExported market movers data to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
    
    except TwelveDataAPIError as e:
        logger.error(f"API Error: {e}")
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error fetching market movers: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)

@stock.group(name="mutual-funds")
def mutual_funds():
    """Commands for accessing mutual fund data."""
    pass


@mutual_funds.command(name="list")
@click.option("--exchange", "-e", help="Filter by exchange")
@click.option("--country", "-c", help="Filter by country")
@click.option("--family", "-f", help="Filter by fund family (e.g., 'Vanguard')")
@click.option("--search", "-s", help="Search by name or symbol")
@click.option("--limit", "-l", type=int, default=100,
              help="Maximum number of funds to display (default: 100, 0 for all)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_mutual_funds_detailed(exchange, country, family, search, limit, detailed,
                      export, output_dir, use_home_dir):
    """
    List available mutual funds with detailed information and filtering.

    Examples:
    \b
    # List all mutual funds (limited to 100 by default)
    stockcli stock mutual-funds list

    # List Vanguard mutual funds with detailed information
    stockcli stock mutual-funds list --family Vanguard --detailed

    # Search for mutual funds containing 'Index' in the name
    stockcli stock mutual-funds list --search Index
    """
    try:
        with create_progress_spinner("Fetching mutual funds...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get mutual funds from the API
            funds = client.get_mutual_funds(exchange=exchange, country=country)
            
            # Filter by fund family if specified
            if family:
                funds = [f for f in funds if family.lower() in (f.get('fund_family', '') or '').lower()]
                
            # Filter by search term if specified
            if search:
                search_term = search.lower()
                funds = [
                    f for f in funds 
                    if search_term in f.get('symbol', '').lower() 
                    or search_term in f.get('name', '').lower()
                    or search_term in (f.get('fund_category', '') or '').lower()
                ]
            
            # Convert API response to MutualFund objects
            from app.models.mutual_fund import MutualFund
            mutual_funds = [MutualFund.from_api_response(f) for f in funds]
            
            # Sort mutual funds by name
            mutual_funds.sort(key=lambda x: x.name)
        
        # Display the mutual funds
        if detailed:
            display_mutual_funds_detailed(mutual_funds, limit)
        else:
            display_funds_table(mutual_funds, limit, detailed)
            
        # Export if requested
        if export:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']
                
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Export the data
            from app.utils.export import export_items
            
            result = export_items(
                mutual_funds, 
                'mutual_funds', 
                export_formats, 
                export_output_dir
            )
            
            if result:
                click.echo("\nExported mutual funds to:")
                for fmt, path in result.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error listing mutual funds: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)


@mutual_funds.command(name="info")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_mutual_fund_profile(symbol, export, output_dir, use_home_dir):
    """
    Get detailed profile information for a specific mutual fund.

    SYMBOL is the mutual fund symbol (e.g., VTSAX, FXAIX)

    Examples:
    \b
    # Get detailed information for Vanguard Total Stock Market Index Fund
    stockcli stock mutual-funds info VTSAX

    # Export detailed information for Fidelity 500 Index Fund
    stockcli stock mutual-funds info FXAIX --export json
    """
    try:
        with create_progress_spinner(f"Fetching mutual fund profile for {symbol}...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get the mutual fund info from the API
            fund_data = client.get_mutual_fund_info(symbol.upper())
            
            if not fund_data:
                click.echo(f"No mutual fund found with symbol: {symbol}", err=True)
                return
                
            # Convert to MutualFund object
            from app.models.mutual_fund import MutualFund
            mutual_fund = MutualFund.from_api_response(fund_data)
            
        # Display the mutual fund profile
        display_mutual_fund_profile(mutual_fund)
        
        # Export if requested
        if export:
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Export to requested format
            result = {}
            if export == 'json':
                # Export to JSON
                filename = f"mutual_fund_{symbol.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = export_output_dir / filename
                
                from app.utils.export import export_to_json
                if export_to_json(mutual_fund.to_dict(), filepath):
                    result['json'] = str(filepath)
            elif export == 'csv':
                # Export to CSV
                filename = f"mutual_fund_{symbol.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = export_output_dir / filename
                
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=mutual_fund.get_csv_header())
                    writer.writeheader()
                    writer.writerow(mutual_fund.to_csv_row())
                    result['csv'] = str(filepath)
                    
            # Display export results
            if result:
                click.echo("\nExported mutual fund data to:")
                for fmt, path in result.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error getting mutual fund profile: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)


@mutual_funds.command(name="families")
@click.option("--search", "-s", help="Search for fund families by name")
@click.option("--limit", "-l", type=int, default=50, 
              help="Maximum number of fund families to display (default: 50, 0 for all)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_fund_families(search: str, limit: int, export: str, output_dir: str, use_home_dir: bool):
    """
    List available fund families with optional filtering.
    
    Examples:
    \b
    # List all fund families (limited to 50 by default)
    stockcli stock mutual-funds families
    
    # Search for fund families containing 'Vanguard' in the name
    stockcli stock mutual-funds families --search Vanguard
    
    # List all fund families and export to JSON
    stockcli stock mutual-funds families --limit 0 --export json
    """
    try:
        with create_progress_spinner("Fetching fund families...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get fund families from the API
            families = client.get_fund_families(search=search)
            
        # Display the fund families
        display_fund_families(families, limit)
        
        # Export if requested
        if export and families:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']
                
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Export the data
            result_paths = {}
            
            # Current timestamp for filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export to JSON
            if 'json' in export_formats:
                filename = f"fund_families_{current_time}.json"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w') as f:
                        json.dump(families, f, indent=2, default=str)
                    result_paths['json'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to JSON: {e}")
                    click.echo(f"Error exporting to JSON: {e}", err=True)
            
            # Export to CSV
            if 'csv' in export_formats:
                filename = f"fund_families_{current_time}.csv"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w', newline='') as f:
                        if families:
                            # Define field names, handling nested popular_funds field
                            fieldnames = ["name", "fund_count", "headquarters", "founded", "aum", "website"]
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            
                            # Write rows, flattening the data structure
                            for family in families:
                                row = {k: v for k, v in family.items() if k in fieldnames}
                                writer.writerow(row)
                                
                            result_paths['csv'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to CSV: {e}")
                    click.echo(f"Error exporting to CSV: {e}", err=True)
            
            # Display export results
            if result_paths:
                click.echo("\nExported fund families to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error listing fund families: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)


@mutual_funds.command(name="family")
@click.argument("name", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_fund_family_detail(name: str, export: str, output_dir: str, use_home_dir: bool):
    """
    Get detailed information about a specific fund family.
    
    NAME is the name of the fund family (e.g., Vanguard, Fidelity)
    
    Examples:
    \b
    # Get detailed information about Vanguard
    stockcli stock mutual-funds family Vanguard
    
    # Export Fidelity fund family details to JSON
    stockcli stock mutual-funds family Fidelity --export json
    """
    try:
        with create_progress_spinner(f"Fetching fund family details for {name}...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get the fund family detail from the API
            family_detail = client.get_fund_family_detail(name)
            
            if not family_detail:
                click.echo(f"No fund family found with name: {name}", err=True)
                return
                
        # Display the fund family detail
        display_fund_family_detail(family_detail)
        
        # Export if requested
        if export:
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Current timestamp for filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            result_paths = {}
            
            # Export to the requested format
            if export == 'json':
                filename = f"fund_family_{name.replace(' ', '_')}_{current_time}.json"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w') as f:
                        json.dump(family_detail, f, indent=2, default=str)
                    result_paths['json'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to JSON: {e}")
                    click.echo(f"Error exporting to JSON: {e}", err=True)
                    
            elif export == 'csv':
                filename = f"fund_family_{name.replace(' ', '_')}_{current_time}.csv"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w', newline='') as f:
                        # Define field names, handling nested structures
                        fieldnames = ["name", "fund_count", "headquarters", "founded", "aum", "website"]
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        # Write the row, flattening the data structure
                        row = {k: v for k, v in family_detail.items() if k in fieldnames}
                        writer.writerow(row)
                            
                        result_paths['csv'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to CSV: {e}")
                    click.echo(f"Error exporting to CSV: {e}", err=True)
                    
            # Display export results
            if result_paths:
                click.echo("\nExported fund family details to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error getting fund family details: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)

@mutual_funds.command(name="types")
@click.option("--limit", "-l", type=int, default=0,
              help="Maximum number of fund types to display (default: 0 = all)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_mutual_fund_types(limit: int, export: str, output_dir: str, use_home_dir: bool):
    """
    List available mutual fund types.
    
    Examples:
    \b
    # List all mutual fund types
    stockcli stock mutual-funds types
    
    # List top 10 mutual fund types
    stockcli stock mutual-funds types --limit 10
    
    # Export all fund types to JSON
    stockcli stock mutual-funds types --export json
    """
    try:
        with create_progress_spinner("Fetching mutual fund types...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get fund types from the API
            fund_types = client.get_mutual_fund_types()
            
        # Display the fund types
        display_mutual_fund_types(fund_types, limit)
        
        # Export if requested
        if export and fund_types:
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']
                
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Export the data
            result_paths = {}
            
            # Current timestamp for filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export to JSON
            if 'json' in export_formats:
                filename = f"fund_types_{current_time}.json"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w') as f:
                        json.dump(fund_types, f, indent=2, default=str)
                    result_paths['json'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to JSON: {e}")
                    click.echo(f"Error exporting to JSON: {e}", err=True)
            
            # Export to CSV
            if 'csv' in export_formats:
                filename = f"fund_types_{current_time}.csv"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w', newline='') as f:
                        if fund_types:
                            # Define field names
                            fieldnames = ["name", "count", "risk_level", "description"]
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            
                            # Write rows, excluding the example_funds field
                            for fund_type in fund_types:
                                row = {k: v for k, v in fund_type.items() if k in fieldnames}
                                writer.writerow(row)
                                
                            result_paths['csv'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to CSV: {e}")
                    click.echo(f"Error exporting to CSV: {e}", err=True)
            
            # Display export results
            if result_paths:
                click.echo("\nExported fund types to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error listing fund types: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)


@mutual_funds.command(name="type")
@click.argument("name", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_mutual_fund_type_detail(name: str, export: str, output_dir: str, use_home_dir: bool):
    """
    Get detailed information about a specific mutual fund type.
    
    NAME is the name of the fund type (e.g., Large Cap, Growth, Income)
    
    Examples:
    \b
    # Get detailed information about Large Cap funds
    stockcli stock mutual-funds type "Large Cap"
    
    # Get details about Growth funds and export to JSON
    stockcli stock mutual-funds type Growth --export json
    """
    try:
        with create_progress_spinner(f"Fetching details for fund type: {name}...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get the fund type detail from the API
            type_detail = client.get_mutual_fund_type_detail(name)
            
            if not type_detail:
                click.echo(f"No fund type found with name: {name}", err=True)
                return
                
        # Display the fund type detail
        display_mutual_fund_type_detail(type_detail)
        
        # Export if requested
        if export:
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Current timestamp for filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            result_paths = {}
            
            # Export to the requested format
            if export == 'json':
                filename = f"fund_type_{name.replace(' ', '_')}_{current_time}.json"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w') as f:
                        json.dump(type_detail, f, indent=2, default=str)
                    result_paths['json'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to JSON: {e}")
                    click.echo(f"Error exporting to JSON: {e}", err=True)
                    
            elif export == 'csv':
                filename = f"fund_type_{name.replace(' ', '_')}_{current_time}.csv"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w', newline='') as f:
                        # Define field names
                        fieldnames = ["name", "count", "risk_level", "description"]
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        # Write the row, excluding complex fields
                        row = {k: v for k, v in type_detail.items() if k in fieldnames}
                        writer.writerow(row)
                            
                        result_paths['csv'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to CSV: {e}")
                    click.echo(f"Error exporting to CSV: {e}", err=True)
                    
            # Display export results
            if result_paths:
                click.echo("\nExported fund type details to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error getting fund type details: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)


@stock.group(name="company")
def company():
    """Commands for accessing company information."""
    pass


@company.command(name="profile")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export company profile to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_company_profile(symbol: str, export: str, output_dir: str, use_home_dir: bool):
    """
    Get detailed profile information for a company.
    
    SYMBOL is the ticker symbol (e.g., AAPL, MSFT, AMZN)
    
    Examples:
    \b
    # Get Apple company profile
    stockcli stock company profile AAPL
    
    # Get Microsoft company profile and export to JSON
    stockcli stock company profile MSFT --export json
    """
    try:
        with create_progress_spinner(f"Fetching company profile for {symbol}...") as progress:
            progress.add_task("Loading...", total=None)
            
            # Get the company profile from the API
            profile_data = client.get_company_profile(symbol.upper())
            
            if not profile_data:
                click.echo(f"No company profile found for symbol: {symbol}", err=True)
                return
                
            # Convert to CompanyProfile object
            from app.models.company import CompanyProfile
            company_profile = CompanyProfile.from_api_response(profile_data)
                
        # Display the company profile
        display_company_profile(company_profile)
        
        # Export if requested
        if export:
            # Handle output directory
            export_output_dir = None
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            # Current timestamp for filename
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            result_paths = {}
            
            # Export to the requested format
            if export == 'json':
                filename = f"company_{symbol.upper()}_{current_time}.json"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w') as f:
                        json.dump(company_profile.to_dict(), f, indent=2, default=str)
                    result_paths['json'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to JSON: {e}")
                    click.echo(f"Error exporting to JSON: {e}", err=True)
                    
            elif export == 'csv':
                filename = f"company_{symbol.upper()}_{current_time}.csv"
                filepath = export_output_dir / filename
                
                try:
                    ensure_directory(filepath)
                    with open(filepath, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=company_profile.get_csv_header())
                        writer.writeheader()
                        writer.writerow(company_profile.to_csv_row())
                        result_paths['csv'] = str(filepath)
                except Exception as e:
                    logger.error(f"Error exporting to CSV: {e}")
                    click.echo(f"Error exporting to CSV: {e}", err=True)
                    
            # Display export results
            if result_paths:
                click.echo("\nExported company profile to:")
                for fmt, path in result_paths.items():
                    click.echo(f"  {fmt.upper()}: {path}")
                    
    except TwelveDataAPIError as e:
        click.echo(f"API Error: {e}", err=True)
    except Exception as e:
        logger.error(f"Error getting company profile: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)

# This contains CLI commands to be added to commands.py

@stock.group(name="dividends")
def dividend_commands():
    """Commands for accessing dividend data."""
    pass


@dividend_commands.command(name="history")
@click.argument("symbol", required=True)
@click.option("--years", "-y", default=10, type=int, 
              help="Number of years of history to retrieve (default: 10)")
@click.option("--detailed", "-d", is_flag=True, 
              help="Show detailed dividend payment information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export dividend history to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_dividend_history_command(symbol: str, years: int, detailed: bool,
                                export: str, output_dir: str, use_home_dir: bool):
    """
    Get dividend payment history for a stock symbol.
    
    Example: stockcli dividends history AAPL --years 10 --detailed
    """
    symbol = symbol.upper()
    logger.info(f"Fetching {years} years of dividend history for {symbol}")
    
    # Create a progress spinner
    with create_progress_spinner(f"Fetching dividend data for {symbol}...") as progress:
        try:
            # Get dividend data from API
            dividend_data = client.get_dividend_history(symbol, years)
            
            # Parse the response into a DividendHistory object
            from app.models.dividend import DividendHistory
            dividend_history = DividendHistory.from_api_response(dividend_data)
            
            # Display the dividend history
            from app.utils.display import display_dividend_history
            display_dividend_history(dividend_history, detailed)
            
            # Handle export if requested
            if export:
                export_formats = []
                if export == 'json':
                    export_formats = ['json']
                elif export == 'csv':
                    export_formats = ['csv']
                elif export == 'both':
                    export_formats = ['json', 'csv']
                
                # Determine output directory
                if output_dir:
                    export_output_dir = Path(output_dir).expanduser().resolve()
                elif use_home_dir:
                    export_output_dir = get_home_export_dir()
                else:
                    export_output_dir = get_default_export_dir()
                
                # Export the data
                export_results = export_dividend_history(
                    dividend_history, export_formats, export_output_dir
                )
                
                if export_results:
                    click.echo("\nExported dividend history to:")
                    for fmt, path in export_results.items():
                        click.echo(f"  {fmt.upper()}: {path}")
            
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}", err=True)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            click.echo(f"An unexpected error occurred: {e}", err=True)


@dividend_commands.command(name="compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--years", "-y", default=10, type=int, 
              help="Number of years of history to retrieve (default: 10)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_dividends_command(symbols: List[str], years: int,
                             export: str, output_dir: str, use_home_dir: bool):
    """
    Compare dividend histories of multiple stock symbols.
    
    Example: stockcli dividends compare AAPL MSFT JNJ --years 10
    """
    if not symbols:
        click.echo("Error: At least one symbol is required.", err=True)
        return
    
    symbols = [symbol.upper() for symbol in symbols]
    logger.info(f"Comparing {years} years of dividend history for: {', '.join(symbols)}")
    
    # Create a progress spinner
    with create_progress_spinner(f"Fetching dividend data...") as progress:
        try:
            dividend_histories = []
            failed_symbols = []
            
            # Get dividend data for each symbol
            for symbol in symbols:
                progress.update(f"Fetching dividend data for {symbol}...")
                try:
                    dividend_data = client.get_dividend_history(symbol, years)
                    from app.models.dividend import DividendHistory
                    history = DividendHistory.from_api_response(dividend_data)
                    dividend_histories.append(history)
                except Exception as e:
                    logger.warning(f"Failed to fetch dividend data for {symbol}: {e}")
                    failed_symbols.append(symbol)
            
            # Report any failures
            if failed_symbols:
                click.echo(f"Warning: Failed to fetch data for: {', '.join(failed_symbols)}", err=True)
            
            # Display the comparison
            if dividend_histories:
                from app.utils.display import display_dividend_comparison
                display_dividend_comparison(symbols, dividend_histories)
                
                # Handle export if requested
                if export:
                    export_formats = []
                    if export == 'json':
                        export_formats = ['json']
                    elif export == 'csv':
                        export_formats = ['csv']
                    elif export == 'both':
                        export_formats = ['json', 'csv']
                    
                    # Determine output directory
                    if output_dir:
                        export_output_dir = Path(output_dir).expanduser().resolve()
                    elif use_home_dir:
                        export_output_dir = get_home_export_dir()
                    else:
                        export_output_dir = get_default_export_dir()
                    
                    # Export the data
                    export_results = export_dividend_comparison(
                        dividend_histories, export_formats, export_output_dir
                    )
                    
                    if export_results:
                        click.echo("\nExported dividend comparison to:")
                        for fmt, path in export_results.items():
                            click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo("No dividend data available for the specified symbols.", err=True)
            
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            click.echo(f"An unexpected error occurred: {e}", err=True)

@dividend_commands.command(name="calendar")
@click.option("--start-date", "-s", 
              help="Start date in YYYY-MM-DD format (required unless --range is specified)")
@click.option("--end-date", "-e", 
              help="End date in YYYY-MM-DD format (required unless --range is specified)")
@click.option("--range", "-r", type=click.Choice(['today', 'week', 'month', 'quarter', 'year']),
              help="Predefined date range (alternative to start/end dates)")
@click.option("--symbol", help="Filter by symbol")
@click.option("--exchange", help="Filter by exchange")
@click.option("--view", "-v", type=click.Choice(['calendar', 'list', 'summary']), 
              default='calendar', help="View mode (default: calendar)")
@click.option("--date-field", "-d", type=click.Choice(['ex_dividend_date', 'payment_date', 'record_date', 'declaration_date']),
              default='ex_dividend_date', help="Date field to organize by (default: ex_dividend_date)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export dividend calendar to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def dividend_calendar_command(start_date: Optional[str], end_date: Optional[str],
                              range: Optional[str], symbol: Optional[str],
                              exchange: Optional[str], view: str, date_field: str,
                              export: Optional[str], output_dir: Optional[str],
                              use_home_dir: bool):
    """
    Get dividend calendar for a specified date range.
    
    Examples:
    
    - Get dividend calendar for this month:
      stockcli dividends calendar --range month
    
    - Get dividend calendar for a custom date range:
      stockcli dividends calendar --start-date 2023-01-01 --end-date 2023-03-31
    
    - Get dividend calendar for a specific symbol:
      stockcli dividends calendar --range quarter --symbol AAPL
    
    - View as a list instead of calendar:
      stockcli dividends calendar --range month --view list
    
    - View summary by symbol:
      stockcli dividends calendar --range month --view summary
    
    - Organize by payment date instead of ex-dividend date:
      stockcli dividends calendar --range month --date-field payment_date
    """
    logger.info(f"Fetching dividend calendar with range: {range or f'{start_date} to {end_date}'}")
    
    # Validate parameters
    if not range and not (start_date and end_date):
        click.echo(
            "Error: Either --range OR both --start-date and --end-date must be specified.", 
            err=True
        )
        return
    
    # Create a progress spinner
    with create_progress_spinner(f"Fetching dividend calendar...") as progress:
        try:
            # Get dividend calendar data from API
            calendar_data = client.get_dividend_calendar(
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                exchange=exchange,
                range_type=range
            )
            
            # Parse the response into a DividendCalendar object
            from app.models.divided_calendar import DividendCalendar
            
            # Determine start and end dates for display purposes
            if range and not (start_date and end_date):
                today = date.today()
                if range == 'today':
                    start_date = end_date = today.strftime("%Y-%m-%d")
                elif range == 'week':
                    # Start of current week (Monday)
                    start_of_week = today - timedelta(days=today.weekday())
                    end_of_week = start_of_week + timedelta(days=6)  # Sunday
                    start_date = start_of_week.strftime("%Y-%m-%d")
                    end_date = end_of_week.strftime("%Y-%m-%d")
                elif range == 'month':
                    # Start of current month
                    start_of_month = date(today.year, today.month, 1)
                    # End of current month
                    if today.month == 12:
                        end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)
                    start_date = start_of_month.strftime("%Y-%m-%d")
                    end_date = end_of_month.strftime("%Y-%m-%d")
                elif range == 'quarter':
                    # Determine current quarter
                    quarter = (today.month - 1) // 3 + 1
                    start_month = (quarter - 1) * 3 + 1
                    end_month = quarter * 3
                    # Start of current quarter
                    start_of_quarter = date(today.year, start_month, 1)
                    # End of current quarter
                    if end_month == 12:
                        end_of_quarter = date(today.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_of_quarter = date(today.year, end_month + 1, 1) - timedelta(days=1)
                    start_date = start_of_quarter.strftime("%Y-%m-%d")
                    end_date = end_of_quarter.strftime("%Y-%m-%d")
                elif range == 'year':
                    # Calendar year
                    start_of_year = date(today.year, 1, 1)
                    end_of_year = date(today.year, 12, 31)
                    start_date = start_of_year.strftime("%Y-%m-%d")
                    end_date = end_of_year.strftime("%Y-%m-%d")
            
            # Create the calendar object
            dividend_calendar = DividendCalendar.from_api_response(
                calendar_data,
                start_date=start_date,
                end_date=end_date
            )
            
            # Display the dividend calendar
            from app.utils.display import display_dividend_calendar
            display_dividend_calendar(
                dividend_calendar, 
                view_mode=view,
                date_field=date_field
            )
            
            # Handle export if requested
            if export:
                export_formats = []
                if export == 'json':
                    export_formats = ['json']
                elif export == 'csv':
                    export_formats = ['csv']
                elif export == 'both':
                    export_formats = ['json', 'csv']
                
                # Determine output directory
                if output_dir:
                    export_output_dir = Path(output_dir).expanduser().resolve()
                elif use_home_dir:
                    export_output_dir = get_home_export_dir()
                else:
                    export_output_dir = get_default_export_dir()
                
                # Export the data
                export_results = export_dividend_calendar(
                    dividend_calendar, export_formats, export_output_dir, view
                )
                
                if export_results:
                    click.echo("\nExported dividend calendar to:")
                    for fmt, path in export_results.items():
                        click.echo(f"  {fmt.upper()}: {path}")
            
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}", err=True)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            click.echo(f"An unexpected error occurred: {e}", err=True)

@stock.group(name="splits")
def splits_commands():
    """Commands for accessing stock splits data."""
    pass


@splits_commands.command(name="history")
@click.argument("symbol", required=True)
@click.option("--years", "-y", default=10, type=int, 
              help="Number of years of history to retrieve (default: 10)")
@click.option("--detailed", "-d", is_flag=True, 
              help="Show detailed split information")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export splits history to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_stock_splits_command(symbol: str, years: int, detailed: bool,
                          export: str, output_dir: str, use_home_dir: bool):
    """
    Get stock splits history for a stock symbol.
    
    Example: stockcli splits history AAPL --years 20 --detailed
    """
    symbol = symbol.upper()
    logger.info(f"Fetching {years} years of stock splits history for {symbol}")
    
    # Create a progress spinner
    with create_progress_spinner(f"Fetching stock splits for {symbol}...") as progress:
        try:
            # Get splits data from API
            splits_data = client.get_stock_splits(symbol, years)
            
            # Parse the response into a SplitHistory object
            from app.models.splits import SplitHistory
            split_history = SplitHistory.from_api_response(splits_data, symbol)
            
            # Display the splits history
            from app.utils.display import display_stock_splits
            display_stock_splits(split_history, detailed)
            
            # Handle export if requested
            if export:
                export_formats = []
                if export == 'json':
                    export_formats = ['json']
                elif export == 'csv':
                    export_formats = ['csv']
                elif export == 'both':
                    export_formats = ['json', 'csv']
                
                # Determine output directory
                if output_dir:
                    export_output_dir = Path(output_dir).expanduser().resolve()
                elif use_home_dir:
                    export_output_dir = get_home_export_dir()
                else:
                    export_output_dir = get_default_export_dir()
                
                # Export the data
                export_results = export_stock_splits(
                    split_history, export_formats, export_output_dir
                )
                
                if export_results:
                    click.echo("\nExported stock splits history to:")
                    for fmt, path in export_results.items():
                        click.echo(f"  {fmt.upper()}: {path}")
            
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}", err=True)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            click.echo(f"An unexpected error occurred: {e}", err=True)


@splits_commands.command(name="compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--years", "-y", default=10, type=int, 
              help="Number of years of history to retrieve (default: 10)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_stock_splits_command(symbols: List[str], years: int,
                               export: str, output_dir: str, use_home_dir: bool):
    """
    Compare stock splits histories of multiple stock symbols.
    
    Example: stockcli splits compare AAPL MSFT GOOG --years 15
    """
    if not symbols:
        click.echo("Error: At least one symbol is required.", err=True)
        return
    
    symbols = [symbol.upper() for symbol in symbols]
    logger.info(f"Comparing {years} years of stock splits history for: {', '.join(symbols)}")
    
    # Create a progress spinner
    with create_progress_spinner(f"Fetching stock splits data...") as progress:
        try:
            split_histories = []
            failed_symbols = []
            
            # Get splits data for each symbol
            for symbol in symbols:
                progress.update(f"Fetching stock splits for {symbol}...")
                try:
                    splits_data = client.get_stock_splits(symbol, years)
                    from app.models.splits import SplitHistory
                    history = SplitHistory.from_api_response(splits_data, symbol)
                    split_histories.append(history)
                except Exception as e:
                    logger.warning(f"Failed to fetch stock splits for {symbol}: {e}")
                    failed_symbols.append(symbol)
            
            # Report any failures
            if failed_symbols:
                click.echo(f"Warning: Failed to fetch data for: {', '.join(failed_symbols)}", err=True)
            
            # Display the comparison
            if split_histories:
                from app.utils.display import display_stock_splits_comparison
                display_stock_splits_comparison(symbols, split_histories)
                
                # Handle export if requested
                if export:
                    export_formats = []
                    if export == 'json':
                        export_formats = ['json']
                    elif export == 'csv':
                        export_formats = ['csv']
                    elif export == 'both':
                        export_formats = ['json', 'csv']
                    
                    # Determine output directory
                    if output_dir:
                        export_output_dir = Path(output_dir).expanduser().resolve()
                    elif use_home_dir:
                        export_output_dir = get_home_export_dir()
                    else:
                        export_output_dir = get_default_export_dir()
                    
                    # Export the data
                    export_results = export_stock_splits_comparison(
                        split_histories, export_formats, export_output_dir
                    )
                    
                    if export_results:
                        click.echo("\nExported stock splits comparison to:")
                        for fmt, path in export_results.items():
                            click.echo(f"  {fmt.upper()}: {path}")
            else:
                click.echo("No stock splits data available for the specified symbols.", err=True)
            
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            click.echo(f"An unexpected error occurred: {e}", err=True)

@splits_commands.command(name="calendar")
@click.option("--start-date", "-s", 
              help="Start date in YYYY-MM-DD format (required unless --range is specified)")
@click.option("--end-date", "-e", 
              help="End date in YYYY-MM-DD format (required unless --range is specified)")
@click.option("--range", "-r", type=click.Choice(['today', 'week', 'month', 'quarter', 'year']),
              help="Predefined date range (alternative to start/end dates)")
@click.option("--symbol", help="Filter by symbol")
@click.option("--exchange", help="Filter by exchange")
@click.option("--view", "-v", type=click.Choice(['calendar', 'list', 'summary']), 
              default='calendar', help="View mode (default: calendar)")
@click.option("--forward-only", is_flag=True, help="Show only forward splits")
@click.option("--reverse-only", is_flag=True, help="Show only reverse splits")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export splits calendar to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def splits_calendar_command(start_date: Optional[str], end_date: Optional[str],
                          range: Optional[str], symbol: Optional[str],
                          exchange: Optional[str], view: str,
                          forward_only: bool, reverse_only: bool,
                          export: Optional[str], output_dir: Optional[str],
                          use_home_dir: bool):
    """
    Get stock splits calendar for a specified date range.
    
    Examples:
    
    - Get stock splits calendar for this month:
      stockcli splits calendar --range month
    
    - Get stock splits calendar for a custom date range:
      stockcli splits calendar --start-date 2023-01-01 --end-date 2023-03-31
    
    - Get stock splits calendar for a specific symbol:
      stockcli splits calendar --range quarter --symbol AAPL
    
    - View as a list instead of calendar:
      stockcli splits calendar --range month --view list
    
    - View only forward or reverse splits:
      stockcli splits calendar --range month --forward-only
      stockcli splits calendar --range month --reverse-only
    
    - Export to CSV:
      stockcli splits calendar --range month --export csv
    """
    logger.info(f"Fetching splits calendar with range: {range or f'{start_date} to {end_date}'}")
    
    # Validate parameters
    if not range and not (start_date and end_date):
        click.echo(
            "Error: Either --range OR both --start-date and --end-date must be specified.", 
            err=True
        )
        return
    
    if forward_only and reverse_only:
        click.echo(
            "Error: Cannot specify both --forward-only and --reverse-only at the same time.", 
            err=True
        )
        return
    
    # Create a progress spinner
    with create_progress_spinner(f"Fetching stock splits calendar...") as progress:
        try:
            # Get splits calendar data from API
            calendar_data = client.get_splits_calendar(
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                exchange=exchange,
                range_type=range
            )
            
            # Parse the response into a SplitsCalendar object
            from app.models.splits_calendar import SplitsCalendar
            
            # Determine start and end dates for display purposes
            if range and not (start_date and end_date):
                today = date.today()
                if range == 'today':
                    start_date = end_date = today.strftime("%Y-%m-%d")
                elif range == 'week':
                    # Start of current week (Monday)
                    start_of_week = today - timedelta(days=today.weekday())
                    end_of_week = start_of_week + timedelta(days=6)  # Sunday
                    start_date = start_of_week.strftime("%Y-%m-%d")
                    end_date = end_of_week.strftime("%Y-%m-%d")
                elif range == 'month':
                    # Start of current month
                    start_of_month = date(today.year, today.month, 1)
                    # End of current month
                    if today.month == 12:
                        end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)
                    start_date = start_of_month.strftime("%Y-%m-%d")
                    end_date = end_of_month.strftime("%Y-%m-%d")
                elif range == 'quarter':
                    # Determine current quarter
                    quarter = (today.month - 1) // 3 + 1
                    start_month = (quarter - 1) * 3 + 1
                    end_month = quarter * 3
                    # Start of current quarter
                    start_of_quarter = date(today.year, start_month, 1)
                    # End of current quarter
                    if end_month == 12:
                        end_of_quarter = date(today.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_of_quarter = date(today.year, end_month + 1, 1) - timedelta(days=1)
                    start_date = start_of_quarter.strftime("%Y-%m-%d")
                    end_date = end_of_quarter.strftime("%Y-%m-%d")
                elif range == 'year':
                    # Calendar year
                    start_of_year = date(today.year, 1, 1)
                    end_of_year = date(today.year, 12, 31)
                    start_date = start_of_year.strftime("%Y-%m-%d")
                    end_date = end_of_year.strftime("%Y-%m-%d")
            
            # Create the calendar object
            splits_calendar = SplitsCalendar.from_api_response(
                calendar_data,
                start_date=start_date,
                end_date=end_date
            )
            
            # Apply forward or reverse filters if requested
            if forward_only:
                splits_calendar = splits_calendar.filter_by_split_type(is_forward=True)
            elif reverse_only:
                splits_calendar = splits_calendar.filter_by_split_type(is_forward=False)
            
            # Display the splits calendar
            from app.utils.display import display_splits_calendar
            display_splits_calendar(
                splits_calendar, 
                view_mode=view
            )
            
            # Handle export if requested
            if export:
                export_formats = []
                if export == 'json':
                    export_formats = ['json']
                elif export == 'csv':
                    export_formats = ['csv']
                elif export == 'both':
                    export_formats = ['json', 'csv']
                
                # Determine output directory
                if output_dir:
                    export_output_dir = Path(output_dir).expanduser().resolve()
                elif use_home_dir:
                    export_output_dir = get_home_export_dir()
                else:
                    export_output_dir = get_default_export_dir()
                
                # Export the data
                export_results = export_splits_calendar(
                    splits_calendar, export_formats, export_output_dir, view
                )
                
                if export_results:
                    click.echo("\nExported stock splits calendar to:")
                    for fmt, path in export_results.items():
                        click.echo(f"  {fmt.upper()}: {path}")
            
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}", err=True)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            click.echo(f"An unexpected error occurred: {e}", err=True)

@stock.group(name="income-statement")
def income_statement_group():
    """Commands for retrieving company income statements."""
    pass


@income_statement_group.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed income statement")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export income statement to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_income_statement_command(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """
    Get income statement for a company.
    
    Retrieves the income statement for a given company symbol, showing revenue, 
    expenses, and profitability metrics.
    
    Examples:
        stockcli income-statement get AAPL --period annual
        stockcli income-statement get MSFT --period quarter --count 4 --detailed
    """
    from app.models.income_statement import IncomeStatement
    from app.utils.display import display_income_statement
    from app.utils.export import export_income_statement, get_default_export_dir, get_home_export_dir
    
    
    with create_progress_spinner(f"Fetching {period} income statement for {symbol}..."):
        try:
            response = client.get_income_statement(symbol, period, count)
            income_statements = []
            
            for item in response.get('income_statement', []):
                income_statement = IncomeStatement.from_api_response(item)
                income_statements.append(income_statement)
            
            if not income_statements:
                click.echo(f"No income statement data available for {symbol}")
                return
        
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display the most recent statement
    most_recent = income_statements[0] if income_statements else None
    if most_recent:
        display_income_statement(most_recent, detailed)
        
        # Export if requested
        if export:
            # Determine export formats
            export_formats = []
            if export == 'json':
                export_formats = ['json']
            elif export == 'csv':
                export_formats = ['csv']
            elif export == 'both':
                export_formats = ['json', 'csv']
                
            # Determine output directory
            if output_dir:
                export_output_dir = Path(output_dir).expanduser().resolve()
            elif use_home_dir:
                export_output_dir = get_home_export_dir()
            else:
                export_output_dir = get_default_export_dir()
                
            export_results = export_income_statement(most_recent, export_formats, export_output_dir)
            
            if export_results:
                click.echo("\nExported income statement to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")


@income_statement_group.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--expenses", "-e", is_flag=True, 
              help="Focus on expense breakdown comparison")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_income_statements_command(symbol, period, count, expenses, export, output_dir, use_home_dir):
    """
    Compare income statements across multiple periods.
    
    Display income statements side-by-side to analyze trends in revenue, 
    expenses, and profitability over time.
    
    Examples:
        stockcli income-statement compare AAPL
        stockcli income-statement compare MSFT --period quarter --count 8 --expenses
    """
    from app.models.income_statement import IncomeStatement
    from app.utils.display import display_income_statement_comparison
    from app.utils.export import export_income_statements, get_default_export_dir, get_home_export_dir
        
    with create_progress_spinner(f"Fetching {period} income statements for {symbol}..."):
        try:
            response = client.get_income_statement(symbol, period, count)
            income_statements = []
            
            for item in response.get('income_statement', []):
                income_statement = IncomeStatement.from_api_response(item)
                income_statements.append(income_statement)
            
            if not income_statements:
                click.echo(f"No income statement data available for {symbol}")
                return
                
            # Sort by date (most recent first)
            income_statements.sort(key=lambda s: s.fiscal_date, reverse=True)
        
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display comparison
    display_income_statement_comparison(income_statements, expense_focus=expenses)
    
    # Export if requested
    if export:
        # Determine export formats
        export_formats = []
        if export == 'json':
            export_formats = ['json']
        elif export == 'csv':
            export_formats = ['csv']
        elif export == 'both':
            export_formats = ['json', 'csv']
            
        # Determine output directory
        if output_dir:
            export_output_dir = Path(output_dir).expanduser().resolve()
        elif use_home_dir:
            export_output_dir = get_home_export_dir()
        else:
            export_output_dir = get_default_export_dir()
            
        export_results = export_income_statements(income_statements, export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported income statements to:")
            for fmt, path in export_results.items():
                if isinstance(path, list):
                    click.echo(f"  {fmt.upper()}: Multiple files in {Path(path[0]).parent}")
                else:
                    click.echo(f"  {fmt.upper()}: {path}")


@income_statement_group.command(name="expenses")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--fiscal-date", "-d", 
              help="Specific fiscal date (e.g. '2023-09-30'). Uses most recent if not specified.")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export expense breakdown to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def expense_breakdown_command(symbol, period, fiscal_date, export, output_dir, use_home_dir):
    """
    Show detailed expense breakdown for a company.
    
    Analyzes and visualizes the expense structure of a company, showing
    relative proportions of different expense categories.
    
    Examples:
        stockcli income-statement expenses AAPL
        stockcli income-statement expenses MSFT --period quarter --fiscal-date 2023-03-31
    """
    from app.models.income_statement import IncomeStatement
    from app.utils.display import display_expense_breakdown
    from app.utils.export import export_expense_breakdown, get_default_export_dir, get_home_export_dir
    
    
    with create_progress_spinner(f"Fetching {period} income statement for {symbol}..."):
        try:
            # We'll fetch the most recent statements (or more if fiscal date is specified)
            fetch_count = 10 if fiscal_date else 1
            response = client.get_income_statement(symbol, period, fetch_count)
            income_statements = []
            
            for item in response.get('income_statement', []):
                income_statement = IncomeStatement.from_api_response(item)
                income_statements.append(income_statement)
            
            if not income_statements:
                click.echo(f"No income statement data available for {symbol}")
                return
                
            # Sort by date (most recent first)
            income_statements.sort(key=lambda s: s.fiscal_date, reverse=True)
            
            # If fiscal date specified, find matching statement
            target_statement = None
            if fiscal_date:
                target_statement = next((s for s in income_statements if s.fiscal_date == fiscal_date), None)
                if not target_statement:
                    click.echo(f"No income statement found for fiscal date {fiscal_date}")
                    click.echo("Available fiscal dates:")
                    for s in income_statements:
                        click.echo(f"  {s.fiscal_date}")
                    return
            else:
                # Use most recent statement
                target_statement = income_statements[0]
        
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display expense breakdown
    display_expense_breakdown(target_statement)
    
    # Export if requested
    if export:
        # Determine export formats
        export_formats = []
        if export == 'json':
            export_formats = ['json']
        elif export == 'csv':
            export_formats = ['csv']
        elif export == 'both':
            export_formats = ['json', 'csv']
            
        # Determine output directory
        if output_dir:
            export_output_dir = Path(output_dir).expanduser().resolve()
        elif use_home_dir:
            export_output_dir = get_home_export_dir()
        else:
            export_output_dir = get_default_export_dir()
            
        export_results = export_expense_breakdown(target_statement, export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported expense breakdown to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


