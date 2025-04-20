"""
TwelveData API client for stock data retrieval.
"""

from datetime import datetime
import os
import requests
import logging
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin
from dotenv import load_dotenv

from app.models.commodity import CommodityPair


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

    def get_cryptocurrencies(self,
                             symbol: Optional[str] = None,
                             exchange: Optional[str] = None,
                             currency_base: Optional[str] = None,
                             currency_quote: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available cryptocurrency pairs from the TwelveData API.

        Args:
            symbol: Filter by symbol (e.g., 'BTC/USD')
            exchange: Filter by exchange (e.g., 'Binance')
            currency_base: Filter by base currency (e.g., 'BTC')
            currency_quote: Filter by quote currency (e.g., 'USD')

        Returns:
            List of available cryptocurrency pairs with their details
        """
        endpoint = "/cryptocurrencies"
        params = {}

        if symbol:
            params['symbol'] = symbol
        if exchange:
            params['exchange'] = exchange
        if currency_base:
            params['currency_base'] = currency_base
        if currency_quote:
            params['currency_quote'] = currency_quote

        logger.debug(
            f"Fetching available cryptocurrencies with filters: {params}")
        result = self._make_request(endpoint, params)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(
                f"Unexpected response format for cryptocurrencies: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for cryptocurrencies endpoint")

        return result['data']

    def get_crypto_exchanges(self) -> List[str]:
        """
        Fetch available cryptocurrency exchanges from the TwelveData API.

        Returns:
            List of available cryptocurrency exchanges
        """
        endpoint = "/cryptocurrency_exchanges"
        logger.debug("Fetching available cryptocurrency exchanges")
        result = self._make_request(endpoint)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(
                f"Unexpected response format for crypto exchanges: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for crypto exchanges endpoint")

        return result['data']

    def get_funds(self,
                  fund_type: Optional[str] = None,
                  exchange: Optional[str] = None,
                  country: Optional[str] = None,
                  symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available funds (ETFs and mutual funds) from the TwelveData API.

        Args:
            fund_type: Filter by fund type ('etf' or 'mutual_fund')
            exchange: Filter by exchange (e.g., 'NASDAQ')
            country: Filter by country (e.g., 'United States')
            symbol: Filter by symbol (partial match)

        Returns:
            List of available funds with their details
        """
        # Reuse the existing symbols endpoint but filter for fund types
        types = []
        if fund_type:
            if fund_type.lower() == 'etf':
                types.append('etf')
            elif fund_type.lower() == 'mutual_fund' or fund_type.lower() == 'mutual':
                types.append('mutual_fund')
        else:
            # Default to both if not specified
            types = ['etf', 'mutual_fund']

        all_funds = []

        for fund_type in types:
            logger.debug(f"Fetching {fund_type} data...")
            try:
                params = {'type': fund_type}

                if exchange:
                    params['exchange'] = exchange
                if country:
                    params['country'] = country
                if symbol:
                    params['symbol'] = symbol

                result = self._make_request("/stocks", params)

                # Check if data is in the expected format
                if not isinstance(result, dict) or 'data' not in result:
                    logger.error(
                        f"Unexpected response format for funds: {result}")
                    raise TwelveDataAPIError(
                        "Unexpected response format for funds endpoint")

                all_funds.extend(result['data'])
            except TwelveDataAPIError as e:
                logger.warning(f"Error fetching {fund_type}: {e}")

        return all_funds

    def get_etfs(self,
                 exchange: Optional[str] = None,
                 country: Optional[str] = None,
                 symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available ETFs from the TwelveData API.

        Args:
            exchange: Filter by exchange
            country: Filter by country
            symbol: Filter by symbol

        Returns:
            List of available ETFs
        """
        return self.get_funds('etf', exchange, country, symbol)

    def get_mutual_funds(self,
                         exchange: Optional[str] = None,
                         country: Optional[str] = None,
                         symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available mutual funds from the TwelveData API.

        Args:
            exchange: Filter by exchange
            country: Filter by country
            symbol: Filter by symbol

        Returns:
            List of available mutual funds
        """
        return self.get_funds('mutual_fund', exchange, country, symbol)

    def get_bonds(self,
                  bond_type: Optional[str] = None,
                  exchange: Optional[str] = None,
                  country: Optional[str] = None,
                  symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available bonds from the TwelveData API.

        Args:
            bond_type: Filter by bond type (e.g., 'government', 'corporate', 'municipal')
            exchange: Filter by exchange (e.g., 'NYSE')
            country: Filter by country (e.g., 'United States')
            symbol: Filter by symbol (partial match)

        Returns:
            List of available bonds with their details
        """
        endpoint = "/bonds"  # Correct endpoint for bonds
        params = {}

        if bond_type:
            params['type'] = bond_type
        if exchange:
            params['exchange'] = exchange
        if country:
            params['country'] = country
        if symbol:
            params['symbol'] = symbol

        logger.debug(f"Fetching available bonds with filters: {params}")

        try:
            result = self._make_request(endpoint, params)

            # Check if data is in the expected format
            if not isinstance(result, dict) or 'data' not in result:
                logger.error(f"Unexpected response format for bonds: {result}")
                raise TwelveDataAPIError(
                    "Unexpected response format for bonds endpoint")

            return result['data']
        except TwelveDataAPIError as e:
            logger.error(f"Error fetching bonds: {e}")
            raise

    def get_bond_types(self) -> List[str]:
        """
        Get available bond types.

        Returns:
            List of available bond types (e.g., government, corporate, municipal)
        """
        # This is a simple list that doesn't change often, so we hardcode it
        # In a real implementation, this might come from the API
        return [
            "government",
            "corporate",
            "municipal",
            "treasury",
            "agency",
            "zero_coupon",
            "convertible",
            "high_yield"
        ]

    def get_government_bonds(self,
                             exchange: Optional[str] = None,
                             country: Optional[str] = None,
                             symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available government bonds from the TwelveData API.

        Args:
            exchange: Filter by exchange
            country: Filter by country
            symbol: Filter by symbol

        Returns:
            List of available government bonds
        """
        return self.get_bonds('government', exchange, country, symbol)

    def get_corporate_bonds(self,
                            exchange: Optional[str] = None,
                            country: Optional[str] = None,
                            symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available corporate bonds from the TwelveData API.

        Args:
            exchange: Filter by exchange
            country: Filter by country
            symbol: Filter by symbol

        Returns:
            List of available corporate bonds
        """
        return self.get_bonds('corporate', exchange, country, symbol)

    def get_etfs(self,
                 asset_class: Optional[str] = None,
                 exchange: Optional[str] = None,
                 country: Optional[str] = None,
                 symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available ETFs from the TwelveData API.

        Args:
            asset_class: Filter by asset class (e.g., 'equity', 'fixed_income')
            exchange: Filter by exchange (e.g., 'NYSE')
            country: Filter by country (e.g., 'United States')
            symbol: Filter by symbol (partial match)

        Returns:
            List of available ETFs with their details
        """
        endpoint = "/etfs"  # Direct ETFs endpoint
        params = {}

        if asset_class:
            params['asset_class'] = asset_class
        if exchange:
            params['exchange'] = exchange
        if country:
            params['country'] = country
        if symbol:
            params['symbol'] = symbol

        logger.debug(f"Fetching available ETFs with filters: {params}")

        try:
            result = self._make_request(endpoint, params)

            # Check if data is in the expected format
            if not isinstance(result, dict) or 'data' not in result:
                logger.error(f"Unexpected response format for ETFs: {result}")
                raise TwelveDataAPIError(
                    "Unexpected response format for ETFs endpoint")

            return result['data']
        except TwelveDataAPIError as e:
            # If the ETFs endpoint is not available, fall back to the stocks endpoint with ETF type
            logger.warning(
                f"ETF-specific endpoint failed: {e}. Falling back to stocks endpoint.")
            return self._get_etfs_via_stocks_endpoint(asset_class, exchange, country, symbol)

    def _get_etfs_via_stocks_endpoint(self,
                                      asset_class: Optional[str] = None,
                                      exchange: Optional[str] = None,
                                      country: Optional[str] = None,
                                      symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Alternative method to fetch ETFs via the stocks endpoint.
        Used as a fallback if the dedicated ETFs endpoint is not available.
        """
        endpoint = "/stocks"
        params = {"type": "etf"}

        if exchange:
            params['exchange'] = exchange
        if country:
            params['country'] = country
        if symbol:
            params['symbol'] = symbol
        # Asset class would be handled in post-processing filtering

        logger.debug(
            f"Fetching ETFs via stocks endpoint with filters: {params}")
        result = self._make_request(endpoint, params)

        # Check if data is in the expected format
        if not isinstance(result, dict) or 'data' not in result:
            logger.error(
                f"Unexpected response format for stocks endpoint: {result}")
            raise TwelveDataAPIError(
                "Unexpected response format for stocks endpoint")

        # Filter for specific asset class if requested
        etfs = result['data']
        if asset_class:
            etfs = [etf for etf in etfs if etf.get(
                'asset_class') == asset_class]

        return etfs

    def get_etf_asset_classes(self) -> List[str]:
        """
        Get available ETF asset classes.

        Returns:
            List of available ETF asset classes (e.g., equity, fixed_income)
        """
        # This is a simple list that doesn't change often, so we hardcode it
        # In a real implementation, this might come from the API
        return [
            "equity",
            "fixed_income",
            "commodity",
            "currency",
            "alternative",
            "specialty",
            "allocation",
            "sector"
        ]

    def get_equity_etfs(self,
                        exchange: Optional[str] = None,
                        country: Optional[str] = None,
                        symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available equity ETFs from the TwelveData API.

        Args:
            exchange: Filter by exchange
            country: Filter by country
            symbol: Filter by symbol

        Returns:
            List of available equity ETFs
        """
        return self.get_etfs('equity', exchange, country, symbol)

    def get_fixed_income_etfs(self,
                              exchange: Optional[str] = None,
                              country: Optional[str] = None,
                              symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available fixed income ETFs from the TwelveData API.

        Args:
            exchange: Filter by exchange
            country: Filter by country
            symbol: Filter by symbol

        Returns:
            List of available fixed income ETFs
        """
        return self.get_etfs('fixed_income', exchange, country, symbol)

    def get_commodity_pairs(self,
                            commodity_group: Optional[str] = None,
                            exchange: Optional[str] = None,
                            symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available commodity pairs from the TwelveData API.

        Args:
            commodity_group: Filter by commodity group (e.g., 'precious_metals', 'energy')
            exchange: Filter by exchange
            symbol: Filter by symbol (partial match)

        Returns:
            List of available commodity pairs with their details
        """
        endpoint = "/commodities"  # Direct commodities endpoint
        params = {}

        if exchange:
            params['exchange'] = exchange
        if symbol:
            params['symbol'] = symbol

        logger.debug(
            f"Fetching available commodity pairs with filters: {params}")

        try:
            result = self._make_request(endpoint, params)

            # Check if data is in the expected format
            if not isinstance(result, dict) or 'data' not in result:
                logger.error(
                    f"Unexpected response format for commodities: {result}")
                raise TwelveDataAPIError(
                    "Unexpected response format for commodities endpoint")

            commodities_data = result['data']

            # Filter by commodity group if requested
            if commodity_group:
                # Since the API might not have a direct commodity_group filter,
                # we'll filter the results in the client
                filtered_data = []
                for item in commodities_data:
                    # Create a CommodityPair to determine its group
                    pair = CommodityPair.from_api_response(item)
                    if pair.commodity_group == commodity_group:
                        filtered_data.append(item)
                return filtered_data

            return commodities_data
        except TwelveDataAPIError as e:
            # If the commodities endpoint is not available, fall back to a more general approach
            logger.warning(
                f"Commodity-specific endpoint failed: {e}. Falling back to alternative method.")
            return self._get_commodity_pairs_via_alternative(commodity_group, exchange, symbol)

    def _get_commodity_pairs_via_alternative(self,
                                             commodity_group: Optional[str] = None,
                                             exchange: Optional[str] = None,
                                             symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Alternative method to fetch commodity pairs if the dedicated endpoint is not available.
        Uses the symbol/price endpoint with common commodity symbols.
        """
        # Common commodity symbols
        commodity_symbols = {
            "precious_metals": ["XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD", "GOLD/USD", "SILVER/USD"],
            "energy": ["CL/USD", "BRENT/USD", "WTI/USD", "NG/USD", "OIL/USD"],
            "agriculture": ["ZC/USD", "ZW/USD", "ZS/USD", "CORN/USD", "WHEAT/USD", "SOYBEAN/USD",
                            "COTTON/USD", "SUGAR/USD", "COFFEE/USD", "COCOA/USD"],
            "industrial_metals": ["HG/USD", "COPPER/USD", "ALU/USD", "ZINC/USD", "NICKEL/USD"]
        }

        # If a specific commodity group is requested, use only those symbols
        symbol_list = []
        if commodity_group and commodity_group in commodity_symbols:
            symbol_list = commodity_symbols[commodity_group]
        else:
            # Otherwise, use all common commodity symbols
            for symbols in commodity_symbols.values():
                symbol_list.extend(symbols)

        # If a specific symbol is requested, filter the list
        if symbol:
            symbol_list = [
                s for s in symbol_list if symbol.upper() in s.upper()]

        # If no symbols remain after filtering, return an empty list
        if not symbol_list:
            return []

        # Batch the symbols to avoid making too many requests
        batch_size = 8  # TwelveData allows multiple symbols in one request
        batches = [symbol_list[i:i + batch_size]
                   for i in range(0, len(symbol_list), batch_size)]

        all_results = []
        for batch in batches:
            symbols_str = ",".join(batch)
            endpoint = "/price"
            params = {"symbol": symbols_str}

            if exchange:
                params['exchange'] = exchange

            try:
                result = self._make_request(endpoint, params)

                # Convert result to a list of commodity pairs
                if isinstance(result, dict):
                    for symbol, data in result.items():
                        if isinstance(data, dict) and 'price' in data:
                            # Create a basic commodity pair entry
                            commodity_entry = {
                                "symbol": symbol,
                                "available_exchanges": [exchange] if exchange else ["GLOBAL"],
                                "is_active": True
                            }
                            all_results.append(commodity_entry)
            except TwelveDataAPIError as e:
                logger.warning(
                    f"Error fetching batch of commodity symbols: {e}")
                continue

        return all_results

    def get_commodity_groups(self) -> List[Dict[str, Any]]:
        """
        Get available commodity groups with descriptions.

        Returns:
            List of available commodity groups
        """
        # Create a list of standard commodity groups
        commodity_groups = [
            {
                "name": "precious_metals",
                "description": "Precious metals like gold, silver, platinum, and palladium",
                "examples": ["XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD"]
            },
            {
                "name": "energy",
                "description": "Energy commodities like crude oil, natural gas, and heating oil",
                "examples": ["CL/USD", "BRENT/USD", "WTI/USD", "NG/USD"]
            },
            {
                "name": "agriculture",
                "description": "Agricultural commodities like corn, wheat, soybeans, and coffee",
                "examples": ["CORN/USD", "WHEAT/USD", "SOYBEAN/USD", "COFFEE/USD"]
            },
            {
                "name": "industrial_metals",
                "description": "Industrial metals like copper, aluminum, zinc, and nickel",
                "examples": ["COPPER/USD", "ALU/USD", "ZINC/USD", "NICKEL/USD"]
            }
        ]

        return commodity_groups

    def get_cross_listed_symbols(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Fetch cross-listed symbols from different exchanges.

        Args:
            symbol: Optional symbol to filter by (e.g., "AAPL")

        Returns:
            List of dictionaries containing cross-listed symbol information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "cross_listings"
        params = {}

        if symbol:
            params['symbol'] = symbol

        response_data = self._make_request(endpoint, params)
        logger.debug(f"Cross-listings API response: {response_data}")

        if isinstance(response_data, dict) and response_data.get("status") == "error":
            message = response_data.get("message", "Unknown error")
            logger.error(f"API Error: {message}")
            raise TwelveDataAPIError(f"API Error: {message}")

        # Handle different response formats
        if isinstance(response_data, dict) and "data" in response_data:
            return response_data["data"]
        elif isinstance(response_data, list):
            return response_data

        # If we can't determine the format, return as is
        logger.warning(f"Unexpected response format: {type(response_data)}")
        return response_data

    def get_exchanges_by_type(self, exchange_type: str = None) -> List[Dict[str, Any]]:
        """
        Fetch exchanges by type from the TwelveData API.

        Args:
            exchange_type: Type of exchange to filter by, e.g., 'stock', 'etf'

        Returns:
            List of exchanges with their details, filtered by type if specified

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "exchanges"
        params = {}

        if exchange_type:
            params['type'] = exchange_type

        logger.debug(f"Fetching exchanges with type={exchange_type}")

        response_data = self._make_request(endpoint, params)

        # Check if response is in the expected format
        if isinstance(response_data, dict) and response_data.get("status") == "error":
            message = response_data.get("message", "Unknown error")
            logger.error(f"API Error: {message}")
            raise TwelveDataAPIError(f"API Error: {message}")

        if isinstance(response_data, dict) and 'data' in response_data:
            return response_data['data']

        logger.warning(
            f"Unexpected response format for exchanges: {response_data}")
        return response_data

    def get_exchange_schedule(self, code: str, date: str = None) -> Dict[str, Any]:
        """
        Fetch exchange schedule, including details and trading hours.

        Args:
            code: Exchange code (e.g., 'NASDAQ', 'NYSE')
            date: Optional date to get trading hours for a specific date (YYYY-MM-DD format)

        Returns:
            Dictionary containing exchange schedule information including details and trading hours

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "exchange_schedule"
        params = {'code': code}

        if date:
            params['date'] = date

        logger.debug(f"Fetching exchange schedule for: {code}, date: {date}")

        response_data = self._make_request(endpoint, params)

        # Check if response is in the expected format
        if isinstance(response_data, dict) and response_data.get("status") == "error":
            message = response_data.get("message", "Unknown error")
            logger.error(f"API Error: {message}")
            raise TwelveDataAPIError(f"API Error: {message}")

        return response_data

    def get_all_exchanges_with_hours(self, limit: int = None, exchange_type: str = None) -> List[Dict[str, Any]]:
        """
        Fetch all exchanges with their trading hours.

        This method will first fetch the list of exchanges, then get the schedule for each exchange.

        Args:
            limit: Optional limit to the number of exchanges to fetch (for testing/development)
            exchange_type: Optional exchange type filter (e.g., 'stock', 'etf')

        Returns:
            List of dictionaries containing exchange data with trading hours

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(
            f"Fetching all exchanges with trading hours (limit={limit}, type={exchange_type})")

        # First, fetch all exchanges
        if exchange_type:
            exchanges = self.get_exchanges_by_type(exchange_type)
        else:
            exchanges = self.get_exchanges()

        # Apply limit if specified
        if limit and limit > 0:
            exchanges = exchanges[:limit]

        # For each exchange, get its schedule
        result = []
        for idx, exchange in enumerate(exchanges):
            exchange_code = exchange.get('code', '')
            if not exchange_code:
                logger.warning(
                    f"Exchange at index {idx} has no 'code' field, skipping")
                continue

            logger.debug(
                f"Fetching schedule for exchange {exchange_code} ({idx+1}/{len(exchanges)})")
            try:
                schedule = self.get_exchange_schedule(exchange_code)
                # Combine the exchange data with its schedule
                result.append(schedule)
            except TwelveDataAPIError as e:
                logger.warning(
                    f"Could not fetch schedule for exchange {exchange_code}: {e}")
                # Include the exchange without schedule data
                result.append(exchange)

        return result

    def get_instrument_types(self) -> List[Dict[str, Any]]:
        """
        Fetch instrument types from the TwelveData API.

        This method fetches the list of available instrument types that can be
        used for filtering in other API endpoints.

        Returns:
            List of instrument types with their details

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "instrument_types"
        logger.debug("Fetching instrument types")

        try:
            response = self._make_request(endpoint)

            # Check if data is in the expected format
            if not isinstance(response, dict) or 'data' not in response:
                logger.error(
                    f"Unexpected response format for instrument types: {response}")
                raise TwelveDataAPIError(
                    "Unexpected response format for instrument types endpoint")

            return response['data']
        except Exception as e:
            logger.error(f"Error fetching instrument types: {e}")
            # If the endpoint doesn't exist or there's another issue,
            # fall back to a hardcoded list of common instrument types
            logger.warning("Falling back to hardcoded instrument types list")
            return [
                {"id": "stock", "name": "Stock"},
                {"id": "etf", "name": "ETF"},
                {"id": "index", "name": "Index"},
                {"id": "forex", "name": "Forex"},
                {"id": "crypto", "name": "Cryptocurrency"},
                {"id": "mutual_fund", "name": "Mutual Fund"},
                {"id": "reit", "name": "Real Estate Investment Trust (REIT)"},
                {"id": "bond", "name": "Bond"},
                {"id": "commodity", "name": "Commodity"}
            ]

    def get_earliest_timestamp(self, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Fetch the earliest available datetime for a given symbol and interval.

        This method queries the time_series endpoint with a very early start_date
        to find the first available data point for the specified symbol and interval.

        Args:
            symbol: The symbol to query (e.g., 'AAPL', 'BTC/USD')
            interval: Time interval (e.g., '1day', '1h', '5min')

        Returns:
            Dictionary containing the earliest available data information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(
            f"Fetching earliest available timestamp for {symbol} at {interval} interval")

        # Use a very early start date to get the earliest available data
        # Most financial data won't go back further than 1970
        early_start_date = "1970-01-01"

        # Request just one data point (the earliest one)
        params = {
            'symbol': symbol,
            'interval': interval,
            'start_date': early_start_date,
            'outputsize': 1  # We only need the first data point
        }

        endpoint = "/time_series"

        try:
            # Make the API request
            response = self._make_request(endpoint, params)

            # Check if we got valid data
            if 'values' not in response or not response['values']:
                logger.warning(
                    f"No historical data found for {symbol} at {interval} interval")
                return {
                    'symbol': symbol,
                    'interval': interval,
                    'earliest_datetime': None,
                    'message': "No historical data available"
                }

            # Extract the earliest datetime from the response
            earliest_data = response['values'][0]
            earliest_datetime = earliest_data.get('datetime')

            return {
                'symbol': symbol,
                'interval': interval,
                'earliest_datetime': earliest_datetime,
                'data': earliest_data
            }

        except TwelveDataAPIError as e:
            logger.error(
                f"API error fetching earliest timestamp for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching earliest timestamp for {symbol}: {e}")
            raise TwelveDataAPIError(
                f"Error fetching earliest timestamp: {str(e)}")

    def search_symbols(self, query: str, outputsize: int = 10,
                       instrument_types: Optional[List[str]] = None,
                       exchange: Optional[str] = None,
                       country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for symbols using a query string.

        Args:
            query: The search query string
            outputsize: Maximum number of results to return (default: 10)
            instrument_types: Optional list of instrument types to filter by
            exchange: Optional exchange code to filter by
            country: Optional country name to filter by

        Returns:
            List of matching symbols with their details

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "/symbol_search"
        params = {
            'symbol': query,
            'outputsize': outputsize
        }

        # Add optional filters if provided
        if instrument_types:
            params['type'] = ','.join(instrument_types)
        if exchange:
            params['exchange'] = exchange
        if country:
            params['country'] = country

        logger.debug(
            f"Searching symbols with query: {query}, params: {params}")

        try:
            response = self._make_request(endpoint, params)

            # Check if the response contains the data
            if not isinstance(response, dict) or 'data' not in response:
                logger.error(
                    f"Unexpected response format for symbol search: {response}")
                raise TwelveDataAPIError(
                    "Unexpected response format for symbol search endpoint")

            # Return the list of matching symbols
            return response['data']

        except TwelveDataAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching symbols: {e}")
            raise TwelveDataAPIError(f"Error searching symbols: {str(e)}")

    def get_time_series(self, symbol: str, interval: str, outputsize: int = 30,
                        start_date: Optional[str] = None, end_date: Optional[str] = None,
                        order: str = "desc", include_ext_premarket: bool = False) -> Dict[str, Any]:
        """
        Fetch historical time series data from the TwelveData API.

        Args:
            symbol: The symbol to query (e.g., "AAPL", "BTC/USD")
            interval: Time interval (e.g., "1min", "5min", "1h", "1day", "1week", "1month")
            outputsize: Number of data points to return (default: 30, max: 5000)
            start_date: Optional start date in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format
            end_date: Optional end date in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format
            order: Order of results ("asc" or "desc" for oldest first or newest first)
            include_ext_premarket: Whether to include extended hours data for stocks

        Returns:
            Dictionary containing meta information and time series values

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(
            f"Fetching time series for {symbol} at {interval} interval")

        endpoint = "/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
        }

        # Add optional parameters
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if order and order.lower() in ["asc", "desc"]:
            params["order"] = order.lower()
        if include_ext_premarket:
            params["dp"] = "true"  # Include extended hours data

        try:
            response = self._make_request(endpoint, params)

            # Validate response to ensure it has the expected structure
            if "meta" not in response or "values" not in response:
                logger.error(
                    f"Unexpected response structure for time series: {response}")
                if "status" in response and "message" in response:
                    raise TwelveDataAPIError(response["message"])
                raise TwelveDataAPIError(
                    "Unexpected response structure from time series endpoint")

            # Return both meta and values data
            return response

        except TwelveDataAPIError as e:
            logger.error(f"API error fetching time series for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching time series for {symbol}: {e}")
            raise TwelveDataAPIError(f"Error fetching time series: {str(e)}")

    def get_exchange_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch real-time exchange rate for a currency pair from the TwelveData API.

        Args:
            symbol: The forex pair symbol (e.g., 'EUR/USD', 'GBP/JPY')

        Returns:
            Dictionary containing exchange rate information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(f"Fetching exchange rate for {symbol}")

        endpoint = "/exchange_rate"
        params = {'symbol': symbol}

        try:
            response = self._make_request(endpoint, params)

            # The exchange_rate endpoint doesn't return any meta/values structure,
            # but directly returns the exchange rate data

            # Make sure the response contains a rate
            if 'rate' not in response:
                logger.error(
                    f"Unexpected response structure for exchange rate: {response}")
                if 'status' in response and response.get('status') == 'error':
                    raise TwelveDataAPIError(response.get(
                        'message', 'Unknown error in exchange rate endpoint'))
                raise TwelveDataAPIError(
                    "Unexpected response structure from exchange rate endpoint")

            return response

        except TwelveDataAPIError as e:
            logger.error(f"API error fetching exchange rate for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error fetching exchange rate for {symbol}: {e}")
            raise TwelveDataAPIError(f"Error fetching exchange rate: {str(e)}")

    def get_eod_price(self, symbol: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch the latest End of Day (EOD) price for a symbol.

        Args:
            symbol: The ticker symbol to get EOD data for
            date: Optional specific date in format YYYY-MM-DD (defaults to latest available EOD)

        Returns:
            Dictionary containing EOD price data

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "/eod"
        params = {
            'symbol': symbol
        }

        if date:
            params['date'] = date

        logger.debug(f"Fetching EOD price for {symbol}, date={date}")
        return self._make_request(endpoint, params)

    def get_market_movers(self, direction: str = "gainers", exchange: Optional[str] = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch the top gaining or losing stocks for the day.

        Args:
            direction: "gainers" for top gainers, "losers" for top losers
            exchange: Optional exchange to filter by (e.g., "NASDAQ", "NYSE")
            limit: Maximum number of stocks to return (default 10)

        Returns:
            List of dictionaries containing stock data sorted by price change

        Raises:
            TwelveDataAPIError: If the API request fails
            ValueError: If direction is not "gainers" or "losers"
        """
        if direction not in ["gainers", "losers"]:
            raise ValueError('Direction must be either "gainers" or "losers"')

        # This API endpoint might vary by provider, but we'll simulate it
        # by fetching multiple stock quotes and sorting them
        # First, get a list of major stocks (TwelveData doesn't directly have a movers endpoint)
        endpoint = "/stocks"
        params = {
            "exchange": exchange if exchange else "NASDAQ"  # Default to NASDAQ
        }
        logger.debug(
            f"Fetching stocks for market movers, direction={direction}, exchange={exchange}")

        # Get list of stocks
        try:
            stocks_response = self._make_request(endpoint, params)
            if not isinstance(stocks_response, dict) or "data" not in stocks_response:
                raise TwelveDataAPIError(
                    "Unexpected response format from stocks endpoint")

            stocks = stocks_response.get("data", [])

            # Take only the first 30 stocks to avoid too many API calls
            top_stocks = stocks[:30]
            symbols = [stock["symbol"] for stock in top_stocks]

            if not symbols:
                logger.warning("No symbols found for market movers")
                return []

            # Get quotes for these stocks
            symbols_str = ",".join(symbols)
            quotes_endpoint = "/quote"
            quotes_params = {
                "symbol": symbols_str
            }

            quotes_response = self._make_request(
                quotes_endpoint, quotes_params)

            # Ensure we have a list of quotes
            if isinstance(quotes_response, dict) and "symbol" in quotes_response:
                # Single quote response
                quotes_list = [quotes_response]
            elif isinstance(quotes_response, list):
                quotes_list = quotes_response
            else:
                logger.error(
                    f"Unexpected format for quotes response: {quotes_response}")
                return []

            # Process and sort the quotes
            movers = []
            for quote in quotes_list:
                # Only include quotes with valid change percent
                if "percent_change" in quote and quote["percent_change"] is not None:
                    try:
                        # Add the quote to movers list with additional stock details
                        stock_info = next(
                            (s for s in top_stocks if s["symbol"] == quote["symbol"]), {})

                        # Create a mover entry combining quote and stock info
                        mover = {
                            "symbol": quote["symbol"],
                            "name": quote.get("name", stock_info.get("name", "Unknown")),
                            "exchange": quote.get("exchange", stock_info.get("exchange", "Unknown")),
                            "price": float(quote.get("close", quote.get("price", 0))),
                            "change": float(quote.get("change", 0)),
                            "percent_change": float(quote.get("percent_change", 0)),
                            "volume": int(quote.get("volume", 0)) if quote.get("volume") else None
                        }
                        movers.append(mover)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Error processing quote for {quote.get('symbol')}: {e}")
                        continue

            # Sort by percent change
            if direction == "gainers":
                movers.sort(key=lambda x: x["percent_change"], reverse=True)
            else:  # losers
                movers.sort(key=lambda x: x["percent_change"])

            # Apply the limit
            return movers[:limit]

        except Exception as e:
            logger.error(f"Error fetching market movers: {e}")
            raise TwelveDataAPIError(
                f"Failed to fetch market movers: {e}") from e

    def get_mutual_fund_info(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific mutual fund.

        Args:
            symbol: The mutual fund symbol (e.g., 'VTSAX')

        Returns:
            Dictionary containing detailed mutual fund data

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        # Use the stocks endpoint with additional parameters to get fund info
        endpoint = "/stocks"
        params = {
            'symbol': symbol,
            'type': 'mutual_fund',
            'show_plan': 'true'  # Request additional details
        }

        logger.debug(f"Fetching detailed mutual fund info for {symbol}")

        response = self._make_request(endpoint, params)

        if not isinstance(response, dict) or "data" not in response:
            raise TwelveDataAPIError("Unexpected response format from API")

        funds_data = response.get("data", [])

        if not funds_data:
            logger.warning(f"No mutual fund found for symbol {symbol}")
            return {}

        # Return the first matching fund (should be only one)
        return funds_data[0]

    def get_fund_families(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch list of fund families from the TwelveData API.

        Args:
            search: Optional search term to filter fund families

        Returns:
            List of dictionaries containing fund family information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        # Endpoint for fund families, modify according to actual TwelveData API structure
        endpoint = "/fund_families"  # This endpoint might not exist in TwelveData API
        params = {}

        if search:
            params['search'] = search

        logger.debug(f"Fetching fund families with search={search}")

        try:
            # Since TwelveData might not have a dedicated endpoint for fund families,
            # we need to simulate it by aggregating fund family data from mutual funds

            # Step 1: Get mutual funds
            mutual_funds = self.get_mutual_funds()

            # Step 2: Extract and aggregate fund family information
            families = {}

            for fund in mutual_funds:
                family_name = fund.get('fund_family') or fund.get(
                    'issuer', 'Unknown')
                if not family_name or family_name == 'Unknown':
                    continue

                # Filter by search term if provided
                if search and search.lower() not in family_name.lower():
                    continue

                if family_name not in families:
                    # Initialize new family entry
                    families[family_name] = {
                        "name": family_name,
                        "fund_count": 1,
                        "popular_funds": [fund.get('name')],
                        "headquarters": "N/A",  # These fields would come from a real API
                        "founded": "N/A",
                        "aum": "N/A",
                        "website": "N/A",
                        "description": ""
                    }
                else:
                    # Update existing family entry
                    families[family_name]["fund_count"] += 1
                    if fund.get('name') and len(families[family_name]["popular_funds"]) < 10:
                        families[family_name]["popular_funds"].append(
                            fund.get('name'))

            # Step 3: Return sorted list of families
            result = list(families.values())
            result.sort(key=lambda x: x["name"])

            return result

        except Exception as e:
            logger.error(f"Error fetching fund families: {e}")
            raise TwelveDataAPIError(
                f"Failed to fetch fund families: {e}") from e

    def get_fund_family_detail(self, family_name: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific fund family.

        Args:
            family_name: The name of the fund family (e.g., 'Vanguard')

        Returns:
            Dictionary containing detailed fund family information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(f"Fetching fund family detail for {family_name}")

        try:
            # Get all funds from the family
            mutual_funds = self.get_mutual_funds()

            family_funds = [fund for fund in mutual_funds
                            if family_name.lower() in (fund.get('fund_family', '') or '').lower()]

            if not family_funds:
                logger.warning(f"No funds found for family: {family_name}")
                return {}

            # Construct family detail from fund data
            family_detail = {
                "name": family_name,
                "fund_count": len(family_funds),
                "popular_funds": [fund.get('name', 'Unknown Fund') for fund in family_funds],
                "headquarters": "N/A",  # These would come from a real API
                "founded": "N/A",
                "aum": "N/A",
                "website": "N/A",
                "description": f"Details for {family_name} investment management company."
            }

            return family_detail

        except Exception as e:
            logger.error(f"Error fetching fund family detail: {e}")
            raise TwelveDataAPIError(
                f"Failed to fetch fund family detail: {e}") from e

    def get_mutual_fund_types(self) -> List[Dict[str, Any]]:
        """
        Fetch the available mutual fund types from the TwelveData API.

        Returns:
            List of dictionaries containing mutual fund type information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug("Fetching mutual fund types")

        # TwelveData may not have a dedicated endpoint for fund types, so we need to
        # extract this information from mutual funds data
        try:
            # Get a sample of mutual funds to extract types
            mutual_funds = self.get_mutual_funds()

            # Extract and compile fund type information
            fund_types = {}

            for fund in mutual_funds:
                # Extract category/type information
                category = fund.get('fund_category')
                if not category:
                    continue

                if category not in fund_types:
                    # Add a new fund type
                    fund_types[category] = {
                        "name": category,
                        "count": 1,
                        "description": "",  # TwelveData may not provide this
                        "example_funds": [fund.get('name', 'Unknown')],
                        "risk_level": self._estimate_risk_level(category)
                    }
                else:
                    # Update existing fund type
                    fund_types[category]["count"] += 1
                    if len(fund_types[category]["example_funds"]) < 5:
                        fund_types[category]["example_funds"].append(
                            fund.get('name', 'Unknown'))

            # Convert to list and sort by name
            result = list(fund_types.values())
            result.sort(key=lambda x: x["name"])

            return result

        except Exception as e:
            logger.error(f"Error fetching mutual fund types: {e}")
            raise TwelveDataAPIError(
                f"Failed to fetch mutual fund types: {e}") from e

    def _estimate_risk_level(self, category: str) -> str:
        """
        Estimate risk level based on fund category name.

        Args:
            category: Fund category/type name

        Returns:
            Estimated risk level (Low, Medium, High)
        """
        # This is a simplified estimation based on common category names
        category_lower = category.lower()

        # Conservative/low risk categories
        if any(term in category_lower for term in [
            'money market', 'short-term bond', 'treasury', 'government bond',
            'municipal', 'inflation', 'stable value', 'conservative'
        ]):
            return "Low"

        # High risk categories
        if any(term in category_lower for term in [
            'small cap', 'emerging market', 'international small cap',
            'sector', 'commodity', 'precious metal', 'aggressive growth',
            'leveraged', 'alternative', 'frontier market', 'high yield'
        ]):
            return "High"

        # Everything else is medium risk
        return "Medium"

    def get_mutual_fund_type_detail(self, type_name: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific mutual fund type.

        Args:
            type_name: The name of the fund type/category

        Returns:
            Dictionary containing detailed fund type information

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(f"Fetching details for mutual fund type: {type_name}")

        try:
            # Get all mutual funds
            mutual_funds = self.get_mutual_funds()

            # Find funds matching the specified type
            matching_funds = [
                fund for fund in mutual_funds
                if fund.get('fund_category', '').lower() == type_name.lower()
            ]

            if not matching_funds:
                logger.warning(f"No funds found for type: {type_name}")
                return {}

            # Analyze funds to extract useful information
            top_families = {}
            example_symbols = []

            for fund in matching_funds:
                # Track fund families
                family = fund.get('fund_family', 'Unknown')
                if family in top_families:
                    top_families[family] += 1
                else:
                    top_families[family] = 1

                # Collect example symbols
                if len(example_symbols) < 10 and 'symbol' in fund:
                    example_symbols.append(fund.get('symbol'))

            # Sort families by fund count
            sorted_families = sorted(
                top_families.items(), key=lambda x: x[1], reverse=True)
            top_families_list = [{"name": name, "count": count}
                                 for name, count in sorted_families[:10]]

            # Create the detailed type information
            type_detail = {
                "name": type_name,
                "count": len(matching_funds),
                "description": self._get_type_description(type_name),
                "risk_level": self._estimate_risk_level(type_name),
                "top_families": top_families_list,
                "example_funds": [fund.get('name', 'Unknown') for fund in matching_funds[:10]],
                "example_symbols": example_symbols
            }

            return type_detail

        except Exception as e:
            logger.error(f"Error fetching fund type detail: {e}")
            raise TwelveDataAPIError(
                f"Failed to fetch fund type detail: {e}") from e

    def _get_type_description(self, type_name: str) -> str:
        """
        Return a description for the fund type.

        Args:
            type_name: Fund type/category name

        Returns:
            Description of the fund type
        """
        # This is a simplified function that returns pre-defined descriptions
        # for common fund types. In a real implementation, this data would come
        # from the API or a more comprehensive database.
        type_lower = type_name.lower()

        descriptions = {
            "large cap": "Funds that invest primarily in stocks of large companies, typically with market capitalizations over $10 billion.",
            "mid cap": "Funds that invest primarily in stocks of mid-sized companies, typically with market capitalizations between $2 billion and $10 billion.",
            "small cap": "Funds that invest primarily in stocks of smaller companies, typically with market capitalizations under $2 billion.",
            "international": "Funds that invest primarily in stocks of companies outside the investor's home country.",
            "emerging market": "Funds that invest primarily in stocks of companies in developing economies.",
            "growth": "Funds that focus on companies expected to grow earnings at an above-average rate compared to other companies.",
            "value": "Funds that focus on stocks that appear to be undervalued compared to the company's intrinsic value.",
            "blend": "Funds that invest in both growth and value stocks.",
            "index": "Funds that aim to replicate the performance of a specific index, such as the S&P 500.",
            "sector": "Funds that focus investments in a particular industry or sector of the economy.",
            "bond": "Funds that invest primarily in bonds and other debt securities.",
            "money market": "Funds that invest in short-term, high-quality debt securities.",
            "balanced": "Funds that invest in both stocks and bonds, typically in a fixed ratio.",
            "target date": "Funds that automatically adjust their asset allocation to become more conservative as they approach their target date.",
            "income": "Funds that focus on generating income through dividends and interest rather than capital appreciation.",
            "tax-exempt": "Funds that invest in securities that provide income exempt from federal or state income taxes.",
            "alternative": "Funds that invest in non-traditional assets or use non-traditional investment strategies."
        }

        # Try to find an exact match
        for key, description in descriptions.items():
            if key == type_lower:
                return description

        # Try to find a partial match
        for key, description in descriptions.items():
            if key in type_lower:
                return description

        # Default description if no match is found
        return f"Mutual funds categorized as {type_name}."

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company profile information.

        Args:
            symbol: The ticker symbol (e.g., 'AAPL', 'MSFT')

        Returns:
            Dictionary containing company profile data

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(f"Fetching company profile for {symbol}")

        # TwelveData has a profile endpoint
        endpoint = "/profile"
        params = {
            'symbol': symbol
        }

        try:
            profile_data = self._make_request(endpoint, params)

            # Enhance the profile with additional information from other endpoints
            # if we need more details in the future

            return profile_data

        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {e}")
            raise TwelveDataAPIError(
                f"Failed to fetch company profile: {e}") from e

    def get_company_logo(self, symbol: str) -> str:
        """
        Fetch company logo URL.

        Args:
            symbol: The ticker symbol (e.g., 'AAPL', 'MSFT')

        Returns:
            URL to the company logo

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        logger.debug(f"Fetching company logo for {symbol}")

        # TwelveData might not have a dedicated logo endpoint, so we're
        # simulating this with a function that uses a placeholder URL
        # In a real implementation, this would connect to the actual API

        try:
            # This is a placeholder. In a real implementation,
            # we would fetch the actual logo URL from the API.
            # For now, we'll use a common logo service as an example.
            return f"https://logo.clearbit.com/{symbol.lower()}.com"
        except Exception as e:
            logger.error(f"Error fetching company logo for {symbol}: {e}")
            # Return a default placeholder if we can't get the logo
            return "https://placehold.co/400"

    # This is the new method to be added to the TwelveDataClient class


    def get_dividend_history(self, symbol: str, years: int = 10) -> Dict[str, Any]:
        """
        Get dividend history for a stock symbol.

        Args:
            symbol: Stock symbol to fetch dividend data for
            years: Number of years of dividend history to fetch (default: 10)

        Returns:
            Dictionary containing dividend history

        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "dividends"
        params = {
            "symbol": symbol,
            "range": f"{years}year"  # API supports format like "10year"
        }

        logger.debug(f"Fetching dividend history for {symbol} over {years} years")
        response = self._make_request(endpoint, params)

        if not response.get("dividends"):
            if response.get("code") == 429:
                raise TwelveDataAPIError("API rate limit exceeded")
            elif response.get("code") == 400:
                logger.warning(f"No dividend data available for {symbol}")
                # Create an empty response structure for consistent handling
                return {
                    "meta": {
                        "symbol": symbol,
                        "name": response.get("name", ""),
                        "currency": "USD",
                        "exchange": "",
                        "mic_code": "",
                        "country": "",
                        "type": ""
                    },
                    "dividends": []
                }
            else:
                error_msg = response.get(
                    "message", "Unknown error fetching dividend data")
                logger.error(f"API Error: {error_msg}")
                raise TwelveDataAPIError(
                    f"Error fetching dividend data: {error_msg}")

        return response

    def get_dividend_calendar(self, start_date: Optional[str] = None, 
                           end_date: Optional[str] = None,
                           symbol: Optional[str] = None,
                           exchange: Optional[str] = None,
                           range_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get dividend calendar for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format (required if range_type not provided)
            end_date: End date in YYYY-MM-DD format (required if range_type not provided)
            symbol: Optional stock symbol to filter by
            exchange: Optional exchange code to filter by
            range_type: Predefined range ('today', 'week', 'month', 'quarter', 'year')
                        Alternative to providing start_date and end_date
            
        Returns:
            Dictionary containing dividend calendar events
            
        Raises:
            TwelveDataAPIError: If the API request fails
            ValueError: If date parameters are invalid
        """
        endpoint = "dividends_calendar"
        params = {}
        
        # Either range_type OR (start_date AND end_date) must be provided
        if range_type:
            if range_type not in ('today', 'week', 'month', 'quarter', 'year'):
                raise ValueError(
                    "range_type must be one of: 'today', 'week', 'month', 'quarter', 'year'"
                )
            params['range'] = range_type
            logger.debug(f"Using predefined range: {range_type}")
        elif start_date and end_date:
            # Validate date format (YYYY-MM-DD)
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Dates must be in YYYY-MM-DD format")
            
            params['start_date'] = start_date
            params['end_date'] = end_date
            logger.debug(f"Using custom date range: {start_date} to {end_date}")
        else:
            raise ValueError(
                "Either range_type OR both start_date and end_date must be provided"
            )
        
        # Add optional filters
        if symbol:
            params['symbol'] = symbol
            logger.debug(f"Filtering by symbol: {symbol}")
        
        if exchange:
            params['exchange'] = exchange
            logger.debug(f"Filtering by exchange: {exchange}")
        
        logger.debug(f"Fetching dividend calendar with params: {params}")
        response = self._make_request(endpoint, params)
        
        if response.get("code") == 429:
            raise TwelveDataAPIError("API rate limit exceeded")
        elif response.get("code") == 400:
            error_msg = response.get("message", f"Error: {response}")
            logger.warning(f"API Error: {error_msg}")
            raise TwelveDataAPIError(f"API Error: {error_msg}")
        
        # If we don't have events in the response, return empty structure
        if not response.get("events") and not response.get("code"):
            logger.warning(f"No dividend calendar events found for the specified parameters")
            return {
                "events": []
            }
        
        return response
    
    def get_stock_splits(self, symbol: str, years: int = 10) -> Dict[str, Any]:
        """
        Get stock splits history for a stock symbol.
        
        Args:
            symbol: Stock symbol to fetch split data for
            years: Number of years of split history to fetch (default: 10)
            
        Returns:
            Dictionary containing splits history
            
        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "splits"
        params = {
            "symbol": symbol,
            "range": f"{years}year"  # API supports format like "10year"
        }
        
        logger.debug(f"Fetching stock splits for {symbol} over {years} years")
        response = self._make_request(endpoint, params)
        
        # Check for API errors
        if response.get("code") == 429:
            raise TwelveDataAPIError("API rate limit exceeded")
        elif response.get("code") == 400:
            error_msg = response.get("message", "")
            if "not found" in error_msg.lower():
                logger.warning(f"No split data available for {symbol}")
                # Create an empty response structure for consistent handling
                return {
                    "meta": {
                        "symbol": symbol,
                        "name": ""
                    },
                    "splits": []
                }
            else:
                logger.error(f"API Error: {error_msg}")
                raise TwelveDataAPIError(f"Error fetching split data: {error_msg}")
        
        # Check if we have the expected structure
        if not isinstance(response.get("splits"), list):
            logger.warning(f"Unexpected response format for splits: {response}")
            # Create a valid empty response
            return {
                "meta": {
                    "symbol": symbol,
                    "name": response.get("meta", {}).get("name", "")
                },
                "splits": []
            }
        
        return response
    
    def get_splits_calendar(self, start_date: Optional[str] = None, 
                            end_date: Optional[str] = None,
                            symbol: Optional[str] = None,
                            exchange: Optional[str] = None,
                            range_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get stock splits calendar for a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format (required if range_type not provided)
            end_date: End date in YYYY-MM-DD format (required if range_type not provided)
            symbol: Optional stock symbol to filter by
            exchange: Optional exchange code to filter by
            range_type: Predefined range ('today', 'week', 'month', 'quarter', 'year')
                        Alternative to providing start_date and end_date
            
        Returns:
            Dictionary containing splits calendar events
            
        Raises:
            TwelveDataAPIError: If the API request fails
            ValueError: If date parameters are invalid
        """
        endpoint = "splits_calendar"
        params = {}
        
        # Either range_type OR (start_date AND end_date) must be provided
        if range_type:
            if range_type not in ('today', 'week', 'month', 'quarter', 'year'):
                raise ValueError(
                    "range_type must be one of: 'today', 'week', 'month', 'quarter', 'year'"
                )
            params['range'] = range_type
            logger.debug(f"Using predefined range: {range_type}")
        elif start_date and end_date:
            # Validate date format (YYYY-MM-DD)
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Dates must be in YYYY-MM-DD format")
            
            params['start_date'] = start_date
            params['end_date'] = end_date
            logger.debug(f"Using custom date range: {start_date} to {end_date}")
        else:
            raise ValueError(
                "Either range_type OR both start_date and end_date must be provided"
            )
        
        # Add optional filters
        if symbol:
            params['symbol'] = symbol
            logger.debug(f"Filtering by symbol: {symbol}")
        
        if exchange:
            params['exchange'] = exchange
            logger.debug(f"Filtering by exchange: {exchange}")
        
        logger.debug(f"Fetching splits calendar with params: {params}")
        response = self._make_request(endpoint, params)
        
        if response.get("code") == 429:
            raise TwelveDataAPIError("API rate limit exceeded")
        elif response.get("code") == 400:
            error_msg = response.get("message", f"Error: {response}")
            logger.warning(f"API Error: {error_msg}")
            raise TwelveDataAPIError(f"API Error: {error_msg}")
        
        # If we don't have events in the response, return empty structure
        if not response.get("events") and not response.get("code"):
            logger.warning(f"No split calendar events found for the specified parameters")
            return {
                "events": []
            }
        
        return response

# Initialize the TwelveData client
client = TwelveDataClient()
