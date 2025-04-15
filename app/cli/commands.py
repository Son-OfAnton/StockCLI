"""
CLI commands for the stock application.
"""

import click
import time
import threading
import logging
from typing import List, Optional, Union
from datetime import datetime
from pathlib import Path

from app.api.twelve_data import TwelveDataAPIError, client
from app.models.bond import Bond
from app.models.commodity import CommodityGroup, CommodityPair
from app.models.etf import ETF
from app.models.stock import Quote
from app.models.symbol import Symbol
from app.utils.display import create_progress_spinner, display_bonds, display_bonds_detailed, display_commodity_groups, display_commodity_pairs, display_commodity_pairs_detailed, display_cross_listed_symbols, display_etfs, display_etfs_detailed
from app.utils.helpers import (
    display_quotes_table, clear_screen
)
from app.utils.export import (
    export_quotes, get_default_export_dir, get_home_export_dir
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
            click.echo(f"Warning: Could not parse all cross-listed symbols: {e}")
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
                    json_file = export_dir / f"cross_listed_symbols_{timestamp}.json"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    
                    with open(json_file, 'w') as f:
                        json.dump(raw_data, f, indent=2)
                    
                    exported_files["json"] = str(json_file)
                
                # Export as CSV (if possible)
                if "csv" in export_formats and isinstance(raw_data, list):
                    csv_file = export_dir / f"cross_listed_symbols_{timestamp}.csv"
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