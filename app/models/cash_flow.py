"""
Model for company cash flow data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any


class CashFlowItem:
    """
    Represents an individual line item in a cash flow statement.
    """
    def __init__(self, name: str, value: Union[float, int], value_str: Optional[str] = None):
        self.name = name
        self.value = value
        self.value_str = value_str or f"{value:,.2f}"
        
        # Determine if item is inflow or outflow
        if value > 0:
            self.flow_type = "inflow"
        elif value < 0:
            self.flow_type = "outflow"
        else:
            self.flow_type = "neutral"

    @classmethod
    def from_api_response(cls, name: str, value: Any) -> 'CashFlowItem':
        """Create a CashFlowItem from API response data"""
        # Handle null/None values from the API
        if value is None:
            return cls(name, 0, "N/A")
        
        # Try to convert to float, fallback to 0 if not possible
        try:
            float_value = float(value)
            return cls(name, float_value)
        except (ValueError, TypeError):
            return cls(name, 0, str(value) if value else "N/A")
            
    def to_dict(self) -> Dict[str, Union[str, float, int]]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "value": self.value,
            "value_str": self.value_str,
            "flow_type": self.flow_type
        }
        
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        return {
            "Item": self.name,
            "Value": self.value_str,
            "Flow Type": self.flow_type.capitalize()
        }


class CashFlowSection:
    """
    Represents a section of a cash flow statement (e.g., Operating Activities, Investing Activities).
    """
    def __init__(self, name: str, items: List[CashFlowItem], total: Optional[CashFlowItem] = None):
        self.name = name
        self.items = items
        
        # If total is not provided, calculate it
        if total is None and items:
            total_value = sum(item.value for item in items)
            self.total = CashFlowItem(f"Net Cash from {name}", total_value)
        else:
            self.total = total
            
    @property
    def value(self) -> float:
        """Get the total value of this section"""
        return self.total.value if self.total else 0
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary for serialization"""
        return {
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
            "total": self.total.to_dict() if self.total else None
        }
        
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Format section for CSV export"""
        rows = []
        
        # Add section header
        rows.append({"Item": f"--- {self.name} ---", "Value": "", "Flow Type": ""})
        
        # Add items
        for item in self.items:
            rows.append(item.to_csv_row())
            
        # Add total if available
        if self.total:
            rows.append(self.total.to_csv_row())
            
        return rows


class CashFlow:
    """
    Represents a company's cash flow statement for a specific period.
    """
    def __init__(self, 
                 symbol: str,
                 fiscal_date: str,
                 fiscal_period: str,
                 currency: str,
                 operating_activities: CashFlowSection,
                 investing_activities: CashFlowSection,
                 financing_activities: CashFlowSection,
                 beginning_cash: CashFlowItem,
                 ending_cash: CashFlowItem,
                 free_cash_flow: Optional[CashFlowItem] = None,
                 raw_data: Dict[str, Any] = None):
        
        self.symbol = symbol
        self.fiscal_date = fiscal_date
        self.fiscal_period = fiscal_period
        self.currency = currency
        
        # Main sections of cash flow statement
        self.operating_activities = operating_activities
        self.investing_activities = investing_activities
        self.financing_activities = financing_activities
        
        # Cash positions
        self.beginning_cash = beginning_cash
        self.ending_cash = ending_cash
        
        # Calculate net change in cash
        self.net_change_in_cash = CashFlowItem(
            "Net Change in Cash",
            self.ending_cash.value - self.beginning_cash.value
        )
        
        # Free cash flow (if provided or calculated)
        if free_cash_flow:
            self.free_cash_flow = free_cash_flow
        else:
            # Typical calculation: Operating Cash Flow - Capital Expenditures
            # Find capital expenditures in investing activities (typically negative)
            capex_item = next(
                (item for item in self.investing_activities.items 
                 if "capital expenditure" in item.name.lower() or 
                    "property, plant" in item.name.lower()),
                None
            )
            
            if capex_item:
                # Capex is typically negative, so we add it to operating cash flow
                self.free_cash_flow = CashFlowItem(
                    "Free Cash Flow",
                    self.operating_activities.total.value + capex_item.value
                )
            else:
                self.free_cash_flow = CashFlowItem("Free Cash Flow", 0, "N/A")
        
        # Store the raw data for access to additional fields
        self.raw_data = raw_data or {}
        
    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> 'CashFlow':
        """Create a CashFlow object from API response"""
        # Extract basic information
        data = response_data.copy()
        symbol = data.get('symbol', '')
        fiscal_date = data.get('fiscal_date', '')
        fiscal_period = data.get('fiscal_period', '')
        currency = data.get('currency', 'USD')
        
        # 1. Operating Activities Section
        operating_items = []
        for item_name, api_key in [
            ("Net Income", "net_income"),
            ("Depreciation and Amortization", "depreciation_and_amortization"),
            ("Deferred Income Taxes", "deferred_income_tax"),
            ("Stock-based Compensation", "stock_based_compensation"),
            ("Change in Working Capital", "change_in_working_capital"),
            ("Accounts Receivable", "accounts_receivable"),
            ("Inventory", "inventory"),
            ("Accounts Payable", "accounts_payable"),
            ("Other Working Capital", "other_working_capital"),
            ("Other Non-Cash Items", "other_non_cash_items")
        ]:
            if api_key in data and data[api_key] is not None:
                operating_items.append(
                    CashFlowItem.from_api_response(item_name, data[api_key])
                )
        
        # Get net cash from operating activities        
        net_operating_cash = CashFlowItem.from_api_response(
            "Net Cash from Operating Activities", 
            data.get('net_cash_provided_by_operating_activities')
        )
        
        operating_section = CashFlowSection(
            "Operating Activities",
            operating_items,
            net_operating_cash
        )
        
        # 2. Investing Activities Section
        investing_items = []
        for item_name, api_key in [
            ("Capital Expenditure", "capital_expenditure"),
            ("Acquisitions, Net", "acquisitions_net"),
            ("Purchases of Investments", "purchases_of_investments"),
            ("Sales/Maturities of Investments", "sales_maturities_of_investments"),
            ("Other Investing Activities", "other_investing_activites")
        ]:
            if api_key in data and data[api_key] is not None:
                investing_items.append(
                    CashFlowItem.from_api_response(item_name, data[api_key])
                )
        
        # Get net cash from investing activities
        net_investing_cash = CashFlowItem.from_api_response(
            "Net Cash from Investing Activities", 
            data.get('net_cash_used_for_investing_activites')
        )
        
        investing_section = CashFlowSection(
            "Investing Activities",
            investing_items,
            net_investing_cash
        )
        
        # 3. Financing Activities Section
        financing_items = []
        for item_name, api_key in [
            ("Debt Repayment", "debt_repayment"),
            ("Common Stock Issued", "common_stock_issued"),
            ("Common Stock Repurchased", "common_stock_repurchased"),
            ("Dividends Paid", "dividends_paid"),
            ("Other Financing Activities", "other_financing_activities")
        ]:
            if api_key in data and data[api_key] is not None:
                financing_items.append(
                    CashFlowItem.from_api_response(item_name, data[api_key])
                )
        
        # Get net cash from financing activities
        net_financing_cash = CashFlowItem.from_api_response(
            "Net Cash from Financing Activities", 
            data.get('net_cash_used_provided_by_financing_activities')
        )
        
        financing_section = CashFlowSection(
            "Financing Activities",
            financing_items,
            net_financing_cash
        )
        
        # Beginning and ending cash
        beginning_cash = CashFlowItem.from_api_response(
            "Cash at Beginning of Period",
            data.get('beginning_cash_position')
        )
        
        ending_cash = CashFlowItem.from_api_response(
            "Cash at End of Period",
            data.get('ending_cash_position')
        )
        
        # Free cash flow (if provided)
        free_cash_flow = CashFlowItem.from_api_response(
            "Free Cash Flow",
            data.get('free_cash_flow')
        ) if 'free_cash_flow' in data else None
        
        return cls(
            symbol=symbol,
            fiscal_date=fiscal_date,
            fiscal_period=fiscal_period,
            currency=currency,
            operating_activities=operating_section,
            investing_activities=investing_section,
            financing_activities=financing_section,
            beginning_cash=beginning_cash,
            ending_cash=ending_cash,
            free_cash_flow=free_cash_flow,
            raw_data=data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "fiscal_date": self.fiscal_date,
            "fiscal_period": self.fiscal_period,
            "currency": self.currency,
            "operating_activities": self.operating_activities.to_dict(),
            "investing_activities": self.investing_activities.to_dict(),
            "financing_activities": self.financing_activities.to_dict(),
            "beginning_cash": self.beginning_cash.to_dict(),
            "ending_cash": self.ending_cash.to_dict(),
            "net_change_in_cash": self.net_change_in_cash.to_dict(), 
            "free_cash_flow": self.free_cash_flow.to_dict() if self.free_cash_flow else None
        }
        
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Create rows for CSV export"""
        rows = []
        
        # Basic info
        rows.append({"Item": "Symbol", "Value": self.symbol, "Flow Type": ""})
        rows.append({"Item": "Fiscal Date", "Value": self.fiscal_date, "Flow Type": ""})
        rows.append({"Item": "Fiscal Period", "Value": self.fiscal_period, "Flow Type": ""})
        rows.append({"Item": "Currency", "Value": self.currency, "Flow Type": ""})
        rows.append({"Item": "", "Value": "", "Flow Type": ""})  # Empty row as separator
        
        # Beginning cash balance
        rows.append(self.beginning_cash.to_csv_row())
        rows.append({"Item": "", "Value": "", "Flow Type": ""})  # Empty row as separator
        
        # Operating Activities
        rows.extend(self.operating_activities.get_csv_rows())
        rows.append({"Item": "", "Value": "", "Flow Type": ""})  # Empty row as separator
        
        # Investing Activities
        rows.extend(self.investing_activities.get_csv_rows())
        rows.append({"Item": "", "Value": "", "Flow Type": ""})  # Empty row as separator
        
        # Financing Activities
        rows.extend(self.financing_activities.get_csv_rows())
        rows.append({"Item": "", "Value": "", "Flow Type": ""})  # Empty row as separator
        
        # Net change and ending cash
        rows.append(self.net_change_in_cash.to_csv_row())
        rows.append(self.ending_cash.to_csv_row())
        rows.append({"Item": "", "Value": "", "Flow Type": ""})  # Empty row as separator
        
        # Free cash flow
        if self.free_cash_flow:
            rows.append(self.free_cash_flow.to_csv_row())
        
        return rows
    
    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get headers for CSV export"""
        return ["Item", "Value", "Flow Type"]