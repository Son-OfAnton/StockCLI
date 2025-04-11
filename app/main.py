#!/usr/bin/env python3
"""
Stock CLI - Main entry point for the application.
This file will setup and run the CLI commands.
"""

import sys
import logging
from pathlib import Path
import click
from app.cli.commands import stock, fetch_and_display_quotes, refresh_quotes, export_last as export_last_quotes
from app.utils.export import get_default_export_dir, get_home_export_dir

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
