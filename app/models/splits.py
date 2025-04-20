"""
Data models for stock splits information.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, ClassVar, Union
import logging

logger = logging.getLogger(__name__)


class StockSplit:
    """Model for a stock split event."""
    
    def __init__(
        self,
        symbol: str,
        date: Optional[datetime] = None,
        from_factor: int = 1,
        to_factor: int = 1,
        ratio: float = 1.0,
        name: Optional[str] = None,
        exchange: Optional[str] = None
    ):
        self.symbol = symbol
        self.date = date
        self.from_factor = from_factor
        self.to_factor = to_factor
        self.ratio = ratio
        self.name = name
        self.exchange = exchange
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], symbol: str, name: Optional[str] = None) -> 'StockSplit':
        """Create a StockSplit instance from TwelveData API response."""
        logger.debug(f"Parsing stock split data: {data}")
        
        # Parse date
        split_date = None
        if data.get('date'):
            try:
                split_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse split date: {e}")
        
        # Parse factors (formats could be like "2:1" or "2-for-1")
        from_factor = 1
        to_factor = 1
        split_ratio = 1.0
        
        if 'split' in data:
            split_text = data['split']
            
            # Try to parse different split formats
            if ":" in split_text:
                try:
                    from_str, to_str = split_text.split(":")
                    from_factor = int(from_str.strip())
                    to_factor = int(to_str.strip())
                    split_ratio = from_factor / to_factor if to_factor != 0 else 0.0
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Could not parse split ratio '{split_text}': {e}")
            
            elif "-for-" in split_text.lower() or " for " in split_text.lower():
                split_text = split_text.lower().replace("-for-", " for ")
                try:
                    from_str, to_str = split_text.split(" for ")
                    from_factor = int(from_str.strip())
                    to_factor = int(to_str.strip())
                    split_ratio = from_factor / to_factor if to_factor != 0 else 0.0
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Could not parse split ratio '{split_text}': {e}")
            
            # Check if it's just a decimal ratio
            elif split_text.replace(".", "").isdigit():
                try:
                    split_ratio = float(split_text)
                    # For common splits like 2.0, 3.0, 0.5, etc.
                    if split_ratio > 1:
                        from_factor = int(split_ratio)
                        to_factor = 1
                    elif split_ratio < 1 and split_ratio > 0:
                        to_factor = int(1 / split_ratio) if split_ratio != 0 else 0
                        from_factor = 1
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Could not parse split ratio '{split_text}': {e}")
        
        # If ratio is directly provided
        if 'ratio' in data and data['ratio'] is not None:
            try:
                split_ratio = float(data['ratio'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse direct split ratio: {e}")
        
        return cls(
            symbol=symbol,
            date=split_date,
            from_factor=from_factor,
            to_factor=to_factor,
            ratio=split_ratio,
            name=name or data.get('name', ''),
            exchange=data.get('exchange', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the stock split to a dictionary."""
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat() if self.date else None,
            'from_factor': self.from_factor,
            'to_factor': self.to_factor,
            'ratio': self.ratio,
            'split_text': f"{self.from_factor}:{self.to_factor}",
            'name': self.name,
            'exchange': self.exchange
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert the stock split to a flat dictionary for CSV export."""
        return {
            'symbol': self.symbol,
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'from_factor': self.from_factor,
            'to_factor': self.to_factor,
            'ratio': self.ratio,
            'split_text': f"{self.from_factor}:{self.to_factor}",
            'name': self.name or '',
            'exchange': self.exchange or ''
        }
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for stock split data."""
        return [
            'symbol', 'date', 'from_factor', 'to_factor', 
            'ratio', 'split_text', 'name', 'exchange'
        ]
    
    @property
    def split_text(self) -> str:
        """Get a human-readable split text."""
        return f"{self.from_factor}:{self.to_factor}"
    
    @property
    def is_forward_split(self) -> bool:
        """Check if this is a forward split (ratio > 1)."""
        return self.ratio > 1.0
    
    @property
    def is_reverse_split(self) -> bool:
        """Check if this is a reverse split (ratio < 1)."""
        return self.ratio < 1.0
    
    @property
    def effect_description(self) -> str:
        """Get a description of the split effect."""
        if self.is_forward_split:
            return f"Shareholders received {self.from_factor} shares for every {self.to_factor} share owned"
        elif self.is_reverse_split:
            return f"Shareholders received {self.to_factor} share for every {self.from_factor} shares owned"
        else:
            return "No change in number of shares"


class SplitHistory:
    """Collection of stock splits for a symbol."""
    
    def __init__(self, symbol: str, name: Optional[str], splits: List[StockSplit]):
        self.symbol = symbol
        self.name = name
        self.splits = sorted(splits, key=lambda s: s.date or datetime.min, reverse=True)
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], symbol: str) -> 'SplitHistory':
        """Create a SplitHistory instance from TwelveData API response."""
        name = data.get('meta', {}).get('name', '')
        splits_data = data.get('splits', [])
        splits = [StockSplit.from_api_response(item, symbol, name) for item in splits_data]
        
        return cls(
            symbol=symbol,
            name=name,
            splits=splits
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the split history to a dictionary."""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'splits_count': len(self.splits),
            'splits': [split.to_dict() for split in self.splits]
        }
    
    def get_splits_by_year(self) -> Dict[int, List[StockSplit]]:
        """Group splits by year."""
        result = {}
        for split in self.splits:
            if not split.date:
                continue
                
            year = split.date.year
            if year not in result:
                result[year] = []
            result[year].append(split)
        
        return result
    
    def get_cumulative_split_factor(self, start_date: Optional[datetime] = None, 
                                  end_date: Optional[datetime] = None) -> float:
        """
        Calculate the cumulative effect of all splits in the given date range.
        
        Args:
            start_date: Start date for range (None for all history)
            end_date: End date for range (None for all history)
            
        Returns:
            Cumulative split factor (multiply original shares by this to get current shares)
        """
        factor = 1.0
        
        for split in self.splits:
            if not split.date:
                continue
                
            # Skip if outside date range
            if start_date and split.date < start_date:
                continue
            if end_date and split.date > end_date:
                continue
                
            factor *= split.ratio
        
        return factor
    
    def get_years_with_splits(self) -> List[int]:
        """Get a list of years that had splits."""
        years = set()
        for split in self.splits:
            if split.date:
                years.add(split.date.year)
        
        return sorted(list(years), reverse=True)