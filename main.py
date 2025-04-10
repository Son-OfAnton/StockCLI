#!/usr/bin/env python3
"""
Stock CLI - Main entry point for the application.
This file will setup and run the CLI commands.
"""

import click
from app.cli import commands

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Stock CLI - A command-line tool for fetching and analyzing stock data."""
    pass

# Register command groups
cli.add_command(commands.stock)

if __name__ == "__main__":
    cli()