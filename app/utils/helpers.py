"""
Utility functions for the stock CLI application.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Date and time utilities
def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
    """Parse a date string into a datetime object."""
    return datetime.strptime(date_str, fmt)

def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format a datetime object into a string."""
    return dt.strftime(fmt)

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