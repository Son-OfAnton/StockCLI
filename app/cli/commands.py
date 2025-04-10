"""
CLI commands for the stock application.
"""

import click

@click.group()
def stock():
    """Commands for interacting with stock data."""
    pass

@stock.command()
@click.argument("symbol")
def quote(symbol):
    """Get current stock quote for SYMBOL."""
    pass

@stock.command()
@click.argument("symbol")
@click.option("--interval", "-i", default="1day", help="Time interval between data points")
@click.option("--start", help="Start date (YYYY-MM-DD)")
@click.option("--end", help="End date (YYYY-MM-DD)")
def history(symbol, interval, start, end):
    """Get historical price data for SYMBOL."""
    pass

@stock.command()
@click.argument("symbol")
@click.argument("indicator")
@click.option("--period", "-p", default=14, help="Period for the indicator calculation")
def indicator(symbol, indicator, period):
    """Calculate technical indicator for SYMBOL."""
    pass