"""
TwelveData API client for stock data retrieval.
"""

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

    def get_fund_families(self, 
                          search: Optional[str] = None,
                          country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of mutual fund families/companies using the dedicated endpoint.
        
        Args:
            search: Optional search term to filter fund families by name
            country: Optional country filter
            
        Returns:
            List of dictionaries with fund family data
            
        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "/mutual_funds/family"
        params = {}
        
        # Add optional filters
        if search:
            params['search'] = search
        if country:
            params['country'] = country
            
        logger.debug(f"Fetching mutual fund families with params: {params}")
        
        try:
            response = self._make_request(endpoint, params)
            
            # Check if response is in the expected format
            if not isinstance(response, dict) or "data" not in response:
                logger.error(f"Unexpected response format for fund families: {response}")
                raise TwelveDataAPIError("Unexpected response format from fund families endpoint")
            
            # Extract and return the data
            families = response.get("data", [])
            
            # Sort by fund count (descending) and then name
            families.sort(key=lambda x: (-x.get('fund_count', 0), x.get('name', '')))
            
            return families
            
        except Exception as e:
            logger.error(f"Error fetching fund families: {e}")
            raise TwelveDataAPIError(f"Failed to get fund families: {e}") from e
            
            
    def get_fund_family_details(self, family_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific fund family.
        
        Args:
            family_id: The ID or name of the fund family
            
        Returns:
            Dictionary with detailed fund family information
            
        Raises:
            TwelveDataAPIError: If the API request fails
        """
        endpoint = "/mutual_funds/family"
        params = {
            'id': family_id
        }
        
        logger.debug(f"Fetching details for fund family: {family_id}")
        
        try:
            response = self._make_request(endpoint, params)
            
            # If the response is a list, take the first item
            if isinstance(response, list) and len(response) > 0:
                return response[0]
                
            return response
            
        except Exception as e:
            logger.error(f"Error fetching fund family details: {e}")
            raise TwelveDataAPIError(f"Failed to get fund family details: {e}") from e

# Initialize the TwelveData client
client = TwelveDataClient()
