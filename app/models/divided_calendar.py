"""
Data models for dividend calendar information.
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Dict, Any, ClassVar, Union
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class DividendCalendarEvent:
    """Model for a single dividend calendar event."""
    
    def __init__(
        self,
        symbol: str,
        name: Optional[str] = None,
        exchange: Optional[str] = None,
        currency: str = "USD",
        payment_date: Optional[datetime] = None,
        ex_dividend_date: Optional[datetime] = None,
        record_date: Optional[datetime] = None,
        declaration_date: Optional[datetime] = None,
        amount: float = 0.0,
        frequency: Optional[str] = None,
        yield_value: Optional[float] = None,
        dividend_type: Optional[str] = None
    ):
        self.symbol = symbol
        self.name = name
        self.exchange = exchange
        self.currency = currency
        self.payment_date = payment_date
        self.ex_dividend_date = ex_dividend_date
        self.record_date = record_date
        self.declaration_date = declaration_date
        self.amount = amount
        self.frequency = frequency
        self.yield_value = yield_value
        self.dividend_type = dividend_type
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'DividendCalendarEvent':
        """Create a DividendCalendarEvent instance from TwelveData API response."""
        logger.debug(f"Parsing dividend calendar event data: {data}")
        
        # Parse dates if available (handling potential None values)
        payment_date = None
        ex_dividend_date = None
        record_date = None
        declaration_date = None
        
        if data.get('payment_date'):
            try:
                payment_date = datetime.fromisoformat(data['payment_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse payment_date: {e}")
        
        if data.get('ex_dividend_date'):
            try:
                ex_dividend_date = datetime.fromisoformat(data['ex_dividend_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse ex_dividend_date: {e}")
        
        if data.get('record_date'):
            try:
                record_date = datetime.fromisoformat(data['record_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse record_date: {e}")
        
        if data.get('declaration_date'):
            try:
                declaration_date = datetime.fromisoformat(data['declaration_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse declaration_date: {e}")
        
        # Parse amount as float
        amount = 0.0
        try:
            amount = float(data.get('amount', 0.0))
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse dividend amount: {e}")
        
        # Parse yield value as float if available
        yield_value = None
        if data.get('yield') is not None:
            try:
                yield_value = float(data.get('yield', 0.0))
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse yield value: {e}")
        
        return cls(
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            exchange=data.get('exchange', ''),
            currency=data.get('currency', 'USD'),
            payment_date=payment_date,
            ex_dividend_date=ex_dividend_date,
            record_date=record_date,
            declaration_date=declaration_date,
            amount=amount,
            frequency=data.get('frequency'),
            yield_value=yield_value,
            dividend_type=data.get('dividend_type')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dividend calendar event to a dictionary."""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'currency': self.currency,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'ex_dividend_date': self.ex_dividend_date.isoformat() if self.ex_dividend_date else None,
            'record_date': self.record_date.isoformat() if self.record_date else None,
            'declaration_date': self.declaration_date.isoformat() if self.declaration_date else None,
            'amount': self.amount,
            'frequency': self.frequency,
            'yield': self.yield_value,
            'dividend_type': self.dividend_type
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert the dividend calendar event to a flat dictionary for CSV export."""
        return {
            'symbol': self.symbol,
            'name': self.name or '',
            'exchange': self.exchange or '',
            'currency': self.currency,
            'payment_date': self.payment_date.strftime('%Y-%m-%d') if self.payment_date else '',
            'ex_dividend_date': self.ex_dividend_date.strftime('%Y-%m-%d') if self.ex_dividend_date else '',
            'record_date': self.record_date.strftime('%Y-%m-%d') if self.record_date else '',
            'declaration_date': self.declaration_date.strftime('%Y-%m-%d') if self.declaration_date else '',
            'amount': self.amount,
            'frequency': self.frequency or '',
            'yield': self.yield_value if self.yield_value is not None else '',
            'dividend_type': self.dividend_type or ''
        }
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for dividend calendar event data."""
        return [
            'symbol', 'name', 'exchange', 'currency', 'payment_date', 
            'ex_dividend_date', 'record_date', 'declaration_date', 
            'amount', 'frequency', 'yield', 'dividend_type'
        ]


class DividendCalendar:
    """Collection of dividend calendar events for a date range."""
    
    def __init__(self, 
                start_date: Union[date, datetime, str], 
                end_date: Union[date, datetime, str],
                events: List[DividendCalendarEvent]):
        
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
                         end_date: Union[date, datetime, str]) -> 'DividendCalendar':
        """Create a DividendCalendar instance from TwelveData API response."""
        events_data = data.get('events', [])
        events = [DividendCalendarEvent.from_api_response(item) for item in events_data]
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            events=events
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dividend calendar to a dictionary."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'events_count': len(self.events),
            'events': [event.to_dict() for event in self.events]
        }
    
    def get_events_by_date(self, date_field: str = 'ex_dividend_date') -> Dict[date, List[DividendCalendarEvent]]:
        """
        Group events by a specific date field.
        
        Args:
            date_field: The field to group by ('ex_dividend_date', 'payment_date', etc.)
        
        Returns:
            Dictionary mapping dates to lists of events
        """
        grouped_events = defaultdict(list)
        
        for event in self.events:
            # Get the date field value
            date_value = None
            if date_field == 'ex_dividend_date' and event.ex_dividend_date:
                date_value = event.ex_dividend_date.date()
            elif date_field == 'payment_date' and event.payment_date:
                date_value = event.payment_date.date()
            elif date_field == 'record_date' and event.record_date:
                date_value = event.record_date.date()
            elif date_field == 'declaration_date' and event.declaration_date:
                date_value = event.declaration_date.date()
                
            # If we have a valid date, add the event to that date's list
            if date_value:
                grouped_events[date_value].append(event)
        
        # Convert defaultdict to regular dict
        return dict(grouped_events)
    
    def get_events_by_symbol(self) -> Dict[str, List[DividendCalendarEvent]]:
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
    
    def filter_by_exchange(self, exchange: str) -> 'DividendCalendar':
        """
        Filter events by exchange.
        
        Args:
            exchange: Exchange code to filter by
            
        Returns:
            New DividendCalendar with filtered events
        """
        filtered_events = [event for event in self.events 
                          if event.exchange and event.exchange.upper() == exchange.upper()]
        
        return DividendCalendar(
            start_date=self.start_date,
            end_date=self.end_date,
            events=filtered_events
        )
    
    def filter_by_symbol(self, symbol: str) -> 'DividendCalendar':
        """
        Filter events by symbol.
        
        Args:
            symbol: Stock symbol to filter by
            
        Returns:
            New DividendCalendar with filtered events
        """
        filtered_events = [event for event in self.events 
                          if event.symbol.upper() == symbol.upper()]
        
        return DividendCalendar(
            start_date=self.start_date,
            end_date=self.end_date,
            events=filtered_events
        )