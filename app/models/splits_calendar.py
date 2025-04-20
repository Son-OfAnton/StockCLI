"""
Data models for stock splits calendar information.
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Dict, Any, ClassVar, Union
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class SplitCalendarEvent:
    """Model for a single stock split calendar event."""
    
    def __init__(
        self,
        symbol: str,
        date: Optional[datetime] = None,
        from_factor: int = 1,
        to_factor: int = 1,
        ratio: float = 1.0,
        name: Optional[str] = None,
        exchange: Optional[str] = None,
        status: Optional[str] = None,  # 'announced', 'completed', etc.
    ):
        self.symbol = symbol
        self.date = date
        self.from_factor = from_factor
        self.to_factor = to_factor
        self.ratio = ratio
        self.name = name
        self.exchange = exchange
        self.status = status
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'SplitCalendarEvent':
        """Create a SplitCalendarEvent instance from TwelveData API response."""
        logger.debug(f"Parsing split calendar event data: {data}")
        
        # Parse date
        split_date = None
        if data.get('date'):
            try:
                split_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse split date: {e}")
        
        # Parse split factors
        from_factor = 1
        to_factor = 1
        split_ratio = 1.0
        
        if 'split' in data:
            split_text = data['split']
            
            # Try to parse different split formats
            if ":" in split_text:
                try:
                    from_str, to_str = split_text.split(":")
                    from_factor = int(from_str.strip())
                    to_factor = int(to_str.strip())
                    split_ratio = from_factor / to_factor if to_factor != 0 else 0.0
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Could not parse split ratio '{split_text}': {e}")
            
            elif "-for-" in split_text.lower() or " for " in split_text.lower():
                split_text = split_text.lower().replace("-for-", " for ")
                try:
                    from_str, to_str = split_text.split(" for ")
                    from_factor = int(from_str.strip())
                    to_factor = int(to_str.strip())
                    split_ratio = from_factor / to_factor if to_factor != 0 else 0.0
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Could not parse split ratio '{split_text}': {e}")
            
            # Check if it's just a decimal ratio
            elif split_text.replace(".", "").isdigit():
                try:
                    split_ratio = float(split_text)
                    # For common splits like 2.0, 3.0, 0.5, etc.
                    if split_ratio > 1:
                        from_factor = int(split_ratio)
                        to_factor = 1
                    elif split_ratio < 1 and split_ratio > 0:
                        to_factor = int(1 / split_ratio) if split_ratio != 0 else 0
                        from_factor = 1
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Could not parse split ratio '{split_text}': {e}")
        
        # If ratio is directly provided
        if 'ratio' in data and data['ratio'] is not None:
            try:
                split_ratio = float(data['ratio'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse direct split ratio: {e}")
        
        return cls(
            symbol=data.get('symbol', ''),
            date=split_date,
            from_factor=from_factor,
            to_factor=to_factor,
            ratio=split_ratio,
            name=data.get('name', ''),
            exchange=data.get('exchange', ''),
            status=data.get('status', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the stock split to a dictionary."""
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat() if self.date else None,
            'from_factor': self.from_factor,
            'to_factor': self.to_factor,
            'ratio': self.ratio,
            'split_text': self.split_text,
            'name': self.name,
            'exchange': self.exchange,
            'status': self.status
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert the split calendar event to a flat dictionary for CSV export."""
        return {
            'symbol': self.symbol,
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'from_factor': self.from_factor,
            'to_factor': self.to_factor,
            'ratio': self.ratio,
            'split_text': self.split_text,
            'name': self.name or '',
            'exchange': self.exchange or '',
            'status': self.status or ''
        }
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for split calendar event data."""
        return [
            'symbol', 'date', 'from_factor', 'to_factor', 
            'ratio', 'split_text', 'name', 'exchange', 'status'
        ]
    
    @property
    def split_text(self) -> str:
        """Get a human-readable split text."""
        return f"{self.from_factor}:{self.to_factor}"
    
    @property
    def is_forward_split(self) -> bool:
        """Check if this is a forward split (ratio > 1)."""
        return self.ratio > 1.0
    
    @property
    def is_reverse_split(self) -> bool:
        """Check if this is a reverse split (ratio < 1)."""
        return self.ratio < 1.0
    
    @property
    def effect_description(self) -> str:
        """Get a description of the split effect."""
        if self.is_forward_split:
            return f"Shareholders receive {self.from_factor} shares for every {self.to_factor} share owned"
        elif self.is_reverse_split:
            return f"Shareholders receive {self.to_factor} share for every {self.from_factor} shares owned"
        else:
            return "No change in number of shares"


