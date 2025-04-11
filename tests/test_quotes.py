import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.api.twelve_data import TwelveDataClient, TwelveDataAPIError
from app.models.stock import Quote
from app.cli.commands import fetch_and_display_quotes


# Sample API responses for testing
SAMPLE_SINGLE_QUOTE = {
    "symbol": "AAPL",
    "name": "Apple Inc",
    "exchange": "NASDAQ",
    "currency": "USD",
    "datetime": "2025-04-11 09:00:00",
    "open": "175.50",
    "high": "178.25",
    "low": "175.00",
    "close": "177.80",
    "volume": "35240500",
    "previous_close": "176.25",
    "change": "1.55",
    "percent_change": "0.88",
    "fifty_two_week_high": "198.23",
    "fifty_two_week_low": "142.10"
}

SAMPLE_MULTIPLE_QUOTES = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc",
        "exchange": "NASDAQ",
        "currency": "USD",
        "datetime": "2025-04-11 09:00:00",
        "open": "175.50",
        "high": "178.25",
        "low": "175.00",
        "close": "177.80",
        "volume": "35240500",
        "previous_close": "176.25",
        "change": "1.55",
        "percent_change": "0.88"
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "datetime": "2025-04-11 09:00:00",
        "open": "420.30",
        "high": "425.15",
        "low": "418.75",
        "close": "423.80",
        "volume": "18750200",
        "previous_close": "421.20",
        "change": "2.60",
        "percent_change": "0.62"
    }
]

ERROR_RESPONSE = {
    "status": "error",
    "message": "Invalid API key or access restricted"
}

MALFORMED_RESPONSE = {
    "some_unexpected_field": "unexpected value"
}


