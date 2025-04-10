"""
Data models for cryptocurrency information.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class CryptoPair:
    """Model for a cryptocurrency trading pair."""
    symbol: str
    base_currency: str
    quote_currency: str
    exchange: str
    available_exchanges: List[str]
    currency_base: str
    currency_quote: str
    
    # Additional fields that may be present
    name: Optional[str] = None
    price: Optional[float] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CryptoPair':
        """Create a CryptoPair instance from TwelveData API response."""
        # Handle different formats of available_exchanges in the API response
        if 'available_exchanges' in data:
            if isinstance(data['available_exchanges'], list):
                available_exchanges = data['available_exchanges']
            elif isinstance(data['available_exchanges'], str):
                available_exchanges = data['available_exchanges'].split(',')
            else:
                available_exchanges = []
        else:
            available_exchanges = []
            
        return cls(
            symbol=data.get('symbol', ''),
            base_currency=data.get('base_currency', ''),
            quote_currency=data.get('quote_currency', ''),
            exchange=data.get('exchange', ''),
            available_exchanges=available_exchanges,
            currency_base=data.get('currency_base', ''),
            currency_quote=data.get('currency_quote', ''),
            name=data.get('name'),
            price=float(data.get('price')) if data.get('price') else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the cryptocurrency pair to a dictionary."""
        result = {
            'symbol': self.symbol,
            'base_currency': self.base_currency,
            'quote_currency': self.quote_currency,
            'exchange': self.exchange,
            'available_exchanges': self.available_exchanges,
            'currency_base': self.currency_base,
            'currency_quote': self.currency_quote,
        }
        
        if self.name:
            result['name'] = self.name
        if self.price is not None:
            result['price'] = self.price
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the cryptocurrency pair to a CSV row (dictionary with string values)."""
        result = {
            'symbol': self.symbol,
            'base_currency': self.base_currency,
            'quote_currency': self.quote_currency,
            'exchange': self.exchange,
            'available_exchanges': ','.join(self.available_exchanges),
            'currency_base': self.currency_base,
            'currency_quote': self.currency_quote,
        }
        
        if self.name:
            result['name'] = self.name
        else:
            result['name'] = ''
            
        if self.price is not None:
            result['price'] = f"{self.price:.8f}"
        else:
            result['price'] = ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for cryptocurrency data."""
        return [
            'symbol', 'base_currency', 'quote_currency', 'exchange',
            'available_exchanges', 'currency_base', 'currency_quote',
            'name', 'price'
        ]