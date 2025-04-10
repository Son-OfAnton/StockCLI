"""
Data models for forex information.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class ForexPair:
    """Model for a forex currency pair."""
    symbol: str
    currency_base: str
    currency_quote: str
    name: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ForexPair':
        """Create a ForexPair instance from TwelveData API response."""
        return cls(
            symbol=data.get('symbol', ''),
            currency_base=data.get('currency_base', ''),
            currency_quote=data.get('currency_quote', ''),
            name=data.get('name')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the forex pair to a dictionary."""
        result = {
            'symbol': self.symbol,
            'currency_base': self.currency_base,
            'currency_quote': self.currency_quote,
        }
        
        if self.name:
            result['name'] = self.name
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the forex pair to a CSV row (dictionary with string values)."""
        result = {
            'symbol': self.symbol,
            'currency_base': self.currency_base,
            'currency_quote': self.currency_quote,
        }
        
        if self.name:
            result['name'] = self.name
        else:
            result['name'] = ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for forex pair data."""
        return [
            'symbol', 'currency_base', 'currency_quote', 'name'
        ]

@dataclass
class Currency:
    """Model for a currency."""
    code: str
    name: str
    currency_name: Optional[str] = None
    country: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Currency':
        """Create a Currency instance from TwelveData API response."""
        return cls(
            code=data.get('code', ''),
            name=data.get('name', ''),
            currency_name=data.get('currency_name'),
            country=data.get('country')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the currency to a dictionary."""
        result = {
            'code': self.code,
            'name': self.name,
        }
        
        if self.currency_name:
            result['currency_name'] = self.currency_name
        if self.country:
            result['country'] = self.country
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the currency to a CSV row (dictionary with string values)."""
        result = {
            'code': self.code,
            'name': self.name,
        }
        
        if self.currency_name:
            result['currency_name'] = self.currency_name
        else:
            result['currency_name'] = ''
            
        if self.country:
            result['country'] = self.country
        else:
            result['country'] = ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for currency data."""
        return [
            'code', 'name', 'currency_name', 'country'
        ]