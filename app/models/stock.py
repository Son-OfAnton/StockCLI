"""
Data models for stock information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, ClassVar, Union
import logging

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