import pytest
from unittest.mock import patch, MagicMock
import click
from click.testing import CliRunner
from datetime import datetime

from app.api.twelve_data import TwelveDataClient, TwelveDataAPIError
from app.models.forex import ForexPair, Currency
from app.cli.commands import list_forex_pairs, list_currencies


# Sample API responses for testing
SAMPLE_FOREX_PAIRS_RESPONSE = {
    "data": [
        {
            "symbol": "EUR/USD",
            "currency_group": "Major",
            "currency_base": "EUR",
            "currency_quote": "USD",
            "available_exchanges": ["FOREX"],
            "is_active": True
        },
        {
            "symbol": "GBP/USD",
            "currency_group": "Major",
            "currency_base": "GBP",
            "currency_quote": "USD",
            "available_exchanges": ["FOREX"],
            "is_active": True
        },
        {
            "symbol": "USD/JPY",
            "currency_group": "Major",
            "currency_base": "USD",
            "currency_quote": "JPY",
            "available_exchanges": ["FOREX"],
            "is_active": True
        },
        {
            "symbol": "AUD/NZD",
            "currency_group": "Minor",
            "currency_base": "AUD",
            "currency_quote": "NZD",
            "available_exchanges": ["FOREX"],
            "is_active": True
        }
    ]
}

SAMPLE_CURRENCIES_RESPONSE = {
    "data": [
        {
            "code": "USD",
            "name": "US Dollar",
            "country": "United States",
            "is_major": True,
            "is_active": True,
            "symbol": "$"
        },
        {
            "code": "EUR",
            "name": "Euro",
            "country": "European Union",
            "is_major": True,
            "is_active": True,
            "symbol": "€"
        },
        {
            "code": "GBP",
            "name": "British Pound",
            "country": "United Kingdom",
            "is_major": True,
            "is_active": True,
            "symbol": "£"
        },
        {
            "code": "JPY",
            "name": "Japanese Yen",
            "country": "Japan",
            "is_major": True,
            "is_active": True,
            "symbol": "¥"
        },
        {
            "code": "AUD",
            "name": "Australian Dollar",
            "country": "Australia",
            "is_major": True,
            "is_active": True,
            "symbol": "$"
        }
    ]
}

ERROR_RESPONSE = {
    "status": "error",
    "message": "Invalid API key or access restricted"
}


