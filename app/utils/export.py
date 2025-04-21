"""
Utility functions for exporting data to various formats.
"""

import os
import json
import csv
import logging
import sys
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union

from app.models.divided_calendar import DividendCalendar, DividendCalendarEvent
from app.models.dividend import Dividend, DividendHistory
from app.models.income_statement import IncomeStatement
from app.models.splits import SplitHistory, StockSplit
from app.models.splits_calendar import SplitCalendarEvent, SplitsCalendar
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

# This contains export functions to be added to export.py


def export_dividend_history(dividend_history: 'DividendHistory', formats: List[str],
                            output_dir: Union[str, Path]) -> Dict[str, str]:
    """
    Export dividend history to specified formats.

    Args:
        dividend_history: DividendHistory object to export
        formats: List of formats to export to ('json', 'csv')
        output_dir: Directory to save exported files

    Returns:
        Dictionary mapping format to exported file path
    """
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    symbol = dividend_history.symbol

    # Ensure the output directory exists
    ensure_directory(output_dir)

    for fmt in formats:
        if fmt.lower() == 'json':
            # Export to JSON
            filename = f"dividend_history_{symbol}_{timestamp}.json"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w') as f:
                    json.dump(dividend_history.to_dict(),
                              f, indent=2, default=str)
                results['json'] = str(filepath)
                logger.info(f"Exported dividend history to JSON: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export dividend history to JSON: {e}")

        elif fmt.lower() == 'csv':
            # Export to CSV
            filename = f"dividend_history_{symbol}_{timestamp}.csv"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(
                        f, fieldnames=Dividend.get_csv_header())
                    writer.writeheader()
                    for dividend in dividend_history.dividends:
                        writer.writerow(dividend.to_csv_row())
                results['csv'] = str(filepath)
                logger.info(f"Exported dividend history to CSV: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export dividend history to CSV: {e}")

    return results


def export_dividend_comparison(dividend_histories: List['DividendHistory'], formats: List[str],
                               output_dir: Union[str, Path]) -> Dict[str, str]:
    """
    Export dividend comparison to specified formats.

    Args:
        dividend_histories: List of DividendHistory objects to export
        formats: List of formats to export to ('json', 'csv')
        output_dir: Directory to save exported files

    Returns:
        Dictionary mapping format to exported file path
    """
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    symbols = "_".join([history.symbol for history in dividend_histories])

    # Limit the filename length by truncating symbols if too many
    if len(symbols) > 50:
        symbols = f"{symbols[:47]}..."

    # Ensure the output directory exists
    ensure_directory(output_dir)

    for fmt in formats:
        if fmt.lower() == 'json':
            # Export to JSON
            filename = f"dividend_comparison_{timestamp}.json"
            filepath = Path(output_dir) / filename

            try:
                comparison_data = {
                    "timestamp": timestamp,
                    "symbols": [history.symbol for history in dividend_histories],
                    "histories": [history.to_dict() for history in dividend_histories]
                }

                with open(filepath, 'w') as f:
                    json.dump(comparison_data, f, indent=2, default=str)
                results['json'] = str(filepath)
                logger.info(
                    f"Exported dividend comparison to JSON: {filepath}")
            except Exception as e:
                logger.error(
                    f"Failed to export dividend comparison to JSON: {e}")

        elif fmt.lower() == 'csv':
            # Export multiple CSV files - one summary and individual files for each symbol

            # First, create a summary file
            summary_filename = f"dividend_comparison_summary_{timestamp}.csv"
            summary_filepath = Path(output_dir) / summary_filename

            try:
                with open(summary_filepath, 'w', newline='') as f:
                    # Create summary headers
                    writer = csv.writer(f)
                    writer.writerow(["Symbol", "Name", "Currency", "Total Dividends",
                                    "Average Annual", "Latest Annual", "5Y Average", "5Y Growth"])

                    # Add summary data for each symbol
                    for history in dividend_histories:
                        annual = history.annual_dividends()

                        # Get the latest year's dividend
                        latest_annual = list(
                            annual.items())[-1][1] if annual else 0.0

                        # Calculate 5-year average
                        recent_years = list(
                            annual.items())[-5:] if len(annual) >= 5 else list(annual.items())
                        five_year_avg = sum(
                            amount for _, amount in recent_years) / len(recent_years) if recent_years else 0.0

                        # Calculate 5-year growth rate
                        five_year_growth = "N/A"
                        if len(recent_years) >= 2:
                            first_year, first_amount = recent_years[0]
                            last_year, last_amount = recent_years[-1]
                            years_diff = last_year - first_year
                            if years_diff > 0 and first_amount > 0:
                                cagr = ((last_amount / first_amount)
                                        ** (1 / years_diff) - 1) * 100
                                five_year_growth = f"{cagr:.2f}%"

                        writer.writerow([
                            history.symbol,
                            history.name,
                            history.currency,
                            len(history.dividends),
                            history.average_annual_dividend(),
                            latest_annual,
                            five_year_avg,
                            five_year_growth
                        ])

                # Now export individual detailed files for each symbol
                for history in dividend_histories:
                    detail_filename = f"dividend_history_{history.symbol}_{timestamp}.csv"
                    detail_filepath = Path(output_dir) / detail_filename

                    with open(detail_filepath, 'w', newline='') as f:
                        writer = csv.DictWriter(
                            f, fieldnames=Dividend.get_csv_header())
                        writer.writeheader()
                        for dividend in history.dividends:
                            writer.writerow(dividend.to_csv_row())

                results['csv'] = str(summary_filepath)
                logger.info(
                    f"Exported dividend comparison to CSV: {summary_filepath}")
            except Exception as e:
                logger.error(
                    f"Failed to export dividend comparison to CSV: {e}")

    return results


