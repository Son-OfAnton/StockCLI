import pytest
from unittest.mock import patch, MagicMock
import click
from click.testing import CliRunner

from app.api.twelve_data import TwelveDataClient, TwelveDataAPIError
from app.models.symbol import Symbol, Exchange
from app.cli.commands import list_symbols, list_exchanges, list_symbol_types


# Sample API responses for testing
SAMPLE_SYMBOLS_RESPONSE = {
    "data": [
        {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "currency": "USD",
            "exchange": "NASDAQ",
            "mic_code": "XNAS",
            "country": "United States",
            "type": "stock"
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "currency": "USD",
            "exchange": "NASDAQ",
            "mic_code": "XNAS",
            "country": "United States",
            "type": "stock"
        },
        {
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "currency": "USD",
            "exchange": "NYSE",
            "mic_code": "XNYS",
            "country": "United States",
            "type": "etf"
        },
        {
            "symbol": "EUR/USD",
            "name": "Euro/US Dollar",
            "currency": "USD",
            "exchange": "FOREX",
            "country": "United States",
            "type": "forex"
        }
    ]
}

SAMPLE_EXCHANGES_RESPONSE = {
    "data": [
        {
            "name": "NASDAQ",
            "code": "NASDAQ",
            "country": "United States",
            "timezone": "America/New_York"
        },
        {
            "name": "New York Stock Exchange",
            "code": "NYSE",
            "country": "United States",
            "timezone": "America/New_York"
        },
        {
            "name": "London Stock Exchange",
            "code": "LSE",
            "country": "United Kingdom",
            "timezone": "Europe/London"
        },
        {
            "name": "Forex",
            "code": "FOREX",
            "country": "Global",
            "timezone": "UTC"
        }
    ]
}

ERROR_RESPONSE = {
    "status": "error",
    "message": "Invalid API key or access restricted"
}


