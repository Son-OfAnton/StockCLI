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
from app.models.commodity import CommodityGroup, CommodityPair
from app.models.etf import ETF
from app.models.exchange_details import ExchangeSchedule
from app.models.forex import ForexRate
from app.models.stock import TimeSeries
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


def display_etfs(etfs: List[ETF]) -> None:
    """Display a list of ETFs in a table format."""
    if not etfs:
        click.echo("No ETFs to display.")
        return

    # Create a Rich table
    table = Table(
        title=f"ETFs ({len(etfs)})",
        show_header=True,
        header_style="bold blue",
    )

    # Add columns to the table
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Asset Class", style="green")
    table.add_column("Exchange")
    table.add_column("Expense Ratio (%)", justify="right")
    table.add_column("Dividend Yield (%)", justify="right")
    table.add_column("AUM (M)", justify="right")

    # Add rows for each ETF
    for etf in etfs:
        expense = f"{etf.expense_ratio:.3f}" if etf.expense_ratio is not None else "N/A"
        dividend = f"{etf.dividend_yield:.2f}" if etf.dividend_yield is not None else "N/A"

        # Convert managed assets to millions for display
        if etf.managed_assets is not None:
            aum = f"{etf.managed_assets / 1_000_000:.1f}"
        else:
            aum = "N/A"

        asset_class = etf.asset_class or "N/A"

        table.add_row(
            etf.symbol,
            etf.name[:40] + ('...' if len(etf.name) > 40 else ''),
            asset_class,
            etf.exchange,
            expense,
            dividend,
            aum
        )

    # Print the table
    console = Console()
    console.print(table)


def display_etfs_detailed(etfs: List[ETF]) -> None:
    """Display detailed information for a list of ETFs."""
    if not etfs:
        click.echo("No ETFs to display.")
        return

    console = Console()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Display each ETF in a panel
    for etf in etfs:
        # Create a table for ETF details
        grid = Table.grid(padding=0, expand=False)
        grid.add_column("Field", style="bold cyan", width=18)
        grid.add_column("Value")

        # Add rows with ETF details
        grid.add_row("Symbol:", etf.symbol)
        grid.add_row("Name:", etf.name)
        grid.add_row("Asset Class:", etf.asset_class or "N/A")
        grid.add_row("Category:", etf.category or "N/A")
        grid.add_row("Exchange:", etf.exchange)
        grid.add_row("Country:", etf.country or "N/A")
        grid.add_row("Currency:", etf.currency)

        if etf.fund_family:
            grid.add_row("Fund Family:", etf.fund_family)

        if etf.expense_ratio is not None:
            grid.add_row("Expense Ratio:", f"{etf.expense_ratio:.4f}%")

        if etf.nav is not None:
            grid.add_row("NAV:", f"{etf.nav:.2f} {etf.currency}")

        if etf.dividend_yield is not None:
            grid.add_row("Dividend Yield:", f"{etf.dividend_yield:.2f}%")

        if etf.managed_assets is not None:
            # Format large numbers with commas
            grid.add_row("Managed Assets:",
                         f"{etf.managed_assets:,.0f} {etf.currency}")

        if etf.benchmark:
            grid.add_row("Benchmark:", etf.benchmark)

        if etf.inception_date:
            grid.add_row("Inception Date:", etf.inception_date)

        if etf.description:
            # Add a new row for description with word wrapping
            grid.add_row("Description:", "")
            description_text = Text(etf.description, style="italic")

            # Create a panel for the description to get nice wrapping
            description_panel = Panel(
                description_text,
                padding=(0, 1, 0, 1),
                expand=False,
                width=80
            )

        # Create a panel containing the grid
        panel = Panel(
            grid,
            title=f"[bold]{etf.symbol}[/bold] - {etf.name}",
            subtitle=f"Data as of {current_time}",
            expand=False
        )

        # Print the panel
        console.print(panel)

        # Print the description if it exists
        if etf.description:
            console.print(description_panel)

        # Add a newline between ETFs except for the last one
        if etf != etfs[-1]:
            console.print("")


def display_commodity_pairs(commodity_pairs: List[CommodityPair]) -> None:
    """Display a list of commodity pairs in a table format."""
    if not commodity_pairs:
        click.echo("No commodity pairs to display.")
        return

    # Create a Rich table
    table = Table(
        title=f"Commodity Pairs ({len(commodity_pairs)})",
        show_header=True,
        header_style="bold blue",
    )

    # Add columns to the table
    table.add_column("Symbol", style="cyan")
    table.add_column("Base", style="green")
    table.add_column("Quote")
    table.add_column("Group", style="yellow")
    table.add_column("Exchanges")
    table.add_column("Active", justify="center")

    # Add rows for each commodity pair
    for pair in commodity_pairs:
        # Format the exchanges list for display
        exchanges = ", ".join(pair.available_exchanges[:3])
        if len(pair.available_exchanges) > 3:
            exchanges += f" +{len(pair.available_exchanges) - 3} more"

        # Get a nice name for the commodity group
        group = pair.commodity_group
        if group:
            # Convert snake_case to Title Case
            group = " ".join(word.capitalize() for word in group.split("_"))
        else:
            group = "Other"

        # Format is_active as a checkmark or X
        active = "✓" if pair.is_active else "✗"
        active_style = "green" if pair.is_active else "red"

        table.add_row(
            pair.symbol,
            pair.base_commodity,
            pair.quote_currency,
            group,
            exchanges,
            Text(active, style=active_style)
        )

    # Print the table
    console = Console()
    console.print(table)


def display_commodity_pairs_detailed(commodity_pairs: List[CommodityPair]) -> None:
    """Display detailed information for a list of commodity pairs."""
    if not commodity_pairs:
        click.echo("No commodity pairs to display.")
        return

    console = Console()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Group the pairs by commodity group for better organization
    pairs_by_group = {}
    for pair in commodity_pairs:
        group = pair.commodity_group or "other"
        if group not in pairs_by_group:
            pairs_by_group[group] = []
        pairs_by_group[group].append(pair)

    # Display pairs grouped by commodity group
    for group_name, pairs in pairs_by_group.items():
        # Convert snake_case to Title Case for display
        display_group = " ".join(word.capitalize()
                                 for word in group_name.split("_"))

        # Create a panel group title
        console.print(f"[bold]{display_group} Commodities[/bold]\n")

        for pair in pairs:
            # Create a table for commodity details
            grid = Table.grid(padding=0, expand=False)
            grid.add_column("Field", style="bold cyan", width=18)
            grid.add_column("Value")

            # Add rows with commodity details
            grid.add_row("Symbol:", pair.symbol)
            grid.add_row("Base Commodity:", pair.base_commodity)
            grid.add_row("Quote Currency:", pair.quote_currency)
            grid.add_row("Group:", display_group)
            grid.add_row("Active:", "Yes" if pair.is_active else "No")

            if pair.symbol_description:
                grid.add_row("Description:", pair.symbol_description)

            # Format the exchanges for display
            if pair.available_exchanges:
                grid.add_row("Exchanges:", ", ".join(pair.available_exchanges))

            # Create a panel containing the grid
            panel = Panel(
                grid,
                title=f"[bold]{pair.symbol}[/bold]",
                expand=False
            )

            # Print the panel with a newline after all except the last one
            console.print(panel)

            if pair != pairs[-1]:
                console.print("")

        # Add a separator between groups
        if group_name != list(pairs_by_group.keys())[-1]:
            console.print("\n" + "─" * 50 + "\n")


