"""
Data models for mutual fund information.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.fund import Fund

class MutualFund(Fund):
    """Model for mutual fund data with additional mutual fund specific fields."""
    def __init__(
        self,
        symbol: str,
        name: str,
        currency: str,
        exchange: str,
        country: str,
        fund_family: Optional[str] = None,
        fund_category: Optional[str] = None,
        inception_date: Optional[datetime] = None,
        investment_objective: Optional[str] = None,
        total_assets: Optional[float] = None,
        net_expense_ratio: Optional[float] = None,
        gross_expense_ratio: Optional[float] = None,
        management_fee: Optional[float] = None,
        minimum_investment: Optional[float] = None,
        turnover_ratio: Optional[float] = None,
        yield_percentage: Optional[float] = None,
        morningstar_rating: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            name=name,
            type="mutual_fund",
            currency=currency,
            exchange=exchange,
            country=country,
            fund_family=fund_family,
            fund_category=fund_category,
            **{k: v for k, v in kwargs.items() if k in ['isin', 'mic_code', 'asset_class', 'expense_ratio']}
        )
        
        self.inception_date = inception_date
        self.investment_objective = investment_objective
        self.total_assets = total_assets
        self.net_expense_ratio = net_expense_ratio
        self.gross_expense_ratio = gross_expense_ratio
        self.management_fee = management_fee
        self.minimum_investment = minimum_investment
        self.turnover_ratio = turnover_ratio
        self.yield_percentage = yield_percentage
        self.morningstar_rating = morningstar_rating
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'MutualFund':
        """Create a MutualFund instance from TwelveData API response."""
        # Extract basic fund information using the parent class method
        fund = Fund.from_api_response(data)
        
        # Extract mutual fund specific fields
        meta = data.get('meta', {})
        
        # Parse inception date if available
        inception_date_str = meta.get('inception_date')
        inception_date = None
        if inception_date_str:
            try:
                inception_date = datetime.strptime(inception_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Create mutual fund instance with extended information
        return cls(
            symbol=fund.symbol,
            name=fund.name,
            currency=fund.currency,
            exchange=fund.exchange,
            country=fund.country,
            isin=fund.isin,
            mic_code=fund.mic_code,
            asset_class=fund.asset_class,
            expense_ratio=fund.expense_ratio,
            fund_family=fund.fund_family,
            fund_category=fund.fund_category,
            inception_date=inception_date,
            investment_objective=meta.get('investment_objective'),
            total_assets=float(meta.get('total_assets')) if meta.get('total_assets') else None,
            net_expense_ratio=float(meta.get('net_expense_ratio')) if meta.get('net_expense_ratio') else None,
            gross_expense_ratio=float(meta.get('gross_expense_ratio')) if meta.get('gross_expense_ratio') else None,
            management_fee=float(meta.get('management_fee')) if meta.get('management_fee') else None,
            minimum_investment=float(meta.get('minimum_investment')) if meta.get('minimum_investment') else None,
            turnover_ratio=float(meta.get('turnover_ratio')) if meta.get('turnover_ratio') else None,
            yield_percentage=float(meta.get('yield')) if meta.get('yield') else None,
            morningstar_rating=int(meta.get('morningstar_rating')) if meta.get('morningstar_rating') else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the mutual fund to a dictionary."""
        result = super().to_dict()
        
        # Add mutual fund specific fields
        if self.inception_date:
            result['inception_date'] = self.inception_date.strftime('%Y-%m-%d')
        if self.investment_objective:
            result['investment_objective'] = self.investment_objective
        if self.total_assets is not None:
            result['total_assets'] = self.total_assets
        if self.net_expense_ratio is not None:
            result['net_expense_ratio'] = self.net_expense_ratio
        if self.gross_expense_ratio is not None:
            result['gross_expense_ratio'] = self.gross_expense_ratio
        if self.management_fee is not None:
            result['management_fee'] = self.management_fee
        if self.minimum_investment is not None:
            result['minimum_investment'] = self.minimum_investment
        if self.turnover_ratio is not None:
            result['turnover_ratio'] = self.turnover_ratio
        if self.yield_percentage is not None:
            result['yield'] = self.yield_percentage
        if self.morningstar_rating is not None:
            result['morningstar_rating'] = self.morningstar_rating
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the mutual fund to a CSV row (dictionary with string values)."""
        result = super().to_csv_row()
        
        # Add mutual fund specific fields, handling None values
        result['inception_date'] = self.inception_date.strftime('%Y-%m-%d') if self.inception_date else ''
        result['investment_objective'] = self.investment_objective if self.investment_objective else ''
        result['total_assets'] = f"{self.total_assets:,.2f}" if self.total_assets is not None else ''
        result['net_expense_ratio'] = f"{self.net_expense_ratio:.4f}" if self.net_expense_ratio is not None else ''
        result['gross_expense_ratio'] = f"{self.gross_expense_ratio:.4f}" if self.gross_expense_ratio is not None else ''
        result['management_fee'] = f"{self.management_fee:.4f}" if self.management_fee is not None else ''
        result['minimum_investment'] = f"{self.minimum_investment:,.2f}" if self.minimum_investment is not None else ''
        result['turnover_ratio'] = f"{self.turnover_ratio:.2f}%" if self.turnover_ratio is not None else ''
        result['yield'] = f"{self.yield_percentage:.2f}%" if self.yield_percentage is not None else ''
        result['morningstar_rating'] = '★' * self.morningstar_rating if self.morningstar_rating else ''
            
        return result
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for mutual fund data."""
        basic_headers = Fund.get_csv_header()
        mutual_fund_headers = [
            'inception_date', 'investment_objective', 'total_assets', 
            'net_expense_ratio', 'gross_expense_ratio', 'management_fee', 
            'minimum_investment', 'turnover_ratio', 'yield', 'morningstar_rating'
        ]
        return basic_headers + mutual_fund_headers