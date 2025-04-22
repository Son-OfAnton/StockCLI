"""
Model for company EPS revisions data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any


class EpsRevisionPeriod:
    """
    Represents EPS revisions for a particular period (week or month).
    """
    def __init__(self, 
                 period_type: str,  # 'week' or 'month'
                 upgrades: int,
                 downgrades: int,
                 maintained: int,
                 total_revisions: int,
                 revisions_by_period: Dict[str, Dict[str, int]] = None):
        
        self.period_type = period_type
        self.upgrades = upgrades
        self.downgrades = downgrades
        self.maintained = maintained
        self.total_revisions = total_revisions
        self.revisions_by_period = revisions_by_period or {}
    
    @classmethod
    def from_api_response(cls, period_type: str, data: Dict[str, Any]) -> 'EpsRevisionPeriod':
        """Create EpsRevisionPeriod from API response data"""
        # Extract general revision numbers
        upgrades = int(data.get('upgrades', 0))
        downgrades = int(data.get('downgrades', 0))
        maintained = int(data.get('maintained', 0))
        total = int(data.get('total', 0))
        
        # Extract revisions by period (quarterly/annual)
        revisions_by_period = {}
        for period_key, period_data in data.items():
            if period_key in ['upgrades', 'downgrades', 'maintained', 'total']:
                continue
                
            if isinstance(period_data, dict):
                period_revisions = {
                    'upgrades': int(period_data.get('upgrades', 0)),
                    'downgrades': int(period_data.get('downgrades', 0)),
                    'maintained': int(period_data.get('maintained', 0)),
                    'total': int(period_data.get('total', 0))
                }
                revisions_by_period[period_key] = period_revisions
        
        return cls(
            period_type=period_type,
            upgrades=upgrades,
            downgrades=downgrades,
            maintained=maintained,
            total_revisions=total,
            revisions_by_period=revisions_by_period
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "period_type": self.period_type,
            "upgrades": self.upgrades,
            "downgrades": self.downgrades,
            "maintained": self.maintained,
            "total_revisions": self.total_revisions,
            "revisions_by_period": self.revisions_by_period
        }


class EpsRevisions:
    """
    Represents EPS revisions data for a company, including weekly and monthly breakdowns.
    """
    def __init__(self,
                 symbol: str,
                 name: Optional[str],
                 weekly: EpsRevisionPeriod,
                 monthly: EpsRevisionPeriod,
                 currency: str = "USD",
                 last_updated: Optional[str] = None,
                 raw_data: Optional[Dict[str, Any]] = None):
        
        self.symbol = symbol
        self.name = name
        self.weekly = weekly
        self.monthly = monthly
        self.currency = currency
        self.last_updated = last_updated
        self.raw_data = raw_data
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'EpsRevisions':
        """Create EpsRevisions from API response"""
        
        # Basic info
        symbol = response.get('symbol', '')
        name = response.get('name')
        currency = response.get('currency', 'USD')
        last_updated = response.get('last_updated')
        
        # Parse weekly revisions
        weekly_data = response.get('week', {})
        weekly_revisions = EpsRevisionPeriod.from_api_response('week', weekly_data)
        
        # Parse monthly revisions
        monthly_data = response.get('month', {})
        monthly_revisions = EpsRevisionPeriod.from_api_response('month', monthly_data)
        
        return cls(
            symbol=symbol,
            name=name,
            weekly=weekly_revisions,
            monthly=monthly_revisions,
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
            "weekly": self.weekly.to_dict(),
            "monthly": self.monthly.to_dict()
        }
    
    def get_csv_rows_summary(self) -> List[Dict[str, str]]:
        """Format summary data for CSV export"""
        rows = []
        
        # Add header row
        rows.append({
            "Period": "Period",
            "Total Revisions": "Total Revisions",
            "Upgrades": "Upgrades",
            "Downgrades": "Downgrades",
            "Maintained": "Maintained"
        })
        
        # Add week data
        rows.append({
            "Period": "Last Week",
            "Total Revisions": str(self.weekly.total_revisions),
            "Upgrades": str(self.weekly.upgrades),
            "Downgrades": str(self.weekly.downgrades),
            "Maintained": str(self.weekly.maintained)
        })
        
        # Add month data
        rows.append({
            "Period": "Last Month",
            "Total Revisions": str(self.monthly.total_revisions),
            "Upgrades": str(self.monthly.upgrades),
            "Downgrades": str(self.monthly.downgrades),
            "Maintained": str(self.monthly.maintained)
        })
        
        return rows
    
    def get_csv_rows_detailed(self) -> List[Dict[str, str]]:
        """Format detailed data for CSV export"""
        rows = []
        
        # Process weekly data
        rows.append({
            "Period": "WEEKLY REVISIONS",
            "Quarter/Year": "",
            "Total": "",
            "Upgrades": "",
            "Downgrades": "",
            "Maintained": ""
        })
        
        for period, data in sorted(self.weekly.revisions_by_period.items()):
            rows.append({
                "Period": "Last Week",
                "Quarter/Year": period,
                "Total": str(data['total']),
                "Upgrades": str(data['upgrades']),
                "Downgrades": str(data['downgrades']),
                "Maintained": str(data['maintained'])
            })
        
        # Add separator
        rows.append({
            "Period": "",
            "Quarter/Year": "",
            "Total": "",
            "Upgrades": "",
            "Downgrades": "",
            "Maintained": ""
        })
        
        # Process monthly data
        rows.append({
            "Period": "MONTHLY REVISIONS",
            "Quarter/Year": "",
            "Total": "",
            "Upgrades": "",
            "Downgrades": "",
            "Maintained": ""
        })
        
        for period, data in sorted(self.monthly.revisions_by_period.items()):
            rows.append({
                "Period": "Last Month",
                "Quarter/Year": period,
                "Total": str(data['total']),
                "Upgrades": str(data['upgrades']),
                "Downgrades": str(data['downgrades']),
                "Maintained": str(data['maintained'])
            })
        
        return rows
    
    @staticmethod
    def get_csv_headers_summary() -> List[str]:
        """Get headers for summary CSV export"""
        return ["Period", "Total Revisions", "Upgrades", "Downgrades", "Maintained"]
    
    @staticmethod
    def get_csv_headers_detailed() -> List[str]:
        """Get headers for detailed CSV export"""
        return ["Period", "Quarter/Year", "Total", "Upgrades", "Downgrades", "Maintained"]