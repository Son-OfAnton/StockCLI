"""
Data models for company information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class CompanyProfile:
    """Model for company profile information."""
    symbol: str
    name: str
    exchange: str
    country: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    ceo: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CompanyProfile':
        """Create a CompanyProfile instance from TwelveData API response."""
        # Extract basic information
        symbol = data.get('symbol', '')
        name = data.get('name', '')
        exchange = data.get('exchange', '')
        country = data.get('country', '')
        
        # Extract detailed profile information
        profile_data = data.get('profile', {})
        if not profile_data and 'meta' in data:
            profile_data = data.get('meta', {})
            
        sector = profile_data.get('sector')
        industry = profile_data.get('industry')
        description = profile_data.get('description')
        website = profile_data.get('website')
        
        # Extract employee count
        employees = None
        if 'employees' in profile_data:
            try:
                employees = int(profile_data['employees'])
            except (ValueError, TypeError):
                pass
                
        # Extract financial metrics
        market_cap = None
        if 'market_cap' in profile_data:
            try:
                market_cap = float(profile_data['market_cap'])
            except (ValueError, TypeError):
                pass
                
        pe_ratio = None
        if 'pe_ratio' in profile_data:
            try:
                pe_ratio = float(profile_data['pe_ratio'])
            except (ValueError, TypeError):
                pass
                
        price_to_book = None
        if 'price_to_book' in profile_data:
            try:
                price_to_book = float(profile_data['price_to_book'])
            except (ValueError, TypeError):
                pass
                
        dividend_yield = None
        if 'dividend_yield' in profile_data:
            try:
                dividend_yield = float(profile_data['dividend_yield'])
            except (ValueError, TypeError):
                pass
                
        # Extract 52-week high/low
        fifty_two_week_high = None
        if '52_week_high' in profile_data:
            try:
                fifty_two_week_high = float(profile_data['52_week_high'])
            except (ValueError, TypeError):
                pass
                
        fifty_two_week_low = None
        if '52_week_low' in profile_data:
            try:
                fifty_two_week_low = float(profile_data['52_week_low'])
            except (ValueError, TypeError):
                pass
                
        # Extract additional information
        ceo = profile_data.get('ceo')
        
        founded_year = None
        if 'founded_year' in profile_data:
            try:
                founded_year = int(profile_data['founded_year'])
            except (ValueError, TypeError):
                pass
                
        headquarters = profile_data.get('headquarters')
        
        return cls(
            symbol=symbol,
            name=name,
            exchange=exchange,
            country=country,
            sector=sector,
            industry=industry,
            description=description,
            website=website,
            employees=employees,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            price_to_book=price_to_book,
            dividend_yield=dividend_yield,
            fifty_two_week_high=fifty_two_week_high,
            fifty_two_week_low=fifty_two_week_low,
            ceo=ceo,
            founded_year=founded_year,
            headquarters=headquarters
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the company profile to a dictionary."""
        result = {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'country': self.country
        }
        
        # Add optional fields if they exist
        if self.sector:
            result['sector'] = self.sector
        if self.industry:
            result['industry'] = self.industry
        if self.description:
            result['description'] = self.description
        if self.website:
            result['website'] = self.website
        if self.employees is not None:
            result['employees'] = self.employees
        if self.market_cap is not None:
            result['market_cap'] = self.market_cap
        if self.pe_ratio is not None:
            result['pe_ratio'] = self.pe_ratio
        if self.price_to_book is not None:
            result['price_to_book'] = self.price_to_book
        if self.dividend_yield is not None:
            result['dividend_yield'] = self.dividend_yield
        if self.fifty_two_week_high is not None:
            result['fifty_two_week_high'] = self.fifty_two_week_high
        if self.fifty_two_week_low is not None:
            result['fifty_two_week_low'] = self.fifty_two_week_low
        if self.ceo:
            result['ceo'] = self.ceo
        if self.founded_year is not None:
            result['founded_year'] = self.founded_year
        if self.headquarters:
            result['headquarters'] = self.headquarters
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the company profile to a CSV row."""
        result = {
            'symbol': self.symbol,
            'name': self.name,
            'exchange': self.exchange,
            'country': self.country,
            'sector': self.sector if self.sector else '',
            'industry': self.industry if self.industry else '',
            'website': self.website if self.website else '',
            'employees': str(self.employees) if self.employees is not None else '',
            'market_cap': f"{self.market_cap:,.2f}" if self.market_cap is not None else '',
            'pe_ratio': f"{self.pe_ratio:.2f}" if self.pe_ratio is not None else '',
            'price_to_book': f"{self.price_to_book:.2f}" if self.price_to_book is not None else '',
            'dividend_yield': f"{self.dividend_yield:.2f}%" if self.dividend_yield is not None else '',
            'fifty_two_week_high': f"{self.fifty_two_week_high:.2f}" if self.fifty_two_week_high is not None else '',
            'fifty_two_week_low': f"{self.fifty_two_week_low:.2f}" if self.fifty_two_week_low is not None else '',
            'ceo': self.ceo if self.ceo else '',
            'founded_year': str(self.founded_year) if self.founded_year is not None else '',
            'headquarters': self.headquarters if self.headquarters else ''
        }
        
        # Description is often long, so truncate it for CSV
        if self.description:
            description = self.description
            if len(description) > 500:
                description = description[:497] + '...'
            result['description'] = description
        else:
            result['description'] = ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for company profile data."""
        return [
            'symbol', 'name', 'exchange', 'country', 'sector', 'industry',
            'description', 'website', 'employees', 'market_cap', 'pe_ratio',
            'price_to_book', 'dividend_yield', 'fifty_two_week_high',
            'fifty_two_week_low', 'ceo', 'founded_year', 'headquarters'
        ]
