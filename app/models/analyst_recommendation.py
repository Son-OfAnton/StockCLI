"""
Model for company analyst recommendations data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any, Tuple


class AnalystRecommendation:
    """
    Represents an individual analyst's recommendation.
    """
    def __init__(self,
                 firm: str,
                 rating: str,
                 action: str,
                 target_price: Optional[float] = None,
                 date: Optional[str] = None):
        
        self.firm = firm
        self.rating = rating  # e.g., "Buy", "Hold", "Sell"
        self.action = action  # e.g., "Maintains", "Upgrades", "Downgrades"
        self.target_price = target_price
        self.date = date
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'AnalystRecommendation':
        """Create AnalystRecommendation from API response data"""
        firm = data.get('firm', '')
        rating = data.get('rating', '')
        action = data.get('action', '')
        
        # Parse target price if available
        target_price = None
        if 'target_price' in data and data['target_price']:
            try:
                target_price = float(data['target_price'])
            except (ValueError, TypeError):
                pass
        
        date = data.get('date')
        
        return cls(
            firm=firm,
            rating=rating,
            action=action,
            target_price=target_price,
            date=date
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "firm": self.firm,
            "rating": self.rating,
            "action": self.action,
            "target_price": self.target_price,
            "date": self.date
        }


class AnalystConsensus:
    """
    Represents the consensus of analyst recommendations.
    """
    # Classification thresholds for average scores
    CLASSIFICATION_THRESHOLDS = {
        (1.0, 1.5): "Strong Buy",
        (1.5, 2.5): "Buy",
        (2.5, 3.5): "Hold",
        (3.5, 4.5): "Sell",
        (4.5, 5.0): "Strong Sell"
    }
    
    def __init__(self,
                 strong_buy: int = 0,
                 buy: int = 0,
                 hold: int = 0,
                 sell: int = 0,
                 strong_sell: int = 0,
                 average_score: Optional[float] = None,
                 total_analysts: int = 0):
        
        self.strong_buy = strong_buy
        self.buy = buy
        self.hold = hold
        self.sell = sell
        self.strong_sell = strong_sell
        self.total_analysts = total_analysts or (strong_buy + buy + hold + sell + strong_sell)
        
        # Calculate average score if not provided
        if average_score is None and self.total_analysts > 0:
            self.average_score = self._calculate_average_score()
        else:
            self.average_score = average_score
        
        # Determine classification based on average score
        self.classification = self._classify_average_score()
    
    def _calculate_average_score(self) -> float:
        """Calculate the average recommendation score (1 = Strong Buy, 5 = Strong Sell)"""
        if self.total_analysts == 0:
            return 0.0
            
        weighted_sum = (
            1 * self.strong_buy +
            2 * self.buy +
            3 * self.hold +
            4 * self.sell +
            5 * self.strong_sell
        )
        
        return weighted_sum / self.total_analysts
    
    def _classify_average_score(self) -> str:
        """Classify the average score into a recommendation category"""
        if self.average_score == 0 or self.total_analysts == 0:
            return "No Consensus"
            
        for (min_value, max_value), classification in self.CLASSIFICATION_THRESHOLDS.items():
            if min_value <= self.average_score < max_value:
                return classification
                
        return "Unknown"
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'AnalystConsensus':
        """Create AnalystConsensus from API response data"""
        strong_buy = int(data.get('strongBuy', 0))
        buy = int(data.get('buy', 0))
        hold = int(data.get('hold', 0))
        sell = int(data.get('sell', 0))
        strong_sell = int(data.get('strongSell', 0))
        
        # Try to get average from API or calculate it
        average_score = None
        if 'average' in data:
            try:
                average_score = float(data['average'])
            except (ValueError, TypeError):
                pass
        
        total = int(data.get('total', 0))
        
        return cls(
            strong_buy=strong_buy,
            buy=buy,
            hold=hold,
            sell=sell,
            strong_sell=strong_sell,
            average_score=average_score,
            total_analysts=total
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "strong_buy": self.strong_buy,
            "buy": self.buy,
            "hold": self.hold,
            "sell": self.sell,
            "strong_sell": self.strong_sell,
            "total_analysts": self.total_analysts,
            "average_score": self.average_score,
            "classification": self.classification
        }
    
    def get_distribution_percentages(self) -> Dict[str, float]:
        """Get the percentage distribution of recommendations"""
        if self.total_analysts == 0:
            return {
                "strong_buy": 0.0,
                "buy": 0.0,
                "hold": 0.0,
                "sell": 0.0,
                "strong_sell": 0.0
            }
        
        return {
            "strong_buy": (self.strong_buy / self.total_analysts) * 100,
            "buy": (self.buy / self.total_analysts) * 100,
            "hold": (self.hold / self.total_analysts) * 100,
            "sell": (self.sell / self.total_analysts) * 100,
            "strong_sell": (self.strong_sell / self.total_analysts) * 100
        }
    
    def get_buy_hold_sell_ratio(self) -> Tuple[float, float, float]:
        """Get the buy/hold/sell ratio as percentages"""
        buy_total = self.strong_buy + self.buy
        sell_total = self.sell + self.strong_sell
        
        if self.total_analysts == 0:
            return (0.0, 0.0, 0.0)
        
        buy_percent = (buy_total / self.total_analysts) * 100
        hold_percent = (self.hold / self.total_analysts) * 100
        sell_percent = (sell_total / self.total_analysts) * 100
        
        return (buy_percent, hold_percent, sell_percent)


class AnalystRecommendations:
    """
    Represents analyst recommendations data for a company.
    """
    def __init__(self,
                 symbol: str,
                 name: Optional[str],
                 consensus: AnalystConsensus,
                 recommendations: List[AnalystRecommendation] = None,
                 currency: str = "USD",
                 last_updated: Optional[str] = None,
                 raw_data: Optional[Dict[str, Any]] = None):
        
        self.symbol = symbol
        self.name = name
        self.consensus = consensus
        self.recommendations = recommendations or []
        self.currency = currency
        self.last_updated = last_updated
        self.raw_data = raw_data
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'AnalystRecommendations':
        """Create AnalystRecommendations from API response"""
        
        # Basic info
        symbol = response.get('symbol', '')
        name = response.get('name')
        currency = response.get('currency', 'USD')
        last_updated = response.get('last_updated')
        
        # Parse consensus data
        consensus_data = response.get('consensus', {})
        consensus = AnalystConsensus.from_api_response(consensus_data)
        
        # Parse individual recommendations
        recommendations_data = response.get('recommendations', [])
        recommendations = []
        
        for rec_data in recommendations_data:
            if isinstance(rec_data, dict):
                recommendation = AnalystRecommendation.from_api_response(rec_data)
                recommendations.append(recommendation)
        
        return cls(
            symbol=symbol,
            name=name,
            consensus=consensus,
            recommendations=recommendations,
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
            "consensus": self.consensus.to_dict(),
            "recommendations": [rec.to_dict() for rec in self.recommendations]
        }
    
    def get_recent_recommendations(self, days: int = 30) -> List[AnalystRecommendation]:
        """Get recommendations from the last specified number of days"""
        if not self.recommendations:
            return []
            
        today = datetime.now()
        recent_recs = []
        
        for rec in self.recommendations:
            if not rec.date:
                continue
                
            try:
                rec_date = datetime.fromisoformat(rec.date.replace('Z', '+00:00'))
                days_ago = (today - rec_date).days
                
                if days_ago <= days:
                    recent_recs.append(rec)
            except (ValueError, TypeError):
                # Skip recommendations with invalid dates
                continue
                
        return recent_recs