def display_commodity_groups(commodity_groups: List[CommodityGroup]) -> None:
    """Display commodity groups with their descriptions."""
    if not commodity_groups:
        click.echo("No commodity groups to display.")
        return

    console = Console()

    # Display each commodity group
    for group in commodity_groups:
        # Convert snake_case to Title Case
        display_name = " ".join(word.capitalize()
                                for word in group.name.split("_"))

        # Create a panel for each group
        panel_content = Text()
        panel_content.append(f"{group.description}\n\n", style="italic")
        panel_content.append("Example symbols: ", style="dim")
        panel_content.append(", ".join(group.examples), style="cyan")

        panel = Panel(
            panel_content,
            title=f"[bold]{display_name}[/bold]",
            expand=False
        )

        console.print(panel)

        # Add spacing between panels
        if group != commodity_groups[-1]:
            console.print("")


def display_cross_listed_symbols(symbols: List[Symbol]) -> None:
    """
    Display a list of cross-listed symbols in a formatted table.

    Args:
        symbols: List of Symbol objects representing cross-listed symbols
    """
    if not symbols:
        console.print("[yellow]No cross-listed symbols found.[/yellow]")
        return

    table = Table(title=f"Cross-Listed Symbols ({len(symbols)})")

    # Define columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Exchange", style="blue")
    table.add_column("Currency", style="yellow")
    table.add_column("Country", style="magenta")
    table.add_column("Type", style="red")

    # Add rows
    for symbol in symbols:
        table.add_row(
            symbol.symbol,
            symbol.name,
            symbol.exchange,
            symbol.currency,
            symbol.country,
            symbol.type
        )

    # Display the table
    console.print(table)
    console.print()


def display_raw_cross_listed_data(data: List) -> None:
    """
    Display raw cross-listed symbols data in a formatted table.

    This is a fallback when the response can't be parsed into Symbol objects.

    Args:
        data: List of dictionaries or other data types from the API response
    """
    if not data:
        console.print("[yellow]No cross-listed symbols data found.[/yellow]")
        return

    # Try to determine the structure of the data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        # Extract common fields from dictionaries
        # First, collect all possible keys
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())

        # Use common fields as columns, prioritize important ones
        important_fields = ["symbol", "name", "exchange",
                            "mic_code", "country", "currency", "type"]
        columns = [field for field in important_fields if field in all_keys]

        # Add any remaining fields
        remaining_fields = sorted(list(all_keys - set(columns)))
        columns.extend(remaining_fields)

        # Create table
        table = Table(title=f"Cross-Listed Symbols ({len(data)})")

        # Add columns with appropriate styles
        styles = {
            "symbol": "cyan",
            "name": "green",
            "exchange": "blue",
            "mic_code": "blue italic",
            "country": "magenta",
            "currency": "yellow",
            "type": "red"
        }

        for column in columns:
            table.add_column(column.replace("_", " ").title(),
                             style=styles.get(column, "white"))

        # Add rows
        for item in data:
            row_values = []
            for column in columns:
                value = item.get(column, "")
                # Format value appropriately
                if value is None:
                    row_values.append("")
                elif isinstance(value, (dict, list)):
                    row_values.append(
                        str(value)[:30] + "..." if len(str(value)) > 30 else str(value))
                else:
                    row_values.append(str(value))

            table.add_row(*row_values)

        # Display the table
        console.print(table)
        console.print()

    elif isinstance(data, list) and data and isinstance(data[0], str):
        # Handle list of strings
        table = Table(title=f"Cross-Listed Symbols ({len(data)})")
        table.add_column("Symbol", style="cyan")

        for item in data:
            table.add_row(str(item))

        console.print(table)
        console.print()

    else:
        # If structure is unknown, fall back to pretty printing
        console.print(
            "[yellow]Could not determine structure of data for tabular display.[/yellow]")
        console.print("[yellow]Showing raw data:[/yellow]")
        from rich.pretty import Pretty
        console.print(Pretty(data))
        console.print()


def display_exchange_details(exchange_details: Any) -> None:
    """
    Display detailed information about an exchange.

    Args:
        exchange_details: ExchangeDetails object to display
    """
    from rich.panel import Panel
    from rich.text import Text

    # Create a panel for the exchange details
    header = Text(
        f"Exchange Details: {exchange_details.name} ({exchange_details.code})")
    header.stylize("bold blue")

    details = []
    details.append(f"Name: {exchange_details.name}")
    details.append(f"Code: {exchange_details.code}")
    details.append(f"Country: {exchange_details.country}")

    if exchange_details.timezone:
        details.append(f"Timezone: {exchange_details.timezone}")
    if exchange_details.currency:
        details.append(f"Currency: {exchange_details.currency}")
    if exchange_details.mic_code:
        details.append(f"MIC Code: {exchange_details.mic_code}")
    if exchange_details.website:
        details.append(f"Website: {exchange_details.website}")
    if exchange_details.operating_mic:
        details.append(f"Operating MIC: {exchange_details.operating_mic}")
    if exchange_details.operating_mic_name:
        details.append(
            f"Operating MIC Name: {exchange_details.operating_mic_name}")

    # Add description at the end if available
    if exchange_details.description:
        description_text = Text("\nDescription:")
        description_text.stylize("bold")
        description = Text(exchange_details.description)

        details_text = "\n".join(details)
        details_text = f"{details_text}\n\n{description_text}\n{description}"
    else:
        details_text = "\n".join(details)

    panel = Panel(details_text, title=header, border_style="blue")
    console.print(panel)


def display_exchange_trading_hours(trading_hours: List) -> None:
    """
    Display trading hours for an exchange.

    Args:
        trading_hours: List of TradingHours objects to display
    """
    if not trading_hours:
        console.print("[yellow]No trading hours information found.[/yellow]")
        return

    exchange_name = trading_hours[0].exchange
    table = Table(title=f"Trading Hours for {exchange_name}")

    # Add columns
    table.add_column("Day", style="cyan")
    table.add_column("Open", style="green")
    table.add_column("Close", style="red")
    table.add_column("Open (UTC)", style="green")
    table.add_column("Close (UTC)", style="red")
    table.add_column("Status", style="yellow")

    # Add rows
    for hours in trading_hours:
        day = hours.day_of_week if hours.day_of_week else "N/A"
        status = hours.status if hours.status else "N/A"
        is_open = "[green]Open[/green]" if hours.is_open_now else "[red]Closed[/red]" if hours.is_open_now is not None else "N/A"

        if hours.status == "open" and hours.is_open_now:
            status = "[green]Open Now[/green]"
        elif hours.status == "closed" and not hours.is_open_now:
            status = "[red]Closed Now[/red]"

        table.add_row(
            day,
            hours.open_time,
            hours.close_time,
            hours.open_time_utc if hours.open_time_utc else "N/A",
            hours.close_time_utc if hours.close_time_utc else "N/A",
            status
        )

    console.print(table)
    console.print()


