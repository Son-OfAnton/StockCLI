"""
Application configuration settings.
"""

import os
from pathlib import Path
import configparser
import logging

# Configure logging
logger = logging.getLogger(__name__)

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

def get_config_file_path():
    """Get the path to the config file."""
    config_dir = Path.home() / '.stock_cli'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.ini'

def create_default_config():
    """Create a default config file if it doesn't exist."""
    config_file = get_config_file_path()
    
    if config_file.exists():
        return
    
    config = configparser.ConfigParser()
    
    for section, options in DEFAULT_CONFIG.items():
        config[section] = {k: str(v) for k, v in options.items()}
    
    with open(config_file, 'w') as f:
        config.write(f)
    
    logger.info(f"Created default config at {config_file}")
    print(f"Created default config at {config_file}")
    print(f"Please set your TwelveData API key in this file or use the TWELVEDATA_API_KEY environment variable.")

def get_api_key():
    """Get the API key from environment or config file."""
    # First check environment variable
    api_key = os.environ.get('TWELVEDATA_API_KEY')
    if api_key:
        return api_key
    
    # Then check config file
    config_file = get_config_file_path()
    
    # Create default config if it doesn't exist
    if not config_file.exists():
        create_default_config()
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    try:
        return config.get('api', 'key')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.warning("No API key found in config file")
        return None

# Application constants
APP_NAME = "Stock CLI"
APP_VERSION = "0.1.0"
DEFAULT_CACHE_DIR = Path.home() / '.stock_cli' / 'cache'