def export_dividend_calendar(dividend_calendar: 'DividendCalendar',
                             formats: List[str],
                             output_dir: Union[str, Path],
                             view_mode: str = 'calendar') -> Dict[str, str]:
    """
    Export dividend calendar to specified formats.

    Args:
        dividend_calendar: DividendCalendar object to export
        formats: List of formats to export to ('json', 'csv')
        output_dir: Directory to save exported files
        view_mode: The view mode that was used (for naming purposes)

    Returns:
        Dictionary mapping format to exported file path
    """
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_range = f"{dividend_calendar.start_date.strftime('%Y%m%d')}-{dividend_calendar.end_date.strftime('%Y%m%d')}"

    # Ensure the output directory exists
    ensure_directory(output_dir)

    for fmt in formats:
        if fmt.lower() == 'json':
            # Export to JSON
            filename = f"dividend_calendar_{date_range}_{timestamp}.json"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w') as f:
                    json.dump(dividend_calendar.to_dict(),
                              f, indent=2, default=str)
                results['json'] = str(filepath)
                logger.info(f"Exported dividend calendar to JSON: {filepath}")
            except Exception as e:
                logger.error(
                    f"Failed to export dividend calendar to JSON: {e}")

        elif fmt.lower() == 'csv':
            # Export to CSV
            filename = f"dividend_calendar_{date_range}_{timestamp}.csv"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(
                        f, fieldnames=DividendCalendarEvent.get_csv_header())
                    writer.writeheader()
                    for event in dividend_calendar.events:
                        writer.writerow(event.to_csv_row())
                results['csv'] = str(filepath)
                logger.info(f"Exported dividend calendar to CSV: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export dividend calendar to CSV: {e}")

            # For a more structured temporal view, create a date-based CSV as well
            if view_mode == 'calendar':
                date_filename = f"dividend_calendar_by_date_{date_range}_{timestamp}.csv"
                date_filepath = Path(output_dir) / date_filename

                try:
                    with open(date_filepath, 'w', newline='') as f:
                        writer = csv.writer(f)

                        # Write headers
                        writer.writerow(
                            ['Date', 'Symbol', 'Name', 'Amount', 'Currency', 'Yield', 'Ex-Date', 'Pay-Date'])

                        # Group by ex-dividend date
                        events_by_date = dividend_calendar.get_events_by_date(
                            'ex_dividend_date')

                        # Sort dates
                        sorted_dates = sorted(events_by_date.keys())

                        # Write data for each date
                        for day_date in sorted_dates:
                            for event in events_by_date[day_date]:
                                # Format the dates for readability
                                ex_date = event.ex_dividend_date.strftime(
                                    "%Y-%m-%d") if event.ex_dividend_date else ""
                                pay_date = event.payment_date.strftime(
                                    "%Y-%m-%d") if event.payment_date else ""
                                yield_value = f"{event.yield_value}%" if event.yield_value is not None else ""

                                writer.writerow([
                                    day_date.strftime("%Y-%m-%d"),
                                    event.symbol,
                                    event.name or "",
                                    event.amount,
                                    event.currency,
                                    yield_value,
                                    ex_date,
                                    pay_date
                                ])

                    # We've created an additional file, but we'll still return just the main one
                    logger.info(
                        f"Exported dividend calendar by date to CSV: {date_filepath}")
                except Exception as e:
                    logger.error(
                        f"Failed to export dividend calendar by date to CSV: {e}")

    return results


