"""
Utility functions for displaying data in the console.
"""

import logging
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from app.models.symbol import Symbol, Exchange

# Console setup for rich output
console = Console()
logger = logging.getLogger(__name__)


def display_symbols_table(symbols: List[Symbol], limit: Optional[int] = None,
                          show_details: bool = False) -> None:
    """
    Display a list of symbols in a formatted table.

    Args:
        symbols: List of Symbol objects to display
        limit: Maximum number of symbols to display
        show_details: Whether to show additional details
    """
    if not symbols:
        console.print(
            "[yellow]No symbols found matching the criteria.[/yellow]")
        return

    # Apply limit if specified
    if limit and len(symbols) > limit:
        display_symbols = symbols[:limit]
        console.print(
            f"[blue]Showing {limit} of {len(symbols)} symbols.[/blue]")
    else:
        display_symbols = symbols

    table = Table(
        title=f"Available Symbols ({len(display_symbols)} displayed)")

    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Exchange")
    table.add_column("Type", style="magenta")
    table.add_column("Country")

    if show_details:
        table.add_column("Currency")
        table.add_column("ISIN")
        table.add_column("MIC Code")

    # Add rows
    for symbol in display_symbols:
        row = [
            symbol.symbol,
            symbol.name,
            symbol.exchange,
            symbol.type,
            symbol.country
        ]

        if show_details:
            row.extend([
                symbol.currency,
                symbol.isin if symbol.isin else "N/A",
                symbol.mic_code
            ])

        table.add_row(*row)

    console.print(table)


def display_exchanges_table(exchanges: List[Exchange]) -> None:
    """
    Display a list of exchanges in a formatted table.

    Args:
        exchanges: List of Exchange objects to display
    """
    if not exchanges:
        console.print("[yellow]No exchanges found.[/yellow]")
        return

    table = Table(title=f"Available Exchanges ({len(exchanges)})")

    # Add columns
    table.add_column("Code", style="cyan")
    table.add_column("Name")
    table.add_column("Country")
    table.add_column("Timezone")

    # Add rows
    for exchange in exchanges:
        table.add_row(
            exchange.code,
            exchange.name,
            exchange.country,
            exchange.timezone if exchange.timezone else "N/A"
        )

    console.print(table)


def create_progress_spinner(description: str = "Loading...") -> Progress:
    """Create a progress spinner for long-running operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        transient=True
    )


def display_forex_pairs_table(forex_pairs: List[Any], limit: Optional[int] = None) -> None:
    """
    Display a list of forex pairs in a formatted table.
    
    Args:
        forex_pairs: List of ForexPair objects to display
        limit: Maximum number of pairs to display
    """
    if not forex_pairs:
        console.print("[yellow]No forex pairs found matching the criteria.[/yellow]")
        return
    
    # Apply limit if specified
    if limit and len(forex_pairs) > limit:
        display_pairs = forex_pairs[:limit]
        console.print(f"[blue]Showing {limit} of {len(forex_pairs)} forex pairs.[/blue]")
    else:
        display_pairs = forex_pairs
    
    table = Table(title=f"Available Forex Pairs ({len(display_pairs)} displayed)")
    
    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Base", style="green")
    table.add_column("Quote", style="red")
    table.add_column("Name")
    
    # Add rows
    for pair in display_pairs:
        table.add_row(
            pair.symbol,
            pair.currency_base,
            pair.currency_quote,
            pair.name if pair.name else f"{pair.currency_base}/{pair.currency_quote}"
        )
    
    console.print(table)

def display_currencies_table(currencies: List[Any]) -> None:
    """
    Display a list of currencies in a formatted table.
    
    Args:
        currencies: List of Currency objects to display
    """
    if not currencies:
        console.print("[yellow]No currencies found.[/yellow]")
        return
    
    table = Table(title=f"Available Currencies ({len(currencies)})")
    
    # Add columns
    table.add_column("Code", style="cyan")
    table.add_column("Name")
    table.add_column("Currency Name")
    table.add_column("Country")
    
    # Add rows
    for currency in currencies:
        table.add_row(
            currency.code,
            currency.name,
            currency.currency_name if currency.currency_name else "N/A",
            currency.country if currency.country else "N/A"
        )
    
    console.print(table)