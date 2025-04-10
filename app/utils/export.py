"""
Utility functions for exporting data to various formats.
"""

import os
import json
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from app.models.stock import Quote, TimeSeries, TechnicalIndicator

logger = logging.getLogger(__name__)


def ensure_directory(filepath: Union[str, Path]) -> None:
    """Ensure that the directory for the file exists."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug(f"Created directory: {directory}")


def export_to_json(data: Union[List[Any], Dict[str, Any]], filepath: Union[str, Path], pretty: bool = True) -> bool:
    """
    Export data to a JSON file.

    Args:
        data: The data to export
        filepath: The path to the output file
        pretty: Whether to format the JSON with indentation

    Returns:
        True if export was successful, False otherwise
    """
    try:
        ensure_directory(filepath)

        # Convert quotes to dictionaries if the input is a list of Quote objects
        if isinstance(data, list) and data and hasattr(data[0], 'to_dict'):
            data = [item.to_dict() for item in data]
        elif hasattr(data, 'to_dict'):
            data = data.to_dict()

        with open(filepath, 'w') as f:
            if pretty:
                json.dump(data, f, indent=2, default=str)
            else:
                json.dump(data, f, default=str)

        logger.info(f"Exported data to JSON file: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to export data to JSON: {e}", exc_info=True)
        return False


def export_quotes_to_csv(quotes: List[Quote], filepath: Union[str, Path]) -> bool:
    """
    Export a list of quotes to a CSV file.

    Args:
        quotes: The quotes to export
        filepath: The path to the output file

    Returns:
        True if export was successful, False otherwise
    """
    try:
        ensure_directory(filepath)

        with open(filepath, 'w', newline='') as f:
            fieldnames = Quote.get_csv_header()
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for quote in quotes:
                writer.writerow(quote.to_csv_row())

        logger.info(f"Exported quotes to CSV file: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to export quotes to CSV: {e}", exc_info=True)
        return False


def export_time_series_to_csv(time_series: TimeSeries, filepath: Union[str, Path]) -> bool:
    """
    Export time series data to a CSV file.

    Args:
        time_series: The time series data to export
        filepath: The path to the output file

    Returns:
        True if export was successful, False otherwise
    """
    try:
        ensure_directory(filepath)

        with open(filepath, 'w', newline='') as f:
            # Add symbol and interval as header comments
            f.write(f"# Symbol: {time_series.symbol}\n")
            f.write(f"# Interval: {time_series.interval}\n")
            f.write(f"# Currency: {time_series.currency}\n")
            f.write(f"# Exported: {datetime.now().isoformat()}\n")

            # Write the actual data
            fieldnames = ["timestamp", "open",
                          "high", "low", "close", "volume"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for bar in time_series.bars:
                writer.writerow(bar.to_csv_row())

        logger.info(f"Exported time series to CSV file: {filepath}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to export time series to CSV: {e}", exc_info=True)
        return False


def generate_export_filename(prefix: str, symbols: List[str], extension: str) -> str:
    """
    Generate a filename for exported data.

    Args:
        prefix: A prefix for the filename (e.g., 'quotes', 'history')
        symbols: The list of symbols included in the data
        extension: The file extension (e.g., 'json', 'csv')

    Returns:
        A formatted filename
    """
    # Format the current date and time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a consolidated symbol name (max 3 symbols in the filename)
    if len(symbols) == 1:
        symbol_str = symbols[0]
    elif len(symbols) <= 3:
        symbol_str = "-".join(symbols)
    else:
        symbol_str = f"{symbols[0]}-and-{len(symbols)-1}-more"

    return f"{prefix}_{symbol_str}_{timestamp}.{extension}"


def get_project_dir() -> Path:
    """Get the project directory path."""
    # If running as installed package
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(
            getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
    else:
        # Get the directory of the stock_cli package
        base_path = Path(__file__).resolve().parent.parent.parent

        # Check if we're in the development directory structure
        if (base_path / 'stock_cli').exists():
            return base_path

    return base_path


def get_default_export_dir() -> Path:
    """Get the default directory for exported files."""
    # Use the project's exports directory
    project_dir = get_project_dir()
    export_dir = project_dir / 'stock_cli' / 'exports'

    # Ensure the directory exists
    export_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Using default export directory: {export_dir}")
    return export_dir


def get_home_export_dir() -> Path:
    """Get the export directory in the user's home folder."""
    export_dir = Path.home() / '.stock_cli' / 'exports'
    export_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Using home directory for exports: {export_dir}")
    return export_dir