def export_stock_splits(split_history: 'SplitHistory', formats: List[str],
                        output_dir: Union[str, Path]) -> Dict[str, str]:
    """
    Export stock splits history to specified formats.

    Args:
        split_history: SplitHistory object to export
        formats: List of formats to export to ('json', 'csv')
        output_dir: Directory to save exported files

    Returns:
        Dictionary mapping format to exported file path
    """
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    symbol = split_history.symbol

    # Ensure the output directory exists
    ensure_directory(output_dir)

    for fmt in formats:
        if fmt.lower() == 'json':
            # Export to JSON
            filename = f"stock_splits_{symbol}_{timestamp}.json"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w') as f:
                    json.dump(split_history.to_dict(),
                              f, indent=2, default=str)
                results['json'] = str(filepath)
                logger.info(f"Exported stock splits to JSON: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export stock splits to JSON: {e}")

        elif fmt.lower() == 'csv':
            # Export to CSV
            filename = f"stock_splits_{symbol}_{timestamp}.csv"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(
                        f, fieldnames=StockSplit.get_csv_header())
                    writer.writeheader()
                    for split in split_history.splits:
                        writer.writerow(split.to_csv_row())
                results['csv'] = str(filepath)
                logger.info(f"Exported stock splits to CSV: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export stock splits to CSV: {e}")

    return results


