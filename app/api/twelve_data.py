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
        
        logger.warning(f"Unexpected response format for exchanges: {response_data}")
        return response_data


# Initialize the TwelveData client
client = TwelveDataClient()