def export_quotes(quotes: List[Quote], formats: List[str],
                  output_dir: Optional[Union[str, Path]] = None,
                  filename_prefix: str = "quotes") -> Dict[str, str]:
    """
    Export quotes to the specified formats.

    Args:
        quotes: The quotes to export
        formats: List of formats to export to (e.g., ['json', 'csv'])
        output_dir: The output directory
        filename_prefix: Prefix for the output filenames

    Returns:
        Dictionary mapping format to output file path
    """
    if not quotes:
        logger.warning("No quotes to export")
        return {}

    # Get the list of symbols
    symbols = [quote.symbol for quote in quotes]

    # Handle output directory
    if output_dir is None:
        # Use default export directory if none provided
        output_dir = get_default_export_dir()
        logger.debug(f"Using default export directory: {output_dir}")
    else:
        # Convert to Path object if it's a string
        output_dir = Path(output_dir)
        logger.debug(f"Using custom export directory: {output_dir}")

    # Ensure the output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {}

    # Export to each format
    for fmt in formats:
        if fmt.lower() == 'json':
            filename = generate_export_filename(
                filename_prefix, symbols, 'json')
            filepath = output_dir / filename
            if export_to_json(quotes, filepath):
                result['json'] = str(filepath)

        elif fmt.lower() == 'csv':
            filename = generate_export_filename(
                filename_prefix, symbols, 'csv')
            filepath = output_dir / filename
            if export_quotes_to_csv(quotes, filepath):
                result['csv'] = str(filepath)
        else:
            logger.warning(f"Unsupported export format: {fmt}")

    return result


def export_symbols_to_csv(symbols: List[Any], filepath: Union[str, Path]) -> bool:
    """
    Export a list of symbols to a CSV file.

    Args:
        symbols: The symbols to export
        filepath: The path to the output file

    Returns:
        True if export was successful, False otherwise
    """
    try:
        ensure_directory(filepath)

        with open(filepath, 'w', newline='') as f:
            fieldnames = symbols[0].get_csv_header()
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for symbol in symbols:
                writer.writerow(symbol.to_csv_row())

        logger.info(f"Exported symbols to CSV file: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to export symbols to CSV: {e}", exc_info=True)
        return False


def export_symbols(symbols: List[Any], formats: List[str],
                   output_dir: Optional[Union[str, Path]] = None,
                   filename_prefix: str = "symbols",
                   use_home_dir: bool = False) -> Dict[str, str]:
    """
    Export symbols to the specified formats.

    Args:
        symbols: The symbols to export
        formats: List of formats to export to (e.g., ['json', 'csv'])
        output_dir: The output directory
        filename_prefix: Prefix for the output filenames
        use_home_dir: Whether to use the user's home directory

    Returns:
        Dictionary mapping format to output file path
    """
    if not symbols:
        logger.warning("No symbols to export")
        return {}

    # Determine the output directory with the following priority:
    # 1. Explicitly provided output_dir
    # 2. User's home directory if use_home_dir is True
    # 3. Default project directory
    if output_dir:
        # Use the explicitly provided directory
        export_dir = Path(output_dir)
        logger.debug(f"Using custom export directory: {export_dir}")
    elif use_home_dir:
        # Use the user's home directory
        export_dir = get_home_export_dir()
    else:
        # Use the default directory (project exports)
        export_dir = get_default_export_dir()

    # Ensure the output directory exists
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created/ensured export directory: {export_dir}")
    except Exception as e:
        logger.error(f"Failed to create export directory {export_dir}: {e}")
        # Fall back to the default directory
        export_dir = get_default_export_dir()
        logger.warning(
            f"Falling back to default export directory: {export_dir}")

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    result = {}

    # Export to each format
    for fmt in formats:
        if fmt.lower() == 'json':
            filename = f"{filename_prefix}_{timestamp}.json"
            filepath = export_dir / filename
            if export_to_json(symbols, filepath):
                result['json'] = str(filepath)

        elif fmt.lower() == 'csv':
            filename = f"{filename_prefix}_{timestamp}.csv"
            filepath = export_dir / filename
            if export_symbols_to_csv(symbols, filepath):
                result['csv'] = str(filepath)
        else:
            logger.warning(f"Unsupported export format: {fmt}")

    return result
