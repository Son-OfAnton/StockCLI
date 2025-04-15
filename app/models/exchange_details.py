"""
Data models for exchange details and trading hours.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, ClassVar
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class TradingHoursSession:
    """Model for a single trading hours session."""
    def __init__(
        self,
        session_name: str,
        start_time: str,
        end_time: str,
        day: Optional[str] = None
    ):
        self.session_name = session_name
        self.start_time = start_time
        self.end_time = end_time
        self.day = day
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_name': self.session_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'day': self.day
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert to CSV row for export."""
        return {
            'session_name': self.session_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'day': self.day if self.day else ''
        }
    
    @classmethod
    def get_csv_header(cls) -> List[str]:
        """Get CSV header fields."""
        return ["session_name", "start_time", "end_time", "day"]


class ExchangeSchedule:
    """Model for exchange schedule including details and trading hours."""
    def __init__(
        self,
        code: str,
        name: str,
        country: str,
        timezone: str,
        sessions: List[TradingHoursSession],
        date: Optional[str] = None,
        suffix: Optional[str] = None,
        mic_code: Optional[str] = None,
        currency: Optional[str] = None,
        is_open: Optional[bool] = None,
        holidays: Optional[List[Dict[str, Any]]] = None,
        operating_mic: Optional[str] = None,
        website: Optional[str] = None,
        type: Optional[str] = None
    ):
        self.code = code
        self.name = name
        self.country = country
        self.timezone = timezone
        self.sessions = sessions
        self.date = date
        self.suffix = suffix
        self.mic_code = mic_code
        self.currency = currency
        self.is_open = is_open
        self.holidays = holidays or []
        self.operating_mic = operating_mic
        self.website = website
        self.type = type
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ExchangeSchedule':
        """Create an ExchangeSchedule instance from TwelveData API response."""
        logger.debug(f"Creating ExchangeSchedule from API data")
        
        # Extract sessions from hours section
        sessions = []
        if 'hours' in data and isinstance(data['hours'], list):
            for session_data in data['hours']:
                session = TradingHoursSession(
                    session_name=session_data.get('type', ''),
                    start_time=session_data.get('open', ''),
                    end_time=session_data.get('close', ''),
                    day=None  # Day is not provided in the API response
                )
                sessions.append(session)
        
        return cls(
            code=data.get('code', ''),
            name=data.get('exchange', ''),
            country=data.get('country', ''),
            timezone=data.get('timezone', ''),
            sessions=sessions,
            date=data.get('date'),
            suffix=data.get('suffix'),
            mic_code=data.get('mic_code'),
            currency=data.get('currency'),
            is_open=data.get('is_open'),
            holidays=data.get('holidays'),
            operating_mic=data.get('operating_mic'),
            website=data.get('website'),
            type=data.get('type')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'code': self.code,
            'name': self.name,
            'country': self.country,
            'timezone': self.timezone,
            'sessions': [session.to_dict() for session in self.sessions],
            'date': self.date,
            'suffix': self.suffix,
            'mic_code': self.mic_code,
            'currency': self.currency,
            'is_open': self.is_open,
            'holidays': self.holidays,
            'operating_mic': self.operating_mic,
            'website': self.website,
            'type': self.type
        }
    
    def to_csv_row(self) -> List[Dict[str, str]]:
        """Convert to CSV rows for export - one row per session."""
        rows = []
        if self.sessions:
            for session in self.sessions:
                session_dict = session.to_csv_row()
                session_dict.update({
                    'code': self.code,
                    'name': self.name,
                    'country': self.country,
                    'timezone': self.timezone,
                    'date': self.date if self.date else '',
                    'is_open': 'Yes' if self.is_open else 'No' if self.is_open is not None else '',
                    'currency': self.currency if self.currency else '',
                    'mic_code': self.mic_code if self.mic_code else '',
                    'suffix': self.suffix if self.suffix else '',
                    'type': self.type if self.type else ''
                })
                rows.append(session_dict)
        else:
            # If no sessions, still create one row with exchange details
            rows.append({
                'code': self.code,
                'name': self.name,
                'country': self.country,
                'timezone': self.timezone,
                'date': self.date if self.date else '',
                'is_open': 'Yes' if self.is_open else 'No' if self.is_open is not None else '',
                'currency': self.currency if self.currency else '',
                'mic_code': self.mic_code if self.mic_code else '',
                'suffix': self.suffix if self.suffix else '',
                'type': self.type if self.type else '',
                'session_name': '',
                'start_time': '',
                'end_time': '',
                'day': ''
            })
        return rows
    
    @classmethod
    def get_csv_header(cls) -> List[str]:
        """Get CSV header fields."""
        return ["code", "name", "country", "timezone", "date", "is_open", "currency", 
                "mic_code", "suffix", "type"] + TradingHoursSession.get_csv_header()