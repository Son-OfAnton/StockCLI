"""
TwelveData API client for stock data retrieval.
"""

import requests
import logging
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class TwelveDataAPIError(Exception):
    """Exception raised for TwelveData API errors."""
    pass

class TwelveDataClient:
    """Client for interacting with the TwelveData API."""
    
    def __init__(self, api_key):
        """Initialize the API client with credentials."""
        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"
        self.session = requests.Session()
        self.timeout = 10  # Default timeout in seconds
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the TwelveData API."""
        if params is None:
            params = {}
        
        # Always include the API key
        params['apikey'] = self.api_key
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            logger.debug(f"Making API request to: {endpoint} with parameters: {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            # Log rate limit information if available
            if 'X-RateLimit-Limit' in response.headers:
                logger.debug(f"Rate limit: {response.headers.get('X-RateLimit-Limit')}, "
                           f"Remaining: {response.headers.get('X-RateLimit-Remaining')}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors in the response body
            if isinstance(data, dict) and data.get('status') == 'error':
                raise TwelveDataAPIError(data.get('message', 'Unknown API error'))
                
            return data
        except requests.RequestException as e:
            logger.error(f"API request error: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status code: {e.response.status_code}")
                if hasattr(e.response, 'text'):
                    logger.error(f"Response content: {e.response.text}")
                    
                    # Try to parse error from response
                    try:
                        error_data = e.response.json()
                        if 'message' in error_data:
                            raise TwelveDataAPIError(error_data['message']) from e
                    except (ValueError, KeyError):
                        pass
            
            raise TwelveDataAPIError(f"API request failed: {str(e)}") from e
        except ValueError as e:
            logger.error(f"Invalid JSON in API response: {e}")
            raise TwelveDataAPIError("Invalid response format from API") from e
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch current quote for a stock symbol."""
        endpoint = "/quote"
        params = {
            'symbol': symbol
        }
        logger.debug(f"Fetching quote for {symbol}")
        return self._make_request(endpoint, params)
    
    def get_quotes(self, symbols: List[str]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Fetch current quotes for multiple stock symbols."""
        if not symbols:
            logger.error("No symbols provided for quotes")
            raise ValueError("At least one symbol must be provided")
            
        endpoint = "/quote"
        params = {
            'symbol': ','.join(symbols)
        }
        
        logger.debug(f"Fetching quotes for {symbols}")
        response = self._make_request(endpoint, params)
        
        # If only one symbol was requested, the API returns a single quote object
        # If multiple symbols were requested, the API returns a list of quote objects
        # Make sure we always return a list for consistent processing
        if len(symbols) == 1 and isinstance(response, dict) and 'symbol' in response:
            # Single quote response
            return [response]
        
        return response
    
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