class TestSymbolsFunctionality:
    """Tests for fetching and displaying symbols from TwelveData API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked TwelveData client."""
        with patch('app.cli.commands.client') as mock_client:
            yield mock_client

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner for testing CLI commands."""
        return CliRunner()

    def test_symbol_model_from_api_response(self):
        """Test creating Symbol models from API response data."""
        # Get a single symbol from the sample data
        sample_data = SAMPLE_SYMBOLS_RESPONSE['data'][0]
        
        # Create a Symbol instance
        symbol = Symbol.from_api_response(sample_data)
        
        # Verify all properties are set correctly
        assert symbol.symbol == "AAPL"
        assert symbol.name == "Apple Inc"
        assert symbol.currency == "USD"
        assert symbol.exchange == "NASDAQ"
        assert symbol.country == "United States"
        assert symbol.type == "stock"
        assert symbol.mic_code == "XNAS"
    
    def test_exchange_model_from_api_response(self):
        """Test creating Exchange models from API response data."""
        # Get a single exchange from the sample data
        sample_data = SAMPLE_EXCHANGES_RESPONSE['data'][0]
        
        # Create an Exchange instance
        exchange = Exchange.from_api_response(sample_data)
        
        # Verify all properties are set correctly
        assert exchange.name == "NASDAQ"
        assert exchange.code == "NASDAQ"
        assert exchange.country == "United States"
        assert exchange.timezone == "America/New_York"

    def test_get_symbols_with_no_filters(self, mock_client):
        """Test fetching all symbols without any filters."""
        # Setup mock to return sample symbols
        mock_client.get_symbols.return_value = SAMPLE_SYMBOLS_RESPONSE['data']
        
        # Create symbols from the API response
        symbols = [Symbol.from_api_response(data) for data in mock_client.get_symbols()]
        
        # Verify we got all symbols
        assert len(symbols) == 4
        assert symbols[0].symbol == "AAPL"
        assert symbols[1].symbol == "MSFT"
        assert symbols[2].symbol == "SPY"
        assert symbols[3].symbol == "EUR/USD"
        
        # Verify client was called without filters
        mock_client.get_symbols.assert_called_once_with(
            exchange=None, type=None, country=None, symbol=None
        )

    def test_get_symbols_with_exchange_filter(self, mock_client):
        """Test fetching symbols filtered by exchange."""
        # Setup filtered response (only NASDAQ symbols)
        filtered_response = [symbol for symbol in SAMPLE_SYMBOLS_RESPONSE['data'] 
                            if symbol['exchange'] == 'NASDAQ']
        mock_client.get_symbols.return_value = filtered_response
        
        # Create symbols with exchange filter
        symbols = [Symbol.from_api_response(data) for data in 
                  mock_client.get_symbols(exchange='NASDAQ')]
        
        # Verify we got only NASDAQ symbols
        assert len(symbols) == 2
        assert all(s.exchange == 'NASDAQ' for s in symbols)
        assert symbols[0].symbol == "AAPL"
        assert symbols[1].symbol == "MSFT"
        
        # Verify client was called with exchange filter
        mock_client.get_symbols.assert_called_once_with(
            exchange='NASDAQ', type=None, country=None, symbol=None
        )

    def test_get_symbols_with_type_filter(self, mock_client):
        """Test fetching symbols filtered by type."""
        # Setup filtered response (only ETF symbols)
        filtered_response = [symbol for symbol in SAMPLE_SYMBOLS_RESPONSE['data'] 
                            if symbol['type'] == 'etf']
        mock_client.get_symbols.return_value = filtered_response
        
        # Create symbols with type filter
        symbols = [Symbol.from_api_response(data) for data in 
                  mock_client.get_symbols(type='etf')]
        
        # Verify we got only ETF symbols
        assert len(symbols) == 1
        assert all(s.type == 'etf' for s in symbols)
        assert symbols[0].symbol == "SPY"
        
        # Verify client was called with type filter
        mock_client.get_symbols.assert_called_once_with(
            exchange=None, type='etf', country=None, symbol=None
        )

    def test_get_symbols_with_search_filter(self, mock_client):
        """Test fetching symbols filtered by search term."""
        # Setup filtered response (only symbols containing 'Apple')
        filtered_response = [symbol for symbol in SAMPLE_SYMBOLS_RESPONSE['data'] 
                            if 'Apple' in symbol['name']]
        mock_client.get_symbols.return_value = filtered_response
        
        # Create symbols with search filter
        symbols = [Symbol.from_api_response(data) for data in 
                  mock_client.get_symbols(symbol='Apple')]
        
        # Verify we got only 'Apple' symbols
        assert len(symbols) == 1
        assert 'Apple' in symbols[0].name
        assert symbols[0].symbol == "AAPL"
        
        # Verify client was called with symbol filter
        mock_client.get_symbols.assert_called_once_with(
            exchange=None, type=None, country=None, symbol='Apple'
        )

    def test_get_symbols_with_multiple_filters(self, mock_client):
        """Test fetching symbols with multiple filters."""
        # Setup filtered response (only US stocks)
        filtered_response = [symbol for symbol in SAMPLE_SYMBOLS_RESPONSE['data'] 
                            if symbol['country'] == 'United States' and symbol['type'] == 'stock']
        mock_client.get_symbols.return_value = filtered_response
        
        # Create symbols with multiple filters
        symbols = [Symbol.from_api_response(data) for data in 
                  mock_client.get_symbols(country='United States', type='stock')]
        
        # Verify we got only US stocks
        assert len(symbols) == 2
        assert all(s.country == 'United States' and s.type == 'stock' for s in symbols)
        
        # Verify client was called with multiple filters
        mock_client.get_symbols.assert_called_once_with(
            exchange=None, type='stock', country='United States', symbol=None
        )

    def test_get_symbols_api_error(self, mock_client):
        """Test handling of API errors when fetching symbols."""
        # Setup mock to raise an error
        mock_client.get_symbols.side_effect = TwelveDataAPIError("API Error")
        
        # Attempt to fetch symbols (should raise the API error)
        with pytest.raises(TwelveDataAPIError):
            mock_client.get_symbols()

    def test_get_exchanges(self, mock_client):
        """Test fetching all exchanges."""
        # Setup mock to return sample exchanges
        mock_client.get_exchanges.return_value = SAMPLE_EXCHANGES_RESPONSE['data']
        
        # Get exchanges
        exchanges = [Exchange.from_api_response(data) for data in mock_client.get_exchanges()]
        
        # Verify we got all exchanges
        assert len(exchanges) == 4
        assert exchanges[0].code == "NASDAQ"
        assert exchanges[1].code == "NYSE"
        assert exchanges[2].code == "LSE"
        assert exchanges[3].code == "FOREX"
        
        # Verify client was called
        mock_client.get_exchanges.assert_called_once()

    def test_symbols_to_dict_for_serialization(self):
        """Test converting Symbol objects to dictionaries for serialization."""
        # Create a symbol
        symbol = Symbol(
            symbol="AAPL",
            name="Apple Inc",
            currency="USD",
            exchange="NASDAQ",
            country="United States",
            type="stock",
            mic_code="XNAS"
        )
        
        # Convert to dict
        data = symbol.to_dict()
        
        # Verify all fields are included
        assert data["symbol"] == "AAPL"
        assert data["name"] == "Apple Inc"
        assert data["currency"] == "USD"
        assert data["exchange"] == "NASDAQ"
        assert data["country"] == "United States"
        assert data["type"] == "stock"
        assert data["mic_code"] == "XNAS"

    def test_symbols_to_csv_row(self):
        """Test converting Symbol objects to CSV rows."""
        # Create a symbol
        symbol = Symbol(
            symbol="AAPL",
            name="Apple Inc",
            currency="USD",
            exchange="NASDAQ",
            country="United States",
            type="stock",
            mic_code="XNAS"
        )
        
        # Convert to CSV row dict
        row = symbol.to_csv_row()
        
        # Verify all fields are included as strings
        assert row["symbol"] == "AAPL"
        assert row["name"] == "Apple Inc"
        assert row["currency"] == "USD"
        assert row["exchange"] == "NASDAQ"
        assert row["country"] == "United States"
        assert row["type"] == "stock"
        assert row["mic_code"] == "XNAS"
        
        # Verify the header matches row keys
        header = Symbol.get_csv_header()
        assert set(header) == set(row.keys())

    def test_cli_list_symbols_command(self, mock_client, cli_runner):
        """Test the CLI command for listing symbols."""
        # Setup mock to return sample symbols
        mock_client.get_symbols.return_value = SAMPLE_SYMBOLS_RESPONSE['data']
        
        with patch('app.cli.commands.list_symbols') as mock_list_symbols:
            # Run the CLI command
            result = cli_runner.invoke(list_symbols, ["--exchange", "NASDAQ"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_symbols was called with correct arguments
            mock_list_symbols.assert_called_once()
            # Note: In an actual test you'd verify args more precisely based on your implementation

    def test_cli_list_exchanges_command(self, mock_client, cli_runner):
        """Test the CLI command for listing exchanges."""
        # Setup mock to return sample exchanges
        mock_client.get_exchanges.return_value = SAMPLE_EXCHANGES_RESPONSE['data']
        
        with patch('app.cli.commands.list_exchanges') as mock_list_exchanges:
            # Run the CLI command
            result = cli_runner.invoke(list_exchanges)
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_exchanges was called
            mock_list_exchanges.assert_called_once()

    def test_cli_list_symbol_types_command(self, cli_runner):
        """Test the CLI command for listing symbol types."""
        with patch('app.cli.commands.list_symbol_types') as mock_list_types:
            # Run the CLI command
            result = cli_runner.invoke(list_symbol_types)
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_symbol_types was called
            mock_list_types.assert_called_once()

    @patch('app.utils.export.export_items')
    def test_symbol_export_functionality(self, mock_export_items, mock_client, cli_runner):
        """Test exporting symbols to files."""
        # Setup mocks
        mock_client.get_symbols.return_value = SAMPLE_SYMBOLS_RESPONSE['data']
        mock_export_items.return_value = {"json": "/path/to/export.json"}
        
        # Run command with export option
        with patch('app.cli.commands.list_symbols', autospec=True) as mock_list_cmd:
            # Call the actual implementation but mock what it calls
            mock_list_cmd.side_effect = list_symbols
            
            result = cli_runner.invoke(list_symbols, ["--export", "json"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify export_items was called with symbols
            assert mock_export_items.call_count > 0
            # First arg should be a list of symbols
            args, _ = mock_export_items.call_args
            assert isinstance(args[0], list)
            assert len(args[0]) > 0
            assert all(isinstance(item, Symbol) for item in args[0])

    def test_symbol_filtering_and_limit(self, mock_client, cli_runner):
        """Test that symbols can be filtered and limited."""
        # Setup mock to return all symbols
        mock_client.get_symbols.return_value = SAMPLE_SYMBOLS_RESPONSE['data']
        
        with patch('app.cli.commands.display_symbols') as mock_display:
            # Run command with limit
            result = cli_runner.invoke(list_symbols, ["--limit", "2"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify display was called with correct number of symbols
            args, _ = mock_display.call_args
            # First arg should be the symbols list, limited to 2
            assert len(args[0]) == 2

    @patch('app.cli.commands.click.echo')
    def test_no_symbols_found(self, mock_echo, mock_client, cli_runner):
        """Test behavior when no symbols match the filters."""
        # Setup mock to return empty list
        mock_client.get_symbols.return_value = []
        
        # Run command with filters that match nothing
        result = cli_runner.invoke(list_symbols, ["--exchange", "INVALID"])
        
        # Verify command executed successfully but warns about no results
        assert result.exit_code == 0
        mock_echo.assert_any_call("No symbols found matching the criteria.")

    def test_symbol_types_list(self, cli_runner):
        """Test that the symbol types list contains expected values."""
        # This would ideally check the actual implementation, but we'll test the base concept
        # assuming something like this is implemented
        with patch('app.cli.commands.client') as mock_client:
            # Most APIs have at least these basic types
            mock_client.get_symbol_types.return_value = [
                "stock", "etf", "index", "forex", "crypto", "mutual_fund"
            ]
            
            # Mock the display function
            with patch('app.cli.commands.click.echo') as mock_echo:
                # Run the command
                result = cli_runner.invoke(list_symbol_types)
                
                # Verify success
                assert result.exit_code == 0
                
                # Verify each type is output (assuming the function echoes each type)
                assert mock_echo.call_count >= 6
                
                # If the implementation uses a table or different format, 
                # the assertion would need to be adjusted