class TestForexFunctionality:
    """Tests for fetching and displaying forex data from TwelveData API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked TwelveData client."""
        with patch('app.cli.commands.client') as mock_client:
            yield mock_client

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner for testing CLI commands."""
        return CliRunner()

    def test_forex_pair_model_from_api_response(self):
        """Test creating ForexPair models from API response data."""
        # Get a single forex pair from the sample data
        sample_data = SAMPLE_FOREX_PAIRS_RESPONSE['data'][0]
        
        # Create a ForexPair instance
        forex_pair = ForexPair.from_api_response(sample_data)
        
        # Verify all properties are set correctly
        assert forex_pair.symbol == "EUR/USD"
        assert forex_pair.currency_group == "Major"
        assert forex_pair.currency_base == "EUR"
        assert forex_pair.currency_quote == "USD"
        assert forex_pair.available_exchanges == ["FOREX"]
        assert forex_pair.is_active is True
    
    def test_currency_model_from_api_response(self):
        """Test creating Currency models from API response data."""
        # Get a single currency from the sample data
        sample_data = SAMPLE_CURRENCIES_RESPONSE['data'][0]
        
        # Create a Currency instance
        currency = Currency.from_api_response(sample_data)
        
        # Verify all properties are set correctly
        assert currency.code == "USD"
        assert currency.name == "US Dollar"
        assert currency.country == "United States"
        assert currency.is_major is True
        assert currency.is_active is True
        assert currency.symbol == "$"

    def test_get_forex_pairs_with_no_filters(self, mock_client):
        """Test fetching all forex pairs without any filters."""
        # Setup mock to return sample forex pairs
        mock_client.get_forex_pairs.return_value = SAMPLE_FOREX_PAIRS_RESPONSE['data']
        
        # Create forex pairs from the API response
        pairs = [ForexPair.from_api_response(data) for data in mock_client.get_forex_pairs()]
        
        # Verify we got all pairs
        assert len(pairs) == 4
        assert pairs[0].symbol == "EUR/USD"
        assert pairs[1].symbol == "GBP/USD"
        assert pairs[2].symbol == "USD/JPY"
        assert pairs[3].symbol == "AUD/NZD"
        
        # Verify client was called without filters
        mock_client.get_forex_pairs.assert_called_once_with(
            currency_base=None, currency_quote=None
        )

    def test_get_forex_pairs_with_base_filter(self, mock_client):
        """Test fetching forex pairs filtered by base currency."""
        # Setup filtered response (only USD base currency)
        filtered_response = [pair for pair in SAMPLE_FOREX_PAIRS_RESPONSE['data'] 
                            if pair['currency_base'] == 'USD']
        mock_client.get_forex_pairs.return_value = filtered_response
        
        # Create forex pairs with base filter
        pairs = [ForexPair.from_api_response(data) for data in 
                mock_client.get_forex_pairs(currency_base='USD')]
        
        # Verify we got only USD base pairs
        assert len(pairs) == 1
        assert all(p.currency_base == 'USD' for p in pairs)
        assert pairs[0].symbol == "USD/JPY"
        
        # Verify client was called with base filter
        mock_client.get_forex_pairs.assert_called_once_with(
            currency_base='USD', currency_quote=None
        )

    def test_get_forex_pairs_with_quote_filter(self, mock_client):
        """Test fetching forex pairs filtered by quote currency."""
        # Setup filtered response (only USD quote currency)
        filtered_response = [pair for pair in SAMPLE_FOREX_PAIRS_RESPONSE['data'] 
                            if pair['currency_quote'] == 'USD']
        mock_client.get_forex_pairs.return_value = filtered_response
        
        # Create forex pairs with quote filter
        pairs = [ForexPair.from_api_response(data) for data in 
                mock_client.get_forex_pairs(currency_quote='USD')]
        
        # Verify we got only USD quote pairs
        assert len(pairs) == 2
        assert all(p.currency_quote == 'USD' for p in pairs)
        assert pairs[0].symbol == "EUR/USD"
        assert pairs[1].symbol == "GBP/USD"
        
        # Verify client was called with quote filter
        mock_client.get_forex_pairs.assert_called_once_with(
            currency_base=None, currency_quote='USD'
        )

    def test_get_forex_pairs_with_both_filters(self, mock_client):
        """Test fetching forex pairs with both base and quote filters."""
        # Setup filtered response (specific base and quote)
        filtered_response = [pair for pair in SAMPLE_FOREX_PAIRS_RESPONSE['data'] 
                           if pair['currency_base'] == 'EUR' and pair['currency_quote'] == 'USD']
        mock_client.get_forex_pairs.return_value = filtered_response
        
        # Create forex pairs with both filters
        pairs = [ForexPair.from_api_response(data) for data in 
                mock_client.get_forex_pairs(currency_base='EUR', currency_quote='USD')]
        
        # Verify we got only the matching pair
        assert len(pairs) == 1
        assert pairs[0].currency_base == 'EUR'
        assert pairs[0].currency_quote == 'USD'
        assert pairs[0].symbol == "EUR/USD"
        
        # Verify client was called with both filters
        mock_client.get_forex_pairs.assert_called_once_with(
            currency_base='EUR', currency_quote='USD'
        )

    def test_get_forex_pairs_api_error(self, mock_client):
        """Test handling of API errors when fetching forex pairs."""
        # Setup mock to raise an error
        mock_client.get_forex_pairs.side_effect = TwelveDataAPIError("API Error")
        
        # Attempt to fetch forex pairs (should raise the API error)
        with pytest.raises(TwelveDataAPIError):
            mock_client.get_forex_pairs()

    def test_get_currencies(self, mock_client):
        """Test fetching all currencies."""
        # Setup mock to return sample currencies
        mock_client.get_currencies.return_value = SAMPLE_CURRENCIES_RESPONSE['data']
        
        # Get currencies
        currencies = [Currency.from_api_response(data) for data in mock_client.get_currencies()]
        
        # Verify we got all currencies
        assert len(currencies) == 5
        assert currencies[0].code == "USD"
        assert currencies[1].code == "EUR"
        assert currencies[2].code == "GBP"
        assert currencies[3].code == "JPY"
        assert currencies[4].code == "AUD"
        
        # Verify client was called
        mock_client.get_currencies.assert_called_once()

    def test_forex_pair_to_dict_for_serialization(self):
        """Test converting ForexPair objects to dictionaries for serialization."""
        # Create a forex pair
        forex_pair = ForexPair(
            symbol="EUR/USD",
            currency_group="Major",
            currency_base="EUR",
            currency_quote="USD",
            available_exchanges=["FOREX"],
            is_active=True
        )
        
        # Convert to dict
        data = forex_pair.to_dict()
        
        # Verify all fields are included
        assert data["symbol"] == "EUR/USD"
        assert data["currency_group"] == "Major"
        assert data["currency_base"] == "EUR"
        assert data["currency_quote"] == "USD"
        assert data["available_exchanges"] == ["FOREX"]
        assert data["is_active"] is True

    def test_forex_pair_to_csv_row(self):
        """Test converting ForexPair objects to CSV rows."""
        # Create a forex pair
        forex_pair = ForexPair(
            symbol="EUR/USD",
            currency_group="Major",
            currency_base="EUR",
            currency_quote="USD",
            available_exchanges=["FOREX"],
            is_active=True
        )
        
        # Convert to CSV row dict
        row = forex_pair.to_csv_row()
        
        # Verify all fields are included as strings
        assert row["symbol"] == "EUR/USD"
        assert row["currency_group"] == "Major"
        assert row["currency_base"] == "EUR"
        assert row["currency_quote"] == "USD"
        assert row["available_exchanges"] == "FOREX"  # Should be joined as string
        assert row["is_active"] == "True"  # Boolean as string
        
        # Verify the header matches row keys
        header = ForexPair.get_csv_header()
        assert set(header) == set(row.keys())

    def test_currency_to_dict_and_csv(self):
        """Test converting Currency objects to dicts and CSV rows."""
        # Create a currency
        currency = Currency(
            code="USD",
            name="US Dollar",
            country="United States",
            is_major=True,
            is_active=True,
            symbol="$"
        )
        
        # Test to_dict
        data = currency.to_dict()
        assert data["code"] == "USD"
        assert data["name"] == "US Dollar"
        assert data["symbol"] == "$"
        
        # Test to_csv_row
        row = currency.to_csv_row()
        assert row["code"] == "USD"
        assert row["name"] == "US Dollar"
        assert row["is_major"] == "True"  # Boolean as string
        
        # Verify header
        header = Currency.get_csv_header()
        assert set(header) == set(row.keys())

    def test_cli_list_forex_pairs_command(self, mock_client, cli_runner):
        """Test the CLI command for listing forex pairs."""
        # Setup mock to return sample forex pairs
        mock_client.get_forex_pairs.return_value = SAMPLE_FOREX_PAIRS_RESPONSE['data']
        
        with patch('app.cli.commands.list_forex_pairs') as mock_list_pairs:
            # Mock the actual command to avoid side effects
            mock_list_pairs.side_effect = list_forex_pairs
            
            # Run the CLI command
            result = cli_runner.invoke(list_forex_pairs, ["--base", "USD"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify the command was called with the correct base argument
            _, kwargs = mock_list_pairs.call_args
            assert kwargs["base"] == "USD"

    def test_cli_list_currencies_command(self, mock_client, cli_runner):
        """Test the CLI command for listing currencies."""
        # Setup mock to return sample currencies
        mock_client.get_currencies.return_value = SAMPLE_CURRENCIES_RESPONSE['data']
        
        with patch('app.cli.commands.list_currencies') as mock_list_currencies:
            # Mock the actual command to avoid side effects
            mock_list_currencies.side_effect = list_currencies
            
            # Run the CLI command
            result = cli_runner.invoke(list_currencies)
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_currencies was called
            mock_list_currencies.assert_called_once()

    @patch('app.utils.export.export_items')
    def test_forex_pair_export_functionality(self, mock_export_items, mock_client, cli_runner):
        """Test exporting forex pairs to files."""
        # Setup mocks
        mock_client.get_forex_pairs.return_value = SAMPLE_FOREX_PAIRS_RESPONSE['data']
        mock_export_items.return_value = {"json": "/path/to/export.json"}
        
        # Run command with export option
        with patch('app.cli.commands.list_forex_pairs', autospec=True) as mock_list_cmd:
            # Call the actual implementation but mock what it calls
            mock_list_cmd.side_effect = list_forex_pairs
            
            result = cli_runner.invoke(list_forex_pairs, ["--export", "json"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify export_items was called with forex pairs
            assert mock_export_items.call_count > 0
            # First arg should be a list of forex pairs
            args, _ = mock_export_items.call_args
            assert isinstance(args[0], list)
            assert len(args[0]) > 0
            assert all(isinstance(item, ForexPair) for item in args[0])

    @patch('app.utils.export.export_items')
    def test_currency_export_functionality(self, mock_export_items, mock_client, cli_runner):
        """Test exporting currencies to files."""
        # Setup mocks
        mock_client.get_currencies.return_value = SAMPLE_CURRENCIES_RESPONSE['data']
        mock_export_items.return_value = {"json": "/path/to/export.json"}
        
        # Run command with export option
        with patch('app.cli.commands.list_currencies', autospec=True) as mock_list_cmd:
            # Call the actual implementation but mock what it calls
            mock_list_cmd.side_effect = list_currencies
            
            result = cli_runner.invoke(list_currencies, ["--export", "json"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify export_items was called with currencies
            assert mock_export_items.call_count > 0
            # First arg should be a list of currencies
            args, _ = mock_export_items.call_args
            assert isinstance(args[0], list)
            assert len(args[0]) > 0
            assert all(isinstance(item, Currency) for item in args[0])

    def test_forex_pair_filtering_and_limit(self, mock_client, cli_runner):
        """Test that forex pairs can be filtered and limited."""
        # Setup mock to return all forex pairs
        mock_client.get_forex_pairs.return_value = SAMPLE_FOREX_PAIRS_RESPONSE['data']
        
        with patch('app.cli.commands.display_forex_pairs') as mock_display:
            # Run command with limit
            result = cli_runner.invoke(list_forex_pairs, ["--limit", "2"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify display was called with correct number of forex pairs
            args, _ = mock_display.call_args
            # First arg should be the forex pairs list, limited to 2
            assert len(args[0]) == 2

    @patch('app.cli.commands.click.echo')
    def test_no_forex_pairs_found(self, mock_echo, mock_client, cli_runner):
        """Test behavior when no forex pairs match the filters."""
        # Setup mock to return empty list
        mock_client.get_forex_pairs.return_value = []
        
        # Run command with filters that match nothing
        result = cli_runner.invoke(list_forex_pairs, ["--base", "INVALID"])
        
        # Verify command executed successfully but warns about no results
        assert result.exit_code == 0
        mock_echo.assert_any_call("No forex pairs found matching the criteria.")

    def test_currency_major_filtering(self, mock_client):
        """Test filtering currencies by major status."""
        # Create a mix of major and non-major currencies
        currencies = [
            Currency(code="USD", name="US Dollar", country="United States", 
                    is_major=True, is_active=True, symbol="$"),
            Currency(code="EUR", name="Euro", country="European Union", 
                    is_major=True, is_active=True, symbol="€"),
            Currency(code="ZWL", name="Zimbabwean Dollar", country="Zimbabwe", 
                    is_major=False, is_active=True, symbol="$")
        ]
        
        # Filter for major currencies
        major_currencies = [c for c in currencies if c.is_major]
        
        # Verify filtering worked
        assert len(major_currencies) == 2
        assert all(c.is_major for c in major_currencies)
        assert "USD" in [c.code for c in major_currencies]
        assert "EUR" in [c.code for c in major_currencies]
        assert "ZWL" not in [c.code for c in major_currencies]

    def test_forex_pair_group_filtering(self):
        """Test filtering forex pairs by currency group."""
        # Create a mix of major and minor pairs
        pairs = [
            ForexPair(symbol="EUR/USD", currency_group="Major", 
                     currency_base="EUR", currency_quote="USD", 
                     available_exchanges=["FOREX"], is_active=True),
            ForexPair(symbol="USD/JPY", currency_group="Major", 
                     currency_base="USD", currency_quote="JPY", 
                     available_exchanges=["FOREX"], is_active=True),
            ForexPair(symbol="AUD/NZD", currency_group="Minor", 
                     currency_base="AUD", currency_quote="NZD", 
                     available_exchanges=["FOREX"], is_active=True)
        ]
        
        # Filter for major pairs
        major_pairs = [p for p in pairs if p.currency_group == "Major"]
        
        # Verify filtering worked
        assert len(major_pairs) == 2
        assert all(p.currency_group == "Major" for p in major_pairs)
        assert "EUR/USD" in [p.symbol for p in major_pairs]
        assert "USD/JPY" in [p.symbol for p in major_pairs]
        assert "AUD/NZD" not in [p.symbol for p in major_pairs]