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

from app.models.analysts_estimates import AnalystEstimates
from app.models.balance_sheet import BalanceSheet
from app.models.cash_flow import CashFlow
from app.models.divided_calendar import DividendCalendar, DividendCalendarEvent
from app.models.dividend import Dividend, DividendHistory
from app.models.executives import Executive, ManagementTeam
from app.models.income_statement import IncomeStatement
from app.models.market_cap import MarketCapHistory
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


def export_balance_sheet(balance_sheet: BalanceSheet, formats: List[str],
                         output_dir: Path) -> Dict[str, str]:
    """
    Export balance sheet data to file(s).

    Args:
        balance_sheet: The balance sheet to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files

    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = balance_sheet.symbol.upper()
    period = balance_sheet.fiscal_period
    date = balance_sheet.fiscal_date

    # Generate filename
    base_filename = generate_export_filename(
        'balance_sheet',
        [symbol],
        additional_parts=[period, date]
    )

    ensure_directory(output_dir)

    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(balance_sheet.to_dict(), f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"

        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(
                f, fieldnames=BalanceSheet.get_csv_headers())
            csv_writer.writeheader()

            for row in balance_sheet.get_csv_rows():
                csv_writer.writerow(row)

        result['csv'] = str(csv_path)

    return result


def export_balance_sheets(balance_sheets: List[BalanceSheet], formats: List[str],
                          output_dir: Path) -> Dict[str, Any]:
    """
    Export multiple balance sheets to file(s).

    Args:
        balance_sheets: The balance sheets to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files

    Returns:
        Dict mapping format to file path(s)
    """
    if not balance_sheets:
        return {}

    result = {}
    symbol = balance_sheets[0].symbol.upper()
    period = balance_sheets[0].fiscal_period
    date_range = f"{balance_sheets[-1].fiscal_date}_to_{balance_sheets[0].fiscal_date}"

    # Generate filename
    base_filename = generate_export_filename(
        'balance_sheets',
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
                "statements": [statement.to_dict() for statement in balance_sheets]
            }, f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV - each statement in a separate file
    if 'csv' in formats:
        # Create a directory for all CSVs
        csv_dir = output_dir / f"{base_filename}_csv"
        ensure_directory(csv_dir)

        csv_paths = []
        for statement in balance_sheets:
            statement_filename = f"{symbol}_{period}_{statement.fiscal_date}.csv"
            csv_path = csv_dir / statement_filename

            with open(csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(
                    f, fieldnames=BalanceSheet.get_csv_headers())
                csv_writer.writeheader()

                for row in statement.get_csv_rows():
                    csv_writer.writerow(row)

            csv_paths.append(str(csv_path))

        result['csv'] = csv_paths

    return result


def export_balance_sheets(balance_sheets: List[BalanceSheet], formats: List[str],
                          output_dir: Path, custom_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Export multiple balance sheets to file(s).

    Args:
        balance_sheets: The balance sheets to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        custom_filename: Optional custom base filename to use

    Returns:
        Dict mapping format to file path(s)
    """
    if not balance_sheets:
        return {}

    result = {}
    symbol = balance_sheets[0].symbol.upper()
    period = balance_sheets[0].fiscal_period
    date_range = f"{balance_sheets[-1].fiscal_date}_to_{balance_sheets[0].fiscal_date}"

    # Generate filename - use custom if provided
    if custom_filename:
        base_filename = custom_filename
    else:
        base_filename = generate_export_filename(
            'balance_sheets',
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
                "statements": [statement.to_dict() for statement in balance_sheets]
            }, f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV - each statement in a separate file
    if 'csv' in formats:
        # Create a directory for all CSVs
        csv_dir = output_dir / f"{base_filename}_csv"
        ensure_directory(csv_dir)

        csv_paths = []
        for statement in balance_sheets:
            statement_filename = f"{symbol}_{period}_{statement.fiscal_date}.csv"
            csv_path = csv_dir / statement_filename

            with open(csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(
                    f, fieldnames=BalanceSheet.get_csv_headers())
                csv_writer.writeheader()

                for row in statement.get_csv_rows():
                    csv_writer.writerow(row)

            csv_paths.append(str(csv_path))

        result['csv'] = csv_paths

    return result


def export_balance_sheet_summary(balance_sheet: BalanceSheet, formats: List[str],
                                 output_dir: Path, custom_filename: Optional[str] = None) -> Dict[str, str]:
    """
    Export a summary of balance sheet structure to file(s).

    Args:
        balance_sheet: The balance sheet to summarize and export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        custom_filename: Optional custom base filename to use

    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = balance_sheet.symbol.upper()
    period = balance_sheet.fiscal_period
    date = balance_sheet.fiscal_date

    # Generate filename - use custom if provided
    if custom_filename:
        base_filename = custom_filename
    else:
        base_filename = generate_export_filename(
            'balance_sheet_summary',
            [symbol],
            additional_parts=[period, date]
        )

    ensure_directory(output_dir)

    # Calculate total assets for percentages
    total_assets = balance_sheet.total_assets.value

    # Export to JSON
    if 'json' in formats:
        # Create a summary structure
        summary = {
            "symbol": symbol,
            "fiscal_date": date,
            "fiscal_period": period,
            "currency": balance_sheet.currency,
            "structure": {
                "assets": {
                    "current_assets": {
                        "value": balance_sheet.current_assets.value,
                        "percentage": (balance_sheet.current_assets.value / total_assets * 100) if total_assets > 0 else 0,
                        "items": [
                            {
                                "name": item.name,
                                "value": item.value,
                                "percentage": (item.value / total_assets * 100) if total_assets > 0 else 0
                            }
                            for item in balance_sheet.current_assets.items
                        ]
                    },
                    "non_current_assets": {
                        "value": balance_sheet.non_current_assets.value,
                        "percentage": (balance_sheet.non_current_assets.value / total_assets * 100) if total_assets > 0 else 0,
                        "items": [
                            {
                                "name": item.name,
                                "value": item.value,
                                "percentage": (item.value / total_assets * 100) if total_assets > 0 else 0
                            }
                            for item in balance_sheet.non_current_assets.items
                        ]
                    }
                },
                "liabilities": {
                    "current_liabilities": {
                        "value": balance_sheet.current_liabilities.value,
                        "percentage": (balance_sheet.current_liabilities.value / total_assets * 100) if total_assets > 0 else 0,
                        "items": [
                            {
                                "name": item.name,
                                "value": item.value,
                                "percentage": (item.value / total_assets * 100) if total_assets > 0 else 0
                            }
                            for item in balance_sheet.current_liabilities.items
                        ]
                    },
                    "non_current_liabilities": {
                        "value": balance_sheet.non_current_liabilities.value,
                        "percentage": (balance_sheet.non_current_liabilities.value / total_assets * 100) if total_assets > 0 else 0,
                        "items": [
                            {
                                "name": item.name,
                                "value": item.value,
                                "percentage": (item.value / total_assets * 100) if total_assets > 0 else 0
                            }
                            for item in balance_sheet.non_current_liabilities.items
                        ]
                    }
                },
                "equity": {
                    "value": balance_sheet.shareholders_equity.value,
                    "percentage": (balance_sheet.shareholders_equity.value / total_assets * 100) if total_assets > 0 else 0,
                    "items": [
                        {
                            "name": item.name,
                            "value": item.value,
                            "percentage": (item.value / total_assets * 100) if total_assets > 0 else 0
                        }
                        for item in balance_sheet.shareholders_equity.items
                    ]
                }
            },
            "financial_health": {
                "working_capital": balance_sheet.current_assets.value - balance_sheet.current_liabilities.value,
                "current_ratio": balance_sheet.current_ratio.value,
                "debt_to_equity": balance_sheet.debt_to_equity.value,
                "debt_ratio": balance_sheet.debt_ratio.value
            }
        }

        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        result['json'] = str(json_path)

    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"

        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.writer(f)

            # Write header
            csv_writer.writerow(
                ["Component", "Amount", "Percentage of Total Assets"])

            # Write assets
            csv_writer.writerow(["ASSETS", "", ""])

            # Current Assets
            csv_writer.writerow(["Current Assets", balance_sheet.current_assets.total.value_str,
                                f"{(balance_sheet.current_assets.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"])

            for item in balance_sheet.current_assets.items:
                csv_writer.writerow([
                    f"  {item.name}",
                    item.value_str,
                    f"{(item.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"
                ])

            # Non-Current Assets
            csv_writer.writerow(["Non-Current Assets", balance_sheet.non_current_assets.total.value_str,
                                f"{(balance_sheet.non_current_assets.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"])

            for item in balance_sheet.non_current_assets.items:
                csv_writer.writerow([
                    f"  {item.name}",
                    item.value_str,
                    f"{(item.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"
                ])

            # Total Assets
            csv_writer.writerow(
                ["TOTAL ASSETS", balance_sheet.total_assets.value_str, "100.00%"])
            csv_writer.writerow(["", "", ""])  # Empty row

            # Write liabilities
            csv_writer.writerow(["LIABILITIES", "", ""])

            # Current Liabilities
            csv_writer.writerow(["Current Liabilities", balance_sheet.current_liabilities.total.value_str,
                                f"{(balance_sheet.current_liabilities.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"])

            for item in balance_sheet.current_liabilities.items:
                csv_writer.writerow([
                    f"  {item.name}",
                    item.value_str,
                    f"{(item.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"
                ])

            # Non-Current Liabilities
            csv_writer.writerow(["Non-Current Liabilities", balance_sheet.non_current_liabilities.total.value_str,
                                f"{(balance_sheet.non_current_liabilities.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"])

            for item in balance_sheet.non_current_liabilities.items:
                csv_writer.writerow([
                    f"  {item.name}",
                    item.value_str,
                    f"{(item.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"
                ])

            # Total Liabilities
            csv_writer.writerow(["TOTAL LIABILITIES", balance_sheet.total_liabilities.value_str,
                                f"{(balance_sheet.total_liabilities.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"])
            csv_writer.writerow(["", "", ""])  # Empty row

            # Write equity
            csv_writer.writerow(["SHAREHOLDERS' EQUITY", "", ""])

            for item in balance_sheet.shareholders_equity.items:
                csv_writer.writerow([
                    f"  {item.name}",
                    item.value_str,
                    f"{(item.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"
                ])

            # Total Equity
            csv_writer.writerow(["TOTAL SHAREHOLDERS' EQUITY", balance_sheet.shareholders_equity.total.value_str,
                                f"{(balance_sheet.shareholders_equity.value / total_assets * 100) if total_assets > 0 else 0:.2f}%"])
            csv_writer.writerow(["", "", ""])  # Empty row

            # Total Liabilities and Equity
            csv_writer.writerow(["TOTAL LIABILITIES AND EQUITY",
                                balance_sheet.total_liabilities_and_equity.value_str, "100.00%"])
            csv_writer.writerow(["", "", ""])  # Empty row

            # Financial Health Indicators
            csv_writer.writerow(["FINANCIAL HEALTH INDICATORS", "", ""])
            csv_writer.writerow(
                ["Working Capital", f"{balance_sheet.current_assets.value - balance_sheet.current_liabilities.value:,.2f}", ""])
            csv_writer.writerow(
                ["Current Ratio", balance_sheet.current_ratio.value_str, ""])
            csv_writer.writerow(
                ["Debt to Equity Ratio", balance_sheet.debt_to_equity.value_str, ""])
            csv_writer.writerow(
                ["Debt Ratio", balance_sheet.debt_ratio.value_str, ""])

        result['csv'] = str(csv_path)

    return result

def export_cash_flow(cash_flow: CashFlow, formats: List[str], 
                    output_dir: Path) -> Dict[str, str]:
    """
    Export cash flow statement data to file(s).
    
    Args:
        cash_flow: The cash flow statement to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = cash_flow.symbol.upper()
    period = cash_flow.fiscal_period
    date = cash_flow.fiscal_date
    
    # Generate filename
    base_filename = generate_export_filename(
        'cash_flow', 
        [symbol], 
        additional_parts=[period, date]
    )
    
    ensure_directory(output_dir)
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(cash_flow.to_dict(), f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(f, fieldnames=CashFlow.get_csv_headers())
            csv_writer.writeheader()
            
            for row in cash_flow.get_csv_rows():
                csv_writer.writerow(row)
                
        result['csv'] = str(csv_path)
    
    return result


def export_cash_flows(cash_flows: List[CashFlow], formats: List[str],
                     output_dir: Path) -> Dict[str, Any]:
    """
    Export multiple cash flow statements to file(s).
    
    Args:
        cash_flows: The cash flow statements to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path(s)
    """
    if not cash_flows:
        return {}
        
    result = {}
    symbol = cash_flows[0].symbol.upper()
    period = cash_flows[0].fiscal_period
    date_range = f"{cash_flows[-1].fiscal_date}_to_{cash_flows[0].fiscal_date}"
    
    # Generate filename
    base_filename = generate_export_filename(
        'cash_flows', 
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
                "statements": [statement.to_dict() for statement in cash_flows]
            }, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV - each statement in a separate file
    if 'csv' in formats:
        # Create a directory for all CSVs
        csv_dir = output_dir / f"{base_filename}_csv"
        ensure_directory(csv_dir)
        
        csv_paths = []
        for statement in cash_flows:
            statement_filename = f"{symbol}_{period}_{statement.fiscal_date}.csv"
            csv_path = csv_dir / statement_filename
            
            with open(csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(f, fieldnames=CashFlow.get_csv_headers())
                csv_writer.writeheader()
                
                for row in statement.get_csv_rows():
                    csv_writer.writerow(row)
                    
            csv_paths.append(str(csv_path))
        
        result['csv'] = csv_paths
    
    return result


def export_cash_flow_analysis(cash_flows: List[CashFlow], formats: List[str],
                             output_dir: Path) -> Dict[str, str]:
    """
    Export cash flow analysis data to file(s).
    
    Args:
        cash_flows: The cash flow statements to analyze and export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    if not cash_flows:
        return {}
        
    result = {}
    symbol = cash_flows[0].symbol.upper()
    period = cash_flows[0].fiscal_period
    date_range = f"{cash_flows[0].fiscal_date}_to_{cash_flows[-1].fiscal_date}"
    
    # Generate filename
    base_filename = generate_export_filename(
        'cash_flow_analysis', 
        [symbol], 
        additional_parts=[period, date_range]
    )
    
    ensure_directory(output_dir)
    
    # Sort statements by date
    sorted_statements = sorted(cash_flows, key=lambda s: s.fiscal_date)
    
    # Prepare analysis data
    operating_values = [s.operating_activities.value for s in sorted_statements]
    investing_values = [s.investing_activities.value for s in sorted_statements]
    financing_values = [s.financing_activities.value for s in sorted_statements]
    
    # Calculate trends
    operating_trend = (operating_values[-1] - operating_values[0]) if len(operating_values) >= 2 else None  
    investing_trend = (investing_values[-1] - investing_values[0]) if len(investing_values) >= 2 else None
    financing_trend = (financing_values[-1] - financing_values[0]) if len(financing_values) >= 2 else None
    
    # Calculate averages
    operating_avg = sum(operating_values) / len(operating_values) if operating_values else 0
    investing_avg = sum(investing_values) / len(investing_values) if investing_values else 0
    financing_avg = sum(financing_values) / len(financing_values) if financing_values else 0
    
    # Free Cash Flow data if available
    fcf_values = [s.free_cash_flow.value for s in sorted_statements 
                 if s.free_cash_flow and s.free_cash_flow.value_str != "N/A"]
    fcf_trend = (fcf_values[-1] - fcf_values[0]) if len(fcf_values) >= 2 else None
    fcf_avg = sum(fcf_values) / len(fcf_values) if fcf_values else 0
    
    # Cash position change
    beginning_cash = sorted_statements[0].beginning_cash.value if sorted_statements else 0
    ending_cash = sorted_statements[-1].ending_cash.value if sorted_statements else 0
    cash_change = ending_cash - beginning_cash
    cash_pct_change = (cash_change / beginning_cash * 100) if beginning_cash != 0 else None
    
    # Create analysis object
    analysis = {
        "symbol": symbol,
        "period": period,
        "analysis_range": date_range,
        "currency": sorted_statements[0].currency if sorted_statements else "USD",
        "operating_cash_flow": {
            "values_by_period": dict(zip([s.fiscal_date for s in sorted_statements], operating_values)),
            "average": operating_avg,
            "trend": operating_trend,
            "growth_pct": (operating_trend / abs(operating_values[0]) * 100) if operating_values and operating_values[0] != 0 and operating_trend is not None else None,
        },
        "investing_cash_flow": {
            "values_by_period": dict(zip([s.fiscal_date for s in sorted_statements], investing_values)),
            "average": investing_avg,
            "trend": investing_trend,
            "growth_pct": (investing_trend / abs(investing_values[0]) * 100) if investing_values and investing_values[0] != 0 and investing_trend is not None else None,
        },
        "financing_cash_flow": {
            "values_by_period": dict(zip([s.fiscal_date for s in sorted_statements], financing_values)),
            "average": financing_avg,
            "trend": financing_trend,
            "growth_pct": (financing_trend / abs(financing_values[0]) * 100) if financing_values and financing_values[0] != 0 and financing_trend is not None else None,
        },
        "cash_position": {
            "beginning": beginning_cash,
            "ending": ending_cash,
            "net_change": cash_change,
            "change_pct": cash_pct_change
        }
    }
    
    # Add free cash flow data if available
    if fcf_values:
        analysis["free_cash_flow"] = {
            "values_by_period": dict(zip([s.fiscal_date for s in sorted_statements if s.free_cash_flow and s.free_cash_flow.value_str != "N/A"], fcf_values)),
            "average": fcf_avg,
            "trend": fcf_trend,
            "growth_pct": (fcf_trend / abs(fcf_values[0]) * 100) if fcf_values and fcf_values[0] != 0 and fcf_trend is not None else None,
        }
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.writer(f)
            
            # Write header information
            csv_writer.writerow(["Cash Flow Analysis", symbol])
            csv_writer.writerow(["Period", period])
            csv_writer.writerow(["Date Range", date_range])
            csv_writer.writerow(["Currency", sorted_statements[0].currency if sorted_statements else "USD"])
            csv_writer.writerow([])  # Empty row
            
            # Write column headers for time series data
            date_headers = ["Cash Flow Category", "Metric"] + [s.fiscal_date for s in sorted_statements]
            csv_writer.writerow(date_headers)
            
            # Write operating cash flow data
            csv_writer.writerow(["Operating Cash Flow", "Value"] + operating_values)
            
            # Write investing cash flow data
            csv_writer.writerow(["Investing Cash Flow", "Value"] + investing_values)
            
            # Write financing cash flow data
            csv_writer.writerow(["Financing Cash Flow", "Value"] + financing_values)
            
            # Write free cash flow data if available
            if fcf_values and len(fcf_values) == len(sorted_statements):
                csv_writer.writerow(["Free Cash Flow", "Value"] + fcf_values)
            
            # Write cash position data
            csv_writer.writerow([])  # Empty row
            csv_writer.writerow(["Cash Position", "Beginning", str(beginning_cash)])
            csv_writer.writerow(["", "Ending", str(ending_cash)])
            csv_writer.writerow(["", "Net Change", str(cash_change)])
            csv_writer.writerow(["", "Change %", str(cash_pct_change) if cash_pct_change is not None else "N/A"])
            
            # Write trend analysis
            csv_writer.writerow([])  # Empty row
            csv_writer.writerow(["Trend Analysis", "Average", "Change", "Growth %"])
            
            # Operating
            operating_growth_pct = (operating_trend / abs(operating_values[0]) * 100) if operating_values and operating_values[0] != 0 and operating_trend is not None else "N/A"
            csv_writer.writerow(["Operating Cash Flow", str(operating_avg), str(operating_trend) if operating_trend is not None else "N/A", str(operating_growth_pct)])
            
            # Investing
            investing_growth_pct = (investing_trend / abs(investing_values[0]) * 100) if investing_values and investing_values[0] != 0 and investing_trend is not None else "N/A"
            csv_writer.writerow(["Investing Cash Flow", str(investing_avg), str(investing_trend) if investing_trend is not None else "N/A", str(investing_growth_pct)])
            
            # Financing
            financing_growth_pct = (financing_trend / abs(financing_values[0]) * 100) if financing_values and financing_values[0] != 0 and financing_trend is not None else "N/A"
            csv_writer.writerow(["Financing Cash Flow", str(financing_avg), str(financing_trend) if financing_trend is not None else "N/A", str(financing_growth_pct)])
            
            # Free Cash Flow
            if fcf_values:
                fcf_growth_pct = (fcf_trend / abs(fcf_values[0]) * 100) if fcf_values and fcf_values[0] != 0 and fcf_trend is not None else "N/A"
                csv_writer.writerow(["Free Cash Flow", str(fcf_avg), str(fcf_trend) if fcf_trend is not None else "N/A", str(fcf_growth_pct)])
                
        result['csv'] = str(csv_path)
    
    return result

def export_executives(management_team: ManagementTeam, formats: List[str], 
                     output_dir: Path) -> Dict[str, str]:
    """
    Export executives data to file(s).
    
    Args:
        management_team: The management team to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = management_team.symbol.upper()
    
    # Generate filename
    base_filename = generate_export_filename(
        'executives', 
        [symbol]
    )
    
    ensure_directory(output_dir)
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(management_team.to_dict(), f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(f, fieldnames=ManagementTeam.get_csv_headers())
            csv_writer.writeheader()
            
            for row in management_team.get_csv_rows():
                csv_writer.writerow(row)
                
        result['csv'] = str(csv_path)
    
    return result


def export_executive_profile(executive: Executive, company_name: str, symbol: str,
                            formats: List[str], output_dir: Path) -> Dict[str, str]:
    """
    Export a single executive's profile to file(s).
    
    Args:
        executive: The executive to export
        company_name: Company name
        symbol: Company symbol
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = symbol.upper()
    
    # Clean up executive name for filename
    exec_name_clean = executive.name.lower().replace(' ', '_')
    
    # Generate filename
    base_filename = generate_export_filename(
        'executive_profile', 
        [symbol, exec_name_clean]
    )
    
    ensure_directory(output_dir)
    
    # Export to JSON
    if 'json' in formats:
        # Create a profile dictionary with executive and company info
        profile = {
            "company": {
                "symbol": symbol,
                "name": company_name
            },
            "executive": executive.to_dict()
        }
        
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(profile, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            # Get CSV row from executive but add company info
            row = executive.to_csv_row()
            row["Symbol"] = symbol
            row["Company"] = company_name
            
            # Write as CSV
            csv_writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            csv_writer.writeheader()
            csv_writer.writerow(row)
                
        result['csv'] = str(csv_path)
    
    return result


def export_compensation_analysis(management_team: ManagementTeam, formats: List[str],
                                output_dir: Path) -> Dict[str, str]:
    """
    Export executive compensation analysis to file(s).
    
    Args:
        management_team: The management team to analyze
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = management_team.symbol.upper()
    
    # Generate filename
    base_filename = generate_export_filename(
        'executive_compensation', 
        [symbol]
    )
    
    ensure_directory(output_dir)
    
    # Filter executives with compensation data
    execs_with_pay = [exec for exec in management_team.executives if exec.pay is not None]
    
    if not execs_with_pay:
        return {}  # No compensation data available
    
    # Calculate statistics (assuming all in same currency)
    total_comp = sum(exec.pay for exec in execs_with_pay)
    avg_comp = total_comp / len(execs_with_pay) if execs_with_pay else 0
    median_pay = sorted([exec.pay for exec in execs_with_pay])[len(execs_with_pay)//2] if len(execs_with_pay) > 0 else 0
    
    # Get CEO pay if available
    ceo = management_team.get_ceo()
    ceo_pay = ceo.pay if ceo else None
    
    # Create analysis dictionary
    analysis = {
        "company": {
            "symbol": symbol,
            "name": management_team.name
        },
        "executives_with_compensation": len(execs_with_pay),
        "compensation_data": {
            "currency": execs_with_pay[0].currency if execs_with_pay else "N/A",
            "total": total_comp,
            "average": avg_comp,
            "median": median_pay,
            "ceo": ceo_pay,
            "ceo_to_average_ratio": (ceo_pay / avg_comp) if (ceo_pay and avg_comp > 0) else None,
        },
        "executives": [
            {
                "name": exec.name,
                "title": exec.title,
                "compensation": exec.pay,
                "year": exec.year
            }
            for exec in sorted(execs_with_pay, key=lambda e: e.pay or 0, reverse=True)
        ]
    }
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.writer(f)
            
            # Write header and company info
            csv_writer.writerow(["Company", "Symbol", "Executives with Compensation Data"])
            csv_writer.writerow([management_team.name, symbol, len(execs_with_pay)])
            csv_writer.writerow([])
            
            # Write statistics
            csv_writer.writerow(["Compensation Statistics (in original currency)"])
            currency = execs_with_pay[0].currency if execs_with_pay else "N/A"
            csv_writer.writerow(["Currency", currency])
            csv_writer.writerow(["Total Compensation", f"{total_comp:,.2f}"])
            csv_writer.writerow(["Average Compensation", f"{avg_comp:,.2f}"])
            csv_writer.writerow(["Median Compensation", f"{median_pay:,.2f}"])
            
            if ceo and ceo.pay:
                csv_writer.writerow(["CEO Compensation", f"{ceo.pay:,.2f}"])
                if avg_comp > 0:
                    csv_writer.writerow(["CEO to Average Ratio", f"{(ceo.pay / avg_comp):.2f}x"])
            
            csv_writer.writerow([])
            
            # Write individual executives
            csv_writer.writerow(["Executive Compensation Ranking"])
            csv_writer.writerow(["Rank", "Name", "Title", "Compensation", "Year"])
            
            for i, exec in enumerate(sorted(execs_with_pay, key=lambda e: e.pay or 0, reverse=True), 1):
                csv_writer.writerow([
                    i, 
                    exec.name, 
                    exec.title, 
                    f"{exec.pay:,.2f}" if exec.pay else "N/A",
                    exec.year or "N/A"
                ])
                
        result['csv'] = str(csv_path)
    
    return result

def export_market_cap(market_cap_history: MarketCapHistory, formats: List[str], 
                     output_dir: Path) -> Dict[str, str]:
    """
    Export market capitalization history data to file(s).
    
    Args:
        market_cap_history: The market cap history to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = market_cap_history.symbol.upper()
    interval = market_cap_history.interval
    
    # Generate filename with start and end dates
    start_date = market_cap_history.points[0].date.isoformat() if market_cap_history.points and market_cap_history.points[0].date else "unknown"
    end_date = market_cap_history.points[-1].date.isoformat() if market_cap_history.points and market_cap_history.points[-1].date else "unknown"
    
    base_filename = generate_export_filename(
        'market_cap', 
        [symbol], 
        additional_parts=[interval, f"{start_date}_to_{end_date}"]
    )
    
    ensure_directory(output_dir)
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(market_cap_history.to_dict(), f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(f, fieldnames=MarketCapHistory.get_csv_headers())
            csv_writer.writeheader()
            
            for row in market_cap_history.get_csv_rows():
                csv_writer.writerow(row)
                
        result['csv'] = str(csv_path)
    
    return result


def export_market_cap_comparison(symbol: str, daily_history: MarketCapHistory, 
                                monthly_history: MarketCapHistory,
                                formats: List[str], output_dir: Path) -> Dict[str, Any]:
    """
    Export market capitalization comparison data to file(s).
    
    Args:
        symbol: The stock symbol
        daily_history: The MarketCapHistory with daily interval
        monthly_history: The MarketCapHistory with monthly interval
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path(s)
    """
    result = {}
    symbol = symbol.upper()
    
    # Generate filename for the comparison
    end_date = daily_history.points[-1].date.isoformat() if daily_history.points and daily_history.points[-1].date else "current"
    
    base_filename = generate_export_filename(
        'market_cap_comparison', 
        [symbol], 
        additional_parts=[end_date]
    )
    
    ensure_directory(output_dir)
    
    # Export to JSON - combined comparison file
    if 'json' in formats:
        # Create comparison summary
        comparison = {
            "symbol": symbol,
            "date": end_date,
            "current_market_cap": daily_history.summary.end_cap if daily_history.summary else None,
            "current_market_cap_formatted": daily_history.summary.end_cap_formatted if daily_history.summary else None,
            "short_term": {
                "interval": daily_history.interval,
                "summary": daily_history.summary.to_dict() if daily_history.summary else None
            },
            "long_term": {
                "interval": monthly_history.interval,
                "summary": monthly_history.summary.to_dict() if monthly_history.summary else None
            },
            "daily_history": daily_history.to_dict(),
            "monthly_history": monthly_history.to_dict()
        }
        
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(comparison, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV - separate files for daily and monthly
    if 'csv' in formats:
        # Create a directory for all CSVs
        csv_dir = output_dir / f"{base_filename}_csv"
        ensure_directory(csv_dir)
        
        # Export daily history
        daily_csv_path = csv_dir / f"{symbol}_market_cap_daily.csv"
        with open(daily_csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(f, fieldnames=MarketCapHistory.get_csv_headers())
            csv_writer.writeheader()
            for row in daily_history.get_csv_rows():
                csv_writer.writerow(row)
                
        # Export monthly history
        monthly_csv_path = csv_dir / f"{symbol}_market_cap_monthly.csv"
        with open(monthly_csv_path, 'w', newline='') as f:
            csv_writer = csv.DictWriter(f, fieldnames=MarketCapHistory.get_csv_headers())
            csv_writer.writeheader()
            for row in monthly_history.get_csv_rows():
                csv_writer.writerow(row)
        
        # Export comparison summary
        summary_csv_path = csv_dir / f"{symbol}_market_cap_comparison.csv"
        with open(summary_csv_path, 'w', newline='') as f:
            csv_writer = csv.writer(f)
            
            # Write header and basic info
            csv_writer.writerow(["Symbol", symbol])
            csv_writer.writerow(["Date", end_date])
            csv_writer.writerow(["Current Market Cap", daily_history.summary.end_cap_formatted if daily_history.summary else "N/A"])
            csv_writer.writerow([])  # Empty row
            
            # Write comparison table
            csv_writer.writerow(["Period", "Start", "End", "Change", "% Change", "Min", "Max"])
            
            if daily_history.summary:
                csv_writer.writerow([
                    f"Short-term ({daily_history.interval})",
                    daily_history.summary.start_cap_formatted,
                    daily_history.summary.end_cap_formatted,
                    daily_history.summary.change_value_formatted,
                    daily_history.summary.change_percent_formatted,
                    daily_history.summary.min_cap_formatted,
                    daily_history.summary.max_cap_formatted
                ])
                
            if monthly_history.summary:
                csv_writer.writerow([
                    f"Long-term ({monthly_history.interval})",
                    monthly_history.summary.start_cap_formatted,
                    monthly_history.summary.end_cap_formatted,
                    monthly_history.summary.change_value_formatted,
                    monthly_history.summary.change_percent_formatted,
                    monthly_history.summary.min_cap_formatted,
                    monthly_history.summary.max_cap_formatted
                ])
                
        result['csv'] = [str(daily_csv_path), str(monthly_csv_path), str(summary_csv_path)]
    
    return result

def export_analyst_estimates(estimates: AnalystEstimates, formats: List[str], 
                            output_dir: Path) -> Dict[str, str]:
    """
    Export analyst estimates data to file(s).
    
    Args:
        estimates: The analyst estimates to export
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = estimates.symbol.upper()
    
    # Generate base filename
    base_filename = generate_export_filename(
        'analyst_estimates', 
        [symbol],
        additional_parts=[]
    )
    
    ensure_directory(output_dir)
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(estimates.to_dict(), f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV - multiple files for different sections
    if 'csv' in formats:
        # Create a directory for all CSVs
        csv_dir = output_dir / f"{base_filename}_csv"
        ensure_directory(csv_dir)
        
        csv_paths = []
        
        # EPS estimates CSV
        if estimates.quarterly_eps_estimates or estimates.annual_eps_estimates:
            eps_csv_path = csv_dir / f"{symbol}_eps_estimates.csv"
            
            with open(eps_csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(f, fieldnames=AnalystEstimates.get_csv_headers_eps())
                csv_writer.writeheader()
                
                for row in estimates.get_csv_rows_eps_estimates():
                    csv_writer.writerow(row)
                    
            csv_paths.append(str(eps_csv_path))
            
        # Revenue estimates CSV
        if estimates.quarterly_revenue_estimates or estimates.annual_revenue_estimates:
            revenue_csv_path = csv_dir / f"{symbol}_revenue_estimates.csv"
            
            with open(revenue_csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(f, fieldnames=AnalystEstimates.get_csv_headers_revenue())
                csv_writer.writeheader()
                
                for row in estimates.get_csv_rows_revenue_estimates():
                    csv_writer.writerow(row)
                    
            csv_paths.append(str(revenue_csv_path))
            
        # Recommendations CSV
        if estimates.recommendation_trends:
            rec_csv_path = csv_dir / f"{symbol}_recommendations.csv"
            
            with open(rec_csv_path, 'w', newline='') as f:
                csv_writer = csv.DictWriter(f, fieldnames=AnalystEstimates.get_csv_headers_recommendations())
                csv_writer.writeheader()
                
                for trend in estimates.recommendation_trends:
                    csv_writer.writerow(trend.to_csv_row())
                    
            csv_paths.append(str(rec_csv_path))
            
        # Price target CSV
        if estimates.price_target:
            price_csv_path = csv_dir / f"{symbol}_price_target.csv"
            
            with open(price_csv_path, 'w', newline='') as f:
                csv_writer = csv.writer(f)
                
                # Write header
                csv_writer.writerow(["Target Type", "Mean Target", "Median Target", "High Target", "Low Target", "Analyst Count", "Currency"])
                
                # Write data
                target = estimates.price_target
                csv_writer.writerow([
                    target.target_type.title(),
                    f"${target.mean_target:.2f}",
                    f"${target.median_target:.2f}" if target.median_target is not None else "N/A",
                    f"${target.high_target:.2f}" if target.high_target is not None else "N/A",
                    f"${target.low_target:.2f}" if target.low_target is not None else "N/A",
                    str(target.analyst_count),
                    target.currency
                ])
                    
            csv_paths.append(str(price_csv_path))
                
        result['csv'] = csv_paths
    
    return result


def export_eps_comparison(symbols: List[str], estimates_list: List[AnalystEstimates], 
                         period_type: str, formats: List[str], output_dir: Path) -> Dict[str, str]:
    """
    Export a comparison of EPS estimates for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        estimates_list: List of AnalystEstimates objects
        period_type: 'quarterly' or 'annual'
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    
    # Generate base filename
    base_filename = generate_export_filename(
        f'{period_type}_eps_comparison', 
        symbols,
        additional_parts=[]
    )
    
    ensure_directory(output_dir)
    
    # Prepare comparison data
    comparison_data = {
        "symbols": symbols,
        "period_type": period_type,
        "comparisons": []
    }
    
    all_periods = set()
    
    # Extract all the estimates
    for estimates in estimates_list:
        estimates_data = {
            "symbol": estimates.symbol,
            "estimates": []
        }
        
        # Choose the correct set of estimates
        if period_type.lower() == 'quarterly':
            estimate_list = estimates.quarterly_eps_estimates
        else:
            estimate_list = estimates.annual_eps_estimates
            
        # Process each estimate
        for est in estimate_list:
            all_periods.add(est.period)
            
            estimates_data["estimates"].append({
                "period": est.period,
                "period_end_date": est.period_end_date,
                "estimate_value": est.estimate_value,
                "actual_value": est.actual_value,
                "surprise_value": est.surprise_value,
                "surprise_percent": est.surprise_percent
            })
            
        comparison_data["comparisons"].append(estimates_data)
            
    # Add periods to the comparison data
    comparison_data["all_periods"] = sorted(list(all_periods))
    
    # Calculate growth rates if we have annual estimates
    if period_type.lower() == 'annual':
        growth_rates = []
        
        for estimates in estimates_list:
            if period_type.lower() == 'annual':
                estimate_list = estimates.annual_eps_estimates
            else:
                estimate_list = estimates.quarterly_eps_estimates
                
            # Sort by period to ensure correct order
            sorted_ests = sorted(estimate_list, key=lambda e: e.period)
            
            if len(sorted_ests) >= 2:
                # Calculate YoY growth from current to next year's estimate
                current_est = sorted_ests[0].estimate_value
                next_est = sorted_ests[1].estimate_value
                
                if current_est > 0:
                    growth = ((next_est - current_est) / current_est) * 100
                    growth_rates.append({
                        "symbol": estimates.symbol,
                        "current_period": sorted_ests[0].period,
                        "next_period": sorted_ests[1].period,
                        "current_estimate": current_est,
                        "next_estimate": next_est,
                        "growth_percent": growth
                    })
                else:
                    # Handle division by zero or negative EPS
                    if current_est < 0 and next_est > 0:
                        status = "positive_turnaround"
                    elif current_est <= 0 and next_est <= 0 and next_est > current_est:
                        status = "improving_negative_eps"
                    else:
                        status = "declining_negative_eps"
                        
                    growth_rates.append({
                        "symbol": estimates.symbol,
                        "current_period": sorted_ests[0].period,
                        "next_period": sorted_ests[1].period,
                        "current_estimate": current_est,
                        "next_estimate": next_est,
                        "growth_status": status
                    })
            else:
                growth_rates.append({
                    "symbol": estimates.symbol,
                    "status": "insufficient_data"
                })
                
        # Add growth rates to the comparison data
        comparison_data["growth_rates"] = growth_rates
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            # Create dynamic headers with symbol names
            headers = ['Period']
            for symbol in symbols:
                headers.append(f"{symbol.upper()} Est. EPS")
                headers.append(f"{symbol.upper()} Act. EPS")
            
            csv_writer = csv.writer(f)
            csv_writer.writerow(headers)
            
            # Write rows for each period
            for period in sorted(all_periods):
                row = [period]
                
                for estimates in estimates_list:
                    if period_type.lower() == 'quarterly':
                        estimate_list = estimates.quarterly_eps_estimates
                    else:
                        estimate_list = estimates.annual_eps_estimates
                        
                    # Find the estimate for this period
                    estimate = next((est for est in estimate_list if est.period == period), None)
                    
                    if estimate:
                        row.append(f"{estimate.estimate_value:.2f}")
                        row.append(f"{estimate.actual_value:.2f}" if estimate.actual_value is not None else "N/A")
                    else:
                        row.append("N/A")
                        row.append("N/A")
                
                csv_writer.writerow(row)
                
            # Add growth rates if available
            if period_type.lower() == 'annual' and 'growth_rates' in comparison_data:
                csv_writer.writerow([])  # Empty row
                csv_writer.writerow(['Symbol', 'Current Period', 'Next Period', 'Current Est.', 'Next Est.', 'Growth %'])
                
                for growth in comparison_data['growth_rates']:
                    if 'growth_percent' in growth:
                        csv_writer.writerow([
                            growth['symbol'],
                            growth['current_period'],
                            growth['next_period'],
                            f"{growth['current_estimate']:.2f}",
                            f"{growth['next_estimate']:.2f}",
                            f"{growth['growth_percent']:.2f}%"
                        ])
                    elif 'growth_status' in growth:
                        csv_writer.writerow([
                            growth['symbol'],
                            growth['current_period'],
                            growth['next_period'],
                            f"{growth['current_estimate']:.2f}",
                            f"{growth['next_estimate']:.2f}",
                            growth['growth_status']
                        ])
                    else:
                        csv_writer.writerow([growth['symbol'], "Insufficient data", "", "", "", ""])
                    
        result['csv'] = str(csv_path)
    
    return result

def export_revenue_estimates(estimates: AnalystEstimates, formats: List[str], 
                            output_dir: Path) -> Dict[str, str]:
    """
    Export revenue estimates data to file(s).
    
    Args:
        estimates: The analyst estimates to export (focusing on revenue)
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    symbol = estimates.symbol.upper()
    
    # Generate base filename
    base_filename = generate_export_filename(
        'revenue_estimates', 
        [symbol],
        additional_parts=[]
    )
    
    ensure_directory(output_dir)
    
    # Get all revenue estimates data
    quarterly_estimates = estimates.quarterly_revenue_estimates
    annual_estimates = estimates.annual_revenue_estimates
    
    # Package the data for export
    revenue_data = {
        "symbol": symbol,
        "name": estimates.name,
        "currency": estimates.currency,
        "last_updated": estimates.last_updated,
        "quarterly_estimates": [est.to_dict() for est in quarterly_estimates],
        "annual_estimates": [est.to_dict() for est in annual_estimates]
    }
    
    # Calculate growth rates for annual estimates if available
    if len(annual_estimates) >= 2:
        # Sort by period to ensure correct order
        sorted_ests = sorted(annual_estimates, key=lambda e: e.period)
        
        growth_rates = []
        prev_value = None
        
        for estimate in sorted_ests:
            value = estimate.estimate_value
            
            if prev_value is not None and prev_value > 0 and value is not None:
                growth_pct = ((value - prev_value) / prev_value) * 100
                growth_rates.append({
                    "period": estimate.period,
                    "value": value,
                    "previous_value": prev_value,
                    "growth_percent": growth_pct
                })
                
            prev_value = value
            
        revenue_data["annual_growth_rates"] = growth_rates
        
        # Calculate CAGR if we have sufficient data
        if len(sorted_ests) >= 2:
            first_est = sorted_ests[0]
            last_est = sorted_ests[-1]
            
            first_value = first_est.actual_value if first_est.actual_value is not None else first_est.estimate_value
            last_value = last_est.actual_value if last_est.actual_value is not None else last_est.estimate_value
            
            years_diff = 0
            try:
                # Try to extract years from period strings
                first_year = int(first_est.period.split()[-1])
                last_year = int(last_est.period.split()[-1])
                years_diff = last_year - first_year
            except (ValueError, IndexError):
                # Fallback to assuming 1 year per estimate
                years_diff = len(sorted_ests) - 1
                
            # Calculate CAGR
            if first_value is not None and last_value is not None and first_value > 0 and years_diff > 0:
                cagr = ((last_value / first_value) ** (1 / years_diff) - 1) * 100
                
                revenue_data["cagr"] = {
                    "first_period": first_est.period,
                    "last_period": last_est.period,
                    "first_value": first_value,
                    "last_value": last_value,
                    "years": years_diff,
                    "cagr_percent": cagr
                }
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(revenue_data, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        # Create a CSV file for quarterly estimates
        if quarterly_estimates:
            quarterly_csv_path = output_dir / f"{symbol}_quarterly_revenue_estimates.csv"
            
            with open(quarterly_csv_path, 'w', newline='') as f:
                csv_writer = csv.writer(f)
                
                # Write header
                csv_writer.writerow([
                    "Period", "Period End Date", "Revenue Estimate ($M)", 
                    "Analyst Count", "Actual Revenue ($M)", "Surprise ($M)", "Surprise (%)"
                ])
                
                # Write data - sort by period end date
                sorted_ests = sorted(quarterly_estimates, key=lambda e: e.period_end_date if e.period_end_date else "9999-99-99")
                for est in sorted_ests:
                    csv_writer.writerow([
                        est.period,
                        est.period_end_date,
                        f"{est.estimate_value:,.2f}" if est.estimate_value is not None else "N/A",
                        est.estimate_count,
                        f"{est.actual_value:,.2f}" if est.actual_value is not None else "Not reported",
                        f"{est.surprise_value:,.2f}" if est.surprise_value is not None else "N/A",
                        f"{est.surprise_percent:.2f}" if est.surprise_percent is not None else "N/A"
                    ])
            
            result['quarterly_csv'] = str(quarterly_csv_path)
            
        # Create a CSV file for annual estimates
        if annual_estimates:
            annual_csv_path = output_dir / f"{symbol}_annual_revenue_estimates.csv"
            
            with open(annual_csv_path, 'w', newline='') as f:
                csv_writer = csv.writer(f)
                
                # Write header
                csv_writer.writerow([
                    "Period", "Period End Date", "Revenue Estimate ($M)", 
                    "Analyst Count", "Actual Revenue ($M)", "Surprise ($M)", "Surprise (%)"
                ])
                
                # Write data - sort by period end date
                sorted_ests = sorted(annual_estimates, key=lambda e: e.period_end_date if e.period_end_date else "9999-99-99")
                for est in sorted_ests:
                    csv_writer.writerow([
                        est.period,
                        est.period_end_date,
                        f"{est.estimate_value:,.2f}" if est.estimate_value is not None else "N/A",
                        est.estimate_count,
                        f"{est.actual_value:,.2f}" if est.actual_value is not None else "Not reported",
                        f"{est.surprise_value:,.2f}" if est.surprise_value is not None else "N/A",
                        f"{est.surprise_percent:.2f}" if est.surprise_percent is not None else "N/A"
                    ])
            
            result['annual_csv'] = str(annual_csv_path)
            
        # Create a CSV file for growth rates if available
        if "annual_growth_rates" in revenue_data and revenue_data["annual_growth_rates"]:
            growth_csv_path = output_dir / f"{symbol}_revenue_growth_rates.csv"
            
            with open(growth_csv_path, 'w', newline='') as f:
                csv_writer = csv.writer(f)
                
                # Write header
                csv_writer.writerow([
                    "Period", "Revenue Estimate ($M)", "Previous Period", "Previous Revenue ($M)", "YoY Growth (%)"
                ])
                
                # Write data
                prev_period = None
                for i, est in enumerate(sorted(annual_estimates, key=lambda e: e.period)):
                    if i > 0 and est.estimate_value is not None and prev_value is not None and prev_value > 0:
                        growth_pct = ((est.estimate_value - prev_value) / prev_value) * 100
                        
                        csv_writer.writerow([
                            est.period,
                            f"{est.estimate_value:,.2f}",
                            prev_period,
                            f"{prev_value:,.2f}",
                            f"{growth_pct:.2f}"
                        ])
                        
                    prev_period = est.period
                    prev_value = est.estimate_value
                    
                # Write CAGR if available
                if "cagr" in revenue_data:
                    cagr = revenue_data["cagr"]
                    csv_writer.writerow([])  # Empty row
                    csv_writer.writerow(["CAGR Analysis", "", "", "", ""])
                    csv_writer.writerow([
                        "First Period", "First Value ($M)", "Last Period", "Last Value ($M)", "CAGR (%)"
                    ])
                    csv_writer.writerow([
                        cagr["first_period"],
                        f"{cagr['first_value']:,.2f}",
                        cagr["last_period"],
                        f"{cagr['last_value']:,.2f}",
                        f"{cagr['cagr_percent']:.2f}"
                    ])
            
            result['growth_csv'] = str(growth_csv_path)
            
        if 'quarterly_csv' in result or 'annual_csv' in result or 'growth_csv' in result:
            result['csv'] = [
                result.get('quarterly_csv', ''),
                result.get('annual_csv', ''),
                result.get('growth_csv', '')
            ]
            # Remove empty strings
            result['csv'] = [path for path in result['csv'] if path]
    
    return result


def export_revenue_comparison(symbols: List[str], estimates_list: List[AnalystEstimates], 
                             period_type: str, formats: List[str], output_dir: Path) -> Dict[str, str]:
    """
    Export a comparison of revenue estimates for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        estimates_list: List of AnalystEstimates objects
        period_type: 'quarterly' or 'annual'
        formats: List of formats to export ('json', 'csv', or both)
        output_dir: Directory to save the exported files
        
    Returns:
        Dict mapping format to file path
    """
    result = {}
    
    # Generate base filename
    base_filename = generate_export_filename(
        f'{period_type}_revenue_comparison', 
        symbols,
        additional_parts=[]
    )
    
    ensure_directory(output_dir)
    
    # Prepare comparison data
    comparison_data = {
        "symbols": symbols,
        "period_type": period_type,
        "comparisons": []
    }
    
    all_periods = set()
    
    # Extract all the estimates
    for estimates in estimates_list:
        estimates_data = {
            "symbol": estimates.symbol,
            "estimates": []
        }
        
        # Choose the correct set of estimates
        if period_type.lower() == 'quarterly':
            estimate_list = estimates.quarterly_revenue_estimates
        else:
            estimate_list = estimates.annual_revenue_estimates
            
        # Process each estimate
        for est in estimate_list:
            all_periods.add(est.period)
            
            estimates_data["estimates"].append({
                "period": est.period,
                "period_end_date": est.period_end_date,
                "estimate_value": est.estimate_value,
                "actual_value": est.actual_value,
                "surprise_value": est.surprise_value,
                "surprise_percent": est.surprise_percent
            })
            
        comparison_data["comparisons"].append(estimates_data)
            
    # Add periods to the comparison data
    comparison_data["all_periods"] = sorted(list(all_periods))
    
    # Calculate growth rates if we have annual estimates
    if period_type.lower() == 'annual':
        growth_rates = []
        
        for estimates in estimates_list:
            if period_type.lower() == 'annual':
                estimate_list = estimates.annual_revenue_estimates
            else:
                estimate_list = estimates.quarterly_revenue_estimates
                
            # Sort by period to ensure correct order
            sorted_ests = sorted(estimate_list, key=lambda e: e.period)
            
            if len(sorted_ests) >= 2:
                # Calculate YoY growth from current to next year's estimate
                current_est = sorted_ests[0].estimate_value
                next_est = sorted_ests[1].estimate_value
                
                if current_est is not None and current_est > 0 and next_est is not None:
                    growth = ((next_est - current_est) / current_est) * 100
                    growth_rates.append({
                        "symbol": estimates.symbol,
                        "current_period": sorted_ests[0].period,
                        "next_period": sorted_ests[1].period,
                        "current_estimate": current_est,
                        "next_estimate": next_est,
                        "growth_percent": growth
                    })
                else:
                    growth_rates.append({
                        "symbol": estimates.symbol,
                        "status": "insufficient_data",
                        "reason": "Invalid or zero current estimate"
                    })
            else:
                growth_rates.append({
                    "symbol": estimates.symbol,
                    "status": "insufficient_data",
                    "reason": "Not enough estimates"
                })
                
        # Add growth rates to the comparison data
        comparison_data["growth_rates"] = growth_rates
    
    # Export to JSON
    if 'json' in formats:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        result['json'] = str(json_path)
    
    # Export to CSV
    if 'csv' in formats:
        csv_path = output_dir / f"{base_filename}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            # Create dynamic headers with symbol names
            headers = ['Period']
            for symbol in symbols:
                headers.append(f"{symbol.upper()} Est. Revenue ($M)")
                headers.append(f"{symbol.upper()} Act. Revenue ($M)")
            
            csv_writer = csv.writer(f)
            csv_writer.writerow(headers)
            
            # Write rows for each period
            for period in sorted(all_periods):
                row = [period]
                
                for estimates in estimates_list:
                    if period_type.lower() == 'quarterly':
                        estimate_list = estimates.quarterly_revenue_estimates
                    else:
                        estimate_list = estimates.annual_revenue_estimates
                        
                    # Find the estimate for this period
                    estimate = next((est for est in estimate_list if est.period == period), None)
                    
                    if estimate:
                        row.append(f"{estimate.estimate_value:,.2f}" if estimate.estimate_value is not None else "N/A")
                        row.append(f"{estimate.actual_value:,.2f}" if estimate.actual_value is not None else "N/A")
                    else:
                        row.append("N/A")
                        row.append("N/A")
                
                csv_writer.writerow(row)
                
            # Add growth rates if available
            if period_type.lower() == 'annual' and 'growth_rates' in comparison_data:
                csv_writer.writerow([])  # Empty row
                csv_writer.writerow(['Symbol', 'Current Period', 'Next Period', 'Current Est. ($M)', 'Next Est. ($M)', 'Growth (%)'])
                
                for growth in comparison_data['growth_rates']:
                    if 'growth_percent' in growth:
                        csv_writer.writerow([
                            growth['symbol'],
                            growth['current_period'],
                            growth['next_period'],
                            f"{growth['current_estimate']:,.2f}",
                            f"{growth['next_estimate']:,.2f}",
                            f"{growth['growth_percent']:.2f}"
                        ])
                    else:
                        csv_writer.writerow([
                            growth['symbol'], 
                            "Insufficient data", 
                            "", 
                            "", 
                            "",
                            growth.get('reason', '')
                        ])
                    
        result['csv'] = str(csv_path)
    
    return result