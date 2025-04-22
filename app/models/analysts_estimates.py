"""
Model for company analyst estimates data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any


class EpsEstimate:
    """
    Represents an EPS estimate for a particular period (quarterly or annual).
    """
    def __init__(self, period: str, period_end_date: str, 
                 estimate_value: float, estimate_count: int,
                 actual_value: Optional[float] = None,
                 surprise_value: Optional[float] = None,
                 surprise_percent: Optional[float] = None,
                 period_str: Optional[str] = None):
        
        self.period = period                # e.g., "Q1 2023", "FY 2023"
        self.period_end_date = period_end_date  # ISO date string
        self.estimate_value = estimate_value    # Mean EPS estimate
        self.estimate_count = estimate_count    # Number of analyst estimates
        self.actual_value = actual_value        # Actual EPS (if reported)
        self.surprise_value = surprise_value    # Difference between actual and estimate
        self.surprise_percent = surprise_percent  # Percentage difference
        
        # Human-readable period string (e.g. "Q1 2023 (ending 2023-03-31)")
        self.period_str = period_str or self._format_period_str()
        
    def _format_period_str(self) -> str:
        """Generate a formatted period string with end date"""
        try:
            # Try to format date in a readable way
            date_obj = datetime.fromisoformat(self.period_end_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%Y-%m-%d')
            return f"{self.period} (ending {formatted_date})"
        except (ValueError, TypeError):
            # Fall back to just using the period
            return self.period
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'EpsEstimate':
        """Create EpsEstimate from API response data"""
        # Extract required fields
        period = data.get('period', '')
        period_end_date = data.get('end_date', '')
        
        # Get estimate value and count
        estimate_value = cls._parse_float(data.get('estimate_value'))
        estimate_count = int(data.get('number_analyst_estimates', 0) or 0)
        
        # Get actual and surprise values if available
        actual_value = cls._parse_float(data.get('actual_value'))
        surprise_value = cls._parse_float(data.get('surprise_value'))
        surprise_percent = cls._parse_float(data.get('surprise_percent'))
        
        return cls(
            period=period,
            period_end_date=period_end_date,
            estimate_value=estimate_value,
            estimate_count=estimate_count,
            actual_value=actual_value,
            surprise_value=surprise_value,
            surprise_percent=surprise_percent
        )
    
    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        """Safely parse a float, returning None if conversion fails"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "period": self.period,
            "period_end_date": self.period_end_date,
            "formatted_period": self.period_str,
            "estimate_value": self.estimate_value,
            "estimate_count": self.estimate_count,
            "actual_value": self.actual_value,
            "surprise_value": self.surprise_value,
            "surprise_percent": self.surprise_percent
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        actual_str = f"{self.actual_value:.2f}" if self.actual_value is not None else "Not reported"
        surprise_str = f"{self.surprise_value:.2f} ({self.surprise_percent:.2f}%)" if self.surprise_value is not None else "N/A"
        
        return {
            "Period": self.period_str,
            "Estimated EPS": f"{self.estimate_value:.2f}",
            "Analyst Count": str(self.estimate_count),
            "Actual EPS": actual_str,
            "Surprise": surprise_str
        }