def display_raw_exchange_trading_hours(data: Dict[str, Any], exchange: str) -> None:
    """
    Display raw trading hours data in a formatted table.

    This is a fallback when the response can't be parsed into TradingHours objects.

    Args:
        data: Dictionary with trading hours data from the API
        exchange: Exchange code
    """
    table = Table(title=f"Trading Hours for {exchange}")

    # Try to determine the structure of the data
    if not data:
        console.print("[yellow]No trading hours information found.[/yellow]")
        return

    # Check if we have a 'timezone' field for formatting
    timezone = data.get('timezone', 'Unknown')

    # Add columns based on what data we have
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    # Add rows for each field
    for field, value in data.items():
        if field == 'is_open_now' and isinstance(value, bool):
            value_str = "[green]Yes[/green]" if value else "[red]No[/red]"
        else:
            value_str = str(value)

        table.add_row(field.replace('_', ' ').title(), value_str)

    console.print(table)
    console.print(f"Timezone: {timezone}")
    console.print()


def display_exchange_schedule(exchange_schedule) -> None:
    """
    Display exchange schedule, including details and trading hours.

    Args:
        exchange_schedule: ExchangeSchedule object to display
    """
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    if not exchange_schedule:
        console.print("[yellow]No exchange schedule found.[/yellow]")
        return

    # Display exchange details in a panel
    title = Text(
        f"{exchange_schedule.name} ({exchange_schedule.code})", style="bold cyan")

    content = []
    content.append(Text.from_markup(
        f"[bold]Country:[/bold] {exchange_schedule.country}"))
    content.append(Text.from_markup(
        f"[bold]Timezone:[/bold] {exchange_schedule.timezone}"))

    if exchange_schedule.date:
        content.append(Text.from_markup(
            f"[bold]Date:[/bold] {exchange_schedule.date}"))

    if exchange_schedule.is_open is not None:
        status = "[green]Open[/green]" if exchange_schedule.is_open else "[red]Closed[/red]"
        content.append(Text.from_markup(f"[bold]Status:[/bold] {status}"))

    if exchange_schedule.currency:
        content.append(Text.from_markup(
            f"[bold]Currency:[/bold] {exchange_schedule.currency}"))

    if exchange_schedule.suffix:
        content.append(Text.from_markup(
            f"[bold]Suffix:[/bold] {exchange_schedule.suffix}"))

    if exchange_schedule.mic_code:
        content.append(Text.from_markup(
            f"[bold]MIC Code:[/bold] {exchange_schedule.mic_code}"))

    if exchange_schedule.operating_mic:
        content.append(Text.from_markup(
            f"[bold]Operating MIC:[/bold] {exchange_schedule.operating_mic}"))

    if exchange_schedule.website:
        content.append(Text.from_markup(
            f"[bold]Website:[/bold] {exchange_schedule.website}"))

    if exchange_schedule.type:
        content.append(Text.from_markup(
            f"[bold]Type:[/bold] {exchange_schedule.type}"))

    # Join with newlines
    panel_content = "\n".join(str(line) for line in content)
    panel = Panel(panel_content, title=title,
                  expand=False, border_style="blue")

    console.print(panel)

    # Display trading hours if available
    if exchange_schedule.sessions:
        console.print("\n[bold cyan]Trading Hours:[/bold cyan]")

        # Create a table for trading sessions
        table = Table()

        table.add_column("Session Type", style="cyan")
        table.add_column("Open", style="green")
        table.add_column("Close", style="red")

        for session in exchange_schedule.sessions:
            table.add_row(
                session.session_name,
                session.start_time,
                session.end_time
            )

        console.print(table)

    # Display holidays if available
    if exchange_schedule.holidays and len(exchange_schedule.holidays) > 0:
        console.print("\n[bold cyan]Upcoming Holidays:[/bold cyan]")

        # Create a table for holidays
        table = Table()

        table.add_column("Date", style="cyan")
        table.add_column("Holiday Name", style="green")

        for holiday in exchange_schedule.holidays:
            table.add_row(
                holiday.get('date', 'N/A'),
                holiday.get('name', 'N/A')
            )

        console.print(table)

    console.print()


def display_exchanges_with_hours_table(exchange_schedules: List['ExchangeSchedule']) -> None:
    """
    Display a list of exchanges with their trading hours in a formatted table.

    Args:
        exchange_schedules: List of ExchangeSchedule objects to display
    """
    if not exchange_schedules:
        console.print("[yellow]No exchanges found.[/yellow]")
        return

    table = Table(
        title=f"Available Exchanges with Trading Hours ({len(exchange_schedules)})")

    # Add columns
    table.add_column("Code", style="cyan")
    table.add_column("Name")
    table.add_column("Country")
    table.add_column("Trading Hours (Start-End)")
    table.add_column("Status")
    table.add_column("Timezone")

    # Add rows
    for schedule in exchange_schedules:
        # Format trading hours
        hours_text = ""
        if hasattr(schedule, 'sessions') and schedule.sessions:
            # Get regular trading session if available
            regular_sessions = [
                s for s in schedule.sessions if s.session_name.lower() == 'regular']
            if regular_sessions:
                session = regular_sessions[0]
                hours_text = f"{session.start_time} - {session.end_time}"
            else:
                # Use the first session if no regular session is found
                session = schedule.sessions[0]
                hours_text = f"{session.start_time} - {session.end_time} ({session.session_name})"
        else:
            hours_text = "N/A"

        # Format status
        status_text = "N/A"
        if hasattr(schedule, 'is_open') and schedule.is_open is not None:
            status_text = "[green]Open[/green]" if schedule.is_open else "[red]Closed[/red]"

        table.add_row(
            schedule.code,
            schedule.name,
            schedule.country,
            hours_text,
            status_text,
            schedule.timezone if hasattr(
                schedule, 'timezone') and schedule.timezone else "N/A"
        )

    console.print(table)


def display_instrument_types_table(instrument_types: List[Dict[str, Any]]) -> None:
    """
    Display instrument types in a formatted table.

    Args:
        instrument_types: List of instrument type dictionaries with 'id' and 'name' keys
    """
    if not instrument_types:
        console.print("[yellow]No instrument types found.[/yellow]")
        return

    table = Table(
        title=f"Available Instrument Types ({len(instrument_types)})")

    # Add columns
    table.add_column("ID", style="cyan")
    table.add_column("Name")

    # Add rows
    for instrument_type in instrument_types:
        # Handle both dictionary format and string format (for backwards compatibility)
        if isinstance(instrument_type, dict):
            type_id = instrument_type.get('id', 'N/A')
            type_name = instrument_type.get('name', 'N/A')
        else:
            # If it's just a string, use it for both ID and name
            type_id = instrument_type
            type_name = instrument_type.capitalize()

        table.add_row(type_id, type_name)

    console.print(table)


def display_earliest_data_info(earliest_data: Dict[str, Any]) -> None:
    """
    Display information about the earliest available data for a symbol at a specific interval.

    Args:
        earliest_data: Dictionary containing earliest available data information
    """
    symbol = earliest_data.get('symbol', 'N/A')
    interval = earliest_data.get('interval', 'N/A')
    earliest_datetime = earliest_data.get('earliest_datetime')

    console.print(f"\n[bold cyan]Earliest Available Data[/bold cyan]")
    console.print(f"[bold]Symbol:[/bold] {symbol}")
    console.print(f"[bold]Interval:[/bold] {interval}")

    if earliest_datetime:
        console.print(
            f"[bold]First Available Datetime:[/bold] [green]{earliest_datetime}[/green]")

        # Display additional data if available
        if 'data' in earliest_data and earliest_data['data']:
            data = earliest_data['data']
            console.print("\n[bold]First Data Point Details:[/bold]")

            # Create a table for the data point details
            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            # Add rows for each property in the data point
            for key, value in data.items():
                if key != 'datetime':  # Skip datetime as we've already displayed it
                    table.add_row(key, str(value))

            console.print(table)
    else:
        console.print(f"[bold red]No historical data available[/bold red]")
        if 'message' in earliest_data:
            console.print(f"[italic]{earliest_data['message']}[/italic]")


