"""
Model for company executives and management data from the TwelveData API.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime


class Executive:
    """
    Represents a single executive or high-level manager at a company.
    """
    def __init__(self,
                 name: str,
                 title: str,
                 age: Optional[int] = None,
                 pay: Optional[float] = None,
                 currency: Optional[str] = None,
                 year: Optional[int] = None,
                 gender: Optional[str] = None,
                 biography: Optional[str] = None,
                 start_date: Optional[str] = None):
        self.name = name
        self.title = title
        self.age = age
        self.pay = pay
        self.currency = currency
        self.year = year
        self.gender = gender
        self.biography = biography
        self.start_date = start_date
        
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Executive':
        """Create an Executive object from API response data"""
        name = data.get('name', '')
        title = data.get('title', '')
        
        # Extract age
        age = None
        age_str = data.get('age')
        if age_str:
            try:
                age = int(age_str)
            except (ValueError, TypeError):
                pass
        
        # Extract pay
        pay = None
        pay_str = data.get('pay')
        if pay_str:
            try:
                pay = float(pay_str)
            except (ValueError, TypeError):
                pass
        
        currency = data.get('currency')
        
        # Extract pay year
        year = None
        year_str = data.get('year')
        if year_str:
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                pass
        
        gender = data.get('gender')
        biography = data.get('biography')
        start_date = data.get('start_date')
        
        return cls(
            name=name,
            title=title,
            age=age,
            pay=pay,
            currency=currency,
            year=year,
            gender=gender,
            biography=biography,
            start_date=start_date
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "name": self.name,
            "title": self.title
        }
        
        if self.age is not None:
            result["age"] = self.age
            
        if self.pay is not None:
            result["pay"] = self.pay
            result["currency"] = self.currency
            result["year"] = self.year
            
        if self.gender:
            result["gender"] = self.gender
            
        if self.biography:
            result["biography"] = self.biography
            
        if self.start_date:
            result["start_date"] = self.start_date
            
        return result
    
    def get_formatted_pay(self) -> str:
        """Get formatted pay string"""
        if self.pay is not None and self.currency:
            # Format in millions if over 1M
            if self.pay >= 1000000:
                pay_in_millions = self.pay / 1000000
                return f"{pay_in_millions:.2f}M {self.currency}"
            else:
                return f"{self.pay:,.0f} {self.currency}"
        return "N/A"
    
    def get_formatted_title(self, max_length: Optional[int] = None) -> str:
        """Get formatted title, optionally truncated"""
        if not self.title:
            return "N/A"
        
        if max_length and len(self.title) > max_length:
            return f"{self.title[:max_length-3]}..."
        
        return self.title
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format executive data for CSV export"""
        row = {
            "Name": self.name,
            "Title": self.title,
        }
        
        if self.age is not None:
            row["Age"] = str(self.age)
        else:
            row["Age"] = ""
            
        if self.pay is not None:
            row["Compensation"] = f"{self.pay:,.0f}"
            row["Currency"] = self.currency or ""
            row["Year"] = str(self.year) if self.year else ""
        else:
            row["Compensation"] = ""
            row["Currency"] = ""
            row["Year"] = ""
            
        if self.gender:
            row["Gender"] = self.gender
        else:
            row["Gender"] = ""
            
        if self.start_date:
            row["Start Date"] = self.start_date
        else:
            row["Start Date"] = ""
            
        if self.biography:
            # Clean up newlines for CSV
            bio = self.biography.replace('\n', ' ').replace('\r', '')
            row["Biography"] = bio
        else:
            row["Biography"] = ""
            
        return row


class ManagementTeam:
    """
    Represents the management team of a company.
    """
    def __init__(self,
                 symbol: str,
                 name: Optional[str] = None,
                 executives: List[Executive] = None):
        self.symbol = symbol
        self.name = name
        self.executives = executives or []
        
        # Group executives by role categories for easier access
        self.categorize_executives()
        
    def categorize_executives(self):
        """Categorize executives by type of role"""
        # Initialize categories
        self.leadership = []  # CEO, President, Chairperson
        self.finance = []     # CFO, Treasurer
        self.operations = []  # COO, Operations roles
        self.technology = []  # CTO, CIO, Technology roles
        self.other = []       # All other executives
        
        for exec in self.executives:
            title = exec.title.lower() if exec.title else ""
            
            if any(role in title for role in ["ceo", "chief executive", "president", "chairman", "chairwoman", "chairperson"]):
                self.leadership.append(exec)
            elif any(role in title for role in ["cfo", "chief financial", "treasurer", "finance"]):
                self.finance.append(exec)
            elif any(role in title for role in ["coo", "chief operating", "operation"]):
                self.operations.append(exec)
            elif any(role in title for role in ["cto", "chief technology", "cio", "chief information", "tech"]):
                self.technology.append(exec)
            else:
                self.other.append(exec)
    
    def get_ceo(self) -> Optional[Executive]:
        """Get the CEO or equivalent top executive"""
        for exec in self.leadership:
            title = exec.title.lower() if exec.title else ""
            if "ceo" in title or "chief executive" in title:
                return exec
        
        # If no exact CEO match, return the first leadership executive if any
        return self.leadership[0] if self.leadership else None
    
    def get_cfo(self) -> Optional[Executive]:
        """Get the CFO or equivalent finance executive"""
        for exec in self.finance:
            title = exec.title.lower() if exec.title else ""
            if "cfo" in title or "chief financial" in title:
                return exec
                
        # If no exact CFO match, return the first finance executive if any
        return self.finance[0] if self.finance else None
    
    def get_coo(self) -> Optional[Executive]:
        """Get the COO or equivalent operations executive"""
        for exec in self.operations:
            title = exec.title.lower() if exec.title else ""
            if "coo" in title or "chief operating" in title:
                return exec
                
        # If no exact COO match, return the first operations executive if any
        return self.operations[0] if self.operations else None
    
    @classmethod
    def from_api_response(cls, symbol: str, data: Dict[str, Any]) -> 'ManagementTeam':
        """Create a ManagementTeam object from API response"""
        company_name = data.get('name', '')
        
        # Extract executives
        executives = []
        executives_data = data.get('executives', [])
        
        for exec_data in executives_data:
            if isinstance(exec_data, dict):  # Ensure it's a valid dictionary
                executive = Executive.from_api_response(exec_data)
                executives.append(executive)
        
        return cls(
            symbol=symbol,
            name=company_name,
            executives=executives
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "executives": [exec.to_dict() for exec in self.executives]
        }
    
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Format management team data for CSV export"""
        rows = []
        
        for executive in self.executives:
            row = executive.to_csv_row()
            # Add company info to each row
            row["Symbol"] = self.symbol
            row["Company"] = self.name or ""
            rows.append(row)
            
        return rows
    
    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get headers for CSV export"""
        return [
            "Symbol", "Company", "Name", "Title", "Age", 
            "Compensation", "Currency", "Year", "Gender", 
            "Start Date", "Biography"
        ]