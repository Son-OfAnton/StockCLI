"""
Data models for stock information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class Quote:
    """Model for a stock quote."""
    symbol: str
    price: float
    change: float
    change_percent: float
    timestamp: datetime
    volume: int
    name: Optional[str] = None
    currency: str = "USD"
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Quote':
        """Create a Quote instance from API response."""
        pass

@dataclass
class HistoricalBar:
    """Model for a single historical data bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

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
        pass

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
        pass