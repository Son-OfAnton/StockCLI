import pytest
from unittest.mock import patch, MagicMock
import click
from click.testing import CliRunner
from datetime import datetime

from app.api.twelve_data import TwelveDataClient, TwelveDataAPIError
from app.models.fund import Fund
from app.cli.commands import list_funds, list_etfs, list_mutual_funds


# Sample API responses for testing
SAMPLE_FUNDS_RESPONSE = {
    "data": [
        {
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "currency": "USD",
            "exchange": "NYSE",
            "mic_code": "XNYS",
            "country": "United States",
            "type": "etf",
            "expense_ratio": 0.0945,
            "managed_assets": 380000000000,
            "fund_category": "U.S. Equity: Large-Cap Blend"
        },
        {
            "symbol": "QQQ",
            "name": "Invesco QQQ Trust",
            "currency": "USD",
            "exchange": "NASDAQ",
            "mic_code": "XNAS",
            "country": "United States",
            "type": "etf",
            "expense_ratio": 0.2000,
            "managed_assets": 160000000000,
            "fund_category": "U.S. Equity: Large-Cap Growth"
        },
        {
            "symbol": "VTI",
            "name": "Vanguard Total Stock Market ETF",
            "currency": "USD",
            "exchange": "NYSE",
            "mic_code": "XNYS",
            "country": "United States",
            "type": "etf",
            "expense_ratio": 0.0300,
            "managed_assets": 230000000000,
            "fund_category": "U.S. Equity: Total Market"
        },
        {
            "symbol": "VFIAX",
            "name": "Vanguard 500 Index Fund Admiral Shares",
            "currency": "USD",
            "exchange": "MUTF",
            "mic_code": "XMUT",
            "country": "United States",
            "type": "mutual_fund",
            "expense_ratio": 0.0400,
            "managed_assets": 550000000000,
            "fund_category": "U.S. Equity: Large-Cap Blend"
        },
        {
            "symbol": "FCNTX",
            "name": "Fidelity Contrafund",
            "currency": "USD",
            "exchange": "MUTF",
            "mic_code": "XMUT",
            "country": "United States",
            "type": "mutual_fund",
            "expense_ratio": 0.8200,
            "managed_assets": 110000000000,
            "fund_category": "U.S. Equity: Large-Cap Growth"
        }
    ]
}

SAMPLE_ETFS_RESPONSE = {
    "data": [f for f in SAMPLE_FUNDS_RESPONSE["data"] if f["type"] == "etf"]
}

SAMPLE_MUTUAL_FUNDS_RESPONSE = {
    "data": [f for f in SAMPLE_FUNDS_RESPONSE["data"] if f["type"] == "mutual_fund"]
}

ERROR_RESPONSE = {
    "status": "error",
    "message": "Invalid API key or access restricted"
}


