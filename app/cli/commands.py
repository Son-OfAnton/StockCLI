"""
CLI commands for the stock application.
"""

import click
import time
import threading
import logging
from typing import List, Optional
from datetime import datetime

from app.api.twelve_data import TwelveDataClient
from app.models.stock import Quote
from app.utils.helpers import (
    display_quotes_table, clear_screen, get_color_for_change, format_change
)
from app.config.settings import get_api_key

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
def quote(symbols: List[str], refresh: bool, interval: int, detailed: bool, debug: bool):
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
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    logger.info(
        f"Quote command called with symbols: {symbols}, refresh: {refresh}, interval: {interval}")

    if interval < 1:
        raise click.BadParameter("Interval must be at least 1 second")

    symbols = [s.upper() for s in symbols]

    # Check API key first
    api_key = get_api_key()
    if not api_key:
        click.echo("Error: API key not found. Please set the TWELVEDATA_API_KEY environment variable "
                   "or configure it in ~/.stock_cli/config.ini")
        logger.error("API key not found")
        return

    if refresh:
        # Start auto-refresh in background thread
        refresh_quotes(symbols, interval, detailed, debug)
    else:
        # Fetch quotes once
        fetch_and_display_quotes(symbols, detailed, debug)


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


def fetch_and_display_quotes(symbols: List[str], detailed: bool = False, debug: bool = False) -> None:
    """Fetch and display quotes for the given symbols."""
    api_key = get_api_key()
    if not api_key:
        click.echo("Error: API key not found. Please set the TWELVEDATA_API_KEY environment variable "
                   "or configure it in ~/.stock_cli/config.ini")
        logger.error("API key not found")
        return

    if debug:
        click.echo(f"Using API key: {api_key[:4]}...{api_key[-4:]}")

    client = TwelveDataClient(api_key)

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
                return
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
            return

        display_quotes_table(quotes, detailed)

    except Exception as e:
        logger.error(f"Error fetching quotes: {e}", exc_info=True)
        click.echo(f"Error fetching quotes: {e}")
        if debug:
            import traceback
            click.echo(traceback.format_exc())


def refresh_quotes(symbols: List[str], interval: int, detailed: bool, debug: bool = False) -> None:
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
        args=(symbols, interval, detailed, debug),
        daemon=True
    )
    _refresh_thread.start()

    click.echo(
        f"Auto-refresh started for {', '.join(symbols)} every {interval} seconds.")
    click.echo("Press Ctrl+C to stop, or run 'stockcli stock stop'")


def _refresh_worker(symbols: List[str], interval: int, detailed: bool, debug: bool = False) -> None:
    """Worker function for the refresh thread."""
    try:
        while not _stop_refresh.is_set():
            clear_screen()
            click.echo(
                f"Auto-refreshing quotes for {', '.join(symbols)} every {interval} seconds.")
            click.echo(
                f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo("Press Ctrl+C to stop")
            click.echo()

            fetch_and_display_quotes(symbols, detailed, debug)

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
