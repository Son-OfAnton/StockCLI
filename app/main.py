#!/usr/bin/env python3
"""
Stock CLI - Main entry point for the application.
This file will setup and run the CLI commands.
"""

import sys
import logging
from pathlib import Path
import click
from app.cli.commands import compare_income_statements_command, expense_breakdown_command, get_income_statement_command, stock, fetch_and_display_quotes, refresh_quotes, export_last as export_last_quotes
from app.utils.display import create_progress_spinner
from app.utils.export import generate_export_filename, get_default_export_dir, get_home_export_dir
from app.api.twelve_data import TwelveDataAPIError, client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_cli.log"),
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
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export quotes to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files (default: project's exports directory)")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def quote_shortcut(symbols, refresh, interval, detailed, debug, export, output_dir, use_home_dir):
    """Shortcut for 'stock quote' command."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

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
        refresh_quotes(symbols, interval, detailed, debug,
                       export_formats, export_output_dir)
    else:
        quotes = fetch_and_display_quotes(symbols, detailed, debug)

        # Export if requested
        if export and quotes:
            from app.utils.export import export_quotes
            export_results = export_quotes(
                quotes, export_formats, export_output_dir)

            if export_results:
                click.echo("\nExported quotes to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")


@cli.command(name="export-last")
@click.option("--format", "-f", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              default='both', help="Export format (default: both)")
@click.option("--output-dir", "-o", type=click.Path(file_okay=False),
              help="Directory to save exported files (default: project's exports directory)")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def export_last_shortcut(format, output_dir, use_home_dir):
    """Export the most recently fetched quotes."""
    ctx = click.get_current_context()
    ctx.invoke(
        export_last_quotes,
        format=format,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="symbols")
def symbols_shortcut():
    """Commands for exploring available symbols (shortcut for 'stock symbols')."""
    pass


@symbols_shortcut.command(name="list")
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
def list_symbols_shortcut(exchange, type, country, search, limit, detailed,
                          export, output_dir, use_home_dir):
    """List available symbols with optional filtering."""
    # Import the actual command function
    from app.cli.commands import list_symbols

    ctx = click.get_current_context()
    ctx.invoke(
        list_symbols,
        exchange=exchange,
        type=type,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="types")
def list_symbol_types_shortcut():
    """List available symbol types."""
    from app.cli.commands import list_symbol_types
    ctx = click.get_current_context()
    ctx.invoke(list_symbol_types)


@symbols_shortcut.command(name="exchanges")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_exchanges_shortcut(export, output_dir, use_home_dir):
    """List available exchanges."""
    from app.cli.commands import list_exchanges
    ctx = click.get_current_context()
    ctx.invoke(
        list_exchanges,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="forex")
def forex_shortcut():
    """Commands for exploring forex currency pairs (shortcut for 'stock forex')."""
    pass


@forex_shortcut.command(name="pairs")
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
def list_forex_pairs_shortcut(base, quote, limit, export, output_dir, use_home_dir):
    """List available forex currency pairs with optional filtering."""
    # Import the actual command function
    from app.cli.commands import list_forex_pairs
    # Call the function with all parameters
    ctx = click.get_current_context()
    ctx.invoke(
        list_forex_pairs,
        base=base,
        quote=quote,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@forex_shortcut.command(name="currencies")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_currencies_shortcut(export, output_dir, use_home_dir):
    """List available currencies."""
    from app.cli.commands import list_currencies
    ctx = click.get_current_context()
    ctx.invoke(
        list_currencies,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="crypto")
def crypto_shortcut():
    """Commands for exploring cryptocurrency data (shortcut for 'stock crypto')."""
    pass


@crypto_shortcut.command(name="list")
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
def list_crypto_pairs_shortcut(exchange, base, quote, search, limit, detailed,
                               export, output_dir, use_home_dir):
    """List available cryptocurrency pairs with optional filtering."""
    # Import the actual command function
    from app.cli.commands import list_crypto_pairs
    # Call the function with all parameters

    ctx = click.get_current_context()
    ctx.invoke(
        list_crypto_pairs,
        exchange=exchange,
        base=base,
        quote=quote,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@crypto_shortcut.command(name="exchanges")
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_crypto_exchanges_shortcut(export, output_dir, use_home_dir):
    """List available cryptocurrency exchanges."""
    from app.cli.commands import list_crypto_exchanges

    ctx = click.get_current_context()
    ctx.invoke(
        list_crypto_exchanges,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="funds")
def funds_shortcut():
    """Commands for exploring available funds (shortcut for 'stock funds')."""
    pass


@funds_shortcut.command(name="list")
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
def list_funds_shortcut(type, exchange, country, search, limit, detailed,
                        export, output_dir, use_home_dir):
    """List available funds (ETFs and mutual funds) with optional filtering."""
    from app.cli.commands import list_funds

    ctx = click.get_current_context()
    ctx.invoke(
        list_funds,
        type=type,
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@funds_shortcut.command(name="etfs")
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
def list_etfs_shortcut(exchange, country, search, limit, detailed,
                       export, output_dir, use_home_dir):
    """List available ETFs with optional filtering."""
    from app.cli.commands import list_etfs

    ctx = click.get_current_context()
    ctx.invoke(
        list_etfs,
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@funds_shortcut.command(name="mutual")
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
def list_mutual_funds_shortcut(exchange, country, search, limit, detailed,
                               export, output_dir, use_home_dir):
    """List available mutual funds with optional filtering."""
    from app.cli.commands import list_mutual_funds
    ctx = click.get_current_context()
    ctx.invoke(
        list_mutual_funds,
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="bonds")
def bonds_shortcut():
    """Commands for exploring available bonds (shortcut for 'stock bonds')."""
    pass


@bonds_shortcut.command(name="list")
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
def list_bonds_shortcut(type, exchange, country, search, limit, detailed,
                        export, output_dir, use_home_dir):
    """List available bonds with optional filtering."""
    from app.cli.commands import list_bonds

    ctx = click.get_current_context()
    ctx.invoke(
        list_bonds,
        type=type,
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@bonds_shortcut.command(name="government")
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
def government_bonds_shortcut(exchange, country, search, limit, detailed,
                              export, output_dir, use_home_dir):
    """List government bonds with optional filtering."""
    from app.cli.commands import list_government_bonds

    ctx = click.get_current_context()
    ctx.invoke(
        list_government_bonds,
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@bonds_shortcut.command(name="corporate")
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
def corporate_bonds_shortcut(exchange, country, search, limit, detailed,
                             export, output_dir, use_home_dir):
    """List corporate bonds with optional filtering."""
    from app.cli.commands import list_corporate_bonds

    ctx = click.get_current_context()
    ctx.invoke(
        list_corporate_bonds,
        exchange=exchange,
        country=country,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@bonds_shortcut.command(name="types")
def bond_types_shortcut():
    """List available bond types."""
    from app.cli.commands import list_bond_types

    ctx = click.get_current_context()
    ctx.invoke(list_bond_types)


@cli.group(name="etfs")
def etfs_shortcut():
    """Commands for exploring available ETFs (Exchange-Traded Funds)."""
    pass


@etfs_shortcut.command(name="list")
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
def list_etfs_shortcut(asset_class, exchange, country, search, limit, detailed, sort_by, descending,
                       export, output_dir, use_home_dir):
    """List available ETFs with optional filtering."""
    from app.cli.commands import list_etfs

    ctx = click.get_current_context()
    ctx.invoke(
        list_etfs,
        asset_class=asset_class,
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


@etfs_shortcut.command(name="equity")
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
def equity_etfs_shortcut(exchange, country, search, limit, detailed, sort_by, descending,
                         export, output_dir, use_home_dir):
    """List equity ETFs with optional filtering."""
    from app.cli.commands import list_equity_etfs

    ctx = click.get_current_context()
    ctx.invoke(
        list_equity_etfs,
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


@etfs_shortcut.command(name="fixed-income")
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
def fixed_income_etfs_shortcut(exchange, country, search, limit, detailed, sort_by, descending,
                               export, output_dir, use_home_dir):
    """List fixed income ETFs (bond ETFs) with optional filtering."""
    from app.cli.commands import list_fixed_income_etfs

    ctx = click.get_current_context()
    ctx.invoke(
        list_fixed_income_etfs,
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


@etfs_shortcut.command(name="info")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def etf_info_shortcut(symbol, export, output_dir, use_home_dir):
    """Get detailed information for a specific ETF by symbol."""
    from app.cli.commands import get_etf_info

    ctx = click.get_current_context()
    ctx.invoke(
        get_etf_info,
        symbol=symbol,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@etfs_shortcut.command(name="asset-classes")
def etf_asset_classes_shortcut():
    """List available ETF asset classes."""
    from app.cli.commands import list_etf_asset_classes

    ctx = click.get_current_context()
    ctx.invoke(list_etf_asset_classes)


@cli.group(name="commodities")
def commodities_shortcut():
    """Commands for exploring available commodity trading pairs."""
    pass


@commodities_shortcut.command(name="list")
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
def list_commodities_shortcut(group, exchange, search, limit, detailed,
                              export, output_dir, use_home_dir):
    """List available commodity trading pairs with optional filtering."""
    from app.cli.commands import list_commodity_pairs

    ctx = click.get_current_context()
    ctx.invoke(
        list_commodity_pairs,
        group=group,
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@commodities_shortcut.command(name="groups")
def commodity_groups_shortcut():
    """List available commodity groups with descriptions."""
    from app.cli.commands import list_commodity_groups

    ctx = click.get_current_context()
    ctx.invoke(list_commodity_groups)


@commodities_shortcut.command(name="precious-metals")
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
def precious_metals_shortcut(exchange, search, limit, detailed,
                             export, output_dir, use_home_dir):
    """List precious metals commodity pairs with optional filtering."""
    from app.cli.commands import list_precious_metals

    ctx = click.get_current_context()
    ctx.invoke(
        list_precious_metals,
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@commodities_shortcut.command(name="energy")
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
def energy_commodities_shortcut(exchange, search, limit, detailed,
                                export, output_dir, use_home_dir):
    """List energy commodity pairs with optional filtering."""
    from app.cli.commands import list_energy_commodities

    ctx = click.get_current_context()
    ctx.invoke(
        list_energy_commodities,
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@commodities_shortcut.command(name="agriculture")
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
def agricultural_commodities_shortcut(exchange, search, limit, detailed,
                                      export, output_dir, use_home_dir):
    """List agricultural commodity pairs with optional filtering."""
    from app.cli.commands import list_agricultural_commodities

    ctx = click.get_current_context()
    ctx.invoke(
        list_agricultural_commodities,
        exchange=exchange,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="cross-list")
@click.option("--symbol", "-s", help="Filter by specific symbol (e.g., 'AAPL')")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def cross_listed_symbols_shortcut(symbol, export, output_dir, use_home_dir):
    """List symbols that are cross-listed on multiple exchanges."""
    from app.cli.commands import list_cross_listed_symbols

    ctx = click.get_current_context()
    ctx.invoke(
        list_cross_listed_symbols,
        symbol=symbol,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="exchanges")
@click.option("--type", "-t", help="Filter by exchange type (e.g., 'stock', 'etf')")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_exchanges_shortcut(type, export, output_dir, use_home_dir):
    """List available exchanges with optional filtering by type."""
    from app.cli.commands import list_exchanges
    ctx = click.get_current_context()
    ctx.invoke(
        list_exchanges,
        type=type,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="exchange-details")
@click.argument("exchange", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def exchange_details_shortcut(exchange, export, output_dir, use_home_dir):
    """Get detailed information for a specific exchange."""
    from app.cli.commands import get_exchange_details_alias

    ctx = click.get_current_context()
    ctx.invoke(
        get_exchange_details_alias,
        exchange=exchange,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="trading-hours")
@click.argument("exchange", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def trading_hours_shortcut(exchange, export, output_dir, use_home_dir):
    """Get trading hours for a specific exchange."""
    from app.cli.commands import get_exchange_trading_hours

    ctx = click.get_current_context()
    ctx.invoke(
        get_exchange_trading_hours,
        exchange=exchange,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="all-trading-hours")
@click.option("--type", "-t", help="Filter by exchange type (e.g., 'stock', 'etf')")
@click.option("--limit", "-l", type=int, help="Limit the number of exchanges to fetch")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def exchanges_with_hours_shortcut(type, limit, export, output_dir, use_home_dir):
    """List all exchanges with their opening and closing times."""
    from app.cli.commands import list_exchanges_with_hours
    ctx = click.get_current_context()
    ctx.invoke(
        list_exchanges_with_hours,
        type=type,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="instrument-types")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def instrument_types_shortcut(export, output_dir, use_home_dir):
    """List available instrument types from the TwelveData API."""
    from app.cli.commands import list_instrument_types
    ctx = click.get_current_context()
    ctx.invoke(
        list_instrument_types,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="earliest-data")
@click.argument("symbol", required=True)
@click.option("--interval", "-i", default="1day",
              help="Time interval (e.g., '1min', '5min', '1h', '1day', '1week', '1month')")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def earliest_data_shortcut(symbol, interval, export, output_dir, use_home_dir):
    """Get the first available datetime for a given instrument at a specific interval."""
    from app.cli.commands import get_earliest_data
    ctx = click.get_current_context()
    ctx.invoke(
        get_earliest_data,
        symbol=symbol,
        interval=interval,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@symbols_shortcut.command(name="search")
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
def symbol_search_shortcut(query, limit, type, exchange, country, export, output_dir, use_home_dir):
    """Search for symbols matching a query string."""
    from app.cli.commands import search_symbols
    ctx = click.get_current_context()
    ctx.invoke(
        search_symbols,
        query=query,
        limit=limit,
        type=type,
        exchange=exchange,
        country=country,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="search")
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
def search_shortcut(query, limit, type, exchange, country, export, output_dir, use_home_dir):
    """Quick search for symbols matching a query string."""
    from app.cli.commands import search_symbols
    ctx = click.get_current_context()
    ctx.invoke(
        search_symbols,
        query=query,
        limit=limit,
        type=type,
        exchange=exchange,
        country=country,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="time-series")
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
def time_series_shortcut(symbol, interval, outputsize, start_date, end_date, order, include_ext,
                         limit, export, output_dir, use_home_dir):
    """Fetch meta and time series data for a requested instrument."""
    from app.cli.commands import get_time_series
    ctx = click.get_current_context()
    ctx.invoke(
        get_time_series,
        symbol=symbol,
        interval=interval,
        outputsize=outputsize,
        start_date=start_date,
        end_date=end_date,
        order=order,
        include_ext=include_ext,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@forex_shortcut.command(name="rate")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def exchange_rate_shortcut(symbol, export, output_dir, use_home_dir):
    """Get real-time exchange rate for a currency pair."""
    from app.cli.commands import get_exchange_rate
    ctx = click.get_current_context()
    ctx.invoke(
        get_exchange_rate,
        symbol=symbol,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="latest-quote")
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
def latest_quote_shortcut(symbol, refresh, interval, simple, export, output_dir, use_home_dir):
    """Get the latest quote for a specific instrument."""
    from app.cli.commands import get_latest_quote
    ctx = click.get_current_context()
    ctx.invoke(
        get_latest_quote,
        symbol=symbol,
        refresh=refresh,
        interval=interval,
        simple=simple,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="eod")
@click.argument("symbol", required=True)
@click.option("--date", "-d", help="Specific date in YYYY-MM-DD format (defaults to latest available)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export EOD data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def eod_shortcut(symbol: str, date: str, export: str, output_dir: str, use_home_dir: bool):
    """Shortcut for 'stock eod' command."""
    from app.cli.commands import eod_command
    ctx = click.get_current_context()
    ctx.invoke(
        eod_command,
        symbol=symbol,
        date=date,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="gainers")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ', 'NYSE')")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of stocks to display")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def gainers_shortcut(exchange: str, limit: int, export: str, output_dir: str, use_home_dir: bool):
    """Shortcut for 'stock gainers' command."""
    from app.cli.commands import gainers_command
    ctx = click.get_current_context()
    ctx.invoke(
        gainers_command,
        exchange=exchange,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.command(name="losers")
@click.option("--exchange", "-e", help="Filter by exchange (e.g., 'NASDAQ', 'NYSE')")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of stocks to display")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def losers_shortcut(exchange: str, limit: int, export: str, output_dir: str, use_home_dir: bool):
    """Shortcut for 'stock losers' command."""
    from app.cli.commands import losers_command
    ctx = click.get_current_context()
    ctx.invoke(
        losers_command,
        exchange=exchange,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="mutual-funds")
def mutual_funds_shortcut():
    """Shortcut for 'stock mutual-funds' commands."""
    pass


@mutual_funds_shortcut.command(name="list")
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
def list_mutual_funds_shortcut(exchange, country, family, search, limit, detailed,
                               export, output_dir, use_home_dir):
    """List available mutual funds with detailed information and filtering."""
    from app.cli.commands import list_mutual_funds_detailed
    ctx = click.get_current_context()
    ctx.invoke(
        list_mutual_funds_detailed,
        exchange=exchange,
        country=country,
        family=family,
        search=search,
        limit=limit,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@mutual_funds_shortcut.command(name="info")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_mutual_fund_profile_shortcut(symbol, export, output_dir, use_home_dir):
    """Get detailed profile information for a specific mutual fund."""
    from app.cli.commands import get_mutual_fund_profile
    ctx = click.get_current_context()
    ctx.invoke(
        get_mutual_fund_profile,
        symbol=symbol,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@mutual_funds_shortcut.command(name="families")
@click.option("--search", "-s", help="Search for fund families by name")
@click.option("--limit", "-l", type=int, default=50,
              help="Maximum number of fund families to display (default: 50, 0 for all)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_fund_families_shortcut(search: str, limit: int, export: str, output_dir: str, use_home_dir: bool):
    """List available fund families with optional filtering."""
    from app.cli.commands import list_fund_families
    ctx = click.get_current_context()
    ctx.invoke(
        list_fund_families,
        search=search,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@mutual_funds_shortcut.command(name="family")
@click.argument("name", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_fund_family_detail_shortcut(name: str, export: str, output_dir: str, use_home_dir: bool):
    """Get detailed information about a specific fund family."""
    from app.cli.commands import get_fund_family_detail
    ctx = click.get_current_context()
    ctx.invoke(
        get_fund_family_detail,
        name=name,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@mutual_funds_shortcut.command(name="types")
@click.option("--limit", "-l", type=int, default=0,
              help="Maximum number of fund types to display (default: 0 = all)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_mutual_fund_types_shortcut(limit: int, export: str, output_dir: str, use_home_dir: bool):
    """List available mutual fund types."""
    from app.cli.commands import list_mutual_fund_types
    ctx = click.get_current_context()
    ctx.invoke(
        list_mutual_fund_types,
        limit=limit,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@mutual_funds_shortcut.command(name="type")
@click.argument("name", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_mutual_fund_type_detail_shortcut(name: str, export: str, output_dir: str, use_home_dir: bool):
    """Get detailed information about a specific mutual fund type."""
    from app.cli.commands import get_mutual_fund_type_detail
    ctx = click.get_current_context()
    ctx.invoke(
        get_mutual_fund_type_detail,
        name=name,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="company")
def company_shortcut():
    """Shortcut for 'stock company' commands."""
    pass


@company_shortcut.command(name="profile")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv'], case_sensitive=False),
              help="Export company profile to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_company_profile_shortcut(symbol: str, export: str, output_dir: str, use_home_dir: bool):
    """Get detailed profile information for a company."""
    from app.cli.commands import get_company_profile
    ctx = click.get_current_context()
    ctx.invoke(
        get_company_profile,
        symbol=symbol,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="dividends")
def dividends_shortcut():
    """Shortcut for 'stock dividends' commands."""
    pass


@dividends_shortcut.command(name="history")
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
def dividend_history_shortcut(symbol, years, detailed, export, output_dir, use_home_dir):
    """Get dividend payment history for a stock symbol."""
    from app.cli.commands import get_dividend_history_command
    ctx = click.get_current_context()
    ctx.invoke(
        get_dividend_history_command,
        symbol=symbol,
        years=years,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@dividends_shortcut.command(name="compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--years", "-y", default=10, type=int,
              help="Number of years of history to retrieve (default: 10)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_dividends_shortcut(symbols, years, export, output_dir, use_home_dir):
    """Compare dividend histories of multiple stock symbols."""
    from app.cli.commands import compare_dividends_command
    ctx = click.get_current_context()
    ctx.invoke(
        compare_dividends_command,
        symbols=symbols,
        years=years,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@dividends_shortcut.command(name="calendar")
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
def dividend_calendar_shortcut(start_date, end_date, range, symbol,
                               exchange, view, date_field,
                               export, output_dir, use_home_dir):
    """Get dividend calendar for a specified date range."""
    from app.cli.commands import dividend_calendar_command
    ctx = click.get_current_context()
    ctx.invoke(
        dividend_calendar_command,
        start_date=start_date,
        end_date=end_date,
        range=range,
        symbol=symbol,
        exchange=exchange,
        view=view,
        date_field=date_field,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cli.group(name="splits")
def splits_shortcut():
    """Shortcut for 'stock splits' commands."""
    pass


@splits_shortcut.command(name="history")
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
def stock_splits_history_shortcut(symbol, years, detailed, export, output_dir, use_home_dir):
    """Get stock splits history for a stock symbol."""
    from app.cli.commands import get_stock_splits_command
    ctx = click.get_current_context()
    ctx.invoke(
        get_stock_splits_command,
        symbol=symbol,
        years=years,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@splits_shortcut.command(name="compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--years", "-y", default=10, type=int,
              help="Number of years of history to retrieve (default: 10)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison results to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_stock_splits_shortcut(symbols, years, export, output_dir, use_home_dir):
    """Compare stock splits histories of multiple stock symbols."""
    from app.cli.commands import compare_stock_splits_command
    ctx = click.get_current_context()
    ctx.invoke(
        compare_stock_splits_command,
        symbols=symbols,
        years=years,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@splits_shortcut.command(name="calendar")
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
def splits_calendar_shortcut(start_date, end_date, range, symbol, exchange, view,
                             forward_only, reverse_only, export, output_dir, use_home_dir):
    """Get stock splits calendar for a specified date range."""
    from app.cli.commands import splits_calendar_command
    ctx = click.get_current_context()
    ctx.invoke(
        splits_calendar_command,
        start_date=start_date,
        end_date=end_date,
        range=range,
        symbol=symbol,
        exchange=exchange,
        view=view,
        forward_only=forward_only,
        reverse_only=reverse_only,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )

# Add shortcut at top level for easier access


@cli.group(name="income-statement")
def income_statement_shortcut():
    """Shortcut for 'stock income-statement' commands."""
    pass


@income_statement_shortcut.command(name="get")
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
def get_income_statement_shortcut(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """Get income statement for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        get_income_statement_command,
        symbol=symbol,
        period=period,
        count=count,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@income_statement_shortcut.command(name="compare")
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
def compare_income_statements_shortcut(symbol, period, count, expenses, export, output_dir, use_home_dir):
    """Compare income statements across multiple periods."""
    ctx = click.get_current_context()
    ctx.invoke(
        compare_income_statements_command,
        symbol=symbol,
        period=period,
        count=count,
        expenses=expenses,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@income_statement_shortcut.command(name="expenses")
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
def expense_breakdown_shortcut(symbol, period, fiscal_date, export, output_dir, use_home_dir):
    """Show detailed expense breakdown for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        expense_breakdown_command,
        symbol=symbol,
        period=period,
        fiscal_date=fiscal_date,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="balance-sheet")
def balance_sheet_group():
    """Commands for retrieving company balance sheets."""
    pass


@balance_sheet_group.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed balance sheet with percentages")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export balance sheet to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_balance_sheet_command(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """
    Get balance sheet for a company.

    Retrieves the balance sheet for a given company symbol, showing assets,
    liabilities, and shareholders' equity.

    Examples:
        stockcli balance-sheet get AAPL --period annual
        stockcli balance-sheet get MSFT --period quarter --count 1 --detailed
    """
    from app.models.balance_sheet import BalanceSheet
    from app.utils.display import display_balance_sheet
    from app.utils.export import export_balance_sheet, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} balance sheet for {symbol}..."):
        try:
            response = client.get_balance_sheet(symbol, period, count)
            balance_sheets = []

            for item in response.get('balance_sheet', []):
                balance_sheet = BalanceSheet.from_api_response(item)
                balance_sheets.append(balance_sheet)

            if not balance_sheets:
                click.echo(f"No balance sheet data available for {symbol}")
                return

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display the most recent statement
    most_recent = balance_sheets[0] if balance_sheets else None
    if most_recent:
        display_balance_sheet(most_recent, detailed)

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

            export_results = export_balance_sheet(
                most_recent, export_formats, export_output_dir)

            if export_results:
                click.echo("\nExported balance sheet to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")


@balance_sheet_group.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--focus", "-f", type=click.Choice(['full', 'assets', 'liabilities', 'equity', 'ratios']),
              default='full', help="Focus on specific section (default: full balance sheet)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_balance_sheets_command(symbol, period, count, focus, export, output_dir, use_home_dir):
    """
    Compare balance sheets across multiple periods.

    Display balance sheets side-by-side to analyze trends in assets,
    liabilities, and equity over time.

    Examples:
        stockcli balance-sheet compare AAPL
        stockcli balance-sheet compare MSFT --period quarter --count 8 --focus assets
    """
    from app.models.balance_sheet import BalanceSheet
    from app.utils.display import display_balance_sheet_comparison
    from app.utils.export import export_balance_sheets, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} balance sheets for {symbol}..."):
        try:
            response = client.get_balance_sheet(symbol, period, count)
            balance_sheets = []

            for item in response.get('balance_sheet', []):
                balance_sheet = BalanceSheet.from_api_response(item)
                balance_sheets.append(balance_sheet)

            if not balance_sheets:
                click.echo(f"No balance sheet data available for {symbol}")
                return

            # Sort by date (most recent first)
            balance_sheets.sort(key=lambda s: s.fiscal_date, reverse=True)

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display comparison
    display_balance_sheet_comparison(balance_sheets, focus=focus)

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

        export_results = export_balance_sheets(
            balance_sheets, export_formats, export_output_dir)

        if export_results:
            click.echo("\nExported balance sheets to:")
            for fmt, path in export_results.items():
                if isinstance(path, list):
                    click.echo(
                        f"  {fmt.upper()}: Multiple files in {Path(path[0]).parent}")
                else:
                    click.echo(f"  {fmt.upper()}: {path}")


@balance_sheet_group.command(name="structure")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--fiscal-date", "-d",
              help="Specific fiscal date (e.g. '2023-09-30'). Uses most recent if not specified.")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export structure breakdown to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def balance_sheet_structure_command(symbol, period, fiscal_date, export, output_dir, use_home_dir):
    """
    Show detailed structure breakdown of a company's balance sheet.

    Analyzes and visualizes the balance sheet structure, showing the relative
    proportions of assets, liabilities, and equity.

    Examples:
        stockcli balance-sheet structure AAPL
        stockcli balance-sheet structure MSFT --period quarter --fiscal-date 2023-03-31
    """
    from app.models.balance_sheet import BalanceSheet
    from app.utils.display import display_balance_sheet_structure
    from app.utils.export import export_balance_sheet_summary, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} balance sheet for {symbol}..."):
        try:
            # We'll fetch the most recent statements (or more if fiscal date is specified)
            fetch_count = 10 if fiscal_date else 1
            response = client.get_balance_sheet(symbol, period, fetch_count)
            balance_sheets = []

            for item in response.get('balance_sheet', []):
                balance_sheet = BalanceSheet.from_api_response(item)
                balance_sheets.append(balance_sheet)

            if not balance_sheets:
                click.echo(f"No balance sheet data available for {symbol}")
                return

            # Sort by date (most recent first)
            balance_sheets.sort(key=lambda s: s.fiscal_date, reverse=True)

            # If fiscal date specified, find matching statement
            target_statement = None
            if fiscal_date:
                target_statement = next(
                    (s for s in balance_sheets if s.fiscal_date == fiscal_date), None)
                if not target_statement:
                    click.echo(
                        f"No balance sheet found for fiscal date {fiscal_date}")
                    click.echo("Available fiscal dates:")
                    for s in balance_sheets:
                        click.echo(f"  {s.fiscal_date}")
                    return
            else:
                # Use most recent statement
                target_statement = balance_sheets[0]

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display structure breakdown
    display_balance_sheet_structure(target_statement)

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

        export_results = export_balance_sheet_summary(
            target_statement, export_formats, export_output_dir)

        if export_results:
            click.echo("\nExported balance sheet structure summary to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


# Add shortcut at top level for easier access
@cli.group(name="balance-sheet")
def balance_sheet_shortcut():
    """Shortcut for 'stock balance-sheet' commands."""
    pass


@balance_sheet_shortcut.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed balance sheet with percentages")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export balance sheet to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_balance_sheet_shortcut(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """Get balance sheet for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        get_balance_sheet_command,
        symbol=symbol,
        period=period,
        count=count,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@balance_sheet_shortcut.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--focus", "-f", type=click.Choice(['full', 'assets', 'liabilities', 'equity', 'ratios']),
              default='full', help="Focus on specific section (default: full balance sheet)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_balance_sheets_shortcut(symbol, period, count, focus, export, output_dir, use_home_dir):
    """Compare balance sheets across multiple periods."""
    ctx = click.get_current_context()
    ctx.invoke(
        compare_balance_sheets_command,
        symbol=symbol,
        period=period,
        count=count,
        focus=focus,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@balance_sheet_shortcut.command(name="structure")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--fiscal-date", "-d",
              help="Specific fiscal date (e.g. '2023-09-30'). Uses most recent if not specified.")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export structure breakdown to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def balance_sheet_structure_shortcut(symbol, period, fiscal_date, export, output_dir, use_home_dir):
    """Show detailed structure breakdown of a company's balance sheet."""
    ctx = click.get_current_context()
    ctx.invoke(
        balance_sheet_structure_command,
        symbol=symbol,
        period=period,
        fiscal_date=fiscal_date,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="consolidated-balance-sheet")
def consolidated_balance_sheet_group():
    """Commands for retrieving company consolidated balance sheets."""
    pass


@consolidated_balance_sheet_group.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed balance sheet with percentages")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export balance sheet to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_consolidated_balance_sheet_command(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """
    Get consolidated balance sheet for a company.

    Retrieves the consolidated balance sheet for a given company symbol, showing assets,
    liabilities, and shareholders' equity across all subsidiaries.

    Examples:
        stockcli consolidated-balance-sheet get AAPL --period annual
        stockcli consolidated-balance-sheet get MSFT --period quarter --count 1 --detailed
    """
    from app.models.balance_sheet import BalanceSheet
    from app.utils.display import display_balance_sheet
    from app.utils.export import export_balance_sheet, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} consolidated balance sheet for {symbol}..."):
        try:
            response = client.get_consolidated_balance_sheet(
                symbol, period, count)
            balance_sheets = []

            for item in response.get('balance_sheet', []):
                balance_sheet = BalanceSheet.from_api_response(item)
                balance_sheets.append(balance_sheet)

            if not balance_sheets:
                click.echo(
                    f"No consolidated balance sheet data available for {symbol}")
                return

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display the most recent statement
    most_recent = balance_sheets[0] if balance_sheets else None
    if most_recent:
        # Add a note that this is a consolidated balance sheet
        click.echo(
            f"[bold]Consolidated Balance Sheet[/bold] - Includes data from all subsidiaries")
        display_balance_sheet(most_recent, detailed)

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

            # Generate special filename to indicate consolidated
            base_filename = generate_export_filename(
                'consolidated_balance_sheet',
                [symbol],
                additional_parts=[period, most_recent.fiscal_date]
            )

            export_results = export_balance_sheet(
                most_recent, export_formats, export_output_dir, base_filename)

            if export_results:
                click.echo("\nExported consolidated balance sheet to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")


@consolidated_balance_sheet_group.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--focus", "-f", type=click.Choice(['full', 'assets', 'liabilities', 'equity', 'ratios']),
              default='full', help="Focus on specific section (default: full balance sheet)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_consolidated_balance_sheets_command(symbol, period, count, focus, export, output_dir, use_home_dir):
    """
    Compare consolidated balance sheets across multiple periods.

    Display consolidated balance sheets side-by-side to analyze trends in assets,
    liabilities, and equity over time.

    Examples:
        stockcli consolidated-balance-sheet compare AAPL
        stockcli consolidated-balance-sheet compare MSFT --period quarter --count 8 --focus assets
    """
    from app.models.balance_sheet import BalanceSheet
    from app.utils.display import display_balance_sheet_comparison
    from app.utils.export import export_balance_sheets, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} consolidated balance sheets for {symbol}..."):
        try:
            response = client.get_consolidated_balance_sheet(
                symbol, period, count)
            balance_sheets = []

            for item in response.get('balance_sheet', []):
                balance_sheet = BalanceSheet.from_api_response(item)
                balance_sheets.append(balance_sheet)

            if not balance_sheets:
                click.echo(
                    f"No consolidated balance sheet data available for {symbol}")
                return

            # Sort by date (most recent first)
            balance_sheets.sort(key=lambda s: s.fiscal_date, reverse=True)

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display comparison
    click.echo(
        f"[bold]Consolidated Balance Sheet Comparison[/bold] - Includes data from all subsidiaries")
    display_balance_sheet_comparison(balance_sheets, focus=focus)

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

        # Generate special filename for consolidated data
        date_range = f"{balance_sheets[-1].fiscal_date}_to_{balance_sheets[0].fiscal_date}"
        base_filename = generate_export_filename(
            'consolidated_balance_sheets',
            [symbol],
            additional_parts=[period, date_range]
        )

        export_results = export_balance_sheets(
            balance_sheets, export_formats, export_output_dir, base_filename)

        if export_results:
            click.echo("\nExported consolidated balance sheets to:")
            for fmt, path in export_results.items():
                if isinstance(path, list):
                    click.echo(
                        f"  {fmt.upper()}: Multiple files in {Path(path[0]).parent}")
                else:
                    click.echo(f"  {fmt.upper()}: {path}")


@consolidated_balance_sheet_group.command(name="structure")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--fiscal-date", "-d",
              help="Specific fiscal date (e.g. '2023-09-30'). Uses most recent if not specified.")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export structure breakdown to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def consolidated_balance_sheet_structure_command(symbol, period, fiscal_date, export, output_dir, use_home_dir):
    """
    Show detailed structure breakdown of a company's consolidated balance sheet.

    Analyzes and visualizes the consolidated balance sheet structure, showing the relative
    proportions of assets, liabilities, and equity across all subsidiaries.

    Examples:
        stockcli consolidated-balance-sheet structure AAPL
        stockcli consolidated-balance-sheet structure MSFT --period quarter --fiscal-date 2023-03-31
    """
    from app.models.balance_sheet import BalanceSheet
    from app.utils.display import display_balance_sheet_structure
    from app.utils.export import export_balance_sheet_summary, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} consolidated balance sheet for {symbol}..."):
        try:
            # We'll fetch the most recent statements (or more if fiscal date is specified)
            fetch_count = 10 if fiscal_date else 1
            response = client.get_consolidated_balance_sheet(
                symbol, period, fetch_count)
            balance_sheets = []

            for item in response.get('balance_sheet', []):
                balance_sheet = BalanceSheet.from_api_response(item)
                balance_sheets.append(balance_sheet)

            if not balance_sheets:
                click.echo(
                    f"No consolidated balance sheet data available for {symbol}")
                return

            # Sort by date (most recent first)
            balance_sheets.sort(key=lambda s: s.fiscal_date, reverse=True)

            # If fiscal date specified, find matching statement
            target_statement = None
            if fiscal_date:
                target_statement = next(
                    (s for s in balance_sheets if s.fiscal_date == fiscal_date), None)
                if not target_statement:
                    click.echo(
                        f"No consolidated balance sheet found for fiscal date {fiscal_date}")
                    click.echo("Available fiscal dates:")
                    for s in balance_sheets:
                        click.echo(f"  {s.fiscal_date}")
                    return
            else:
                # Use most recent statement
                target_statement = balance_sheets[0]

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display structure breakdown
    click.echo(
        f"[bold]Consolidated Balance Sheet Structure[/bold] - Includes data from all subsidiaries")
    display_balance_sheet_structure(target_statement)

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

        # Generate special filename for consolidated data
        base_filename = generate_export_filename(
            'consolidated_balance_sheet_summary',
            [symbol],
            additional_parts=[period, target_statement.fiscal_date]
        )

        export_results = export_balance_sheet_summary(
            target_statement, export_formats, export_output_dir, base_filename)

        if export_results:
            click.echo(
                "\nExported consolidated balance sheet structure summary to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


# Add shortcut at top level for easier access
@cli.group(name="consolidated-balance-sheet")
def consolidated_balance_sheet_shortcut():
    """Shortcut for 'stock consolidated-balance-sheet' commands."""
    pass


@consolidated_balance_sheet_shortcut.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed balance sheet with percentages")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export balance sheet to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_consolidated_balance_sheet_shortcut(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """Get consolidated balance sheet for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        get_consolidated_balance_sheet_command,
        symbol=symbol,
        period=period,
        count=count,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@consolidated_balance_sheet_shortcut.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--focus", "-f", type=click.Choice(['full', 'assets', 'liabilities', 'equity', 'ratios']),
              default='full', help="Focus on specific section (default: full balance sheet)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_consolidated_balance_sheets_shortcut(symbol, period, count, focus, export, output_dir, use_home_dir):
    """Compare consolidated balance sheets across multiple periods."""
    ctx = click.get_current_context()
    ctx.invoke(
        compare_consolidated_balance_sheets_command,
        symbol=symbol,
        period=period,
        count=count,
        focus=focus,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@consolidated_balance_sheet_shortcut.command(name="structure")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--fiscal-date", "-d",
              help="Specific fiscal date (e.g. '2023-09-30'). Uses most recent if not specified.")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export structure breakdown to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def consolidated_balance_sheet_structure_shortcut(symbol, period, fiscal_date, export, output_dir, use_home_dir):
    """Show detailed structure breakdown of a company's consolidated balance sheet."""
    ctx = click.get_current_context()
    ctx.invoke(
        consolidated_balance_sheet_structure_command,
        symbol=symbol,
        period=period,
        fiscal_date=fiscal_date,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="cash-flow")
def cash_flow_group():
    """Commands for retrieving company cash flow statements."""
    pass


@cash_flow_group.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed cash flow statement")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export cash flow to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_cash_flow_command(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """
    Get cash flow statement for a company.

    Retrieves the cash flow statement for a given company symbol, showing inflows and outflows
    of cash from operating, investing, and financing activities.

    Examples:
        stockcli cash-flow get AAPL --period annual
        stockcli cash-flow get MSFT --period quarter --count 1 --detailed
    """
    from app.models.cash_flow import CashFlow
    from app.utils.display import display_cash_flow
    from app.utils.export import export_cash_flow, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} cash flow statement for {symbol}..."):
        try:
            response = client.get_cash_flow(symbol, period, count)
            cash_flows = []

            for item in response.get('cash_flow', []):
                cash_flow = CashFlow.from_api_response(item)
                cash_flows.append(cash_flow)

            if not cash_flows:
                click.echo(f"No cash flow data available for {symbol}")
                return

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display the most recent statement
    most_recent = cash_flows[0] if cash_flows else None
    if most_recent:
        display_cash_flow(most_recent, detailed)

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

            export_results = export_cash_flow(
                most_recent, export_formats, export_output_dir)

            if export_results:
                click.echo("\nExported cash flow statement to:")
                for fmt, path in export_results.items():
                    click.echo(f"  {fmt.upper()}: {path}")


@cash_flow_group.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--focus", "-f", type=click.Choice(['full', 'operating', 'investing', 'financing', 'summary']),
              default='full', help="Focus on specific section (default: full cash flow)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_cash_flows_command(symbol, period, count, focus, export, output_dir, use_home_dir):
    """
    Compare cash flow statements across multiple periods.

    Display cash flow statements side-by-side to analyze trends in cash inflows
    and outflows over time.

    Examples:
        stockcli cash-flow compare AAPL
        stockcli cash-flow compare MSFT --period quarter --count 8 --focus operating
    """
    from app.models.cash_flow import CashFlow
    from app.utils.display import display_cash_flow_comparison
    from app.utils.export import export_cash_flows, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} cash flow statements for {symbol}..."):
        try:
            response = client.get_cash_flow(symbol, period, count)
            cash_flows = []

            for item in response.get('cash_flow', []):
                cash_flow = CashFlow.from_api_response(item)
                cash_flows.append(cash_flow)

            if not cash_flows:
                click.echo(f"No cash flow data available for {symbol}")
                return

            # Sort by date (most recent first)
            cash_flows.sort(key=lambda s: s.fiscal_date, reverse=True)

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display comparison
    display_cash_flow_comparison(cash_flows, focus=focus)

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

        export_results = export_cash_flows(
            cash_flows, export_formats, export_output_dir)

        if export_results:
            click.echo("\nExported cash flow statements to:")
            for fmt, path in export_results.items():
                if isinstance(path, list):
                    click.echo(
                        f"  {fmt.upper()}: Multiple files in {Path(path[0]).parent}")
                else:
                    click.echo(f"  {fmt.upper()}: {path}")


@cash_flow_group.command(name="analyze")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=5,
              help="Number of periods to analyze (default: 5, max: 20)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export analysis to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def analyze_cash_flow_command(symbol, period, count, export, output_dir, use_home_dir):
    """
    Analyze cash flow trends and patterns over time.

    Analyzes multiple periods of cash flow data to identify trends, patterns,
    and insights about a company's cash management.

    Examples:
        stockcli cash-flow analyze AAPL
        stockcli cash-flow analyze MSFT --period quarter --count 8
    """
    from app.models.cash_flow import CashFlow
    from app.utils.display import display_cash_flow_analysis
    from app.utils.export import export_cash_flow_analysis, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching {period} cash flow statements for {symbol}..."):
        try:
            response = client.get_cash_flow(symbol, period, count)
            cash_flows = []

            for item in response.get('cash_flow', []):
                cash_flow = CashFlow.from_api_response(item)
                cash_flows.append(cash_flow)

            if not cash_flows:
                click.echo(f"No cash flow data available for {symbol}")
                return

            # Sort by date (oldest first for trend analysis)
            cash_flows.sort(key=lambda s: s.fiscal_date)

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display analysis
    display_cash_flow_analysis(cash_flows)

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

        export_results = export_cash_flow_analysis(
            cash_flows, export_formats, export_output_dir)

        if export_results:
            click.echo("\nExported cash flow analysis to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


# Add shortcut at top level for easier access
@cli.group(name="cash-flow")
def cash_flow_shortcut():
    """Shortcut for 'stock cash-flow' commands."""
    pass


@cash_flow_shortcut.command(name="get")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=1,
              help="Number of periods to retrieve (default: 1, max: 20)")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed cash flow statement")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export cash flow to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_cash_flow_shortcut(symbol, period, count, detailed, export, output_dir, use_home_dir):
    """Get cash flow statement for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        get_cash_flow_command,
        symbol=symbol,
        period=period,
        count=count,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cash_flow_shortcut.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=4,
              help="Number of periods to compare (default: 4, max: 20)")
@click.option("--focus", "-f", type=click.Choice(['full', 'operating', 'investing', 'financing', 'summary']),
              default='full', help="Focus on specific section (default: full cash flow)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_cash_flows_shortcut(symbol, period, count, focus, export, output_dir, use_home_dir):
    """Compare cash flow statements across multiple periods."""
    ctx = click.get_current_context()
    ctx.invoke(
        compare_cash_flows_command,
        symbol=symbol,
        period=period,
        count=count,
        focus=focus,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@cash_flow_shortcut.command(name="analyze")
@click.argument("symbol", required=True)
@click.option("--period", "-p", type=click.Choice(['annual', 'quarter']), default='annual',
              help="Period type (annual or quarterly)")
@click.option("--count", "-c", type=int, default=5,
              help="Number of periods to analyze (default: 5, max: 20)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export analysis to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def analyze_cash_flow_shortcut(symbol, period, count, export, output_dir, use_home_dir):
    """Analyze cash flow trends and patterns over time."""
    ctx = click.get_current_context()
    ctx.invoke(
        analyze_cash_flow_command,
        symbol=symbol,
        period=period,
        count=count,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="executives")
def executives_group():
    """Commands for retrieving company executives and management information."""
    pass


@executives_group.command(name="list")
@click.argument("symbol", required=True)
@click.option("--detailed", "-d", is_flag=True, help="Show detailed executive information with biographies")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export executives data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_executives_command(symbol, detailed, export, output_dir, use_home_dir):
    """
    List the executives of a company.

    Retrieves information about the top management team of a company,
    including executive names, titles, and other available information.

    Examples:
        stockcli executives list AAPL
        stockcli executives list MSFT --detailed
    """
    from app.models.executives import ManagementTeam
    from app.utils.display import display_executives
    from app.utils.export import export_executives, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching executive information for {symbol}..."):
        try:
            response = client.get_executives(symbol)
            management_team = ManagementTeam.from_api_response(
                symbol, response)

            if not management_team.executives:
                click.echo(f"No executive data available for {symbol}")
                return

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display executives
    display_executives(management_team, detailed)

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

        export_results = export_executives(
            management_team, export_formats, export_output_dir)

        if export_results:
            click.echo("\nExported executives data to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


@executives_group.command(name="profile")
@click.argument("symbol", required=True)
@click.option("--name", help="Executive name to search for (partial match)")
@click.option("--position", help="Position/title to search for (CEO, CFO, etc.)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export executive profile to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def executive_profile_command(symbol, name, position, export, output_dir, use_home_dir):
    """
    Get detailed profile for a specific executive.

    Search for and display detailed information about a specific executive
    by name or position. If no exact match is found, the most relevant
    executive will be shown.

    Examples:
        stockcli executives profile AAPL --name "Tim Cook"
        stockcli executives profile MSFT --position "CEO"
    """
    from app.models.executives import ManagementTeam, Executive
    from app.utils.display import display_executive_profile
    from app.utils.export import export_executive_profile, get_default_export_dir, get_home_export_dir

    # Validate inputs
    if not name and not position:
        click.echo("Error: Either --name or --position must be specified")
        return

    with create_progress_spinner(f"Fetching executive information for {symbol}..."):
        try:
            response = client.get_executives(symbol)
            management_team = ManagementTeam.from_api_response(
                symbol, response)

            if not management_team.executives:
                click.echo(f"No executive data available for {symbol}")
                return

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Find the executive by name or position
    target_executive = None

    # If name is provided, search by name
    if name:
        name_lower = name.lower()
        # First try exact match
        for exec in management_team.executives:
            if exec.name.lower() == name_lower:
                target_executive = exec
                break

        # If no exact match, try partial match
        if not target_executive:
            for exec in management_team.executives:
                if name_lower in exec.name.lower():
                    target_executive = exec
                    break

    # If position is provided or no match found by name, search by position
    if (not target_executive) and position:
        position_lower = position.lower()

        # Common abbreviations for executive positions
        if position_lower == "ceo":
            position_lower = "chief executive"
        elif position_lower == "cfo":
            position_lower = "chief financial"
        elif position_lower == "coo":
            position_lower = "chief operating"
        elif position_lower == "cto":
            position_lower = "chief technology"

        # Search by position
        for exec in management_team.executives:
            if exec.title and position_lower in exec.title.lower():
                target_executive = exec
                break

    # If still no match, try to get CEO or first executive
    if not target_executive:
        if position and position.lower() == "ceo":
            target_executive = management_team.get_ceo()
        elif position and position.lower() == "cfo":
            target_executive = management_team.get_cfo()
        elif position and position.lower() == "coo":
            target_executive = management_team.get_coo()

    # If still no match, use first executive as fallback
    if not target_executive and management_team.executives:
        target_executive = management_team.executives[0]

    if not target_executive:
        click.echo(f"No executives found for {symbol}")
        return

    # Display the executive profile
    display_executive_profile(target_executive, management_team.name)

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

        export_results = export_executive_profile(
            target_executive,
            management_team.name,
            symbol,
            export_formats,
            export_output_dir
        )

        if export_results:
            click.echo("\nExported executive profile to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


@executives_group.command(name="compensation")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export compensation analysis to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def executive_compensation_command(symbol, export, output_dir, use_home_dir):
    """
    Analyze executive compensation for a company.

    Shows an analysis of executive compensation structure, including
    visualizations and statistics about the distribution of pay.

    Examples:
        stockcli executives compensation AAPL
        stockcli executives compensation MSFT --export json
    """
    from app.models.executives import ManagementTeam
    from app.utils.display import display_compensation_analysis
    from app.utils.export import export_compensation_analysis, get_default_export_dir, get_home_export_dir

    with create_progress_spinner(f"Fetching executive information for {symbol}..."):
        try:
            response = client.get_executives(symbol)
            management_team = ManagementTeam.from_api_response(
                symbol, response)

            if not management_team.executives:
                click.echo(f"No executive data available for {symbol}")
                return

        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return

    # Display compensation analysis
    display_compensation_analysis(management_team)

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

        export_results = export_compensation_analysis(
            management_team, export_formats, export_output_dir)

        if export_results:
            click.echo("\nExported compensation analysis to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


# Add shortcut at top level for easier access
@cli.group(name="executives")
def executives_shortcut():
    """Shortcut for 'stock executives' commands."""
    pass


@executives_shortcut.command(name="list")
@click.argument("symbol", required=True)
@click.option("--detailed", "-d", is_flag=True, help="Show detailed executive information with biographies")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export executives data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def list_executives_shortcut(symbol, detailed, export, output_dir, use_home_dir):
    """List the executives of a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        list_executives_command,
        symbol=symbol,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@executives_shortcut.command(name="profile")
@click.argument("symbol", required=True)
@click.option("--name", help="Executive name to search for (partial match)")
@click.option("--position", help="Position/title to search for (CEO, CFO, etc.)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export executive profile to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def executive_profile_shortcut(symbol, name, position, export, output_dir, use_home_dir):
    """Get detailed profile for a specific executive."""
    ctx = click.get_current_context()
    ctx.invoke(
        executive_profile_command,
        symbol=symbol,
        name=name,
        position=position,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@executives_shortcut.command(name="compensation")
@click.argument("symbol", required=True)
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export compensation analysis to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def executive_compensation_shortcut(symbol, export, output_dir, use_home_dir):
    """Analyze executive compensation for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        executive_compensation_command,
        symbol=symbol,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="market-cap")
def market_cap_group():
    """Commands for retrieving market capitalization data."""
    pass


@market_cap_group.command(name="history")
@click.argument("symbol", required=True)
@click.option("--interval", "-i", default="1day",
              help="Time interval between data points (1min to 1month, default: 1day)")
@click.option("--count", "-c", type=int, default=30,
              help="Number of data points to retrieve (default: 30, max: 5000)")
@click.option("--start-date", "-s", 
              help="Optional start date in format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
@click.option("--end-date", "-e", 
              help="Optional end date in format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
@click.option("--detailed", "-d", is_flag=True, help="Show more detailed data points")
@click.option("--chart", is_flag=True, help="Show a chart visualization of market cap trends")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export market cap history to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def market_cap_history_command(symbol, interval, count, start_date, end_date, detailed, 
                           chart, export, output_dir, use_home_dir):
    """
    Get market capitalization history for a company.
    
    Retrieves the market cap history for a given stock symbol over a specified period.
    
    Examples:
        stockcli market-cap history AAPL
        stockcli market-cap history MSFT --interval 1week --count 52 --chart
    """
    from app.models.market_cap import MarketCapHistory
    from app.utils.display import display_market_cap_history, display_market_cap_chart
    from app.utils.export import export_market_cap, get_default_export_dir, get_home_export_dir
    

    
    with create_progress_spinner(f"Fetching market cap history for {symbol}..."):
        try:
            response = client.get_market_cap(symbol, interval, count, start_date, end_date)
            market_cap_history = MarketCapHistory.from_api_response(response)
            
            if not market_cap_history.points:
                click.echo(f"No market cap data available for {symbol}")
                return
        
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display market cap history
    display_market_cap_history(market_cap_history, detailed)
    
    # Show chart if requested
    if chart:
        display_market_cap_chart(market_cap_history)
    
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
            
        export_results = export_market_cap(market_cap_history, export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported market cap history to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


@market_cap_group.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--daily-count", "-d", type=int, default=30,
              help="Number of daily data points (default: 30)")
@click.option("--monthly-count", "-m", type=int, default=24,
              help="Number of monthly data points (default: 24)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def market_cap_compare_command(symbol, daily_count, monthly_count, export, output_dir, use_home_dir):
    """
    Compare short-term and long-term market cap trends.
    
    Analyzes market capitalization data across different time intervals to provide
    insights on short-term and long-term trends.
    
    Examples:
        stockcli market-cap compare AAPL
        stockcli market-cap compare MSFT --daily-count 60 --monthly-count 36
    """
    from app.models.market_cap import MarketCapHistory
    from app.utils.display import display_market_cap_comparison
    from app.utils.export import export_market_cap_comparison, get_default_export_dir, get_home_export_dir
    

    
    with create_progress_spinner(f"Fetching market cap data for {symbol}..."):
        try:
            # Fetch daily data
            daily_response = client.get_market_cap(symbol, "1day", daily_count)
            daily_history = MarketCapHistory.from_api_response(daily_response)
            
            # Fetch monthly data
            monthly_response = client.get_market_cap(symbol, "1month", monthly_count)
            monthly_history = MarketCapHistory.from_api_response(monthly_response)
            
            if not daily_history.points or not monthly_history.points:
                click.echo(f"Insufficient market cap data available for {symbol}")
                return
        
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display comparison
    display_market_cap_comparison(symbol, daily_history, monthly_history)
    
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
            
        export_results = export_market_cap_comparison(
            symbol, 
            daily_history, 
            monthly_history, 
            export_formats, 
            export_output_dir
        )
        
        if export_results:
            click.echo("\nExported market cap comparison to:")
            for fmt, paths in export_results.items():
                if isinstance(paths, list):
                    click.echo(f"  {fmt.upper()}: Multiple files in {Path(paths[0]).parent}")
                else:
                    click.echo(f"  {fmt.upper()}: {paths}")


# Add shortcut at top level for easier access
@cli.group(name="market-cap")
def market_cap_shortcut():
    """Shortcut for 'stock market-cap' commands."""
    pass


@market_cap_shortcut.command(name="history")
@click.argument("symbol", required=True)
@click.option("--interval", "-i", default="1day",
              help="Time interval between data points (1min to 1month, default: 1day)")
@click.option("--count", "-c", type=int, default=30,
              help="Number of data points to retrieve (default: 30, max: 5000)")
@click.option("--start-date", "-s", 
              help="Optional start date in format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
@click.option("--end-date", "-e", 
              help="Optional end date in format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
@click.option("--detailed", "-d", is_flag=True, help="Show more detailed data points")
@click.option("--chart", is_flag=True, help="Show a chart visualization of market cap trends")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export market cap history to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def market_cap_history_shortcut(symbol, interval, count, start_date, end_date, detailed, 
                             chart, export, output_dir, use_home_dir):
    """Get market capitalization history for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        market_cap_history_command,
        symbol=symbol,
        interval=interval,
        count=count,
        start_date=start_date,
        end_date=end_date,
        detailed=detailed,
        chart=chart,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@market_cap_shortcut.command(name="compare")
@click.argument("symbol", required=True)
@click.option("--daily-count", "-d", type=int, default=30,
              help="Number of daily data points (default: 30)")
@click.option("--monthly-count", "-m", type=int, default=24,
              help="Number of monthly data points (default: 24)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def market_cap_compare_shortcut(symbol, daily_count, monthly_count, export, output_dir, use_home_dir):
    """Compare short-term and long-term market cap trends."""
    ctx = click.get_current_context()
    ctx.invoke(
        market_cap_compare_command,
        symbol=symbol,
        daily_count=daily_count,
        monthly_count=monthly_count,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@stock.group(name="analysts")
def analysts_group():
    """Commands for retrieving analyst estimates and recommendations."""
    pass


@analysts_group.command(name="estimates")
@click.argument("symbol", required=True)
@click.option("--focus", "-f", type=click.Choice(['eps', 'revenue', 'recommendations', 'price', 'all']),
              default='eps', help="Focus area (default: eps)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export analyst estimates to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_analyst_estimates_command(symbol, focus, export, output_dir, use_home_dir):
    """
    Get analyst estimates for a company symbol.
    
    Retrieves various analyst estimates including EPS forecasts,
    revenue estimates, price targets, and recommendation trends.
    
    Examples:
        stockcli analysts estimates AAPL
        stockcli analysts estimates MSFT --focus all
    """
    from app.models.analysts_estimates import AnalystEstimates
    from app.utils.display import display_analyst_estimates
    from app.utils.export import export_analyst_estimates, get_default_export_dir, get_home_export_dir
    
    
    with create_progress_spinner(f"Fetching analyst estimates for {symbol}..."):
        try:
            response = client.get_analyst_estimates(symbol)
            estimates = AnalystEstimates.from_api_response(response)
            
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display the estimates
    display_analyst_estimates(estimates, focus)
    
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
            
        export_results = export_analyst_estimates(estimates, export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported analyst estimates to:")
            for fmt, path in export_results.items():
                if isinstance(path, list):
                    click.echo(f"  {fmt.upper()}: Multiple files in {Path(path[0]).parent}")
                else:
                    click.echo(f"  {fmt.upper()}: {path}")


@analysts_group.command(name="eps-compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--period-type", "-p", type=click.Choice(['quarterly', 'annual']), default='annual',
              help="Period type to compare (default: annual)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_eps_estimates_command(symbols, period_type, export, output_dir, use_home_dir):
    """
    Compare EPS estimates across multiple companies.
    
    Retrieve and compare analyst EPS estimates for multiple symbols
    side-by-side to analyze expected performance.
    
    Examples:
        stockcli analysts eps-compare AAPL MSFT GOOGL
        stockcli analysts eps-compare AAPL MSFT --period-type quarterly
    """
    from app.models.analysts_estimates import AnalystEstimates
    from app.utils.display import display_eps_comparison
    from app.utils.export import export_eps_comparison, get_default_export_dir, get_home_export_dir
    
    
    # Clean up symbol list
    symbols = [symbol.upper() for symbol in symbols]
    
    # Fetch estimates for all symbols
    all_estimates = []
    
    with create_progress_spinner(f"Fetching analyst estimates for {len(symbols)} symbols..."):
        for symbol in symbols:
            try:
                response = client.get_analyst_estimates(symbol)
                estimates = AnalystEstimates.from_api_response(response)
                all_estimates.append(estimates)
                
            except TwelveDataAPIError as e:
                click.echo(f"Error fetching estimates for {symbol}: {e}")
                
    if not all_estimates:
        click.echo("No estimates data available for the provided symbols")
        return
    
    # Display the comparison
    display_eps_comparison(symbols, all_estimates, period_type)
    
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
            
        export_results = export_eps_comparison(symbols, all_estimates, period_type, 
                                              export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported EPS comparison to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


# Add shortcut commands at top level
@cli.group(name="analysts")
def analysts_shortcut():
    """Shortcut for 'stock analysts' commands."""
    pass


@analysts_shortcut.command(name="estimates")
@click.argument("symbol", required=True)
@click.option("--focus", "-f", type=click.Choice(['eps', 'revenue', 'recommendations', 'price', 'all']),
              default='eps', help="Focus area (default: eps)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export analyst estimates to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_analyst_estimates_shortcut(symbol, focus, export, output_dir, use_home_dir):
    """Get analyst estimates for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        get_analyst_estimates_command,
        symbol=symbol,
        focus=focus,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@analysts_shortcut.command(name="eps-compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--period-type", "-p", type=click.Choice(['quarterly', 'annual']), default='annual',
              help="Period type to compare (default: annual)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_eps_estimates_shortcut(symbols, period_type, export, output_dir, use_home_dir):
    """Compare EPS estimates across multiple companies."""
    ctx = click.get_current_context()
    ctx.invoke(
        compare_eps_estimates_command,
        symbols=symbols,
        period_type=period_type,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )

@analysts_group.command(name="revenue")
@click.argument("symbol", required=True)
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information including historical surprises")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export revenue estimates to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_revenue_estimates_command(symbol, detailed, export, output_dir, use_home_dir):
    """
    Get revenue estimates for a company symbol.
    
    Retrieves analyst forecasts for a company's quarterly and annual 
    sales (total revenue), both historical and future projections.
    
    Examples:
        stockcli analysts revenue AAPL
        stockcli analysts revenue MSFT --detailed
    """
    from app.models.analysts_estimates import AnalystEstimates
    from app.utils.display import display_revenue_estimates, display_revenue_growth_visualization
    from app.utils.export import export_revenue_estimates, get_default_export_dir, get_home_export_dir
    
    
    with create_progress_spinner(f"Fetching revenue estimates for {symbol}..."):
        try:
            response = client.get_analyst_estimates(symbol)
            estimates = AnalystEstimates.from_api_response(response)
            
            # Verify we have revenue estimates
            if not estimates.quarterly_revenue_estimates and not estimates.annual_revenue_estimates:
                click.echo(f"No revenue forecast data available for {symbol}")
                return
            
        except TwelveDataAPIError as e:
            click.echo(f"Error: {e}")
            return
    
    # Display the estimates
    display_revenue_estimates(estimates, detailed)
    
    # Also show the growth visualization
    if estimates.annual_revenue_estimates:
        display_revenue_growth_visualization(estimates)
    
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
            
        export_results = export_revenue_estimates(estimates, export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported revenue estimates to:")
            for fmt, paths in export_results.items():
                if fmt == 'json':
                    click.echo(f"  JSON: {paths}")
                elif fmt == 'csv' and isinstance(paths, list):
                    for i, path in enumerate(paths):
                        if i == 0:
                            click.echo(f"  CSV files:")
                        click.echo(f"    - {path}")


@analysts_group.command(name="revenue-compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--period-type", "-p", type=click.Choice(['quarterly', 'annual']), default='annual',
              help="Period type to compare (default: annual)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_revenue_estimates_command(symbols, period_type, export, output_dir, use_home_dir):
    """
    Compare revenue estimates across multiple companies.
    
    Retrieve and compare analyst revenue forecasts for multiple symbols
    side-by-side to analyze expected sales performance.
    
    Examples:
        stockcli analysts revenue-compare AAPL MSFT GOOGL
        stockcli analysts revenue-compare AAPL MSFT --period-type quarterly
    """
    from app.models.analysts_estimates import AnalystEstimates
    from app.utils.display import display_revenue_comparison
    from app.utils.export import export_revenue_comparison, get_default_export_dir, get_home_export_dir
    
    
    # Clean up symbol list
    symbols = [symbol.upper() for symbol in symbols]
    
    # Fetch estimates for all symbols
    all_estimates = []
    
    with create_progress_spinner(f"Fetching revenue estimates for {len(symbols)} symbols..."):
        for symbol in symbols:
            try:
                response = client.get_analyst_estimates(symbol)
                estimates = AnalystEstimates.from_api_response(response)
                
                # Verify we have revenue estimates
                if ((period_type == 'quarterly' and estimates.quarterly_revenue_estimates) or 
                    (period_type == 'annual' and estimates.annual_revenue_estimates)):
                    all_estimates.append(estimates)
                else:
                    click.echo(f"No {period_type} revenue estimates available for {symbol}")
                
            except TwelveDataAPIError as e:
                click.echo(f"Error fetching estimates for {symbol}: {e}")
                
    if not all_estimates:
        click.echo("No revenue estimates data available for the provided symbols")
        return
    
    # Display the comparison
    display_revenue_comparison(symbols, all_estimates, period_type)
    
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
            
        export_results = export_revenue_comparison(symbols, all_estimates, period_type, 
                                                 export_formats, export_output_dir)
        
        if export_results:
            click.echo("\nExported revenue comparison to:")
            for fmt, path in export_results.items():
                click.echo(f"  {fmt.upper()}: {path}")


# Add shortcut commands at top level
@analysts_shortcut.command(name="revenue")
@click.argument("symbol", required=True)
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information including historical surprises")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export revenue estimates to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def get_revenue_estimates_shortcut(symbol, detailed, export, output_dir, use_home_dir):
    """Get revenue estimates for a company."""
    ctx = click.get_current_context()
    ctx.invoke(
        get_revenue_estimates_command,
        symbol=symbol,
        detailed=detailed,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )


@analysts_shortcut.command(name="revenue-compare")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--period-type", "-p", type=click.Choice(['quarterly', 'annual']), default='annual',
              help="Period type to compare (default: annual)")
@click.option("--export", type=click.Choice(['json', 'csv', 'both'], case_sensitive=False),
              help="Export comparison data to file format")
@click.option("--output-dir", type=click.Path(file_okay=False),
              help="Directory to save exported files")
@click.option("--use-home-dir", is_flag=True,
              help="Save exports to user's home directory instead of project directory")
def compare_revenue_estimates_shortcut(symbols, period_type, export, output_dir, use_home_dir):
    """Compare revenue estimates across multiple companies."""
    ctx = click.get_current_context()
    ctx.invoke(
        compare_revenue_estimates_command,
        symbols=symbols,
        period_type=period_type,
        export=export,
        output_dir=output_dir,
        use_home_dir=use_home_dir
    )

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
