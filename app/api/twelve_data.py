"""
TwelveData API client for stock data retrieval.
"""

import os
import requests
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TwelveDataClient:
    """Client for interacting with the TwelveData API."""
    
    def __init__(self, api_key):
        """Initialize the API client with credentials."""
        self.api_key = api_key
        self.base_url = os.environ.get("TWELVEDATA_BASE_URL")
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the TwelveData API."""
        if params is None:
            params = {}
        
        # Always include the API key
        params['apikey'] = self.api_key
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request error: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch current quote for a stock symbol."""
        endpoint = "/quote"
        params = {
            'symbol': symbol
        }
        return self._make_request(endpoint, params)
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch current quotes for multiple stock symbols."""
        endpoint = "/quote"
        params = {
            'symbol': ','.join(symbols)
        }
        return self._make_request(endpoint, params)
    
    def get_time_series(self, symbol: str, interval: str, start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """Fetch historical time series data."""
        endpoint = "/time_series"
        params = {
            'symbol': symbol,
            'interval': interval,
        }
        
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
            
        return self._make_request(endpoint, params)
    
    def get_technical_indicator(self, symbol: str, indicator: str, 
                               interval: str = "1day", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch technical indicator values."""
        endpoint = f"/{indicator}"
        
        request_params = {
            'symbol': symbol,
            'interval': interval
        }
        
        if params:
            request_params.update(params)
            
        return self._make_request(endpoint, request_params)