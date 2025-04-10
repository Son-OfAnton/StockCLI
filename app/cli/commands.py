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

from app.api.twelve_data import client
from app.models.stock import Quote
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