def export_stock_splits_comparison(split_histories: List['SplitHistory'], formats: List[str],
                                   output_dir: Union[str, Path]) -> Dict[str, str]:
    """
    Export stock splits comparison to specified formats.

    Args:
        split_histories: List of SplitHistory objects to export
        formats: List of formats to export to ('json', 'csv')
        output_dir: Directory to save exported files

    Returns:
        Dictionary mapping format to exported file path
    """
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    symbols = "_".join([history.symbol for history in split_histories])

    # Limit the filename length by truncating symbols if too many
    if len(symbols) > 50:
        symbols = f"{symbols[:47]}..."

    # Ensure the output directory exists
    ensure_directory(output_dir)

    for fmt in formats:
        if fmt.lower() == 'json':
            # Export to JSON
            filename = f"splits_comparison_{timestamp}.json"
            filepath = Path(output_dir) / filename

            try:
                comparison_data = {
                    "timestamp": timestamp,
                    "symbols": [history.symbol for history in split_histories],
                    "histories": [history.to_dict() for history in split_histories]
                }

                with open(filepath, 'w') as f:
                    json.dump(comparison_data, f, indent=2, default=str)
                results['json'] = str(filepath)
                logger.info(f"Exported splits comparison to JSON: {filepath}")
            except Exception as e:
                logger.error(
                    f"Failed to export splits comparison to JSON: {e}")

        elif fmt.lower() == 'csv':
            # Export multiple CSV files - one summary and individual files for each symbol

            # First, create a summary file
            summary_filename = f"splits_comparison_summary_{timestamp}.csv"
            summary_filepath = Path(output_dir) / summary_filename

            try:
                with open(summary_filepath, 'w', newline='') as f:
                    # Create summary headers
                    writer = csv.writer(f)
                    writer.writerow(["Symbol", "Company", "Total Splits", "Latest Split Date",
                                    "Latest Split Ratio", "Cumulative Factor"])

                    # Add summary data for each symbol
                    for history in split_histories:
                        recent_split = history.splits[0] if history.splits else None
                        recent_date = recent_split.date.strftime(
                            "%Y-%m-%d") if recent_split and recent_split.date else ""
                        recent_ratio = f"{recent_split.split_text}" if recent_split else ""

                        writer.writerow([
                            history.symbol,
                            history.name or "",
                            len(history.splits),
                            recent_date,
                            recent_ratio,
                            history.get_cumulative_split_factor()
                        ])

                # Now create a timeline csv showing splits by year
                timeline_filename = f"splits_timeline_{timestamp}.csv"
                timeline_filepath = Path(output_dir) / timeline_filename

                # Find all years with splits
                all_years = set()
                for history in split_histories:
                    all_years.update(history.get_years_with_splits())

                if all_years:
                    with open(timeline_filepath, 'w', newline='') as f:
                        writer = csv.writer(f)

                        # Create header with years
                        header = ["Symbol"]
                        for year in sorted(all_years, reverse=True):
                            header.append(str(year))
                        writer.writerow(header)

                        # Add data for each company
                        for history in split_histories:
                            row = [history.symbol]
                            years_with_splits = history.get_splits_by_year()

                            for year in sorted(all_years, reverse=True):
                                if year in years_with_splits:
                                    splits_in_year = years_with_splits[year]
                                    year_start = datetime(year, 1, 1)
                                    year_end = datetime(year, 12, 31)
                                    year_factor = history.get_cumulative_split_factor(
                                        year_start, year_end)

                                    # Add split count and factor
                                    row.append(
                                        f"{len(splits_in_year)},{year_factor:.2f}")
                                else:
                                    row.append("")

                            writer.writerow(row)

                # Now export individual detailed files for each symbol
                for history in split_histories:
                    detail_filename = f"stock_splits_{history.symbol}_{timestamp}.csv"
                    detail_filepath = Path(output_dir) / detail_filename

                    with open(detail_filepath, 'w', newline='') as f:
                        writer = csv.DictWriter(
                            f, fieldnames=StockSplit.get_csv_header())
                        writer.writeheader()
                        for split in history.splits:
                            writer.writerow(split.to_csv_row())

                results['csv'] = str(summary_filepath)
                logger.info(
                    f"Exported splits comparison to CSV: {summary_filepath}")
                logger.info(
                    f"Exported splits timeline to CSV: {timeline_filepath}")
            except Exception as e:
                logger.error(f"Failed to export splits comparison to CSV: {e}")

    return results


