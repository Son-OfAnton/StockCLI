"""
Data models for ETF (Exchange-Traded Fund) information.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ETF:
    """Model for ETF (Exchange-Traded Fund) data."""
    symbol: str
    name: str
    currency: str
    exchange: str
    country: Optional[str] = None
    type: str = "etf"
    asset_class: Optional[str] = None  # equity, fixed_income, commodity, etc.
    expense_ratio: Optional[float] = None
    managed_assets: Optional[float] = None
    fund_family: Optional[str] = None
    nav: Optional[float] = None  # Net Asset Value
    category: Optional[str] = None  # e.g., "Large-Cap Blend", "Technology", etc.
    benchmark: Optional[str] = None
    description: Optional[str] = None
    inception_date: Optional[str] = None
    dividend_yield: Optional[float] = None
    mic_code: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'ETF':
        """Create an ETF instance from TwelveData API response."""
        # Extract all possible fields that might be in the API response
        return cls(
            symbol=data["symbol"],
            name=data.get("name", ""),
            currency=data.get("currency", ""),
            exchange=data.get("exchange", ""),
            country=data.get("country"),
            type=data.get("type", "etf"),
            asset_class=data.get("asset_class"),
            expense_ratio=float(data["expense_ratio"]) if "expense_ratio" in data and data["expense_ratio"] is not None else None,
            managed_assets=float(data["managed_assets"]) if "managed_assets" in data and data["managed_assets"] is not None else None,
            fund_family=data.get("fund_family"),
            nav=float(data["nav"]) if "nav" in data and data["nav"] is not None else None,
            category=data.get("category"),
            benchmark=data.get("benchmark"),
            description=data.get("description"),
            inception_date=data.get("inception_date"),
            dividend_yield=float(data["dividend_yield"]) if "dividend_yield" in data and data["dividend_yield"] is not None else None,
            mic_code=data.get("mic_code")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the ETF to a dictionary."""
        result = {
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "exchange": self.exchange,
            "type": self.type
        }
        
        # Add optional fields if they exist
        for attr, value in {
            "country": self.country,
            "asset_class": self.asset_class,
            "expense_ratio": self.expense_ratio,
            "managed_assets": self.managed_assets,
            "fund_family": self.fund_family,
            "nav": self.nav,
            "category": self.category,
            "benchmark": self.benchmark,
            "description": self.description,
            "inception_date": self.inception_date,
            "dividend_yield": self.dividend_yield,
            "mic_code": self.mic_code
        }.items():
            if value is not None:
                result[attr] = value
                
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the ETF to a CSV row (dictionary with string values)."""
        row = {
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "exchange": self.exchange,
            "country": self.country if self.country else "",
            "type": self.type,
            "asset_class": self.asset_class if self.asset_class else "",
            "expense_ratio": f"{self.expense_ratio:.4f}" if self.expense_ratio is not None else "",
            "managed_assets": f"{self.managed_assets:.2f}" if self.managed_assets is not None else "",
            "fund_family": self.fund_family if self.fund_family else "",
            "nav": f"{self.nav:.2f}" if self.nav is not None else "",
            "category": self.category if self.category else "",
            "benchmark": self.benchmark if self.benchmark else "",
            "description": self.description[:100] if self.description else "",
            "inception_date": self.inception_date if self.inception_date else "",
            "dividend_yield": f"{self.dividend_yield:.4f}" if self.dividend_yield is not None else "",
            "mic_code": self.mic_code if self.mic_code else ""
        }
        return row
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for ETF data."""
        return [
            "symbol", "name", "currency", "exchange", "country", "type", "asset_class",
            "expense_ratio", "managed_assets", "fund_family", "nav", "category",
            "benchmark", "description", "inception_date", "dividend_yield", "mic_code"
        ]