class TestStockQuotes:
    """Tests for retrieving stock quotes from TwelveData API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked TwelveData client."""
        with patch('app.cli.commands.client') as mock_client:
            yield mock_client

    @pytest.fixture
    def mock_display(self):
        """Mock the display_quotes_table function."""
        with patch('app.cli.commands.display_quotes_table') as mock_display:
            yield mock_display

    def test_quote_model_from_api_response_single(self):
        """Test creating a Quote model from a single API response."""
        quote = Quote.from_api_response(SAMPLE_SINGLE_QUOTE)
        
        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc"
        assert quote.price == 177.80
        assert quote.change == 1.55
        assert quote.change_percent == 0.88
        assert quote.currency == "USD"
        assert quote.volume == 35240500
        assert quote.open_price == 175.50
        assert quote.high_price == 178.25
        assert quote.low_price == 175.00
        assert quote.previous_close == 176.25
        assert quote.fifty_two_week_high == 198.23
        assert quote.fifty_two_week_low == 142.10
        assert isinstance(quote.timestamp, datetime)

    def test_quote_model_to_dict(self):
        """Test converting a Quote model to dictionary for serialization."""
        quote = Quote.from_api_response(SAMPLE_SINGLE_QUOTE)
        data = quote.to_dict()
        
        assert data["symbol"] == "AAPL"
        assert data["price"] == 177.80
        assert data["change"] == 1.55
        assert data["change_percent"] == 0.88
        assert "timestamp" in data
        assert data["volume"] == 35240500

    def test_fetch_quotes_single_symbol_success(self, mock_client, mock_display):
        """Test fetching a single stock quote successfully."""
        # Setup mock client to return single quote
        mock_client.get_quotes.return_value = SAMPLE_SINGLE_QUOTE
        
        # Call the function to fetch quotes
        quotes = fetch_and_display_quotes(["AAPL"])
        
        # Verify the client was called with the right symbol
        mock_client.get_quotes.assert_called_once_with(["AAPL"])
        
        # Verify the display function was called
        mock_display.assert_called_once()
        
        # Check the returned quotes
        assert len(quotes) == 1
        assert quotes[0].symbol == "AAPL"
        assert quotes[0].price == 177.80

    def test_fetch_quotes_multiple_symbols_success(self, mock_client, mock_display):
        """Test fetching multiple stock quotes successfully."""
        # Setup mock to return multiple quotes
        mock_client.get_quotes.return_value = SAMPLE_MULTIPLE_QUOTES
        
        # Call the function to fetch quotes
        quotes = fetch_and_display_quotes(["AAPL", "MSFT"])
        
        # Verify the client was called with the right symbols
        mock_client.get_quotes.assert_called_once_with(["AAPL", "MSFT"])
        
        # Verify the display function was called
        mock_display.assert_called_once()
        
        # Check the returned quotes
        assert len(quotes) == 2
        assert quotes[0].symbol == "AAPL"
        assert quotes[1].symbol == "MSFT"

    def test_fetch_quotes_api_error(self, mock_client, mock_display, capsys):
        """Test behavior when the API returns an error."""
        # Setup mock to return an error
        mock_client.get_quotes.return_value = ERROR_RESPONSE
        
        # Call the function
        quotes = fetch_and_display_quotes(["AAPL"])
        
        # Verify the API was called
        mock_client.get_quotes.assert_called_once_with(["AAPL"])
        
        # Verify the display function was not called (no quotes to display)
        mock_display.assert_not_called()
        
        # Check that we got an empty list of quotes
        assert quotes == []
        
        # Verify error message was printed to console
        captured = capsys.readouterr()
        assert "API Error" in captured.out

    def test_fetch_quotes_api_exception(self, mock_client, mock_display, capsys):
        """Test behavior when the API client raises an exception."""
        # Setup mock to raise an exception
        mock_client.get_quotes.side_effect = TwelveDataAPIError("API connection failed")
        
        # Call the function
        quotes = fetch_and_display_quotes(["AAPL"])
        
        # Verify the API was called
        mock_client.get_quotes.assert_called_once_with(["AAPL"])
        
        # Verify the display function was not called (no quotes to display)
        mock_display.assert_not_called()
        
        # Check that we got an empty list of quotes
        assert quotes == []
        
        # Verify error message was printed to console
        captured = capsys.readouterr()
        assert "Error fetching quotes" in captured.out

    def test_fetch_quotes_malformed_response(self, mock_client, mock_display, capsys):
        """Test behavior with malformed API response."""
        # Setup mock to return malformed data
        mock_client.get_quotes.return_value = MALFORMED_RESPONSE
        
        # Call the function
        quotes = fetch_and_display_quotes(["AAPL"])
        
        # Verify the API was called
        mock_client.get_quotes.assert_called_once_with(["AAPL"])
        
        # Verify the display function was not called (no quotes to display)
        mock_display.assert_not_called()
        
        # Check that we got an empty list of quotes
        assert quotes == []
        
        # Verify error message was printed to console
        captured = capsys.readouterr()
        assert "No valid quotes found" in captured.out

    @patch('app.cli.commands._last_quotes')
    def test_fetch_quotes_updates_last_quotes(self, mock_last_quotes, mock_client, mock_display):
        """Test that successful quote fetching updates the _last_quotes variable."""
        # Setup mock to return single quote
        mock_client.get_quotes.return_value = SAMPLE_SINGLE_QUOTE
        mock_last_quotes.clear()  # Ensure it starts empty
        
        # Call the function
        quotes = fetch_and_display_quotes(["AAPL"])
        
        # Verify quotes were stored in the last_quotes variable
        assert len(quotes) == 1
        assert quotes[0] in mock_last_quotes

    def test_quote_model_handles_different_field_names(self):
        """Test that Quote model properly handles different field names used by the API."""
        # Some APIs use different field names for the same data
        variant_response = {
            "symbol": "AAPL",
            "price": "177.80",  # Instead of "close"
            "price_change": "1.55",  # Instead of "change"
            "change_percentage": "0.88",  # Instead of "percent_change"
            "datetime": "2025-04-11 09:00:00"
        }
        
        quote = Quote.from_api_response(variant_response)
        assert quote.symbol == "AAPL"
        assert quote.price == 177.80
        assert quote.change == 1.55
        assert quote.change_percent == 0.88

    def test_quote_model_handles_missing_optional_fields(self):
        """Test that Quote model properly handles missing optional fields."""
        minimal_response = {
            "symbol": "AAPL",
            "close": "177.80",
            "change": "1.55",
            "percent_change": "0.88",
            "datetime": "2025-04-11 09:00:00"
        }
        
        quote = Quote.from_api_response(minimal_response)
        assert quote.symbol == "AAPL"
        assert quote.price == 177.80
        assert quote.volume is None
        assert quote.name is None
        assert quote.open_price is None

    def test_quote_model_raises_error_on_missing_required_fields(self):
        """Test that Quote model raises error when required fields are missing."""
        invalid_response = {
            "symbol": "AAPL",
            # Missing price/close field
            "change": "1.55",
            "percent_change": "0.88",
            "datetime": "2025-04-11 09:00:00"
        }
        
        with pytest.raises(ValueError):
            Quote.from_api_response(invalid_response)