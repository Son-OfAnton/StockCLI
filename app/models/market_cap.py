"""
Model for market capitalization data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any

class MarketCapPoint:
    """
    Represents a single market capitalization data point at a specific timestamp.
    """
    def __init__(self, 
                timestamp: str, 
                market_cap: float, 
                shares_outstanding: Union[float, int],
                market_cap_formatted: Optional[str] = None):
        self.timestamp = timestamp
        self.market_cap = market_cap  # Raw market cap value
        self.shares_outstanding = shares_outstanding  # Number of shares outstanding
        
        # Format market cap (e.g. "$125.32B") if not provided
        if market_cap_formatted:
            self.market_cap_formatted = market_cap_formatted
        else:
            self.market_cap_formatted = self._format_market_cap(market_cap)
            
        # Convert timestamp to datetime for easier manipulation
        try:
            self.datetime = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            self.date = self.datetime.date()
        except ValueError:
            # Handle alternative timestamp formats
            try:
                self.datetime = datetime.fromisoformat(timestamp)
                self.date = self.datetime.date()
            except ValueError:
                self.datetime = None
                self.date = None
    
    @staticmethod
    def _format_market_cap(value: float) -> str:
        """Format market capitalization value with appropriate scale (B, M, K)"""
        if value >= 1_000_000_000_000:  # Trillions
            return f"${value / 1_000_000_000_000:.2f}T"
        elif value >= 1_000_000_000:  # Billions
            return f"${value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:  # Millions
            return f"${value / 1_000_000:.2f}M"
        elif value >= 1_000:  # Thousands
            return f"${value / 1_000:.2f}K"
        else:
            return f"${value:.2f}"
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'MarketCapPoint':
        """Create a MarketCapPoint from API response data"""
        return cls(
            timestamp=data.get("datetime", ""),
            market_cap=float(data.get("market_cap", 0)),
            shares_outstanding=float(data.get("shares_outstanding", 0))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp,
            "market_cap": self.market_cap,
            "market_cap_formatted": self.market_cap_formatted,
            "shares_outstanding": self.shares_outstanding
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        return {
            "Timestamp": self.timestamp,
            "Date": self.date.isoformat() if self.date else "",
            "Market Cap": self.market_cap_formatted,
            "Market Cap Value": str(self.market_cap),
            "Shares Outstanding": str(self.shares_outstanding)
        }


class MarketCapSummary:
    """
    Summary statistics for market capitalization data over a period.
    """
    def __init__(self,
                min_cap: float, 
                max_cap: float, 
                avg_cap: float, 
                start_cap: float, 
                end_cap: float,
                change_value: float,
                change_percent: float):
        self.min_cap = min_cap
        self.max_cap = max_cap
        self.avg_cap = avg_cap
        self.start_cap = start_cap
        self.end_cap = end_cap
        self.change_value = change_value
        self.change_percent = change_percent
        
        # Formatted versions
        self.min_cap_formatted = MarketCapPoint._format_market_cap(min_cap)
        self.max_cap_formatted = MarketCapPoint._format_market_cap(max_cap)
        self.avg_cap_formatted = MarketCapPoint._format_market_cap(avg_cap)
        self.start_cap_formatted = MarketCapPoint._format_market_cap(start_cap)
        self.end_cap_formatted = MarketCapPoint._format_market_cap(end_cap)
        self.change_value_formatted = MarketCapPoint._format_market_cap(abs(change_value))
        if change_value < 0:
            self.change_value_formatted = f"-{self.change_value_formatted}"
        self.change_percent_formatted = f"{change_percent:.2f}%"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "min_cap": self.min_cap,
            "min_cap_formatted": self.min_cap_formatted,
            "max_cap": self.max_cap,
            "max_cap_formatted": self.max_cap_formatted,
            "avg_cap": self.avg_cap,
            "avg_cap_formatted": self.avg_cap_formatted,
            "start_cap": self.start_cap,
            "start_cap_formatted": self.start_cap_formatted,
            "end_cap": self.end_cap,
            "end_cap_formatted": self.end_cap_formatted,
            "change_value": self.change_value,
            "change_value_formatted": self.change_value_formatted,
            "change_percent": self.change_percent,
            "change_percent_formatted": self.change_percent_formatted
        }


class MarketCapHistory:
    """
    Represents the market capitalization history for a symbol over time.
    """
    def __init__(self, 
                symbol: str, 
                interval: str,
                points: List[MarketCapPoint],
                currency: str = "USD"):
        self.symbol = symbol
        self.interval = interval
        self.points = sorted(points, key=lambda p: p.timestamp)
        self.currency = currency
        
        # Calculate summary statistics
        self.summary = self._calculate_summary()
    
    def _calculate_summary(self) -> Optional[MarketCapSummary]:
        """Calculate summary statistics from the market cap points"""
        if not self.points:
            return None
            
        min_cap = min(point.market_cap for point in self.points)
        max_cap = max(point.market_cap for point in self.points)
        avg_cap = sum(point.market_cap for point in self.points) / len(self.points)
        start_cap = self.points[0].market_cap
        end_cap = self.points[-1].market_cap
        change_value = end_cap - start_cap
        change_percent = (change_value / start_cap) * 100 if start_cap > 0 else 0
        
        return MarketCapSummary(
            min_cap=min_cap,
            max_cap=max_cap,
            avg_cap=avg_cap,
            start_cap=start_cap,
            end_cap=end_cap,
            change_value=change_value,
            change_percent=change_percent
        )
    
    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> 'MarketCapHistory':
        """Create a MarketCapHistory object from API response"""
        symbol = response_data.get("meta", {}).get("symbol", "")
        interval = response_data.get("meta", {}).get("interval", "")
        currency = response_data.get("meta", {}).get("currency", "USD")
        
        # Extract market cap values
        values = response_data.get("values", [])
        points = [MarketCapPoint.from_api_response(value) for value in values]
        
        return cls(
            symbol=symbol,
            interval=interval,
            points=points,
            currency=currency
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "currency": self.currency,
            "summary": self.summary.to_dict() if self.summary else None,
            "points": [point.to_dict() for point in self.points]
        }
    
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Format market cap history for CSV export"""
        return [point.to_csv_row() for point in self.points]
    
    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get headers for CSV export"""
        return ["Timestamp", "Date", "Market Cap", "Market Cap Value", "Shares Outstanding"]