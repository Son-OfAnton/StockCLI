#!/usr/bin/env python3
"""
Stock CLI - Main entry point for the application.
This file will setup and run the CLI commands.
"""

import sys
import logging
import click
from app.cli.commands import stock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Stock CLI - A command-line tool for fetching and analyzing stock data."""
    pass


# Register command groups
cli.add_command(stock)

# Additional top-level commands can be added here


@cli.command()
def version():
    """Show the application version."""
    click.echo("Stock CLI v0.1.0")


@cli.command(name="quote")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--refresh", "-r", is_flag=True, help="Enable auto-refresh of quotes")
@click.option("--interval", "-i", default=10, help="Refresh interval in seconds (default: 10)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed quote information")
@click.option("--debug", is_flag=True, help="Enable debug output")
def quote_shortcut(symbols, refresh, interval, detailed, debug):
    """Shortcut for 'stock quote' command."""
    from app.cli.commands import fetch_and_display_quotes, refresh_quotes

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    symbols = [s.upper() for s in symbols]

    if refresh:
        refresh_quotes(symbols, interval, detailed, debug)
    else:
        fetch_and_display_quotes(symbols, detailed, debug)


def main():
    """Main entry point for the CLI app."""
    try:
        cli()
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
