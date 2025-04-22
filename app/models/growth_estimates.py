"""
Model for company growth estimates data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any


class GrowthEstimates:
    """
    Represents consensus analyst estimates for a company's growth rates.
    """
    def __init__(self,
                 symbol: str,
                 name: Optional[str],
                 current_quarter: Optional[float] = None,
                 next_quarter: Optional[float] = None,
                 current_year: Optional[float] = None,
                 next_year: Optional[float] = None,
                 next_five_years: Optional[float] = None,
                 past_five_years: Optional[float] = None,
                 sales_growth_current_quarter: Optional[float] = None,
                 sales_growth_current_year: Optional[float] = None,
                 eps_growth_current_quarter: Optional[float] = None,
                 eps_growth_next_quarter: Optional[float] = None,
                 eps_growth_current_year: Optional[float] = None,
                 eps_growth_next_year: Optional[float] = None,
                 currency: str = "USD",
                 last_updated: Optional[str] = None,
                 raw_data: Optional[Dict[str, Any]] = None):
        
        self.symbol = symbol
        self.name = name
        self.currency = currency
        self.last_updated = last_updated
        self.raw_data = raw_data
        
        # Growth rate estimates
        self.current_quarter = current_quarter
        self.next_quarter = next_quarter
        self.current_year = current_year
        self.next_year = next_year
        self.next_five_years = next_five_years
        self.past_five_years = past_five_years
        
        # Sales growth estimates
        self.sales_growth_current_quarter = sales_growth_current_quarter
        self.sales_growth_current_year = sales_growth_current_year
        
        # EPS growth estimates
        self.eps_growth_current_quarter = eps_growth_current_quarter
        self.eps_growth_next_quarter = eps_growth_next_quarter
        self.eps_growth_current_year = eps_growth_current_year
        self.eps_growth_next_year = eps_growth_next_year
    
    @staticmethod
    def _parse_growth_value(value: Any) -> Optional[float]:
        """Parse a growth value, handling different formats (5%, 5, "NA", etc.)"""
        if value is None or value == "" or value == "NA" or value == "N/A":
            return None
        
        # Try to handle percentage format
        if isinstance(value, str):
            # Remove % symbol if present and convert to float
            value = value.replace("%", "").strip()
            if not value:
                return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'GrowthEstimates':
        """Create GrowthEstimates from API response"""
        
        # Basic info
        symbol = response.get('symbol', '')
        name = response.get('name')
        currency = response.get('currency', 'USD')
        last_updated = response.get('last_updated')
        
        # Growth rate estimates
        current_quarter = cls._parse_growth_value(response.get('current_quarter_growth_estimate'))
        next_quarter = cls._parse_growth_value(response.get('next_quarter_growth_estimate'))
        current_year = cls._parse_growth_value(response.get('current_year_growth_estimate'))
        next_year = cls._parse_growth_value(response.get('next_year_growth_estimate'))
        next_five_years = cls._parse_growth_value(response.get('next_5_years_growth_estimate'))
        past_five_years = cls._parse_growth_value(response.get('past_5_years_growth_rate'))
        
        # Sales growth estimates
        sales_growth_current_quarter = cls._parse_growth_value(response.get('current_quarter_sales_growth_estimate'))
        sales_growth_current_year = cls._parse_growth_value(response.get('current_year_sales_growth_estimate'))
        
        # EPS growth estimates
        eps_growth_current_quarter = cls._parse_growth_value(response.get('current_quarter_eps_growth_estimate'))
        eps_growth_next_quarter = cls._parse_growth_value(response.get('next_quarter_eps_growth_estimate'))
        eps_growth_current_year = cls._parse_growth_value(response.get('current_year_eps_growth_estimate'))
        eps_growth_next_year = cls._parse_growth_value(response.get('next_year_eps_growth_estimate'))
        
        return cls(
            symbol=symbol,
            name=name,
            current_quarter=current_quarter,
            next_quarter=next_quarter,
            current_year=current_year,
            next_year=next_year,
            next_five_years=next_five_years,
            past_five_years=past_five_years,
            sales_growth_current_quarter=sales_growth_current_quarter,
            sales_growth_current_year=sales_growth_current_year,
            eps_growth_current_quarter=eps_growth_current_quarter,
            eps_growth_next_quarter=eps_growth_next_quarter,
            eps_growth_current_year=eps_growth_current_year,
            eps_growth_next_year=eps_growth_next_year,
            currency=currency,
            last_updated=last_updated,
            raw_data=response
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "last_updated": self.last_updated,
            "growth_estimates": {
                "current_quarter": self.current_quarter,
                "next_quarter": self.next_quarter,
                "current_year": self.current_year,
                "next_year": self.next_year,
                "next_five_years": self.next_five_years,
                "past_five_years": self.past_five_years
            },
            "sales_growth_estimates": {
                "current_quarter": self.sales_growth_current_quarter,
                "current_year": self.sales_growth_current_year
            },
            "eps_growth_estimates": {
                "current_quarter": self.eps_growth_current_quarter,
                "next_quarter": self.eps_growth_next_quarter,
                "current_year": self.eps_growth_current_year,
                "next_year": self.eps_growth_next_year
            }
        }
    
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Format data for CSV export"""
        rows = []
        
        # Add a category header for growth estimates
        rows.append({
            "Period": "GROWTH ESTIMATES",
            "Growth Rate (%)": "",
            "Description": ""
        })
        
        # Add growth estimate values
        if self.current_quarter is not None:
            rows.append({
                "Period": "Current Quarter",
                "Growth Rate (%)": f"{self.current_quarter:.2f}%",
                "Description": "Expected growth in the current quarter"
            })
            
        if self.next_quarter is not None:
            rows.append({
                "Period": "Next Quarter",
                "Growth Rate (%)": f"{self.next_quarter:.2f}%",
                "Description": "Expected growth in the next quarter"
            })
            
        if self.current_year is not None:
            rows.append({
                "Period": "Current Year",
                "Growth Rate (%)": f"{self.current_year:.2f}%",
                "Description": "Expected growth in the current fiscal year"
            })
            
        if self.next_year is not None:
            rows.append({
                "Period": "Next Year",
                "Growth Rate (%)": f"{self.next_year:.2f}%",
                "Description": "Expected growth in the next fiscal year"
            })
            
        if self.next_five_years is not None:
            rows.append({
                "Period": "Next 5 Years (per annum)",
                "Growth Rate (%)": f"{self.next_five_years:.2f}%",
                "Description": "Expected average annual growth over the next five years"
            })
            
        if self.past_five_years is not None:
            rows.append({
                "Period": "Past 5 Years (per annum)",
                "Growth Rate (%)": f"{self.past_five_years:.2f}%",
                "Description": "Historical average annual growth over the past five years"
            })
        
        # Add a separator
        rows.append({
            "Period": "",
            "Growth Rate (%)": "",
            "Description": ""
        })
        
        # Add a category header for sales growth
        rows.append({
            "Period": "SALES GROWTH ESTIMATES",
            "Growth Rate (%)": "",
            "Description": ""
        })
        
        # Add sales growth values
        if self.sales_growth_current_quarter is not None:
            rows.append({
                "Period": "Current Quarter (Sales)",
                "Growth Rate (%)": f"{self.sales_growth_current_quarter:.2f}%",
                "Description": "Expected sales growth in the current quarter"
            })
            
        if self.sales_growth_current_year is not None:
            rows.append({
                "Period": "Current Year (Sales)",
                "Growth Rate (%)": f"{self.sales_growth_current_year:.2f}%",
                "Description": "Expected sales growth in the current fiscal year"
            })
        
        # Add a separator
        rows.append({
            "Period": "",
            "Growth Rate (%)": "",
            "Description": ""
        })
        
        # Add a category header for EPS growth
        rows.append({
            "Period": "EPS GROWTH ESTIMATES",
            "Growth Rate (%)": "",
            "Description": ""
        })
        
        # Add EPS growth values
        if self.eps_growth_current_quarter is not None:
            rows.append({
                "Period": "Current Quarter (EPS)",
                "Growth Rate (%)": f"{self.eps_growth_current_quarter:.2f}%",
                "Description": "Expected EPS growth in the current quarter"
            })
            
        if self.eps_growth_next_quarter is not None:
            rows.append({
                "Period": "Next Quarter (EPS)",
                "Growth Rate (%)": f"{self.eps_growth_next_quarter:.2f}%",
                "Description": "Expected EPS growth in the next quarter"
            })
            
        if self.eps_growth_current_year is not None:
            rows.append({
                "Period": "Current Year (EPS)",
                "Growth Rate (%)": f"{self.eps_growth_current_year:.2f}%",
                "Description": "Expected EPS growth in the current fiscal year"
            })
            
        if self.eps_growth_next_year is not None:
            rows.append({
                "Period": "Next Year (EPS)",
                "Growth Rate (%)": f"{self.eps_growth_next_year:.2f}%",
                "Description": "Expected EPS growth in the next fiscal year"
            })
        
        return rows
    
    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get headers for CSV export"""
        return ["Period", "Growth Rate (%)", "Description"]