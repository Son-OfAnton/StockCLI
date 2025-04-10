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
        logger.debug(f"Using default project export directory: {export_output_dir}")
    
    if refresh:
        refresh_quotes(symbols, interval, detailed, debug, export_formats, export_output_dir)
    else:
        quotes = fetch_and_display_quotes(symbols, detailed, debug)
        
        # Export if requested
        if export and quotes:
            from app.utils.export import export_quotes
            export_results = export_quotes(quotes, export_formats, export_output_dir)
            
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
    export_last_quotes(format, output_dir, use_home_dir)

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