import pytest
import json
import csv
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

from app.models.stock import Quote
from app.utils.export import export_quotes, get_default_export_dir, get_home_export_dir


# Sample quote objects for testing exports
@pytest.fixture
def sample_quotes():
    now = datetime.now()
    
    quote1 = Quote(
        symbol="AAPL",
        price=177.80,
        change=1.55,
        change_percent=0.88,
        timestamp=now,
        volume=35240500,
        name="Apple Inc",
        currency="USD",
        open_price=175.50,
        high_price=178.25,
        low_price=175.00,
        previous_close=176.25,
        fifty_two_week_high=198.23,
        fifty_two_week_low=142.10
    )
    
    quote2 = Quote(
        symbol="MSFT",
        price=423.80,
        change=2.60,
        change_percent=0.62,
        timestamp=now - timedelta(minutes=2),  # Slightly older timestamp
        volume=18750200,
        name="Microsoft Corporation",
        currency="USD",
        open_price=420.30,
        high_price=425.15,
        low_price=418.75,
        previous_close=421.20
    )
    
    return [quote1, quote2]


class TestQuoteExports:
    """Tests for exporting stock quotes to JSON and CSV."""

    def test_get_default_export_dir(self):
        """Test that get_default_export_dir returns a valid path."""
        export_dir = get_default_export_dir()
        assert isinstance(export_dir, Path)
        assert "exports" in str(export_dir)
    
    def test_get_home_export_dir(self):
        """Test that get_home_export_dir returns a path in the home directory."""
        export_dir = get_home_export_dir()
        assert isinstance(export_dir, Path)
        assert str(Path.home()) in str(export_dir)
        assert "stockcli_exports" in str(export_dir)
    
    @pytest.fixture
    def mock_path_exists(self):
        """Mock Path.exists to return True for directory checks."""
        with patch('pathlib.Path.exists', return_value=True):
            yield
    
    @pytest.fixture
    def mock_path_mkdir(self):
        """Mock Path.mkdir to avoid actually creating directories."""
        with patch('pathlib.Path.mkdir'):
            yield
    
    def test_export_quotes_to_json(self, sample_quotes, mock_path_exists, mock_path_mkdir, tmp_path):
        """Test exporting quotes to JSON format."""
        # Use a temporary directory for the test
        export_dir = tmp_path
        
        # Mock open to capture file writes
        m = mock_open()
        
        with patch('builtins.open', m):
            # Call the export function with JSON format
            result = export_quotes(sample_quotes, ['json'], export_dir)
            
            # Verify function returned the expected result
            assert 'json' in result
            assert str(export_dir) in str(result['json'])
            assert any(s in str(result['json']) for s in ['AAPL', 'MSFT'])
            
            # Verify the file was opened for writing
            m.assert_called_once()
            
            # Get the write calls
            write_call = m().write.call_args[0][0]
            
            # Parse the JSON and check content
            json_data = json.loads(write_call)
            assert len(json_data) == 2
            assert json_data[0]['symbol'] == 'AAPL'
            assert json_data[1]['symbol'] == 'MSFT'
            assert json_data[0]['price'] == 177.80
    
    def test_export_quotes_to_csv(self, sample_quotes, mock_path_exists, mock_path_mkdir, tmp_path):
        """Test exporting quotes to CSV format."""
        # Use a temporary directory for the test
        export_dir = tmp_path
        
        with patch('builtins.open', mock_open()) as m, \
             patch('csv.DictWriter') as mock_csv_writer:
            # Setup the CSV writer mock
            mock_writer_instance = MagicMock()
            mock_csv_writer.return_value = mock_writer_instance
            
            # Call the export function with CSV format
            result = export_quotes(sample_quotes, ['csv'], export_dir)
            
            # Verify function returned the expected result
            assert 'csv' in result
            assert str(export_dir) in str(result['csv'])
            assert any(s in str(result['csv']) for s in ['AAPL', 'MSFT'])
            
            # Verify the file was opened for writing
            m.assert_called_once()
            
            # Verify CSV DictWriter was created with correct fieldnames
            fieldnames_arg = mock_csv_writer.call_args[1]['fieldnames']
            assert 'symbol' in fieldnames_arg
            assert 'price' in fieldnames_arg
            assert 'change' in fieldnames_arg
            assert 'timestamp' in fieldnames_arg
            
            # Verify writeheader and writerows were called
            mock_writer_instance.writeheader.assert_called_once()
            mock_writer_instance.writerows.assert_called_once()
            
            # Check the rows that were written
            rows_arg = mock_writer_instance.writerows.call_args[0][0]
            assert len(rows_arg) == 2
            assert rows_arg[0]['symbol'] == 'AAPL'
            assert rows_arg[1]['symbol'] == 'MSFT'
    
    def test_export_quotes_both_formats(self, sample_quotes, mock_path_exists, mock_path_mkdir):
        """Test exporting quotes to both JSON and CSV formats."""
        # Mock directory
        export_dir = Path("/mock/export/dir")
        
        # Mock both file open calls
        json_content = None
        csv_calls = []
        
        def side_effect(path, mode, **kwargs):
            nonlocal json_content, csv_calls
            mock_file = MagicMock()
            
            # Capture JSON content
            if str(path).endswith('.json'):
                def write_json(content):
                    nonlocal json_content
                    json_content = content
                mock_file.write.side_effect = write_json
            
            # For CSV, we'll track the filename
            if str(path).endswith('.csv'):
                csv_calls.append(str(path))
                
            return mock_file
        
        # Mock open and csv.DictWriter
        with patch('builtins.open', side_effect=side_effect), \
             patch('csv.DictWriter') as mock_csv_writer:
            # Setup the CSV writer mock
            mock_writer_instance = MagicMock()
            mock_csv_writer.return_value = mock_writer_instance
            
            # Call the export function with both formats
            result = export_quotes(sample_quotes, ['json', 'csv'], export_dir)
            
            # Verify function returned paths for both formats
            assert 'json' in result
            assert 'csv' in result
            
            # Check that both file paths were used
            assert str(result['json']).endswith('.json')
            assert str(result['csv']).endswith('.csv')
            
            # Verify JSON content was written
            assert json_content is not None
            
            # Verify CSV writer was used
            assert len(csv_calls) > 0
    
    def test_export_quotes_creates_directory(self, sample_quotes):
        """Test that the export function creates the output directory if it doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            # Create a subdirectory that doesn't exist yet
            export_dir = Path(temp_dir) / "new_subdir" / "exports"
            assert not export_dir.exists()
            
            # Export quotes
            result = export_quotes(sample_quotes, ['json'], export_dir)
            
            # Verify directory was created
            assert export_dir.exists()
            assert export_dir.is_dir()
            
            # Verify file was created
            json_path = Path(result['json'])
            assert json_path.exists()
            assert json_path.is_file()
            
            # Read and verify content
            with open(json_path, 'r') as f:
                content = json.load(f)
                assert len(content) == 2
                assert content[0]['symbol'] == 'AAPL'
                assert content[1]['symbol'] == 'MSFT'
    
    def test_export_quotes_empty_list(self, mock_path_exists, mock_path_mkdir):
        """Test behavior when trying to export an empty list of quotes."""
        export_dir = Path("/mock/export/dir")
        
        # Call with empty quotes list
        result = export_quotes([], ['json', 'csv'], export_dir)
        
        # Should return empty dict (no files created)
        assert result == {}
    
    @patch('app.utils.export.logger')
    def test_export_quotes_handles_errors(self, mock_logger, sample_quotes, mock_path_exists, mock_path_mkdir):
        """Test that export_quotes properly handles errors during export."""
        export_dir = Path("/mock/export/dir")
        
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Call the export function
            result = export_quotes(sample_quotes, ['json'], export_dir)
            
            # Verify function handled the error
            assert result == {}
            
            # Verify error was logged
            mock_logger.error.assert_called()
            assert "Error exporting quotes" in mock_logger.error.call_args[0][0]
    
    def test_export_quotes_with_real_filesystem(self, sample_quotes):
        """Integration test using the actual filesystem."""
        with TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)
            
            # Test exporting to JSON
            json_result = export_quotes(sample_quotes, ['json'], export_dir)
            assert 'json' in json_result
            json_path = Path(json_result['json'])
            assert json_path.exists()
            assert json_path.suffix == '.json'
            
            # Verify JSON content
            with open(json_path, 'r') as f:
                json_content = json.load(f)
                assert len(json_content) == 2
                assert json_content[0]['symbol'] == 'AAPL'
                assert json_content[1]['symbol'] == 'MSFT'
            
            # Test exporting to CSV
            csv_result = export_quotes(sample_quotes, ['csv'], export_dir)
            assert 'csv' in csv_result
            csv_path = Path(csv_result['csv'])
            assert csv_path.exists()
            assert csv_path.suffix == '.csv'
            
            # Verify CSV content
            with open(csv_path, 'r', newline='') as f:
                csv_reader = csv.DictReader(f)
                rows = list(csv_reader)
                assert len(rows) == 2
                assert rows[0]['symbol'] == 'AAPL'
                assert rows[1]['symbol'] == 'MSFT'
                assert float(rows[0]['price']) == 177.80
                assert float(rows[1]['price']) == 423.80
    
    def test_filename_generation_includes_symbols(self, sample_quotes):
        """Test that export filenames include the stock symbols."""
        with TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)
            
            result = export_quotes(sample_quotes, ['json'], export_dir)
            filename = os.path.basename(result['json'])
            
            # Filename should include both symbols and a timestamp
            assert 'AAPL' in filename
            assert 'MSFT' in filename
            assert '.json' in filename
            
            # Should include date format (numbers separated by dashes, underscores, etc.)
            assert any(c.isdigit() for c in filename)
    
    def test_export_with_timestamp_in_filename(self, sample_quotes):
        """Test that export filenames include a timestamp component."""
        with TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)
            
            # Get current date components
            now = datetime.now()
            year = str(now.year)
            month = str(now.month).zfill(2)
            day = str(now.day).zfill(2)
            
            # Export and check filename
            result = export_quotes(sample_quotes, ['json'], export_dir)
            filename = os.path.basename(result['json'])
            
            # Filename should include date components
            assert year in filename
            # Either as separate components or together
            assert month in filename or f"{year}{month}" in filename
            assert day in filename or f"{month}{day}" in filename