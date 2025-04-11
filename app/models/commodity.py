"""
Data models for commodity pair information.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class CommodityPair:
    """Model for commodity trading pair data."""
    symbol: str
    base_commodity: str
    quote_currency: str
    available_exchanges: List[str]
    is_active: bool = True
    commodity_group: Optional[str] = None  # precious_metals, energy, agriculture, etc.
    symbol_description: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CommodityPair':
        """Create a CommodityPair instance from TwelveData API response."""
        # Extract all possible fields that might be in the API response
        # Split the symbol to get base and quote
        symbol = data["symbol"]
        
        # Handle different symbol formats (XAU/USD or XAUUSD)
        if "/" in symbol:
            base, quote = symbol.split("/", 1)
        else:
            # Try to identify base and quote from common patterns
            if symbol.startswith("XAU") or symbol.startswith("XAG") or symbol.startswith("XPD") or symbol.startswith("XPT"):
                base = symbol[:3]
                quote = symbol[3:]
            elif symbol.endswith("USD") or symbol.endswith("EUR") or symbol.endswith("GBP"):
                base = symbol[:-3]
                quote = symbol[-3:]
            else:
                # If we can't determine, use the whole symbol as base
                base = symbol
                quote = ""
        
        # Determine commodity group based on common commodity codes
        commodity_group = None
        if base in ["XAU", "XAG", "XPT", "XPD", "GOLD", "SILVER"]:
            commodity_group = "precious_metals"
        elif base in ["CL", "NG", "BRENT", "WTI", "OIL", "GAS"]:
            commodity_group = "energy"
        elif base in ["ZC", "ZW", "ZS", "CORN", "WHEAT", "SOYBEAN", "COTTON", "SUGAR", "COFFEE", "COCOA"]:
            commodity_group = "agriculture"
        elif base in ["HG", "COPPER", "ALU", "ALUMINIUM", "ZINC", "NICKEL"]:
            commodity_group = "industrial_metals"
        
        # Extract available exchanges
        available_exchanges = data.get("available_exchanges", [])
        if isinstance(available_exchanges, str):
            available_exchanges = [available_exchanges]
        
        return cls(
            symbol=symbol,
            base_commodity=base,
            quote_currency=quote,
            available_exchanges=available_exchanges,
            is_active=data.get("is_active", True),
            commodity_group=data.get("commodity_group", commodity_group),
            symbol_description=data.get("symbol_description", None)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the commodity pair to a dictionary."""
        return {
            "symbol": self.symbol,
            "base_commodity": self.base_commodity,
            "quote_currency": self.quote_currency,
            "available_exchanges": self.available_exchanges,
            "is_active": self.is_active,
            "commodity_group": self.commodity_group,
            "symbol_description": self.symbol_description
        }
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the commodity pair to a CSV row (dictionary with string values)."""
        row = {
            "symbol": self.symbol,
            "base_commodity": self.base_commodity,
            "quote_currency": self.quote_currency,
            "available_exchanges": ", ".join(self.available_exchanges),
            "is_active": str(self.is_active),
            "commodity_group": self.commodity_group if self.commodity_group else "",
            "symbol_description": self.symbol_description if self.symbol_description else ""
        }
        return row
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for commodity pair data."""
        return [
            "symbol", "base_commodity", "quote_currency", "available_exchanges",
            "is_active", "commodity_group", "symbol_description"
        ]


@dataclass
class CommodityGroup:
    """Model for commodity group information."""
    name: str
    description: str
    examples: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the commodity group to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "examples": self.examples
        }