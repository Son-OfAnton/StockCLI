from dataclasses import dataclass
from typing import List, Optional, Dict, Any, ClassVar


@dataclass
class Bond:
    """Model for bond data."""
    symbol: str
    name: str
    currency: str
    exchange: str
    country: Optional[str] = None
    type: str = "bond"
    bond_type: Optional[str] = None  # government, corporate, municipal, etc.
    issuer: Optional[str] = None
    maturity_date: Optional[str] = None
    coupon_rate: Optional[float] = None
    face_value: Optional[float] = None
    credit_rating: Optional[str] = None
    is_callable: Optional[bool] = None
    yield_to_maturity: Optional[float] = None
    mic_code: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Bond':
        """Create a Bond instance from TwelveData API response."""
        # Extract all possible fields that might be in the API response
        return cls(
            symbol=data["symbol"],
            name=data.get("name", ""),
            currency=data.get("currency", ""),
            exchange=data.get("exchange", ""),
            country=data.get("country"),
            type=data.get("type", "bond"),
            bond_type=data.get("bond_type"),
            issuer=data.get("issuer"),
            maturity_date=data.get("maturity_date"),
            coupon_rate=float(data["coupon_rate"]) if "coupon_rate" in data and data["coupon_rate"] is not None else None,
            face_value=float(data["face_value"]) if "face_value" in data and data["face_value"] is not None else None,
            credit_rating=data.get("credit_rating"),
            is_callable=bool(data["is_callable"]) if "is_callable" in data else None,
            yield_to_maturity=float(data["yield_to_maturity"]) if "yield_to_maturity" in data and data["yield_to_maturity"] is not None else None,
            mic_code=data.get("mic_code")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the bond to a dictionary."""
        result = {
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "exchange": self.exchange,
            "type": self.type
        }
        
        # Add optional fields if they exist
        if self.country:
            result["country"] = self.country
        if self.bond_type:
            result["bond_type"] = self.bond_type
        if self.issuer:
            result["issuer"] = self.issuer
        if self.maturity_date:
            result["maturity_date"] = self.maturity_date
        if self.coupon_rate is not None:
            result["coupon_rate"] = self.coupon_rate
        if self.face_value is not None:
            result["face_value"] = self.face_value
        if self.credit_rating:
            result["credit_rating"] = self.credit_rating
        if self.is_callable is not None:
            result["is_callable"] = self.is_callable
        if self.yield_to_maturity is not None:
            result["yield_to_maturity"] = self.yield_to_maturity
        if self.mic_code:
            result["mic_code"] = self.mic_code
            
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convert the bond to a CSV row (dictionary with string values)."""
        row = {
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "exchange": self.exchange,
            "country": self.country if self.country else "",
            "type": self.type,
            "bond_type": self.bond_type if self.bond_type else "",
            "issuer": self.issuer if self.issuer else "",
            "maturity_date": self.maturity_date if self.maturity_date else "",
            "coupon_rate": f"{self.coupon_rate:.4f}" if self.coupon_rate is not None else "",
            "face_value": f"{self.face_value:.2f}" if self.face_value is not None else "",
            "credit_rating": self.credit_rating if self.credit_rating else "",
            "is_callable": str(self.is_callable) if self.is_callable is not None else "",
            "yield_to_maturity": f"{self.yield_to_maturity:.4f}" if self.yield_to_maturity is not None else "",
            "mic_code": self.mic_code if self.mic_code else ""
        }
        return row
    
    @staticmethod
    def get_csv_header() -> List[str]:
        """Get the CSV header for bond data."""
        return [
            "symbol", "name", "currency", "exchange", "country", "type", "bond_type",
            "issuer", "maturity_date", "coupon_rate", "face_value", "credit_rating",
            "is_callable", "yield_to_maturity", "mic_code"
        ]