class RevenueEstimate:
    """
    Represents a revenue estimate for a particular period (quarterly or annual).
    """
    def __init__(self, period: str, period_end_date: str, 
                 estimate_value: float, estimate_count: int,
                 actual_value: Optional[float] = None,
                 surprise_value: Optional[float] = None,
                 surprise_percent: Optional[float] = None,
                 period_str: Optional[str] = None):
        
        self.period = period                # e.g., "Q1 2023", "FY 2023"
        self.period_end_date = period_end_date  # ISO date string
        self.estimate_value = estimate_value    # Mean revenue estimate (in millions)
        self.estimate_count = estimate_count    # Number of analyst estimates
        self.actual_value = actual_value        # Actual revenue (if reported)
        self.surprise_value = surprise_value    # Difference between actual and estimate
        self.surprise_percent = surprise_percent  # Percentage difference
        
        # Human-readable period string (e.g. "Q1 2023 (ending 2023-03-31)")
        self.period_str = period_str or self._format_period_str()
        
    def _format_period_str(self) -> str:
        """Generate a formatted period string with end date"""
        try:
            # Try to format date in a readable way
            date_obj = datetime.fromisoformat(self.period_end_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%Y-%m-%d')
            return f"{self.period} (ending {formatted_date})"
        except (ValueError, TypeError):
            # Fall back to just using the period
            return self.period
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'RevenueEstimate':
        """Create RevenueEstimate from API response data"""
        # Extract required fields
        period = data.get('period', '')
        period_end_date = data.get('end_date', '')
        
        # Get estimate value and count
        estimate_value = cls._parse_float(data.get('estimate_value'))
        estimate_count = int(data.get('number_analyst_estimates', 0) or 0)
        
        # Get actual and surprise values if available
        actual_value = cls._parse_float(data.get('actual_value'))
        surprise_value = cls._parse_float(data.get('surprise_value'))
        surprise_percent = cls._parse_float(data.get('surprise_percent'))
        
        return cls(
            period=period,
            period_end_date=period_end_date,
            estimate_value=estimate_value,
            estimate_count=estimate_count,
            actual_value=actual_value,
            surprise_value=surprise_value,
            surprise_percent=surprise_percent
        )
    
    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        """Safely parse a float, returning None if conversion fails"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "period": self.period,
            "period_end_date": self.period_end_date,
            "formatted_period": self.period_str,
            "estimate_value": self.estimate_value,
            "estimate_count": self.estimate_count,
            "actual_value": self.actual_value,
            "surprise_value": self.surprise_value,
            "surprise_percent": self.surprise_percent
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        estimate_str = f"${self.estimate_value:,.2f}M" if self.estimate_value is not None else "N/A"
        actual_str = f"${self.actual_value:,.2f}M" if self.actual_value is not None else "Not reported"
        surprise_str = f"${self.surprise_value:,.2f}M ({self.surprise_percent:.2f}%)" if self.surprise_value is not None else "N/A"
        
        return {
            "Period": self.period_str,
            "Estimated Revenue": estimate_str,
            "Analyst Count": str(self.estimate_count),
            "Actual Revenue": actual_str,
            "Surprise": surprise_str
        }


class AnalystTarget:
    """
    Represents an analyst target for a stock (e.g., price target).
    """
    def __init__(self, 
                 target_type: str,
                 mean_target: float,
                 median_target: Optional[float] = None,
                 high_target: Optional[float] = None,
                 low_target: Optional[float] = None,
                 analyst_count: int = 0,
                 currency: str = 'USD'):
        
        self.target_type = target_type      # e.g., "price", "revenue"
        self.mean_target = mean_target      # Average target
        self.median_target = median_target  # Median target
        self.high_target = high_target      # Highest target
        self.low_target = low_target        # Lowest target
        self.analyst_count = analyst_count  # Number of analysts
        self.currency = currency            # Currency for the target
        
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], target_type: str) -> 'AnalystTarget':
        """Create AnalystTarget from API response data"""
        # Get target values
        mean_target = cls._parse_float(data.get('mean_target', 0))
        median_target = cls._parse_float(data.get('median_target'))
        high_target = cls._parse_float(data.get('high_target'))
        low_target = cls._parse_float(data.get('low_target'))
        
        # Get analyst count
        analyst_count = int(data.get('number_of_analysts', 0) or 0)
        
        # Get currency
        currency = data.get('currency', 'USD')
        
        return cls(
            target_type=target_type,
            mean_target=mean_target,
            median_target=median_target,
            high_target=high_target,
            low_target=low_target,
            analyst_count=analyst_count,
            currency=currency
        )
    
    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        """Safely parse a float, returning None if conversion fails"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "target_type": self.target_type,
            "mean_target": self.mean_target,
            "median_target": self.median_target,
            "high_target": self.high_target,
            "low_target": self.low_target,
            "analyst_count": self.analyst_count,
            "currency": self.currency
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        target_type_str = self.target_type.title()
        mean_str = f"${self.mean_target:.2f}" if self.target_type == "price" else f"${self.mean_target:,.2f}M"
        median_str = f"${self.median_target:.2f}" if self.median_target is not None else "N/A"
        high_str = f"${self.high_target:.2f}" if self.high_target is not None else "N/A"
        low_str = f"${self.low_target:.2f}" if self.low_target is not None else "N/A"
        
        return {
            "Target Type": target_type_str,
            "Mean Target": mean_str,
            "Median Target": median_str,
            "High Target": high_str,
            "Low Target": low_str,
            "Analyst Count": str(self.analyst_count),
            "Currency": self.currency
        }


class RecommendationTrend:
    """
    Represents analyst recommendation trends for a stock.
    """
    def __init__(self, 
                 period: str,
                 strong_buy: int = 0,
                 buy: int = 0,
                 hold: int = 0,
                 sell: int = 0,
                 strong_sell: int = 0):
        
        self.period = period          # e.g., "Current", "1 Month Ago"
        self.strong_buy = strong_buy  # Strong buy recommendations
        self.buy = buy                # Buy recommendations
        self.hold = hold              # Hold recommendations
        self.sell = sell              # Sell recommendations
        self.strong_sell = strong_sell  # Strong sell recommendations
        
        # Calculate total and average score
        self.total_analysts = self.strong_buy + self.buy + self.hold + self.sell + self.strong_sell
        
        # Calculate weighted score (1=Strong Sell, 2=Sell, 3=Hold, 4=Buy, 5=Strong Buy)
        self.score = 0
        if self.total_analysts > 0:
            self.score = (
                (5 * self.strong_buy) +
                (4 * self.buy) +
                (3 * self.hold) +
                (2 * self.sell) +
                (1 * self.strong_sell)
            ) / self.total_analysts
            
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'RecommendationTrend':
        """Create RecommendationTrend from API response data"""
        period = data.get('period', 'Unknown')
        
        # Get recommendation counts
        strong_buy = int(data.get('strong_buy', 0) or 0)
        buy = int(data.get('buy', 0) or 0)
        hold = int(data.get('hold', 0) or 0)
        sell = int(data.get('sell', 0) or 0)
        strong_sell = int(data.get('strong_sell', 0) or 0)
        
        return cls(
            period=period,
            strong_buy=strong_buy,
            buy=buy,
            hold=hold,
            sell=sell,
            strong_sell=strong_sell
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "period": self.period,
            "strong_buy": self.strong_buy,
            "buy": self.buy,
            "hold": self.hold,
            "sell": self.sell,
            "strong_sell": self.strong_sell,
            "total_analysts": self.total_analysts,
            "score": self.score
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        # Get recommendation string
        rec_str = self._get_recommendation_str()
        
        return {
            "Period": self.period,
            "Strong Buy": str(self.strong_buy),
            "Buy": str(self.buy),
            "Hold": str(self.hold),
            "Sell": str(self.sell),
            "Strong Sell": str(self.strong_sell),
            "Total Analysts": str(self.total_analysts),
            "Average Score": f"{self.score:.2f}",
            "Recommendation": rec_str
        }
    
    def _get_recommendation_str(self) -> str:
        """Convert score to a recommendation string"""
        if self.total_analysts == 0:
            return "N/A"
        elif self.score >= 4.5:
            return "Strong Buy"
        elif self.score >= 3.5:
            return "Buy"
        elif self.score >= 2.5:
            return "Hold"
        elif self.score >= 1.5:
            return "Sell"
        else:
            return "Strong Sell"


class AnalystEstimates:
    """
    Represents a collection of analyst estimates for a company.
    """
    def __init__(self, 
                 symbol: str,
                 name: Optional[str],
                 currency: str,
                 quarterly_eps_estimates: List[EpsEstimate],
                 annual_eps_estimates: List[EpsEstimate],
                 quarterly_revenue_estimates: Optional[List[RevenueEstimate]] = None,
                 annual_revenue_estimates: Optional[List[RevenueEstimate]] = None,
                 price_target: Optional[AnalystTarget] = None,
                 recommendation_trends: Optional[List[RecommendationTrend]] = None,
                 last_updated: Optional[str] = None,
                 raw_data: Dict[str, Any] = None):
        
        self.symbol = symbol
        self.name = name
        self.currency = currency
        self.quarterly_eps_estimates = quarterly_eps_estimates
        self.annual_eps_estimates = annual_eps_estimates
        self.quarterly_revenue_estimates = quarterly_revenue_estimates or []
        self.annual_revenue_estimates = annual_revenue_estimates or []
        self.price_target = price_target
        self.recommendation_trends = recommendation_trends or []
        self.last_updated = last_updated
        self.raw_data = raw_data or {}
        
        # Sort estimates by end date (most recent first)
        self._sort_estimates()
        
    def _sort_estimates(self):
        """Sort all estimates by end date (most recent first)"""
        def sort_key(estimate):
            try:
                return datetime.fromisoformat(estimate.period_end_date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return datetime.min
            
        self.quarterly_eps_estimates.sort(key=sort_key, reverse=True)
        self.annual_eps_estimates.sort(key=sort_key, reverse=True)
        self.quarterly_revenue_estimates.sort(key=sort_key, reverse=True)
        self.annual_revenue_estimates.sort(key=sort_key, reverse=True)
        
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'AnalystEstimates':
        """Create AnalystEstimates from API response"""
        
        # Basic info
        symbol = response.get('symbol', '')
        name = response.get('name')
        currency = response.get('earnings_currency', 'USD')
        last_updated = response.get('last_updated')
        
        # Parse quarterly EPS estimates
        quarterly_eps_estimates = []
        quarterly_eps_data = response.get('quarterly_earnings_estimate', [])
        if isinstance(quarterly_eps_data, list):
            for eps_data in quarterly_eps_data:
                estimate = EpsEstimate.from_api_response(eps_data)
                quarterly_eps_estimates.append(estimate)
                
        # Parse annual EPS estimates
        annual_eps_estimates = []
        annual_eps_data = response.get('yearly_earnings_estimate', [])
        if isinstance(annual_eps_data, list):
            for eps_data in annual_eps_data:
                estimate = EpsEstimate.from_api_response(eps_data)
                annual_eps_estimates.append(estimate)
                
        # Parse quarterly revenue estimates
        quarterly_revenue_estimates = []
        quarterly_revenue_data = response.get('quarterly_revenue_estimate', [])
        if isinstance(quarterly_revenue_data, list):
            for revenue_data in quarterly_revenue_data:
                estimate = RevenueEstimate.from_api_response(revenue_data)
                quarterly_revenue_estimates.append(estimate)
                
        # Parse annual revenue estimates
        annual_revenue_estimates = []
        annual_revenue_data = response.get('yearly_revenue_estimate', [])
        if isinstance(annual_revenue_data, list):
            for revenue_data in annual_revenue_data:
                estimate = RevenueEstimate.from_api_response(revenue_data)
                annual_revenue_estimates.append(estimate)
                
        # Parse price target
        price_target = None
        price_target_data = response.get('price_target')
        if isinstance(price_target_data, dict):
            price_target = AnalystTarget.from_api_response(price_target_data, "price")
            
        # Parse recommendation trends
        recommendation_trends = []
        recommendation_data = response.get('recommendation_trend', [])
        if isinstance(recommendation_data, list):
            for rec_data in recommendation_data:
                trend = RecommendationTrend.from_api_response(rec_data)
                recommendation_trends.append(trend)
                
        return cls(
            symbol=symbol,
            name=name,
            currency=currency,
            quarterly_eps_estimates=quarterly_eps_estimates,
            annual_eps_estimates=annual_eps_estimates,
            quarterly_revenue_estimates=quarterly_revenue_estimates,
            annual_revenue_estimates=annual_revenue_estimates,
            price_target=price_target,
            recommendation_trends=recommendation_trends,
            last_updated=last_updated,
            raw_data=response
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "last_updated": self.last_updated,
            "eps_estimates": {
                "quarterly": [estimate.to_dict() for estimate in self.quarterly_eps_estimates],
                "annual": [estimate.to_dict() for estimate in self.annual_eps_estimates]
            }
        }
        
        # Add revenue estimates if available
        if self.quarterly_revenue_estimates or self.annual_revenue_estimates:
            result["revenue_estimates"] = {
                "quarterly": [estimate.to_dict() for estimate in self.quarterly_revenue_estimates],
                "annual": [estimate.to_dict() for estimate in self.annual_revenue_estimates]
            }
            
        # Add price target if available
        if self.price_target:
            result["price_target"] = self.price_target.to_dict()
            
        # Add recommendation trends if available
        if self.recommendation_trends:
            result["recommendation_trends"] = [trend.to_dict() for trend in self.recommendation_trends]
            
        return result
    
    def get_csv_rows_eps_estimates(self) -> List[Dict[str, str]]:
        """Format EPS estimates for CSV export"""
        rows = []
        
        # Add quarterly EPS estimates
        if self.quarterly_eps_estimates:
            rows.append({"Period": "QUARTERLY EPS ESTIMATES", "Estimated EPS": "", "Analyst Count": "", "Actual EPS": "", "Surprise": ""})
            for estimate in self.quarterly_eps_estimates:
                rows.append(estimate.to_csv_row())
        
        # Add a separator
        if self.quarterly_eps_estimates and self.annual_eps_estimates:
            rows.append({"Period": "", "Estimated EPS": "", "Analyst Count": "", "Actual EPS": "", "Surprise": ""})
        
        # Add annual EPS estimates
        if self.annual_eps_estimates:
            rows.append({"Period": "ANNUAL EPS ESTIMATES", "Estimated EPS": "", "Analyst Count": "", "Actual EPS": "", "Surprise": ""})
            for estimate in self.annual_eps_estimates:
                rows.append(estimate.to_csv_row())
                
        return rows
    
    def get_csv_rows_revenue_estimates(self) -> List[Dict[str, str]]:
        """Format revenue estimates for CSV export"""
        rows = []
        
        # Add quarterly revenue estimates
        if self.quarterly_revenue_estimates:
            rows.append({"Period": "QUARTERLY REVENUE ESTIMATES", "Estimated Revenue": "", "Analyst Count": "", "Actual Revenue": "", "Surprise": ""})
            for estimate in self.quarterly_revenue_estimates:
                rows.append(estimate.to_csv_row())
        
        # Add a separator
        if self.quarterly_revenue_estimates and self.annual_revenue_estimates:
            rows.append({"Period": "", "Estimated Revenue": "", "Analyst Count": "", "Actual Revenue": "", "Surprise": ""})
        
        # Add annual revenue estimates
        if self.annual_revenue_estimates:
            rows.append({"Period": "ANNUAL REVENUE ESTIMATES", "Estimated Revenue": "", "Analyst Count": "", "Actual Revenue": "", "Surprise": ""})
            for estimate in self.annual_revenue_estimates:
                rows.append(estimate.to_csv_row())
                
        return rows
    
    @staticmethod
    def get_csv_headers_eps() -> List[str]:
        """Get headers for EPS estimates CSV export"""
        return ["Period", "Estimated EPS", "Analyst Count", "Actual EPS", "Surprise"]
    
    @staticmethod
    def get_csv_headers_revenue() -> List[str]:
        """Get headers for revenue estimates CSV export"""
        return ["Period", "Estimated Revenue", "Analyst Count", "Actual Revenue", "Surprise"]
    
    @staticmethod
    def get_csv_headers_recommendations() -> List[str]:
        """Get headers for recommendations CSV export"""
        return ["Period", "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell", 
                "Total Analysts", "Average Score", "Recommendation"]