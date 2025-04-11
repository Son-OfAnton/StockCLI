"""
Utility functions for displaying data in the console.
"""

from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.box import Box

from app.models.bond import Bond
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
        console.print(
            "[yellow]No forex pairs found matching the criteria.[/yellow]")
        return

    # Apply limit if specified
    if limit and len(forex_pairs) > limit:
        display_pairs = forex_pairs[:limit]
        console.print(
            f"[blue]Showing {limit} of {len(forex_pairs)} forex pairs.[/blue]")
    else:
        display_pairs = forex_pairs

    table = Table(
        title=f"Available Forex Pairs ({len(display_pairs)} displayed)")

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


def display_crypto_pairs_table(crypto_pairs: List[Any], limit: Optional[int] = None,
                               show_details: bool = False) -> None:
    """
    Display a list of cryptocurrency pairs in a formatted table.

    Args:
        crypto_pairs: List of CryptoPair objects to display
        limit: Maximum number of crypto pairs to display
        show_details: Whether to show additional details
    """
    if not crypto_pairs:
        console.print(
            "[yellow]No cryptocurrency pairs found matching the criteria.[/yellow]")
        return

    # Apply limit if specified
    if limit and len(crypto_pairs) > limit:
        display_pairs = crypto_pairs[:limit]
        console.print(
            f"[blue]Showing {limit} of {len(crypto_pairs)} cryptocurrency pairs.[/blue]")
    else:
        display_pairs = crypto_pairs

    table = Table(
        title=f"Available Cryptocurrency Pairs ({len(display_pairs)} displayed)")

    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Base", style="green")
    table.add_column("Quote", style="magenta")
    table.add_column("Exchange")

    if show_details:
        table.add_column("Available Exchanges")
        table.add_column("Price")

    # Add rows
    for pair in display_pairs:
        row = [
            pair.symbol,
            pair.base_currency or pair.currency_base,
            pair.quote_currency or pair.currency_quote,
            pair.exchange
        ]

        if show_details:
            exchanges = ", ".join(pair.available_exchanges[:3])
            if len(pair.available_exchanges) > 3:
                exchanges += f" +{len(pair.available_exchanges) - 3} more"

            row.extend([
                exchanges,
                f"{pair.price:.8f}" if pair.price is not None else "N/A"
            ])

        table.add_row(*row)

    console.print(table)


def display_crypto_exchanges_list(exchanges: List[str]) -> None:
    """
    Display a list of cryptocurrency exchanges.

    Args:
        exchanges: List of exchange names to display
    """
    if not exchanges:
        console.print("[yellow]No cryptocurrency exchanges found.[/yellow]")
        return

    table = Table(
        title=f"Available Cryptocurrency Exchanges ({len(exchanges)})")

    # Add columns
    table.add_column("Exchange Name", style="cyan")

    # Add rows
    for exchange in sorted(exchanges):
        table.add_row(exchange)

    console.print(table)


def display_funds_table(funds: List[Any], limit: Optional[int] = None,
                        show_details: bool = False) -> None:
    """
    Display a list of funds in a formatted table.

    Args:
        funds: List of Fund objects to display
        limit: Maximum number of funds to display
        show_details: Whether to show additional details
    """
    if not funds:
        console.print("[yellow]No funds found matching the criteria.[/yellow]")
        return

    # Apply limit if specified
    if limit and len(funds) > limit:
        display_funds = funds[:limit]
        console.print(f"[blue]Showing {limit} of {len(funds)} funds.[/blue]")
    else:
        display_funds = funds

    table = Table(title=f"Available Funds ({len(display_funds)} displayed)")

    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Type", style="magenta")
    table.add_column("Exchange")

    if show_details:
        table.add_column("Fund Family")
        table.add_column("Asset Class")
        table.add_column("Expense Ratio")
        table.add_column("Country")
        table.add_column("Currency")

    # Add rows
    for fund in display_funds:
        row = [
            fund.symbol,
            fund.name,
            fund.type.replace('_', ' ').title(),
            fund.exchange
        ]

        if show_details:
            expense_ratio = f"{fund.expense_ratio:.4%}" if fund.expense_ratio is not None else "N/A"
            row.extend([
                fund.fund_family if fund.fund_family else "N/A",
                fund.asset_class if fund.asset_class else "N/A",
                expense_ratio,
                fund.country,
                fund.currency
            ])

        table.add_row(*row)

    console.print(table)


def display_bonds(bonds: List[Bond]) -> None:
    """Display a list of bonds in a table format."""
    if not bonds:
        click.echo("No bonds to display.")
        return

    # Create a Rich table
    table = Table(
        title=f"Bonds ({len(bonds)})",
        show_header=True,
        header_style="bold blue",
        box=Box.SIMPLE
    )

    # Add columns to the table
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Type", style="green")
    table.add_column("Exchange")
    table.add_column("Country")
    table.add_column("Coupon (%)", justify="right")
    table.add_column("Maturity", justify="right")

    # Add rows for each bond
    for bond in bonds:
        coupon = f"{bond.coupon_rate:.3f}" if bond.coupon_rate is not None else "N/A"
        maturity = bond.maturity_date or "N/A"
        bond_type = bond.bond_type or "bond"

        table.add_row(
            bond.symbol,
            bond.name[:40] + ('...' if len(bond.name) > 40 else ''),
            bond_type,
            bond.exchange,
            bond.country or "N/A",
            coupon,
            maturity
        )

    # Print the table
    console = Console()
    console.print(table)


def display_bonds_detailed(bonds: List[Bond]) -> None:
    """Display detailed information for a list of bonds."""
    if not bonds:
        click.echo("No bonds to display.")
        return

    console = Console()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Display each bond in a panel
    for bond in bonds:
        # Create a table for bond details
        grid = Table.grid(padding=0, expand=False)
        grid.add_column("Field", style="bold cyan", width=18)
        grid.add_column("Value")

        # Add rows with bond details
        grid.add_row("Symbol:", bond.symbol)
        grid.add_row("Name:", bond.name)
        grid.add_row("Type:", bond.bond_type or "bond")
        grid.add_row("Exchange:", bond.exchange)
        grid.add_row("Country:", bond.country or "N/A")
        grid.add_row("Currency:", bond.currency)

        if bond.issuer:
            grid.add_row("Issuer:", bond.issuer)

        if bond.coupon_rate is not None:
            grid.add_row("Coupon Rate:", f"{bond.coupon_rate:.3f}%")

        if bond.face_value is not None:
            grid.add_row(
                "Face Value:", f"{bond.face_value:.2f} {bond.currency}")

        if bond.yield_to_maturity is not None:
            grid.add_row("Yield to Maturity:",
                         f"{bond.yield_to_maturity:.3f}%")

        if bond.maturity_date:
            grid.add_row("Maturity Date:", bond.maturity_date)

        if bond.credit_rating:
            grid.add_row("Credit Rating:", bond.credit_rating)

        if bond.is_callable is not None:
            grid.add_row("Callable:", "Yes" if bond.is_callable else "No")

        # Create a panel containing the grid
        panel = Panel(
            grid,
            title=f"[bold]{bond.symbol}[/bold] - {bond.name}",
            subtitle=f"Data as of {current_time}",
            expand=False
        )

        # Print the panel with a newline after all except the last one
        console.print(panel)
        if bond != bonds[-1]:
            console.print("")
