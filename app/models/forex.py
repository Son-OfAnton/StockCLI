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
    

@dataclass
class ForexRate:
    """Model for a forex exchange rate."""
    symbol: str
    rate: float
    currency_base: str
    currency_quote: str
    timestamp: str
    name: Optional[str] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ForexRate':
        """Create a ForexRate instance from TwelveData API response."""
        # Extract base currency and quote currency from the symbol
        # Format is typically BASE/QUOTE (e.g., EUR/USD)
        symbol = data.get('symbol', '')
        currency_parts = symbol.split('/')
        base_currency = currency_parts[0] if len(currency_parts) > 0 else ''
        quote_currency = currency_parts[1] if len(currency_parts) > 1 else ''
        
        # Use explicitly provided currencies if available, otherwise use parsed ones
        base_currency = data.get('currency_base', base_currency)
        quote_currency = data.get('currency_quote', quote_currency)
        
        return cls(
            symbol=symbol,
            rate=float(data.get('rate', 0.0)),
            currency_base=base_currency,
            currency_quote=quote_currency,
            timestamp=data.get('timestamp', ''),
            name=data.get('name'),
            bid=float(data.get('bid')) if 'bid' in data else None,
            ask=float(data.get('ask')) if 'ask' in data else None,
            high=float(data.get('high')) if 'high' in data else None,
            low=float(data.get('low')) if 'low' in data else None,
            change=float(data.get('change')) if 'change' in data else None,
            change_percent=float(data.get('change_percent')) if 'change_percent' in data else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the forex rate to a dictionary."""
        result = {
            'symbol': self.symbol,
            'rate': self.rate,
            'currency_base': self.currency_base,
            'currency_quote': self.currency_quote,
            'timestamp': self.timestamp
        }
        
        # Add optional fields if present
        if self.name:
            result['name'] = self.name
        if self.bid is not None:
            result['bid'] = self.bid
        if self.ask is not None:
            result['ask'] = self.ask
        if self.high is not None:
            result['high'] = self.high
        if self.low is not None:
            result['low'] = self.low
        if self.change is not None:
            result['change'] = self.change
        if self.change_percent is not None:
            result['change_percent'] = self.change_percent
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the forex rate to a CSV row."""
        result = {
            'symbol': self.symbol,
            'rate': f"{self.rate:.6f}",
            'currency_base': self.currency_base,
            'currency_quote': self.currency_quote,
            'timestamp': self.timestamp
        }
        
        # Add optional fields if present
        if self.name:
            result['name'] = self.name
        if self.bid is not None:
            result['bid'] = f"{self.bid:.6f}"
        if self.ask is not None:
            result['ask'] = f"{self.ask:.6f}"
        if self.high is not None:
            result['high'] = f"{self.high:.6f}"
        if self.low is not None:
            result['low'] = f"{self.low:.6f}"
        if self.change is not None:
            result['change'] = f"{self.change:.6f}"
        if self.change_percent is not None:
            result['change_percent'] = f"{self.change_percent:.2f}%"
            
        return result
    
    @classmethod
    def get_csv_header(cls) -> List[str]:
        """Get CSV header fields."""
        return ["symbol", "rate", "currency_base", "currency_quote", "timestamp", 
                "name", "bid", "ask", "high", "low", "change", "change_percent"]