"""
Data models for stock information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, ClassVar, Union
import logging
import json

logger = logging.getLogger(__name__)

class Quote:
    """Model for a stock quote."""
    def __init__(
        self, 
        symbol: str,
        price: float,
        change: float,
        change_percent: float,
        timestamp: datetime,
        volume: Optional[int] = None,
        name: Optional[str] = None,
        currency: str = "USD",
        open_price: Optional[float] = None,
        high_price: Optional[float] = None,
        low_price: Optional[float] = None,
        previous_close: Optional[float] = None,
        fifty_two_week_high: Optional[float] = None,
        fifty_two_week_low: Optional[float] = None
    ):
        self.symbol = symbol
        self.price = price
        self.change = change
        self.change_percent = change_percent
        self.timestamp = timestamp
        self.volume = volume
        self.name = name
        self.currency = currency
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.previous_close = previous_close
        self.fifty_two_week_high = fifty_two_week_high
        self.fifty_two_week_low = fifty_two_week_low
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Quote':
        """Create a Quote instance from TwelveData API response."""
        logger.debug(f"Parsing quote data: {data}")
        
        # Handle case where the API returns a list of quotes
        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError("Empty quotes list received from API")
            data = data[0]  # Take the first quote
            
        # Check if required fields are present
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
            
        if 'symbol' not in data:
            raise ValueError("Quote data missing 'symbol' field")
        
        # Parse the timestamp
        timestamp_str = data.get('datetime')
        try:
            if timestamp_str:
                # Try to parse ISO format
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # If no timestamp provided, use current time
                timestamp = datetime.now()
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            timestamp = datetime.now()
        
        # Extract required and optional fields
        try:
            # Handle different field names that might be used in the API
            price = None
            for field in ['close', 'price', 'last']:
                if field in data and data[field]:
                    try:
                        price = float(data[field])
                        break
                    except (ValueError, TypeError):
                        pass
            
            if price is None:
                raise ValueError("No valid price field found in quote data")
                
            # Get change and percent change
            change = 0.0
            change_percent = 0.0
            
            # Try different field names for change
            for field in ['change', 'price_change']:
                if field in data and data[field]:
                    try:
                        change = float(data[field])
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Try different field names for percent change
            for field in ['percent_change', 'change_percent', 'change_percentage']:
                if field in data and data[field]:
                    try:
                        change_percent = float(data[field])
                        break
                    except (ValueError, TypeError):
                        pass
            
            return cls(
                symbol=data['symbol'],
                price=price,
                change=change,
                change_percent=change_percent,
                timestamp=timestamp,
                volume=int(data['volume']) if 'volume' in data and data['volume'] else None,
                name=data.get('name'),
                currency=data.get('currency', 'USD'),
                open_price=float(data['open']) if 'open' in data and data['open'] else None,
                high_price=float(data['high']) if 'high' in data and data['high'] else None,
                low_price=float(data['low']) if 'low' in data and data['low'] else None,
                previous_close=float(data['previous_close']) if 'previous_close' in data and data['previous_close'] else None,
                fifty_two_week_high=float(data['fifty_two_week_high']) if 'fifty_two_week_high' in data and data['fifty_two_week_high'] else None,
                fifty_two_week_low=float(data['fifty_two_week_low']) if 'fifty_two_week_low' in data and data['fifty_two_week_low'] else None,
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse quote data: {e}", exc_info=True)
            raise ValueError(f"Failed to parse quote data: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert the quote to a dictionary."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "timestamp": self.timestamp.isoformat(),
            "volume": self.volume,
            "name": self.name,
            "currency": self.currency,
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "previous_close": self.previous_close,
            "fifty_two_week_high": self.fifty_two_week_high,
            "fifty_two_week_low": self.fifty_two_week_low,
        }
        
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the quote to a CSV row (dictionary with string values)."""
        return {
            "symbol": self.symbol,
            "price": f"{self.price:.2f}" if self.price is not None else "",
            "change": f"{self.change:.2f}" if self.change is not None else "",
            "change_percent": f"{self.change_percent:.2f}" if self.change_percent is not None else "",
            "timestamp": self.timestamp.isoformat() if self.timestamp else "",
            "volume": f"{self.volume}" if self.volume is not None else "",
            "name": self.name if self.name else "",
            "currency": self.currency if self.currency else "",
            "open": f"{self.open_price:.2f}" if self.open_price is not None else "",
            "high": f"{self.high_price:.2f}" if self.high_price is not None else "",
            "low": f"{self.low_price:.2f}" if self.low_price is not None else "",
            "previous_close": f"{self.previous_close:.2f}" if self.previous_close is not None else "",
            "fifty_two_week_high": f"{self.fifty_two_week_high:.2f}" if self.fifty_two_week_high is not None else "",
            "fifty_two_week_low": f"{self.fifty_two_week_low:.2f}" if self.fifty_two_week_low is not None else "",
        }
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for quote data."""
        return [
            "symbol", "price", "change", "change_percent", "timestamp", 
            "volume", "name", "currency", "open", "high", "low", 
            "previous_close", "fifty_two_week_high", "fifty_two_week_low"
        ]
        
    def __repr__(self) -> str:
        return (f"Quote(symbol='{self.symbol}', price={self.price}, "
                f"change={self.change}, change_percent={self.change_percent})")


@dataclass
class HistoricalBar:
    """Model for a single historical data bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the bar to a dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the bar to a CSV row."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": f"{self.open:.2f}",
            "high": f"{self.high:.2f}",
            "low": f"{self.low:.2f}",
            "close": f"{self.close:.2f}",
            "volume": f"{self.volume}" if self.volume is not None else "",
        }

    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for historical bar data."""
        return ["timestamp", "open", "high", "low", "close", "volume"]


@dataclass
class TimeSeries:
    """Model for time series data."""
    symbol: str
    interval: str
    bars: List[HistoricalBar]
    currency: str = "USD"
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'TimeSeries':
        """Create a TimeSeries instance from API response."""
        symbol = data.get('meta', {}).get('symbol', '')
        interval = data.get('meta', {}).get('interval', '')
        currency = data.get('meta', {}).get('currency', 'USD')
        
        values = data.get('values', [])
        bars = []
        
        for bar_data in values:
            try:
                timestamp = datetime.fromisoformat(bar_data.get('datetime').replace('Z', '+00:00'))
                bars.append(HistoricalBar(
                    timestamp=timestamp,
                    open=float(bar_data.get('open')),
                    high=float(bar_data.get('high')),
                    low=float(bar_data.get('low')),
                    close=float(bar_data.get('close')),
                    volume=int(bar_data.get('volume')) if bar_data.get('volume') else None
                ))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Skipping invalid bar data: {e}")
                continue
                
        return cls(
            symbol=symbol,
            interval=interval,
            bars=bars,
            currency=currency
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the time series to a dictionary."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "currency": self.currency,
            "bars": [bar.to_dict() for bar in self.bars],
        }


@dataclass
class TechnicalIndicator:
    """Model for technical indicator data."""
    symbol: str
    indicator: str
    values: List[float]
    timestamps: List[datetime]
    parameters: Dict[str, Any]
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'TechnicalIndicator':
        """Create a TechnicalIndicator instance from API response."""
        meta = data.get('meta', {})
        values_data = data.get('values', [])
        
        values = []
        timestamps = []
        
        for item in values_data:
            try:
                timestamps.append(datetime.fromisoformat(item.get('datetime').replace('Z', '+00:00')))
                # Most indicators have a 'value' field, but some might have different names
                for key in ['value', 'sma', 'rsi', 'macd', 'macd_signal', 'macd_hist']:
                    if key in item:
                        values.append(float(item[key]))
                        break
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid indicator data: {e}")
                continue
                
        return cls(
            symbol=meta.get('symbol', ''),
            indicator=meta.get('indicator', ''),
            values=values,
            timestamps=timestamps,
            parameters={
                k: v for k, v in meta.items() 
                if k not in ['symbol', 'indicator', 'exchange']
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the indicator to a dictionary."""
        data = []
        for i, (ts, val) in enumerate(zip(self.timestamps, self.values)):
            data.append({
                "timestamp": ts.isoformat(),
                "value": val,
            })
            
        return {
            "symbol": self.symbol,
            "indicator": self.indicator,
            "parameters": self.parameters,
            "data": data,
        }