def export_splits_calendar(splits_calendar: 'SplitsCalendar',
                           formats: List[str],
                           output_dir: Union[str, Path],
                           view_mode: str = 'calendar') -> Dict[str, str]:
    """
    Export stock splits calendar to specified formats.

    Args:
        splits_calendar: SplitsCalendar object to export
        formats: List of formats to export to ('json', 'csv')
        output_dir: Directory to save exported files
        view_mode: The view mode that was used (for naming purposes)

    Returns:
        Dictionary mapping format to exported file path
    """
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_range = f"{splits_calendar.start_date.strftime('%Y%m%d')}-{splits_calendar.end_date.strftime('%Y%m%d')}"

    # Ensure the output directory exists
    ensure_directory(output_dir)

    for fmt in formats:
        if fmt.lower() == 'json':
            # Export to JSON
            filename = f"splits_calendar_{date_range}_{timestamp}.json"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w') as f:
                    json.dump(splits_calendar.to_dict(),
                              f, indent=2, default=str)
                results['json'] = str(filepath)
                logger.info(f"Exported splits calendar to JSON: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export splits calendar to JSON: {e}")

        elif fmt.lower() == 'csv':
            # Export to CSV
            filename = f"splits_calendar_{date_range}_{timestamp}.csv"
            filepath = Path(output_dir) / filename

            try:
                with open(filepath, 'w', newline='') as f:
                    writer = csv.DictWriter(
                        f, fieldnames=SplitCalendarEvent.get_csv_header())
                    writer.writeheader()
                    for event in splits_calendar.events:
                        writer.writerow(event.to_csv_row())
                results['csv'] = str(filepath)
                logger.info(f"Exported splits calendar to CSV: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export splits calendar to CSV: {e}")

            # For a more structured temporal view, create a date-based CSV as well
            if view_mode == 'calendar':
                date_filename = f"splits_calendar_by_date_{date_range}_{timestamp}.csv"
                date_filepath = Path(output_dir) / date_filename

                try:
                    with open(date_filepath, 'w', newline='') as f:
                        writer = csv.writer(f)

                        # Write headers
                        writer.writerow(
                            ['Date', 'Symbol', 'Company', 'Split', 'Ratio', 'Type', 'Exchange'])

                        # Group by date
                        events_by_date = splits_calendar.get_events_by_date()

                        # Sort dates
                        sorted_dates = sorted(events_by_date.keys())

                        # Write data for each date
                        for day_date in sorted_dates:
                            for event in events_by_date[day_date]:
                                # Determine split type
                                split_type = "Forward" if event.is_forward_split else "Reverse" if event.is_reverse_split else "Neutral"

                                writer.writerow([
                                    day_date.strftime("%Y-%m-%d"),
                                    event.symbol,
                                    event.name or "",
                                    event.split_text,
                                    f"{event.ratio:.2f}",
                                    split_type,
                                    event.exchange or ""
                                ])

                    # We've created an additional file, but we'll still return just the main one
                    logger.info(
                        f"Exported splits calendar by date to CSV: {date_filepath}")
                except Exception as e:
                    logger.error(
                        f"Failed to export splits calendar by date to CSV: {e}")

            # Also create a summary CSV if view mode is 'summary'
            if view_mode == 'summary':
                summary_filename = f"splits_calendar_summary_{date_range}_{timestamp}.csv"
                summary_filepath = Path(output_dir) / summary_filename

                try:
                    with open(summary_filepath, 'w', newline='') as f:
                        writer = csv.writer(f)

                        # Write headers
                        writer.writerow([
                            'Symbol', 'Company', 'Total Splits', 'Forward Splits',
                            'Reverse Splits', 'Next Split Date', 'Next Split Ratio', 'Next Split Type'
                        ])

                        # Group by symbol
                        events_by_symbol = splits_calendar.get_events_by_symbol()

                        # Write data for each symbol
                        for symbol, events in sorted(events_by_symbol.items()):
                            # Basic information
                            company_name = events[0].name or ""

                            # Count split types
                            total = len(events)
                            forward_count = sum(
                                1 for e in events if e.is_forward_split)
                            reverse_count = sum(
                                1 for e in events if e.is_reverse_split)

                            # Find next split
                            next_date = ""
                            next_ratio = ""
                            next_type = ""

                            future_events = [
                                e for e in events if e.date and e.date.date() >= date.today()]
                            if future_events:
                                future_events.sort(key=lambda e: e.date)
                                next_event = future_events[0]

                                if next_event.date:
                                    next_date = next_event.date.strftime(
                                        "%Y-%m-%d")
                                    next_ratio = next_event.split_text
                                    next_type = "Forward" if next_event.is_forward_split else "Reverse" if next_event.is_reverse_split else "Neutral"

                            writer.writerow([
                                symbol,
                                company_name,
                                total,
                                forward_count,
                                reverse_count,
                                next_date,
                                next_ratio,
                                next_type
                            ])

                    logger.info(
                        f"Exported splits calendar summary to CSV: {summary_filepath}")
                except Exception as e:
                    logger.error(
                        f"Failed to export splits calendar summary to CSV: {e}")

    return results


