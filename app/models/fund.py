"""
Data models for fund information.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Fund:
    """Model for fund data (ETFs and mutual funds)."""
    symbol: str
    name: str
    type: str  # 'etf' or 'mutual_fund'
    currency: str
    exchange: str
    country: str
    
    # Additional fields
    isin: Optional[str] = None
    mic_code: Optional[str] = None
    asset_class: Optional[str] = None
    expense_ratio: Optional[float] = None
    fund_family: Optional[str] = None
    fund_category: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Fund':
        """Create a Fund instance from TwelveData API response."""
        # Identify additional fields that might be present for funds
        asset_class = None
        expense_ratio = None
        fund_family = None
        fund_category = None
        
        # Extract additional fields if they're in the response
        if 'meta' in data:
            meta = data.get('meta', {})
            asset_class = meta.get('asset_class')
            expense_ratio = meta.get('expense_ratio')
            fund_family = meta.get('fund_family') or meta.get('issuer')
            fund_category = meta.get('category')
        
        return cls(
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            type=data.get('type', ''),
            currency=data.get('currency', ''),
            exchange=data.get('exchange', ''),
            country=data.get('country', ''),
            isin=data.get('isin'),
            mic_code=data.get('mic_code'),
            asset_class=asset_class,
            expense_ratio=float(expense_ratio) if expense_ratio else None,
            fund_family=fund_family,
            fund_category=fund_category
        )
    
    @classmethod
    def from_symbol(cls, symbol_data: Dict[str, Any]) -> 'Fund':
        """Create a Fund instance from a Symbol API response."""
        return cls(
            symbol=symbol_data.get('symbol', ''),
            name=symbol_data.get('name', ''),
            type=symbol_data.get('type', ''),
            currency=symbol_data.get('currency', ''),
            exchange=symbol_data.get('exchange', ''),
            country=symbol_data.get('country', ''),
            isin=symbol_data.get('isin'),
            mic_code=symbol_data.get('mic_code')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the fund to a dictionary."""
        result = {
            'symbol': self.symbol,
            'name': self.name,
            'type': self.type,
            'currency': self.currency,
            'exchange': self.exchange,
            'country': self.country,
        }
        
        # Add optional fields if they exist
        if self.isin:
            result['isin'] = self.isin
        if self.mic_code:
            result['mic_code'] = self.mic_code
        if self.asset_class:
            result['asset_class'] = self.asset_class
        if self.expense_ratio is not None:
            result['expense_ratio'] = self.expense_ratio
        if self.fund_family:
            result['fund_family'] = self.fund_family
        if self.fund_category:
            result['fund_category'] = self.fund_category
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the fund to a CSV row (dictionary with string values)."""
        result = {
            'symbol': self.symbol,
            'name': self.name,
            'type': self.type,
            'currency': self.currency,
            'exchange': self.exchange,
            'country': self.country,
            'isin': self.isin if self.isin else '',
            'mic_code': self.mic_code if self.mic_code else '',
        }
        
        # Add optional fields, handling None values
        result['asset_class'] = self.asset_class if self.asset_class else ''
        result['expense_ratio'] = f"{self.expense_ratio:.4f}" if self.expense_ratio is not None else ''
        result['fund_family'] = self.fund_family if self.fund_family else ''
        result['fund_category'] = self.fund_category if self.fund_category else ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for fund data."""
        return [
            'symbol', 'name', 'type', 'currency', 'exchange', 'country', 
            'isin', 'mic_code', 'asset_class', 'expense_ratio', 
            'fund_family', 'fund_category'
        ]