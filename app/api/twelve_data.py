"""
TwelveData API client for stock data retrieval.
"""

import os
import requests
import logging
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


class TwelveDataAPIError(Exception):
    """Exception raised for TwelveData API errors."""
    pass


class TwelveDataClient:
    """Client for interacting with the TwelveData API."""

    def __init__(self):
        """Initialize the API client with credentials."""
        try:
            self.base_url = os.environ["TWELVEDATA_BASE_URL"]
            self.api_key = os.environ["TWELVEDATA_API_KEY"]
        except KeyError as e:
            missing_var = e.args[0]
            logger.error(f"{missing_var} environment variable not set.")
            raise ValueError(f"{missing_var} environment variable not set.")
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
            logger.debug(
                f"Making API request to: {endpoint} with parameters: {params}")
            response = self.session.get(
                url, params=params, timeout=self.timeout)

            # Log rate limit information if available
            if 'X-RateLimit-Limit' in response.headers:
                logger.debug(f"Rate limit: {response.headers.get('X-RateLimit-Limit')}, "
                             f"Remaining: {response.headers.get('X-RateLimit-Remaining')}")

            # Check for HTTP errors
            response.raise_for_status()

            data = response.json()

            # Check for API errors in the response body
            if isinstance(data, dict) and data.get('status') == 'error':
                raise TwelveDataAPIError(
                    data.get('message', 'Unknown API error'))

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
                            raise TwelveDataAPIError(
                                error_data['message']) from e
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

    def get_symbols(self,
                    exchange: Optional[str] = None,
                    type: Optional[str] = None,
                    country: Optional[str] = None,
                    symbol: Optional[str] = None,
                    show_plan: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch available symbols from the TwelveData API.

        Args:
            exchange: Filter by exchange (e.g., 'NASDAQ')
            type: Filter by type (e.g., 'stock', 'etf', 'index')
            country: Filter by country (e.g., 'United States')
            symbol: Filter by symbol (partial match)
            show_plan: Whether to include plan information in the response

        Returns:
            List of available symbols with their details
        """
        endpoint = "/stocks"
        params = {}

        if exchange:
            params['exchange'] = exchange
        if type:
            params['type'] = type
        if country:
            params['country'] = country
        if symbol:
            params['symbol'] = symbol
        if show_plan:
            params['show_plan'] = 'true'

        logger.debug(f"Fetching available symbols with filters: {params}")
        result = self._make_request(endpoint, params)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(f"Unexpected response format for symbols: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for symbols endpoint")

        return result['data']

    def get_exchanges(self) -> List[Dict[str, Any]]:
        """
        Fetch available exchanges from the TwelveData API.

        Returns:
            List of available exchanges with their details
        """
        endpoint = "/exchanges"
        logger.debug("Fetching available exchanges")
        result = self._make_request(endpoint)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(f"Unexpected response format for exchanges: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for exchanges endpoint")

        return result['data']

    def get_symbol_types(self) -> List[str]:
        """
        Get available symbol types from the TwelveData API.

        Returns:
            List of available symbol types (e.g., stock, etf, index)
        """
        # This is a simple list that doesn't change often, so we hardcode it
        # If needed, this could be fetched from the API in the future
        return [
            "stock", "etf", "index", "reit", "mutual_fund", "forex", "crypto"
        ]

    def get_forex_pairs(self,
                        currency_base: Optional[str] = None,
                        currency_quote: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available forex pairs from the TwelveData API.

        Args:
            currency_base: Filter by base currency (e.g., 'USD')
            currency_quote: Filter by quote currency (e.g., 'EUR')

        Returns:
            List of available forex pairs with their details
        """
        endpoint = "/forex_pairs"
        params = {}

        if currency_base:
            params['currency_base'] = currency_base
        if currency_quote:
            params['currency_quote'] = currency_quote

        logger.debug(f"Fetching forex pairs with filters: {params}")
        result = self._make_request(endpoint, params)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(
                f"Unexpected response format for forex pairs: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for forex_pairs endpoint")

        return result['data']

    def get_cryptocurrencies(self,
                             symbol: Optional[str] = None,
                             currency_base: Optional[str] = None,
                             currency_quote: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available cryptocurrencies from the TwelveData API.

        Args:
            symbol: Filter by symbol (partial match)
            currency_base: Filter by base currency (e.g., 'BTC')
            currency_quote: Filter by quote currency (e.g., 'USD')

        Returns:
            List of available cryptocurrencies with their details
        """
        endpoint = "/cryptocurrencies"
        params = {}

        if symbol:
            params['symbol'] = symbol
        if currency_base:
            params['currency_base'] = currency_base
        if currency_quote:
            params['currency_quote'] = currency_quote

        logger.debug(f"Fetching cryptocurrencies with filters: {params}")
        result = self._make_request(endpoint, params)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(
                f"Unexpected response format for cryptocurrencies: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for cryptocurrencies endpoint")

        return result['data']

    def get_currencies(self) -> List[Dict[str, Any]]:
        """
        Fetch available currencies from the TwelveData API.

        Returns:
            List of available currencies with their details
        """
        endpoint = "/currencies"
        logger.debug("Fetching available currencies")
        result = self._make_request(endpoint)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(
                f"Unexpected response format for currencies: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for currencies endpoint")

        return result['data']


client = TwelveDataClient()
