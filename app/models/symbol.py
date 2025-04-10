"""
Data models for symbol information.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Symbol:
    """Model for a financial symbol (stock, ETF, index, etc.)."""
    symbol: str
    name: str
    currency: str
    exchange: str
    mic_code: str
    country: str
    type: str
    
    # Additional fields that may be present
    isin: Optional[str] = None
    base_currency: Optional[str] = None
    access: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Symbol':
        """Create a Symbol instance from TwelveData API response."""
        return cls(
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            currency=data.get('currency', ''),
            exchange=data.get('exchange', ''),
            mic_code=data.get('mic_code', ''),
            country=data.get('country', ''),
            type=data.get('type', ''),
            isin=data.get('isin'),
            base_currency=data.get('base_currency'),
            access=data.get('access')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the symbol to a dictionary."""
        result = {
            'symbol': self.symbol,
            'name': self.name,
            'currency': self.currency,
            'exchange': self.exchange,
            'mic_code': self.mic_code,
            'country': self.country,
            'type': self.type,
        }
        
        if self.isin:
            result['isin'] = self.isin
        if self.base_currency:
            result['base_currency'] = self.base_currency
        if self.access:
            result['access'] = self.access
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the symbol to a CSV row (dictionary with string values)."""
        result = {
            'symbol': self.symbol,
            'name': self.name,
            'currency': self.currency,
            'exchange': self.exchange,
            'mic_code': self.mic_code,
            'country': self.country,
            'type': self.type,
        }
        
        if self.isin:
            result['isin'] = self.isin
        else:
            result['isin'] = ''
            
        if self.base_currency:
            result['base_currency'] = self.base_currency
        else:
            result['base_currency'] = ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for symbol data."""
        return [
            'symbol', 'name', 'currency', 'exchange', 'mic_code', 
            'country', 'type', 'isin', 'base_currency'
        ]

@dataclass
class Exchange:
    """Model for an exchange."""
    name: str
    code: str
    country: str
    timezone: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Exchange':
        """Create an Exchange instance from TwelveData API response."""
        return cls(
            name=data.get('name', ''),
            code=data.get('code', ''),
            country=data.get('country', ''),
            timezone=data.get('timezone')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the exchange to a dictionary."""
        result = {
            'name': self.name,
            'code': self.code,
            'country': self.country,
        }
        
        if self.timezone:
            result['timezone'] = self.timezone
            
        return result