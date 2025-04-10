"""
Utility functions for the stock CLI application.
"""

import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Console setup for rich output
console = Console()

# Date and time utilities
def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
    """Parse a date string into a datetime object."""
    return datetime.strptime(date_str, fmt)

def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format a datetime object into a string."""
    return dt.strftime(fmt)

def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object into a datetime string."""
    return dt.strftime(fmt)

def get_local_time(dt: datetime) -> datetime:
    """Convert UTC datetime to local time."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()

# Formatting utilities
def format_price(price: float, decimal_places: int = 2) -> str:
    """Format a price with the specified number of decimal places."""
    return f"{price:.{decimal_places}f}"

def format_change(change: float, percentage: float, decimal_places: int = 2) -> str:
    """Format price change and percentage."""
    change_str = format_price(change, decimal_places)
    percentage_str = f"{percentage:.{decimal_places}f}%"
    
    if change >= 0:
        return f"+{change_str} (+{percentage_str})"
    else:
        return f"{change_str} ({percentage_str})"

def get_color_for_change(change: float) -> str:
    """Get color based on price change."""
    if change > 0:
        return "green"
    elif change < 0:
        return "red"
    else:
        return "white"

# Rich display functions
def display_quotes_table(quotes: List[Any], detailed: bool = False) -> None:
    """Display stock quotes in a rich table."""
    table = Table(title="Stock Quotes")
    
    # Add columns
    table.add_column("Symbol")
    table.add_column("Price")
    table.add_column("Change")
    table.add_column("Time")
    
    if detailed:
        table.add_column("Open")
        table.add_column("High")
        table.add_column("Low")
        table.add_column("Volume")
    
    # Add rows
    for quote in quotes:
        change_text = Text(format_change(quote.change, quote.change_percent))
        change_text.stylize(get_color_for_change(quote.change))
        
        local_time = get_local_time(quote.timestamp)
        time_str = format_datetime(local_time, "%H:%M:%S")
        
        row = [
            quote.symbol,
            format_price(quote.price),
            change_text,
            time_str
        ]
        
        if detailed:
            row.extend([
                format_price(quote.open_price) if quote.open_price else "N/A",
                format_price(quote.high_price) if quote.high_price else "N/A",
                format_price(quote.low_price) if quote.low_price else "N/A",
                f"{quote.volume:,}" if quote.volume else "N/A"
            ])
            
        table.add_row(*row)
    
    console.print(table)

def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

# Cache utilities
def get_cache_path(key: str, cache_dir: Optional[Path] = None) -> Path:
    """Get the path for a cached item."""
    if cache_dir is None:
        cache_dir = Path.home() / '.stock_cli' / 'cache'
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"

def save_to_cache(key: str, data: Dict[str, Any], cache_dir: Optional[Path] = None) -> None:
    """Save data to cache."""
    cache_path = get_cache_path(key, cache_dir)
    with open(cache_path, 'w') as f:
        json.dump({
            'data': data,
            'timestamp': datetime.now().timestamp()
        }, f)

def load_from_cache(key: str, ttl: int = 3600, cache_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load data from cache if it exists and is not expired."""
    cache_path = get_cache_path(key, cache_dir)
    
    if not cache_path.exists():
        return None
    
    with open(cache_path, 'r') as f:
        cached = json.load(f)
    
    cache_time = cached.get('timestamp', 0)
    if (datetime.now().timestamp() - cache_time) > ttl:
        return None
    
    return cached.get('data')