class SplitsCalendar:
    """Collection of split calendar events for a date range."""
    
    def __init__(self, 
                start_date: Union[date, datetime, str], 
                end_date: Union[date, datetime, str],
                events: List[SplitCalendarEvent]):
        
        # Ensure dates are datetime.date objects
        if isinstance(start_date, str):
            self.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
        elif isinstance(start_date, datetime):
            self.start_date = start_date.date()
        else:
            self.start_date = start_date
            
        if isinstance(end_date, str):
            self.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
        elif isinstance(end_date, datetime):
            self.end_date = end_date.date()
        else:
            self.end_date = end_date
            
        self.events = events
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], 
                         start_date: Union[date, datetime, str], 
                         end_date: Union[date, datetime, str]) -> 'SplitsCalendar':
        """Create a SplitsCalendar instance from TwelveData API response."""
        events_data = data.get('events', [])
        events = [SplitCalendarEvent.from_api_response(item) for item in events_data]
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            events=events
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the splits calendar to a dictionary."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'events_count': len(self.events),
            'events': [event.to_dict() for event in self.events]
        }
    
    def get_events_by_date(self) -> Dict[date, List[SplitCalendarEvent]]:
        """
        Group events by date.
        
        Returns:
            Dictionary mapping dates to lists of events
        """
        grouped_events = defaultdict(list)
        
        for event in self.events:
            if event.date:
                grouped_events[event.date.date()].append(event)
        
        # Convert defaultdict to regular dict
        return dict(grouped_events)
    
    def get_events_by_symbol(self) -> Dict[str, List[SplitCalendarEvent]]:
        """
        Group events by symbol.
        
        Returns:
            Dictionary mapping symbols to lists of events
        """
        grouped_events = defaultdict(list)
        
        for event in self.events:
            grouped_events[event.symbol].append(event)
        
        # Convert defaultdict to regular dict
        return dict(grouped_events)
    
    def filter_by_exchange(self, exchange: str) -> 'SplitsCalendar':
        """
        Filter events by exchange.
        
        Args:
            exchange: Exchange code to filter by
            
        Returns:
            New SplitsCalendar with filtered events
        """
        filtered_events = [event for event in self.events 
                          if event.exchange and event.exchange.upper() == exchange.upper()]
        
        return SplitsCalendar(
            start_date=self.start_date,
            end_date=self.end_date,
            events=filtered_events
        )
    
    def filter_by_symbol(self, symbol: str) -> 'SplitsCalendar':
        """
        Filter events by symbol.
        
        Args:
            symbol: Stock symbol to filter by
            
        Returns:
            New SplitsCalendar with filtered events
        """
        filtered_events = [event for event in self.events 
                          if event.symbol.upper() == symbol.upper()]
        
        return SplitsCalendar(
            start_date=self.start_date,
            end_date=self.end_date,
            events=filtered_events
        )
    
    def filter_by_split_type(self, is_forward: bool = True) -> 'SplitsCalendar':
        """
        Filter events by split type (forward or reverse).
        
        Args:
            is_forward: True for forward splits, False for reverse splits
            
        Returns:
            New SplitsCalendar with filtered events
        """
        if is_forward:
            filtered_events = [event for event in self.events if event.is_forward_split]
        else:
            filtered_events = [event for event in self.events if event.is_reverse_split]
        
        return SplitsCalendar(
            start_date=self.start_date,
            end_date=self.end_date,
            events=filtered_events
        )