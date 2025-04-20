"""
Data models for dividend information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, ClassVar, Union
import logging

logger = logging.getLogger(__name__)


class Dividend:
    """Model for a stock dividend payment."""
    
    def __init__(
        self,
        symbol: str,
        payment_date: Optional[datetime] = None,
        ex_dividend_date: Optional[datetime] = None,
        record_date: Optional[datetime] = None,
        declaration_date: Optional[datetime] = None,
        amount: float = 0.0,
        currency: str = "USD",
        frequency: Optional[str] = None,
        description: Optional[str] = None
    ):
        self.symbol = symbol
        self.payment_date = payment_date
        self.ex_dividend_date = ex_dividend_date
        self.record_date = record_date
        self.declaration_date = declaration_date
        self.amount = amount
        self.currency = currency
        self.frequency = frequency
        self.description = description
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], symbol: str) -> 'Dividend':
        """Create a Dividend instance from TwelveData API response."""
        logger.debug(f"Parsing dividend data: {data}")
        
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
        
        return cls(
            symbol=symbol,
            payment_date=payment_date,
            ex_dividend_date=ex_dividend_date,
            record_date=record_date,
            declaration_date=declaration_date,
            amount=amount,
            currency=data.get('currency', 'USD'),
            frequency=data.get('frequency'),
            description=data.get('description')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dividend object to a dictionary."""
        return {
            'symbol': self.symbol,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'ex_dividend_date': self.ex_dividend_date.isoformat() if self.ex_dividend_date else None,
            'record_date': self.record_date.isoformat() if self.record_date else None,
            'declaration_date': self.declaration_date.isoformat() if self.declaration_date else None,
            'amount': self.amount,
            'currency': self.currency,
            'frequency': self.frequency,
            'description': self.description
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert the dividend to a flat dictionary for CSV export."""
        return {
            'symbol': self.symbol,
            'payment_date': self.payment_date.strftime('%Y-%m-%d') if self.payment_date else '',
            'ex_dividend_date': self.ex_dividend_date.strftime('%Y-%m-%d') if self.ex_dividend_date else '',
            'record_date': self.record_date.strftime('%Y-%m-%d') if self.record_date else '',
            'declaration_date': self.declaration_date.strftime('%Y-%m-%d') if self.declaration_date else '',
            'amount': self.amount,
            'currency': self.currency,
            'frequency': self.frequency or '',
            'description': self.description or ''
        }
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for dividend data."""
        return [
            'symbol', 'payment_date', 'ex_dividend_date', 'record_date',
            'declaration_date', 'amount', 'currency', 'frequency', 'description'
        ]


class DividendHistory:
    """Collection of dividend data for a symbol."""
    
    def __init__(self, symbol: str, meta: Dict[str, Any], dividends: List[Dividend]):
        self.symbol = symbol
        self.name = meta.get('name', '')
        self.currency = meta.get('currency', 'USD')
        self.exchange = meta.get('exchange', '')
        self.mic_code = meta.get('mic_code', '')
        self.country = meta.get('country', '')
        self.type = meta.get('type', '')
        self.dividends = dividends
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'DividendHistory':
        """Create a DividendHistory instance from TwelveData API response."""
        meta = data.get('meta', {})
        symbol = meta.get('symbol', '')
        
        dividends_data = data.get('dividends', [])
        dividends = [Dividend.from_api_response(item, symbol) for item in dividends_data]
        
        return cls(
            symbol=symbol,
            meta=meta,
            dividends=dividends
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dividend history to a dictionary."""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'currency': self.currency,
            'exchange': self.exchange,
            'mic_code': self.mic_code,
            'country': self.country,
            'type': self.type,
            'dividends': [d.to_dict() for d in self.dividends]
        }
    
    def annual_dividends(self) -> Dict[int, float]:
        """Calculate total dividends paid per year."""
        annual_sums = {}
        
        for dividend in self.dividends:
            if dividend.payment_date:
                year = dividend.payment_date.year
                if year in annual_sums:
                    annual_sums[year] += dividend.amount
                else:
                    annual_sums[year] = dividend.amount
        
        # Sort by year
        return dict(sorted(annual_sums.items()))
    
    def total_dividends(self) -> float:
        """Calculate total dividends paid across all years."""
        return sum(dividend.amount for dividend in self.dividends)
    
    def average_annual_dividend(self) -> float:
        """Calculate the average annual dividend based on available years."""
        annual = self.annual_dividends()
        if not annual:
            return 0.0
        return sum(annual.values()) / len(annual)
    
    def dividend_growth_rate(self) -> Dict[int, float]:
        """Calculate year-over-year dividend growth rate."""
        annual = self.annual_dividends()
        years = sorted(annual.keys())
        
        growth_rates = {}
        for i in range(1, len(years)):
            current_year = years[i]
            prev_year = years[i-1]
            
            if annual[prev_year] > 0:
                growth = (annual[current_year] - annual[prev_year]) / annual[prev_year] * 100
                growth_rates[current_year] = growth
        
        return growth_rates