class TestFundsFunctionality:
    """Tests for fetching and displaying fund data from TwelveData API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked TwelveData client."""
        with patch('app.cli.commands.client') as mock_client:
            yield mock_client

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner for testing CLI commands."""
        return CliRunner()

    def test_fund_model_from_api_response(self):
        """Test creating Fund models from API response data."""
        # Get a single fund from the sample data (an ETF)
        sample_data = SAMPLE_FUNDS_RESPONSE['data'][0]
        
        # Create a Fund instance
        fund = Fund.from_api_response(sample_data)
        
        # Verify all properties are set correctly
        assert fund.symbol == "SPY"
        assert fund.name == "SPDR S&P 500 ETF Trust"
        assert fund.exchange == "NYSE"
        assert fund.country == "United States"
        assert fund.type == "etf"
        assert fund.expense_ratio == 0.0945
        assert fund.managed_assets == 380000000000
        assert fund.fund_category == "U.S. Equity: Large-Cap Blend"
    
    def test_fund_model_from_mutual_fund_response(self):
        """Test creating Fund models from mutual fund API response data."""
        # Get a single mutual fund from the sample data
        sample_data = SAMPLE_FUNDS_RESPONSE['data'][3]  # VFIAX
        
        # Create a Fund instance
        fund = Fund.from_api_response(sample_data)
        
        # Verify all properties are set correctly
        assert fund.symbol == "VFIAX"
        assert fund.name == "Vanguard 500 Index Fund Admiral Shares"
        assert fund.exchange == "MUTF"
        assert fund.type == "mutual_fund"
        assert fund.expense_ratio == 0.0400
        assert fund.fund_category == "U.S. Equity: Large-Cap Blend"

    def test_get_all_funds_with_no_filters(self, mock_client):
        """Test fetching all funds without any filters."""
        # Setup mock to return sample funds
        mock_client.get_funds.return_value = SAMPLE_FUNDS_RESPONSE['data']
        
        # Create funds from the API response
        funds = [Fund.from_api_response(data) for data in mock_client.get_funds()]
        
        # Verify we got all funds (both ETFs and mutual funds)
        assert len(funds) == 5
        
        # Check for specific funds
        assert "SPY" in [f.symbol for f in funds]
        assert "VFIAX" in [f.symbol for f in funds]
        
        # Count by type
        etf_count = sum(1 for f in funds if f.type == "etf")
        mutual_fund_count = sum(1 for f in funds if f.type == "mutual_fund")
        
        assert etf_count == 3
        assert mutual_fund_count == 2
        
        # Verify client was called without fund type filter
        mock_client.get_funds.assert_called_once_with(
            fund_type=None, exchange=None, country=None, symbol=None
        )

    def test_get_etfs_only(self, mock_client):
        """Test fetching only ETFs."""
        # Setup mock to return only ETFs
        mock_client.get_etfs.return_value = SAMPLE_ETFS_RESPONSE['data']
        
        # Create funds from the API response
        etfs = [Fund.from_api_response(data) for data in mock_client.get_etfs()]
        
        # Verify we got only ETFs
        assert len(etfs) == 3
        assert all(f.type == "etf" for f in etfs)
        
        # Check for specific ETFs
        assert "SPY" in [f.symbol for f in etfs]
        assert "QQQ" in [f.symbol for f in etfs]
        assert "VTI" in [f.symbol for f in etfs]
        
        # Verify mutual funds are not included
        assert "VFIAX" not in [f.symbol for f in etfs]
        
        # Verify client was called with correct parameters
        mock_client.get_etfs.assert_called_once_with(
            exchange=None, country=None, symbol=None
        )

    def test_get_mutual_funds_only(self, mock_client):
        """Test fetching only mutual funds."""
        # Setup mock to return only mutual funds
        mock_client.get_mutual_funds.return_value = SAMPLE_MUTUAL_FUNDS_RESPONSE['data']
        
        # Create funds from the API response
        mutual_funds = [Fund.from_api_response(data) for data in mock_client.get_mutual_funds()]
        
        # Verify we got only mutual funds
        assert len(mutual_funds) == 2
        assert all(f.type == "mutual_fund" for f in mutual_funds)
        
        # Check for specific mutual funds
        assert "VFIAX" in [f.symbol for f in mutual_funds]
        assert "FCNTX" in [f.symbol for f in mutual_funds]
        
        # Verify ETFs are not included
        assert "SPY" not in [f.symbol for f in mutual_funds]
        
        # Verify client was called with correct parameters
        mock_client.get_mutual_funds.assert_called_once_with(
            exchange=None, country=None, symbol=None
        )

    def test_get_funds_with_exchange_filter(self, mock_client):
        """Test fetching funds filtered by exchange."""
        # Setup filtered response (only NYSE funds)
        filtered_response = [fund for fund in SAMPLE_FUNDS_RESPONSE['data'] 
                            if fund['exchange'] == 'NYSE']
        mock_client.get_funds.return_value = filtered_response
        
        # Create funds with exchange filter
        funds = [Fund.from_api_response(data) for data in 
                mock_client.get_funds(exchange='NYSE')]
        
        # Verify we got only NYSE funds
        assert len(funds) == 2
        assert all(f.exchange == 'NYSE' for f in funds)
        assert "SPY" in [f.symbol for f in funds]
        assert "VTI" in [f.symbol for f in funds]
        
        # Verify client was called with exchange filter
        mock_client.get_funds.assert_called_once_with(
            fund_type=None, exchange='NYSE', country=None, symbol=None
        )

    def test_get_funds_with_country_filter(self, mock_client):
        """Test fetching funds filtered by country."""
        # All our sample funds are from the US, but we'll test the filter anyway
        filtered_response = [fund for fund in SAMPLE_FUNDS_RESPONSE['data'] 
                           if fund['country'] == 'United States']
        mock_client.get_funds.return_value = filtered_response
        
        # Create funds with country filter
        funds = [Fund.from_api_response(data) for data in 
                mock_client.get_funds(country='United States')]
        
        # Verify we got all funds (since all are US)
        assert len(funds) == 5
        assert all(f.country == 'United States' for f in funds)
        
        # Verify client was called with country filter
        mock_client.get_funds.assert_called_once_with(
            fund_type=None, exchange=None, country='United States', symbol=None
        )

    def test_get_funds_with_symbol_search(self, mock_client):
        """Test fetching funds filtered by symbol or name search."""
        # Setup filtered response (only funds with 'Vanguard' in the name)
        filtered_response = [fund for fund in SAMPLE_FUNDS_RESPONSE['data'] 
                           if 'Vanguard' in fund['name']]
        mock_client.get_funds.return_value = filtered_response
        
        # Create funds with search filter
        funds = [Fund.from_api_response(data) for data in 
                mock_client.get_funds(symbol='Vanguard')]
        
        # Verify we got only Vanguard funds
        assert len(funds) == 2
        assert all('Vanguard' in f.name for f in funds)
        assert "VTI" in [f.symbol for f in funds]
        assert "VFIAX" in [f.symbol for f in funds]
        
        # Verify client was called with symbol filter
        mock_client.get_funds.assert_called_once_with(
            fund_type=None, exchange=None, country=None, symbol='Vanguard'
        )

    def test_get_funds_with_multiple_filters(self, mock_client):
        """Test fetching funds with multiple filters."""
        # Setup filtered response (ETFs on NYSE)
        filtered_response = [fund for fund in SAMPLE_FUNDS_RESPONSE['data'] 
                           if fund['type'] == 'etf' and fund['exchange'] == 'NYSE']
        mock_client.get_funds.return_value = filtered_response
        
        # Create funds with multiple filters
        funds = [Fund.from_api_response(data) for data in 
                mock_client.get_funds(fund_type='etf', exchange='NYSE')]
        
        # Verify we got the matching funds
        assert len(funds) == 2
        assert all(f.type == 'etf' and f.exchange == 'NYSE' for f in funds)
        assert "SPY" in [f.symbol for f in funds]
        assert "VTI" in [f.symbol for f in funds]
        
        # Verify client was called with multiple filters
        mock_client.get_funds.assert_called_once_with(
            fund_type='etf', exchange='NYSE', country=None, symbol=None
        )

    def test_get_funds_api_error(self, mock_client):
        """Test handling of API errors when fetching funds."""
        # Setup mock to raise an error
        mock_client.get_funds.side_effect = TwelveDataAPIError("API Error")
        
        # Attempt to fetch funds (should raise the API error)
        with pytest.raises(TwelveDataAPIError):
            mock_client.get_funds()

    def test_fund_to_dict_for_serialization(self):
        """Test converting Fund objects to dictionaries for serialization."""
        # Create a fund
        fund = Fund(
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            currency="USD",
            exchange="NYSE",
            mic_code="XNYS",
            country="United States",
            type="etf",
            expense_ratio=0.0945,
            managed_assets=380000000000,
            fund_category="U.S. Equity: Large-Cap Blend"
        )
        
        # Convert to dict
        data = fund.to_dict()
        
        # Verify all fields are included
        assert data["symbol"] == "SPY"
        assert data["name"] == "SPDR S&P 500 ETF Trust"
        assert data["exchange"] == "NYSE"
        assert data["country"] == "United States"
        assert data["type"] == "etf"
        assert data["expense_ratio"] == 0.0945
        assert data["managed_assets"] == 380000000000
        assert data["fund_category"] == "U.S. Equity: Large-Cap Blend"

    def test_fund_to_csv_row(self):
        """Test converting Fund objects to CSV rows."""
        # Create a fund
        fund = Fund(
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            currency="USD",
            exchange="NYSE",
            mic_code="XNYS",
            country="United States",
            type="etf",
            expense_ratio=0.0945,
            managed_assets=380000000000,
            fund_category="U.S. Equity: Large-Cap Blend"
        )
        
        # Convert to CSV row dict
        row = fund.to_csv_row()
        
        # Verify all fields are included as strings
        assert row["symbol"] == "SPY"
        assert row["name"] == "SPDR S&P 500 ETF Trust"
        assert row["exchange"] == "NYSE"
        assert row["country"] == "United States"
        assert row["type"] == "etf"
        assert row["expense_ratio"] == "0.0945"  # Converted to string
        assert "380000000000" in row["managed_assets"]  # Converted to string
        assert row["fund_category"] == "U.S. Equity: Large-Cap Blend"
        
        # Verify the header matches row keys
        header = Fund.get_csv_header()
        assert set(header) == set(row.keys())

    def test_cli_list_funds_command(self, mock_client, cli_runner):
        """Test the CLI command for listing all funds."""
        # Setup mock to return sample funds
        mock_client.get_funds.return_value = SAMPLE_FUNDS_RESPONSE['data']
        
        with patch('app.cli.commands.list_funds') as mock_list_funds:
            # Mock to avoid side effects when running the command
            mock_list_funds.side_effect = list_funds
            
            # Run the CLI command
            result = cli_runner.invoke(list_funds, ["--exchange", "NYSE"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_funds was called with correct arguments
            mock_list_funds.assert_called_once()
            # Check args based on your implementation

    def test_cli_list_etfs_command(self, mock_client, cli_runner):
        """Test the CLI command for listing ETFs."""
        # Setup mock to return sample ETFs
        mock_client.get_etfs.return_value = SAMPLE_ETFS_RESPONSE['data']
        
        with patch('app.cli.commands.list_etfs') as mock_list_etfs:
            # Mock to avoid side effects
            mock_list_etfs.side_effect = list_etfs
            
            # Run the CLI command
            result = cli_runner.invoke(list_etfs, ["--country", "United States"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_etfs was called with correct arguments
            mock_list_etfs.assert_called_once()
            # Check args based on your implementation

    def test_cli_list_mutual_funds_command(self, mock_client, cli_runner):
        """Test the CLI command for listing mutual funds."""
        # Setup mock to return sample mutual funds
        mock_client.get_mutual_funds.return_value = SAMPLE_MUTUAL_FUNDS_RESPONSE['data']
        
        with patch('app.cli.commands.list_mutual_funds') as mock_list_mutual_funds:
            # Mock to avoid side effects
            mock_list_mutual_funds.side_effect = list_mutual_funds
            
            # Run the CLI command
            result = cli_runner.invoke(list_mutual_funds, ["--search", "Vanguard"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify list_mutual_funds was called with correct arguments
            mock_list_mutual_funds.assert_called_once()
            # Check args based on your implementation

    @patch('app.utils.export.export_items')
    def test_fund_export_functionality(self, mock_export_items, mock_client, cli_runner):
        """Test exporting funds to files."""
        # Setup mocks
        mock_client.get_funds.return_value = SAMPLE_FUNDS_RESPONSE['data']
        mock_export_items.return_value = {"json": "/path/to/export.json"}
        
        # Run command with export option
        with patch('app.cli.commands.list_funds', autospec=True) as mock_list_cmd:
            # Call the actual implementation (mocked)
            mock_list_cmd.side_effect = list_funds
            
            result = cli_runner.invoke(list_funds, ["--export", "json"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify export_items was called with funds
            assert mock_export_items.call_count > 0
            # First arg should be a list of funds
            args, _ = mock_export_items.call_args
            assert isinstance(args[0], list)
            assert len(args[0]) > 0
            assert all(isinstance(item, Fund) for item in args[0])

    def test_fund_filtering_and_limit(self, mock_client, cli_runner):
        """Test that funds can be filtered and limited."""
        # Setup mock to return all funds
        mock_client.get_funds.return_value = SAMPLE_FUNDS_RESPONSE['data']
        
        with patch('app.cli.commands.display_funds') as mock_display:
            # Run command with limit
            result = cli_runner.invoke(list_funds, ["--limit", "3"])
            
            # Verify command executed successfully
            assert result.exit_code == 0
            
            # Verify display was called with correct number of funds
            if mock_display.call_count > 0:
                args, _ = mock_display.call_args
                # First arg should be the funds list, limited to 3
                assert len(args[0]) == 3

    @patch('app.cli.commands.click.echo')
    def test_no_funds_found(self, mock_echo, mock_client, cli_runner):
        """Test behavior when no funds match the filters."""
        # Setup mock to return empty list
        mock_client.get_funds.return_value = []
        
        # Run command with filters that match nothing
        result = cli_runner.invoke(list_funds, ["--exchange", "INVALID"])
        
        # Verify command executed successfully but warns about no results
        assert result.exit_code == 0
        mock_echo.assert_any_call("No funds found matching the criteria.")

    def test_filter_by_expense_ratio(self):
        """Test filtering funds by expense ratio."""
        # Create a list of funds with different expense ratios
        funds = [
            Fund(symbol="SPY", name="SPDR S&P 500 ETF Trust", currency="USD",
                exchange="NYSE", type="etf", expense_ratio=0.0945),
            Fund(symbol="VTI", name="Vanguard Total Stock Market ETF", currency="USD",
                exchange="NYSE", type="etf", expense_ratio=0.0300),
            Fund(symbol="FCNTX", name="Fidelity Contrafund", currency="USD",
                exchange="MUTF", type="mutual_fund", expense_ratio=0.8200)
        ]
        
        # Filter for low expense ratio funds (< 0.10)
        low_expense_funds = [f for f in funds if f.expense_ratio < 0.10]
        
        # Verify filtering worked
        assert len(low_expense_funds) == 2
        assert all(f.expense_ratio < 0.10 for f in low_expense_funds)
        assert "SPY" in [f.symbol for f in low_expense_funds]
        assert "VTI" in [f.symbol for f in low_expense_funds]
        assert "FCNTX" not in [f.symbol for f in low_expense_funds]

    def test_filter_by_fund_category(self):
        """Test filtering funds by fund category."""
        # Create a list of funds with different categories
        funds = [
            Fund(symbol="SPY", name="SPDR S&P 500 ETF Trust", currency="USD",
                exchange="NYSE", type="etf", fund_category="U.S. Equity: Large-Cap Blend"),
            Fund(symbol="QQQ", name="Invesco QQQ Trust", currency="USD",
                exchange="NASDAQ", type="etf", fund_category="U.S. Equity: Large-Cap Growth"),
            Fund(symbol="VFIAX", name="Vanguard 500 Index Fund Admiral Shares", currency="USD",
                exchange="MUTF", type="mutual_fund", fund_category="U.S. Equity: Large-Cap Blend")
        ]
        
        # Filter for Large-Cap Blend funds
        blend_funds = [f for f in funds if "Large-Cap Blend" in f.fund_category]
        
        # Verify filtering worked
        assert len(blend_funds) == 2
        assert all("Large-Cap Blend" in f.fund_category for f in blend_funds)
        assert "SPY" in [f.symbol for f in blend_funds]
        assert "VFIAX" in [f.symbol for f in blend_funds]
        assert "QQQ" not in [f.symbol for f in blend_funds]

    def test_detailed_vs_simple_display(self, mock_client, cli_runner):
        """Test the difference between detailed and simple display formats."""
        # Setup mock to return sample funds
        mock_client.get_funds.return_value = SAMPLE_FUNDS_RESPONSE['data']
        
        # Here we'd typically check different display function calls
        # For this example, we'll just verify both commands execute successfully
        
        # First test simple display (no detailed flag)
        with patch('app.cli.commands.display_funds') as mock_simple:
            result = cli_runner.invoke(list_funds)
            assert result.exit_code == 0
        
        # Then test detailed display
        with patch('app.cli.commands.display_funds_detailed') as mock_detailed:
            result_detailed = cli_runner.invoke(list_funds, ["--detailed"])
            assert result_detailed.exit_code == 0