def display_symbol_search_results(symbols: List[Dict[str, Any]], query: str) -> None:
    """
    Display symbol search results in a formatted table.

    Args:
        symbols: List of symbol dictionaries from search results
        query: The original search query
    """
    if not symbols:
        console.print(f"[yellow]No symbols found matching '{query}'.[/yellow]")
        return

    table = Table(
        title=f"Symbol Search Results for '{query}' ({len(symbols)} matches)")

    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Type", style="magenta")
    table.add_column("Exchange")
    table.add_column("Country")
    table.add_column("Currency")

    # Add rows
    for symbol in symbols:
        table.add_row(
            symbol.get('symbol', 'N/A'),
            symbol.get('instrument_name', symbol.get('name', 'N/A')),
            symbol.get('type', 'N/A'),
            symbol.get('exchange', 'N/A'),
            symbol.get('country', 'N/A'),
            symbol.get('currency', 'N/A')
        )

    console.print(table)


def display_time_series_meta(meta_data: Dict[str, Any]) -> None:
    """
    Display meta information for time series data.

    Args:
        meta_data: Dictionary containing meta information from time series endpoint
    """
    console.print("\n[bold cyan]Time Series Metadata[/bold cyan]")

    # Create a table for the metadata
    table = Table(show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    # Add rows for each metadata property
    for key, value in meta_data.items():
        table.add_row(key, str(value))

    console.print(table)


def display_time_series_data(time_series: 'TimeSeries', limit: Optional[int] = 10) -> None:
    """
    Display time series data in a table format.

    Args:
        time_series: TimeSeries object to display
        limit: Maximum number of data points to display (None for all)
    """
    if not time_series or not hasattr(time_series, 'bars') or not time_series.bars:
        console.print("[yellow]No time series data found.[/yellow]")
        return

    # Apply limit if specified
    bars_to_display = time_series.bars[:limit] if limit else time_series.bars

    # Create a table for the time series data
    table = Table(
        title=f"Time Series Data for {time_series.symbol} ({time_series.interval})")

    # Add columns
    table.add_column("Timestamp", style="cyan")
    table.add_column("Open")
    table.add_column("High")
    table.add_column("Low")
    table.add_column("Close")

    # Only add volume column if any bar has volume data
    has_volume = any(bar.volume is not None for bar in bars_to_display)
    if has_volume:
        table.add_column("Volume")

    # Format decimal places for price values
    def price_format(price): return f"{price:.2f}"

    # Add rows for each bar
    for bar in bars_to_display:
        # Format the timestamp - show date only for intervals >= 1day
        if time_series.interval.lower() in ['1day', '1week', '1month']:
            timestamp_str = bar.timestamp.strftime('%Y-%m-%d')
        else:
            timestamp_str = bar.timestamp.strftime('%Y-%m-%d %H:%M')

        # Build row data
        row = [
            timestamp_str,
            price_format(bar.open),
            price_format(bar.high),
            price_format(bar.low),
            price_format(bar.close)
        ]

        # Add volume if present
        if has_volume:
            # Format volume with thousands separator
            volume_str = f"{bar.volume:,}" if bar.volume is not None else "N/A"
            row.append(volume_str)

        table.add_row(*row)

    console.print(table)

    # Show a message if data was limited
    if limit and len(time_series.bars) > limit:
        console.print(
            f"[italic]Showing {limit} of {len(time_series.bars)} data points. Use --limit option to show more.[/italic]")


def display_time_series_response(response_data: Dict[str, Any], limit: Optional[int] = 10) -> None:
    """
    Display a time series response, including meta information and data.

    Args:
        response_data: Dictionary containing meta and values from time series endpoint
        limit: Maximum number of data points to display (None for all)
    """
    from app.models.stock import TimeSeries

    # Display meta information
    if 'meta' in response_data:
        display_time_series_meta(response_data['meta'])

    # Create TimeSeries object and display data
    try:
        time_series = TimeSeries.from_api_response(response_data)
        display_time_series_data(time_series, limit)
    except Exception as e:
        logger.error(f"Error creating TimeSeries object: {e}")
        console.print(
            "[bold red]Error displaying time series data.[/bold red]")

        # Fallback to displaying raw values if TimeSeries creation fails
        if 'values' in response_data and response_data['values']:
            values = response_data['values']
            values_to_display = values[:limit] if limit else values

            console.print("\n[bold yellow]Raw Time Series Data[/bold yellow]")
            console.print(values_to_display)


def display_forex_rate(forex_rate: 'ForexRate') -> None:
    """
    Display forex exchange rate information.

    Args:
        forex_rate: ForexRate object to display
    """
    if not forex_rate:
        console.print("[yellow]No exchange rate data found.[/yellow]")
        return

    # Create a panel with exchange rate information
    from rich.panel import Panel
    from rich.text import Text

    title = Text(f"Exchange Rate: {forex_rate.symbol}", style="bold cyan")

    # Determine if rate has changed and set color accordingly
    rate_color = "white"
    if hasattr(forex_rate, 'change') and forex_rate.change is not None:
        rate_color = "green" if forex_rate.change >= 0 else "red"

    # Format the main rate
    rate_text = Text(f"{forex_rate.rate:.6f}", style=f"bold {rate_color}")

    # Create the panel content
    content = []
    content.append(Text(f"Rate: {rate_text}"))
    content.append(Text.from_markup(
        f"[bold]Base Currency:[/bold] {forex_rate.currency_base}"))
    content.append(Text.from_markup(
        f"[bold]Quote Currency:[/bold] {forex_rate.currency_quote}"))
    content.append(Text.from_markup(
        f"[bold]Timestamp:[/bold] {forex_rate.timestamp}"))

    # Add additional information if available
    if forex_rate.name:
        content.append(Text.from_markup(
            f"[bold]Name:[/bold] {forex_rate.name}"))

    # Add bid/ask spread if available
    if forex_rate.bid is not None and forex_rate.ask is not None:
        content.append(Text.from_markup(
            f"[bold]Bid:[/bold] {forex_rate.bid:.6f}"))
        content.append(Text.from_markup(
            f"[bold]Ask:[/bold] {forex_rate.ask:.6f}"))
        spread = forex_rate.ask - forex_rate.bid
        spread_pips = spread * 10000  # Standard forex pip calculation
        content.append(Text.from_markup(
            f"[bold]Spread:[/bold] {spread:.6f} ({spread_pips:.1f} pips)"))

    # Add high/low if available
    if forex_rate.high is not None and forex_rate.low is not None:
        content.append(Text.from_markup(
            f"[bold]High:[/bold] {forex_rate.high:.6f}"))
        content.append(Text.from_markup(
            f"[bold]Low:[/bold] {forex_rate.low:.6f}"))

    # Add change information if available
    if forex_rate.change is not None:
        change_color = "green" if forex_rate.change >= 0 else "red"
        change_sign = "+" if forex_rate.change > 0 else ""
        content.append(Text.from_markup(
            f"[bold]Change:[/bold] [{change_color}]{change_sign}{forex_rate.change:.6f}[/{change_color}]"))

    if forex_rate.change_percent is not None:
        change_color = "green" if forex_rate.change_percent >= 0 else "red"
        change_sign = "+" if forex_rate.change_percent > 0 else ""
        content.append(Text.from_markup(
            f"[bold]Change %:[/bold] [{change_color}]{change_sign}{forex_rate.change_percent:.2f}%[/{change_color}]"))

    # Create and display the panel
    panel = Panel.fit(
        "\n".join(str(line) for line in content),
        title=title,
        border_style="cyan",
    )

    console.print(panel)


def display_detailed_quote(quote, simplified=False):
    """
    Display a single quote with detailed information in a rich format.

    Args:
        quote: Quote object to display
        simplified: Whether to show simplified view (less detail)
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.columns import Columns
    from rich.layout import Layout
    from app.utils.helpers import format_price, format_change, get_color_for_change, get_local_time, format_datetime

    # Format the price and change
    price_text = Text(f"{format_price(quote.price)}")
    price_text.stylize("bold")

    change_text = Text(format_change(quote.change, quote.change_percent))
    change_color = get_color_for_change(quote.change)
    change_text.stylize(change_color)

    # Create a panel for the main price information
    header = f"[bold]{quote.symbol}"
    if hasattr(quote, 'name') and quote.name:
        header += f" - {quote.name}"
    header += "[/bold]"

    # Format timestamp
    local_time = get_local_time(quote.timestamp)
    time_str = format_datetime(local_time, "%Y-%m-%d %H:%M:%S")

    if simplified:
        # Simplified view - just the essentials
        main_content = [
            f"[bold]Price:[/bold] {price_text}",
            f"[bold]Change:[/bold] {change_text}",
            f"[bold]Time:[/bold] {time_str}"
        ]

        if hasattr(quote, 'volume') and quote.volume:
            main_content.append(f"[bold]Volume:[/bold] {quote.volume:,}")

        main_panel = Panel(
            "\n".join(main_content),
            title=header,
            expand=False
        )
        console.print(main_panel)

    else:
        # Full detailed view
        # Create primary info panel
        primary_info = [
            f"[bold]Price:[/bold] {price_text}",
            f"[bold]Change:[/bold] {change_text}",
            f"[bold]Volume:[/bold] {quote.volume:,}" if quote.volume else "[bold]Volume:[/bold] N/A",
            f"[bold]Time:[/bold] {time_str}"
        ]

        primary_panel = Panel(
            "\n".join(primary_info),
            title=header,
            expand=False
        )

        # Create OHLC (Open/High/Low/Close) panel
        ohlc_info = [
            f"[bold]Open:[/bold] {format_price(quote.open_price)}" if quote.open_price else "[bold]Open:[/bold] N/A",
            f"[bold]High:[/bold] {format_price(quote.high_price)}" if quote.high_price else "[bold]High:[/bold] N/A",
            f"[bold]Low:[/bold] {format_price(quote.low_price)}" if quote.low_price else "[bold]Low:[/bold] N/A",
            f"[bold]Previous Close:[/bold] {format_price(quote.previous_close)}" if quote.previous_close else "[bold]Previous Close:[/bold] N/A"
        ]

        ohlc_panel = Panel(
            "\n".join(ohlc_info),
            title="[bold]OHLC Data[/bold]",
            expand=False
        )

        # Create additional info panel (52-week high/low, etc.)
        if hasattr(quote, 'fifty_two_week_high') or hasattr(quote, 'fifty_two_week_low'):
            additional_info = []

            if hasattr(quote, 'fifty_two_week_high') and quote.fifty_two_week_high:
                additional_info.append(
                    f"[bold]52-Week High:[/bold] {format_price(quote.fifty_two_week_high)}")

            if hasattr(quote, 'fifty_two_week_low') and quote.fifty_two_week_low:
                additional_info.append(
                    f"[bold]52-Week Low:[/bold] {format_price(quote.fifty_two_week_low)}")

            if hasattr(quote, 'currency') and quote.currency:
                additional_info.append(
                    f"[bold]Currency:[/bold] {quote.currency}")

            # Only create this panel if we have any additional info
            if additional_info:
                additional_panel = Panel(
                    "\n".join(additional_info),
                    title="[bold]Additional Information[/bold]",
                    expand=False
                )

                # Display all panels in a column layout
                console.print(
                    Columns([primary_panel, ohlc_panel, additional_panel]))
            else:
                # Display just the two main panels
                console.print(Columns([primary_panel, ohlc_panel]))
        else:
            # Display just the two main panels if no 52-week data
            console.print(Columns([primary_panel, ohlc_panel]))


def display_eod_price(eod_data: Dict[str, Any], symbol: str) -> None:
    """
    Display End of Day (EOD) price information for a symbol.

    Args:
        eod_data: Dictionary containing EOD price data
        symbol: The ticker symbol
    """
    if not eod_data:
        console.print(f"[yellow]No EOD data found for {symbol}.[/yellow]")
        return

    # Create a panel for the EOD information
    title = Text(f"End of Day Price: {symbol}", style="bold cyan")

    # Format EOD data
    date = eod_data.get('datetime', 'N/A')
    close_price = eod_data.get('close', 'N/A')
    open_price = eod_data.get('open', 'N/A')
    high = eod_data.get('high', 'N/A')
    low = eod_data.get('low', 'N/A')
    volume = eod_data.get('volume', 'N/A')

    # Calculate change and percent change
    previous_close = eod_data.get('previous_close')
    if previous_close and close_price and previous_close != 'N/A' and close_price != 'N/A':
        change = float(close_price) - float(previous_close)
        change_percent = (change / float(previous_close)) * 100
        change_str = f"{change:.2f}"
        change_percent_str = f"{change_percent:.2f}%"

        # Color code based on change direction
        change_color = "green" if change >= 0 else "red"
        change_str = f"[{change_color}]{change_str}[/{change_color}]"
        change_percent_str = f"[{change_color}]{change_percent_str}[/{change_color}]"
    else:
        change_str = "N/A"
        change_percent_str = "N/A"

    # Create content for the panel
    content = []
    content.append(f"Date: {date}")
    content.append(f"Close: {close_price}")
    content.append(f"Open: {open_price}")
    content.append(f"High: {high}")
    content.append(f"Low: {low}")
    content.append(f"Volume: {volume}")
    content.append(f"Change: {change_str}")
    content.append(f"Change %: {change_percent_str}")

    # If there's additional data, add it to the panel
    exchange = eod_data.get('exchange')
    if exchange:
        content.append(f"Exchange: {exchange}")

    currency = eod_data.get('currency')
    if currency:
        content.append(f"Currency: {currency}")

    # Create and display the panel
    panel = Panel("\n".join(content), title=title, border_style="cyan")
    console.print(panel)


def display_market_movers(movers: List[Dict[str, Any]], direction: str) -> None:
    """
    Display a list of market movers (gainers or losers) in a formatted table.

    Args:
        movers: List of dictionaries with market mover data
        direction: "gainers" for top gainers, "losers" for top losers
    """
    if not movers:
        console.print(f"[yellow]No {direction} found for today.[/yellow]")
        return

    # Create an appropriate title
    title = f"Top {direction.title()} for Today ({len(movers)} stocks)"
    table = Table(title=title)

    # Add columns
    table.add_column("Rank", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Price")
    table.add_column("Change")
    table.add_column("% Change")
    table.add_column("Volume")
    table.add_column("Exchange")

    # Add rows
    for i, mover in enumerate(movers, 1):
        # Determine color based on change direction
        change_value = mover.get("change", 0)
        percent_change = mover.get("percent_change", 0)
        color = "green" if change_value >= 0 else "red"

        # Format values
        price = f"${mover.get('price', 0):.2f}"
        change = f"[{color}]{change_value:+.2f}[/{color}]"
        percent = f"[{color}]{percent_change:+.2f}%[/{color}]"

        # Format volume with commas
        volume = mover.get("volume")
        if volume:
            volume_str = f"{volume:,}"
        else:
            volume_str = "N/A"

        # Add row to table
        table.add_row(
            str(i),
            mover.get("symbol", ""),
            mover.get("name", "Unknown"),
            price,
            change,
            percent,
            volume_str,
            mover.get("exchange", "")
        )

    console.print(table)


def display_mutual_funds_detailed(mutual_funds: List[Any], limit: Optional[int] = None) -> None:
    """
    Display a detailed list of mutual funds in a formatted table.

    Args:
        mutual_funds: List of MutualFund objects to display
        limit: Maximum number of funds to display
    """
    if not mutual_funds:
        console.print(
            "[yellow]No mutual funds found matching the criteria.[/yellow]")
        return

    # Apply limit if specified
    if limit and len(mutual_funds) > limit:
        display_funds = mutual_funds[:limit]
        console.print(
            f"[blue]Showing {limit} of {len(mutual_funds)} mutual funds.[/blue]")
    else:
        display_funds = mutual_funds

    table = Table(
        title=f"Available Mutual Funds ({len(display_funds)} displayed)")

    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Fund Family", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Expense Ratio", style="red")
    table.add_column("Yield", style="green")
    table.add_column("Rating", style="yellow")
    table.add_column("Min. Investment", style="blue")
    table.add_column("Assets", style="magenta")

    # Add rows
    for fund in display_funds:
        # Format expense ratio
        expense_ratio = f"{fund.expense_ratio:.2f}%" if fund.expense_ratio is not None else "N/A"

        # Format yield
        fund_yield = f"{fund.yield_percentage:.2f}%" if fund.yield_percentage is not None else "N/A"

        # Format rating as stars
        rating = "★" * fund.morningstar_rating if fund.morningstar_rating else "N/A"

        # Format min investment with comma separator
        min_investment = f"${fund.minimum_investment:,.0f}" if fund.minimum_investment is not None else "N/A"

        # Format total assets
        assets = f"${fund.total_assets:,.1f}M" if fund.total_assets is not None else "N/A"

        table.add_row(
            fund.symbol,
            fund.name,
            fund.fund_family or "N/A",
            fund.fund_category or "N/A",
            expense_ratio,
            fund_yield,
            rating,
            min_investment,
            assets
        )

    console.print(table)


def display_mutual_fund_profile(mutual_fund: Any) -> None:
    """
    Display detailed profile for a single mutual fund.

    Args:
        mutual_fund: MutualFund object to display
    """
    if not mutual_fund:
        console.print("[yellow]Mutual fund not found.[/yellow]")
        return

    # Create a panel for the mutual fund profile
    title = Text(
        f"Mutual Fund Profile: {mutual_fund.symbol}", style="bold cyan")

    content = []

    # Basic information section
    content.append(Text("Basic Information", style="bold underline"))
    content.append(f"Name: {mutual_fund.name}")
    content.append(f"Symbol: {mutual_fund.symbol}")
    content.append(f"Exchange: {mutual_fund.exchange}")
    content.append(f"Fund Family: {mutual_fund.fund_family or 'N/A'}")
    content.append(f"Category: {mutual_fund.fund_category or 'N/A'}")
    content.append(f"Asset Class: {mutual_fund.asset_class or 'N/A'}")
    if mutual_fund.inception_date:
        content.append(
            f"Inception Date: {mutual_fund.inception_date.strftime('%Y-%m-%d')}")
    content.append("")

    # Financial information section
    content.append(Text("Financial Information", style="bold underline"))
    if mutual_fund.total_assets is not None:
        content.append(
            f"Total Assets: ${mutual_fund.total_assets:,.1f} million")
    if mutual_fund.expense_ratio is not None:
        content.append(f"Expense Ratio: {mutual_fund.expense_ratio:.2f}%")
    if mutual_fund.net_expense_ratio is not None:
        content.append(
            f"Net Expense Ratio: {mutual_fund.net_expense_ratio:.2f}%")
    if mutual_fund.gross_expense_ratio is not None:
        content.append(
            f"Gross Expense Ratio: {mutual_fund.gross_expense_ratio:.2f}%")
    if mutual_fund.management_fee is not None:
        content.append(f"Management Fee: {mutual_fund.management_fee:.2f}%")
    if mutual_fund.yield_percentage is not None:
        content.append(f"Yield: {mutual_fund.yield_percentage:.2f}%")
    if mutual_fund.turnover_ratio is not None:
        content.append(f"Turnover Ratio: {mutual_fund.turnover_ratio:.2f}%")
    content.append("")

    # Investment details
    content.append(Text("Investment Details", style="bold underline"))
    if mutual_fund.minimum_investment is not None:
        content.append(
            f"Minimum Investment: ${mutual_fund.minimum_investment:,.2f}")
    if mutual_fund.morningstar_rating:
        stars = "★" * mutual_fund.morningstar_rating
        content.append(
            f"Morningstar Rating: {stars} ({mutual_fund.morningstar_rating}/5)")
    content.append("")

    # Investment objective
    if mutual_fund.investment_objective:
        content.append(Text("Investment Objective", style="bold underline"))
        content.append(mutual_fund.investment_objective)

    # Create panel with all sections
    panel_content = "\n".join(str(line) for line in content)
    panel = Panel(panel_content, title=title,
                  border_style="cyan", expand=False)
    console.print(panel)


def display_fund_families(families: List[Dict[str, Any]], limit: Optional[int] = None) -> None:
    """
    Display a list of fund families in a formatted table.

    Args:
        families: List of dictionaries with fund family data
        limit: Maximum number of fund families to display
    """
    if not families:
        console.print("[yellow]No fund families found.[/yellow]")
        return

    # Process the families data to extract key information
    processed_families = []
    for family in families:
        # Create a standardized structure for each family
        processed_family = {
            "name": family.get("name", "Unknown"),
            "fund_count": family.get("fund_count", 0),
            "headquarters": family.get("headquarters", "N/A"),
            "founded": family.get("founded", "N/A"),
            "aum": family.get("aum", "N/A"),  # Assets Under Management
            "website": family.get("website", "N/A"),
            "popular_funds": family.get("popular_funds", [])
        }
        processed_families.append(processed_family)

    # Sort by fund count (if available) then by name
    processed_families.sort(
        key=lambda x: (-x["fund_count"] if isinstance(x["fund_count"], int) else 0, x["name"]))

    # Apply limit if specified
    if limit and len(processed_families) > limit:
        display_families = processed_families[:limit]
        console.print(
            f"[blue]Showing {limit} of {len(processed_families)} fund families.[/blue]")
    else:
        display_families = processed_families

    # Create table for displaying the families
    table = Table(title=f"Fund Families ({len(display_families)} displayed)")

    # Add columns
    table.add_column("Name", style="cyan")
    table.add_column("Fund Count", justify="right")
    table.add_column("Headquarters", style="green")
    table.add_column("Founded")
    table.add_column("AUM", style="yellow")
    table.add_column("Popular Funds")

    # Add rows
    for family in display_families:
        # Format popular funds as a comma-separated list (limited to 3)
        popular_funds = family["popular_funds"]
        if isinstance(popular_funds, list) and popular_funds:
            if len(popular_funds) > 3:
                formatted_funds = ", ".join(
                    popular_funds[:3]) + f" +{len(popular_funds) - 3} more"
            else:
                formatted_funds = ", ".join(popular_funds)
        else:
            formatted_funds = "N/A"

        # Format AUM (Assets Under Management) with proper units
        aum = family["aum"]
        if isinstance(aum, (int, float)):
            if aum >= 1_000_000_000_000:  # Trillions
                formatted_aum = f"${aum / 1_000_000_000_000:.2f}T"
            elif aum >= 1_000_000_000:  # Billions
                formatted_aum = f"${aum / 1_000_000_000:.2f}B"
            elif aum >= 1_000_000:  # Millions
                formatted_aum = f"${aum / 1_000_000:.2f}M"
            else:
                formatted_aum = f"${aum:,.0f}"
        else:
            formatted_aum = str(aum)

        # Add the row to the table
        table.add_row(
            family["name"],
            str(family["fund_count"]),
            str(family["headquarters"]),
            str(family["founded"]),
            formatted_aum,
            formatted_funds
        )

    console.print(table)


def display_fund_family_detail(family: Dict[str, Any]) -> None:
    """
    Display detailed information about a specific fund family.

    Args:
        family: Dictionary containing fund family data
    """
    if not family:
        console.print("[yellow]Fund family information not found.[/yellow]")
        return

    # Create a panel for the fund family
    title = Text(
        f"Fund Family: {family.get('name', 'Unknown')}", style="bold cyan")

    # Format the panel content
    content = []

    # Basic Information section
    content.append(Text("Basic Information", style="bold underline"))

    # Add headquarters if available
    if "headquarters" in family and family["headquarters"]:
        content.append(f"Headquarters: {family['headquarters']}")

    # Add founded date if available
    if "founded" in family and family["founded"]:
        content.append(f"Founded: {family['founded']}")

    # Add website if available
    if "website" in family and family["website"]:
        website = Text(f"Website: {family['website']}", style="blue underline")
        content.append(website)

    content.append("")  # Add blank line

    # Financial Information section
    content.append(Text("Financial Information", style="bold underline"))

    # Add AUM if available
    if "aum" in family and family["aum"]:
        aum = family["aum"]
        if isinstance(aum, (int, float)):
            if aum >= 1_000_000_000_000:  # Trillions
                formatted_aum = f"${aum / 1_000_000_000_000:.2f} trillion"
            elif aum >= 1_000_000_000:  # Billions
                formatted_aum = f"${aum / 1_000_000_000:.2f} billion"
            elif aum >= 1_000_000:  # Millions
                formatted_aum = f"${aum / 1_000_000:.2f} million"
            else:
                formatted_aum = f"${aum:,.0f}"
        else:
            formatted_aum = str(aum)
        content.append(f"Assets Under Management: {formatted_aum}")

    # Add fund count if available
    if "fund_count" in family and family["fund_count"]:
        content.append(f"Number of Funds: {family['fund_count']:,}")

    content.append("")  # Add blank line

    # Popular Funds section
    popular_funds = family.get("popular_funds", [])
    if popular_funds:
        content.append(Text("Popular Funds", style="bold underline"))
        for fund in popular_funds[:10]:  # Limit to 10 funds to prevent overflow
            content.append(f"• {fund}")

        if len(popular_funds) > 10:
            content.append(f"... and {len(popular_funds) - 10} more")

    # Add description if available
    if "description" in family and family["description"]:
        content.append("")  # Add blank line
        content.append(Text("Description", style="bold underline"))
        content.append(Text(family["description"]))

    # Create and display the panel
    panel_content = "\n".join(str(line) for line in content)
    panel = Panel(panel_content, title=title,
                  border_style="cyan", expand=False)
    console.print(panel)


def display_mutual_fund_types(fund_types: List[Dict[str, Any]], limit: Optional[int] = None) -> None:
    """
    Display a list of mutual fund types in a formatted table.

    Args:
        fund_types: List of dictionaries with mutual fund type data
        limit: Maximum number of fund types to display
    """
    if not fund_types:
        console.print("[yellow]No mutual fund types found.[/yellow]")
        return

    # Apply limit if specified
    if limit and limit > 0 and len(fund_types) > limit:
        display_types = fund_types[:limit]
        console.print(
            f"[blue]Showing {limit} of {len(fund_types)} fund types.[/blue]")
    else:
        display_types = fund_types

    # Create table for displaying the fund types
    table = Table(title=f"Mutual Fund Types ({len(display_types)} displayed)")

    # Add columns
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Risk Level", style="yellow")
    table.add_column("Example Funds")

    # Add rows
    for fund_type in display_types:
        # Format risk level with color coding
        risk_level = fund_type.get("risk_level", "Medium")
        if risk_level == "Low":
            risk_level_formatted = "[green]Low[/green]"
        elif risk_level == "Medium":
            risk_level_formatted = "[yellow]Medium[/yellow]"
        else:  # High
            risk_level_formatted = "[red]High[/red]"

        # Format example funds as a comma-separated list (limited to 3)
        example_funds = fund_type.get("example_funds", [])
        if example_funds:
            if len(example_funds) > 3:
                formatted_funds = ", ".join(
                    example_funds[:3]) + f" +{len(example_funds) - 3} more"
            else:
                formatted_funds = ", ".join(example_funds)
        else:
            formatted_funds = "N/A"

        # Add the row to the table
        table.add_row(
            fund_type.get("name", "Unknown"),
            str(fund_type.get("count", 0)),
            risk_level_formatted,
            formatted_funds
        )

    console.print(table)


def display_mutual_fund_type_detail(type_detail: Dict[str, Any]) -> None:
    """
    Display detailed information about a specific mutual fund type.

    Args:
        type_detail: Dictionary containing fund type data
    """
    if not type_detail:
        console.print("[yellow]Fund type information not found.[/yellow]")
        return

    # Create a panel for the fund type
    title = Text(
        f"Mutual Fund Type: {type_detail.get('name', 'Unknown')}", style="bold cyan")

    # Format the panel content
    content = []

    # Overview section
    content.append(Text("Overview", style="bold underline"))

    # Count of funds
    content.append(f"Number of Funds: {type_detail.get('count', 0):,}")

    # Risk level
    risk_level = type_detail.get("risk_level", "Medium")
    if risk_level == "Low":
        risk_text = Text(f"Risk Level: Low", style="green")
    elif risk_level == "Medium":
        risk_text = Text(f"Risk Level: Medium", style="yellow")
    else:  # High
        risk_text = Text(f"Risk Level: High", style="red")
    content.append(risk_text)

    # Description
    content.append("")
    content.append(Text("Description", style="bold underline"))
    content.append(type_detail.get("description", "No description available."))

    # Top fund families section
    top_families = type_detail.get("top_families", [])
    if top_families:
        content.append("")
        content.append(Text("Top Fund Families", style="bold underline"))

        # Create a bullet list of top families with counts
        for i, family in enumerate(top_families[:5], 1):
            content.append(
                f"• {family.get('name', 'Unknown')}: {family.get('count', 0):,} funds")

        if len(top_families) > 5:
            content.append(f"... and {len(top_families) - 5} more families")

    # Example funds section
    example_funds = type_detail.get("example_funds", [])
    if example_funds:
        content.append("")
        content.append(Text("Example Funds", style="bold underline"))

        # Create a bullet list of example funds
        for i, fund in enumerate(example_funds[:8], 1):
            content.append(f"• {fund}")

        if len(example_funds) > 8:
            content.append(f"... and {len(example_funds) - 8} more funds")

    # Example symbols section
    example_symbols = type_detail.get("example_symbols", [])
    if example_symbols:
        content.append("")
        content.append(Text("Example Symbols", style="bold underline"))
        content.append(", ".join(example_symbols))

    # Create and display the panel
    panel_content = "\n".join(str(line) for line in content)
    panel = Panel(panel_content, title=title,
                  border_style="cyan", expand=False)
    console.print(panel)


def display_company_profile(company: Any) -> None:
    """
    Display detailed company profile information.

    Args:
        company: CompanyProfile object to display
    """
    if not company:
        console.print("[yellow]Company information not found.[/yellow]")
        return

    # Create a panel for the company profile
    title = Text(
        f"Company Profile: {company.name} ({company.symbol})", style="bold cyan")

    # Format the panel content
    content = []

    # Basic Information section
    content.append(Text("Basic Information", style="bold underline"))
    content.append(f"Name: {company.name}")
    content.append(f"Symbol: {company.symbol}")
    content.append(f"Exchange: {company.exchange}")
    content.append(f"Country: {company.country}")

    if company.industry:
        content.append(f"Industry: {company.industry}")
    if company.sector:
        content.append(f"Sector: {company.sector}")

    if company.founded:
        content.append(f"Founded: {company.founded}")
    if company.employees:
        content.append(f"Employees: {company.employees:,}")

    if company.ceo:
        content.append(f"CEO: {company.ceo}")

    if company.website:
        website_text = Text(
            f"Website: {company.website}", style="blue underline")
        content.append(website_text)

    if company.address or company.phone:
        content.append("")
        content.append(Text("Contact Information", style="bold underline"))
        if company.address:
            content.append(f"Address: {company.address}")
        if company.phone:
            content.append(f"Phone: {company.phone}")

    # Financial Information section if any financial metrics are available
    if any([company.market_cap, company.revenue, company.net_income, company.pe_ratio, company.dividend_yield]):
        content.append("")
        content.append(Text("Financial Information", style="bold underline"))

        if company.market_cap:
            # Format market cap with appropriate units (B for billions, T for trillions)
            if company.market_cap >= 1_000_000_000_000:
                market_cap_str = f"${company.market_cap / 1_000_000_000_000:.2f}T"
            elif company.market_cap >= 1_000_000_000:
                market_cap_str = f"${company.market_cap / 1_000_000_000:.2f}B"
            elif company.market_cap >= 1_000_000:
                market_cap_str = f"${company.market_cap / 1_000_000:.2f}M"
            else:
                market_cap_str = f"${company.market_cap:,.0f}"

            content.append(f"Market Cap: {market_cap_str}")

        if company.revenue:
            # Format revenue with appropriate units
            if company.revenue >= 1_000_000_000_000:
                revenue_str = f"${company.revenue / 1_000_000_000_000:.2f}T"
            elif company.revenue >= 1_000_000_000:
                revenue_str = f"${company.revenue / 1_000_000_000:.2f}B"
            elif company.revenue >= 1_000_000:
                revenue_str = f"${company.revenue / 1_000_000:.2f}M"
            else:
                revenue_str = f"${company.revenue:,.0f}"

            content.append(f"Annual Revenue: {revenue_str}")

        if company.net_income:
            # Format net income with appropriate units
            if abs(company.net_income) >= 1_000_000_000_000:
                income_str = f"${company.net_income / 1_000_000_000_000:.2f}T"
            elif abs(company.net_income) >= 1_000_000_000:
                income_str = f"${company.net_income / 1_000_000_000:.2f}B"
            elif abs(company.net_income) >= 1_000_000:
                income_str = f"${company.net_income / 1_000_000:.2f}M"
            else:
                income_str = f"${company.net_income:,.0f}"

            # Add color based on whether profit or loss
            if company.net_income >= 0:
                income_text = Text(f"Net Income: {income_str}", style="green")
            else:
                income_text = Text(f"Net Income: {income_str}", style="red")

            content.append(income_text)

        if company.pe_ratio:
            content.append(f"P/E Ratio: {company.pe_ratio:.2f}")

        if company.dividend_yield:
            content.append(f"Dividend Yield: {company.dividend_yield:.2f}%")

    # Executive section if available
    if company.executives and len(company.executives) > 0:
        content.append("")
        content.append(Text("Key Executives", style="bold underline"))

        # Limit to top 5 execs to avoid lengthy display
        for exec in company.executives[:5]:
            exec_line = f"• {exec.name}, {exec.title}"
            if exec.salary:
                exec_line += f" - Salary: ${exec.salary:,.0f}"

            content.append(exec_line)

        if len(company.executives) > 5:
            content.append(
                f"... {len(company.executives) - 5} more executives not shown")

    # Description section if available
    if company.description:
        content.append("")
        content.append(Text("Business Description", style="bold underline"))

        # Wrap the description to fit in the panel
        from textwrap import fill
        wrapped_description = fill(company.description, width=100)
        content.append(wrapped_description)

    # Create and display the panel
    panel_content = "\n".join(str(line) for line in content)
    panel = Panel(panel_content, title=title,
                  border_style="cyan", expand=False)
    console.print(panel)


def display_company_search_results(companies: List[Dict[str, Any]], query: str) -> None:
    """
    Display search results for companies.

    Args:
        companies: List of dictionaries with company information
        query: Original search query
    """
    if not companies:
        console.print(
            f"[yellow]No companies found matching '{query}'.[/yellow]")
        return

    table = Table(
        title=f"Company Search Results for '{query}' ({len(companies)} found)")

    # Add columns
    table.add_column("Symbol", style="cyan")
    table.add_column("Name")
    table.add_column("Exchange")
    table.add_column("Country")
    table.add_column("Type")

    # Add rows
    for company in companies:
        table.add_row(
            company.get("symbol", ""),
            company.get("name", ""),
            company.get("exchange", ""),
            company.get("country", ""),
            company.get("type", "")
        )

    console.print(table)
    console.print(
        "[blue]Tip: Use 'stockcli company info SYMBOL' to get detailed company information.[/blue]")
