"""
TwelveData API client for stock data retrieval.
"""


class TwelveDataClient:
    """Client for interacting with the TwelveData API."""
    
    def __init__(self, api_key):
        """Initialize the API client with credentials."""
        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"
    
    def get_quote(self, symbol):
        """Fetch current quote for a stock symbol."""
        pass
    
    def get_time_series(self, symbol, interval, start_date=None, end_date=None):
        """Fetch historical time series data."""
        pass
    
    def get_technical_indicator(self, symbol, indicator, params=None):
        """Fetch technical indicator values."""
        pass