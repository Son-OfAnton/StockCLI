"""
Application configuration settings.
"""

import os
from pathlib import Path
import configparser

# Default configuration
DEFAULT_CONFIG = {
    'api': {
        'key': '',
        'base_url': 'https://api.twelvedata.com',
        'timeout': 30,
    },
    'display': {
        'date_format': '%Y-%m-%d',
        'decimal_places': 2,
    },
    'cache': {
        'enabled': True,
        'ttl': 3600,  # Time to live in seconds
        'directory': '~/.stock_cli/cache',
    }
}

def get_api_key():
    """Get the API key from environment or config file."""
    # First check environment variable
    api_key = os.environ.get('TWELVEDATA_API_KEY')
    if api_key:
        return api_key
    
    # Then check config file
    config_file = Path.home() / '.stock_cli' / 'config.ini'
    if config_file.exists():
        config = configparser.ConfigParser()
        config.read(config_file)
        return config.get('api', 'key', fallback=None)
    
    return None

# Application constants
APP_NAME = "Stock CLI"
APP_VERSION = "0.1.0"
DEFAULT_CACHE_DIR = Path.home() / '.stock_cli' / 'cache'