def export_income_statement(income_statement: IncomeStatement, formats: List[str],
                            output_dir: Path) -> Dict[str, str]:
    """
    Export income statement data to file(s).

    Args:
        income_statement: The income statement to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files

    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = income_statement.symbol.upper()
    period = income_statement.fiscal_period
    date = income_statement.fiscal_date

    # Generate filename
    base_filename = generate_export_filename(
        'income_statement',
        [symbol],
        additional_parts=[period, date]
    )

    ensure_directory(output_dir)

    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(income_statement.to_dict(), f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"

        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(
                f, fieldnames=IncomeStatement.get_csv_headers())
            csv_writer.writeheader()

            for row in income_statement.get_csv_rows():
                csv_writer.writerow(row)

        result['csv'] = str(csv_path)

    return result


def export_income_statements(income_statements: List[IncomeStatement], formats: List[str],
                             output_dir: Path) -> Dict[str, str]:
    """
    Export multiple income statements to file(s).

    Args:
        income_statements: The income statements to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files

    Returns:
        Dict mapping format to file path
    """
    if not income_statements:
        return {}

    result = {}
    symbol = income_statements[0].symbol.upper()
    period = income_statements[0].fiscal_period
    date_range = f"{income_statements[-1].fiscal_date}_to_{income_statements[0].fiscal_date}"

    # Generate filename
    base_filename = generate_export_filename(
        'income_statements',
        [symbol],
        additional_parts=[period, date_range]
    )

    ensure_directory(output_dir)

    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump({
                "symbol": symbol,
                "period": period,
                "statements": [statement.to_dict() for statement in income_statements]
            }, f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV - each statement in a separate file
    if 'csv' in formats:
        # Create a directory for all CSVs
        csv_dir = output_dir / f"{base_filename}_csv"
        ensure_directory(csv_dir)

        csv_paths = []
        for statement in income_statements:
            statement_filename = f"{symbol}_{period}_{statement.fiscal_date}.csv"
            csv_path = csv_dir / statement_filename

            with open(csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(
                    f, fieldnames=IncomeStatement.get_csv_headers())
                csv_writer.writeheader()

                for row in statement.get_csv_rows():
                    csv_writer.writerow(row)

            csv_paths.append(str(csv_path))

        result['csv'] = csv_paths

    return result


def export_expense_breakdown(income_statement: IncomeStatement, formats: List[str],
                             output_dir: Path) -> Dict[str, str]:
    """
    Export expense breakdown data to file(s).

    Args:
        income_statement: The income statement to export expenses from
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files

    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = income_statement.symbol.upper()
    period = income_statement.fiscal_period
    date = income_statement.fiscal_date

    # Generate filename
    base_filename = generate_export_filename(
        'expense_breakdown',
        [symbol],
        additional_parts=[period, date]
    )

    ensure_directory(output_dir)

    expenses = income_statement.get_all_expenses()

    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump({
                "symbol": symbol,
                "period": period,
                "fiscal_date": date,
                "currency": income_statement.currency,
                "revenue": income_statement.revenue.to_dict(),
                "expenses": [expense.to_dict() for expense in expenses]
            }, f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"

        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(["Expense Category", "Amount", "% of Revenue"])

            for expense in expenses:
                csv_writer.writerow([
                    expense.name,
                    expense.value_str,
                    expense.percentage_str
                ])

        result['csv'] = str(csv_path)

    return result
