"""
Model for company balance sheet data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any


class BalanceSheetItem:
    """
    Represents an individual line item in a balance sheet.
    """
    def __init__(self, name: str, value: Union[float, int], percentage: Optional[float] = None,
                 value_str: Optional[str] = None, percentage_str: Optional[str] = None):
        self.name = name
        self.value = value
        self.value_str = value_str or f"{value:,.2f}"
        self.percentage = percentage
        self.percentage_str = percentage_str or (f"{percentage:.2f}%" if percentage is not None else "N/A")

    @classmethod
    def from_api_response(cls, name: str, value: Any, total_value: Optional[float] = None) -> 'BalanceSheetItem':
        """Create a BalanceSheetItem from API response data with optional percentage of total"""
        # Handle null/None values from the API
        if value is None:
            return cls(name, 0, None, "N/A", "N/A")
        
        # Try to convert to float, fallback to 0 if not possible
        try:
            float_value = float(value)
            
            # Calculate percentage if total value is provided
            percentage = None
            if total_value is not None and total_value != 0:
                percentage = (float_value / total_value) * 100
                
            return cls(name, float_value, percentage)
        except (ValueError, TypeError):
            return cls(name, 0, None, str(value) if value else "N/A", "N/A")
            
    def to_dict(self) -> Dict[str, Union[str, float]]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "value": self.value,
            "value_str": self.value_str,
            "percentage": self.percentage,
            "percentage_str": self.percentage_str
        }
        
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        return {
            "Item": self.name,
            "Value": self.value_str,
            "Percentage": self.percentage_str
        }


class BalanceSheetSection:
    """
    Represents a section of a balance sheet (e.g., Current Assets, Long-term Liabilities).
    """
    def __init__(self, name: str, items: List[BalanceSheetItem], total: Optional[BalanceSheetItem] = None):
        self.name = name
        self.items = items
        
        # If total is not provided, calculate it
        if total is None and items:
            total_value = sum(item.value for item in items)
            self.total = BalanceSheetItem(f"Total {name}", total_value)
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
        rows.append({"Item": f"--- {self.name} ---", "Value": "", "Percentage": ""})
        
        # Add items
        for item in self.items:
            rows.append(item.to_csv_row())
            
        # Add total if available
        if self.total:
            rows.append(self.total.to_csv_row())
            
        return rows


class BalanceSheet:
    """
    Represents a company's balance sheet for a specific period.
    """
    def __init__(self, 
                 symbol: str,
                 fiscal_date: str,
                 fiscal_period: str,
                 currency: str,
                 current_assets: BalanceSheetSection,
                 non_current_assets: BalanceSheetSection,
                 current_liabilities: BalanceSheetSection,
                 non_current_liabilities: BalanceSheetSection,
                 shareholders_equity: BalanceSheetSection,
                 total_assets: BalanceSheetItem,
                 total_liabilities: BalanceSheetItem,
                 raw_data: Dict[str, Any]):
        
        self.symbol = symbol
        self.fiscal_date = fiscal_date
        self.fiscal_period = fiscal_period
        self.currency = currency
        
        # Assets
        self.current_assets = current_assets
        self.non_current_assets = non_current_assets
        self.total_assets = total_assets
        
        # Liabilities
        self.current_liabilities = current_liabilities
        self.non_current_liabilities = non_current_liabilities
        self.total_liabilities = total_liabilities
        
        # Shareholders' Equity
        self.shareholders_equity = shareholders_equity
        
        # Total liabilities + equity (should equal total assets)
        self.total_liabilities_and_equity = BalanceSheetItem(
            "Total Liabilities and Shareholders' Equity",
            self.total_liabilities.value + self.shareholders_equity.total.value
        )
        
        # Store the raw data for access to additional fields
        self.raw_data = raw_data
        
        # Calculate financial ratios
        self.calculate_ratios()
        
    def calculate_ratios(self):
        """Calculate key financial ratios from the balance sheet data"""
        # Current ratio (liquidity)
        if self.current_liabilities.value != 0:
            current_ratio = self.current_assets.value / self.current_liabilities.value
            self.current_ratio = BalanceSheetItem("Current Ratio", current_ratio)
        else:
            self.current_ratio = BalanceSheetItem("Current Ratio", 0, None, "N/A")
            
        # Debt to equity ratio
        if self.shareholders_equity.value != 0:
            debt_to_equity = self.total_liabilities.value / self.shareholders_equity.value
            self.debt_to_equity = BalanceSheetItem("Debt to Equity Ratio", debt_to_equity)
        else:
            self.debt_to_equity = BalanceSheetItem("Debt to Equity Ratio", 0, None, "N/A")
            
        # Debt ratio
        if self.total_assets.value != 0:
            debt_ratio = self.total_liabilities.value / self.total_assets.value
            self.debt_ratio = BalanceSheetItem("Debt Ratio", debt_ratio)
        else:
            self.debt_ratio = BalanceSheetItem("Debt Ratio", 0, None, "N/A")
            
    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> 'BalanceSheet':
        """Create a BalanceSheet object from API response"""
        # Extract basic information
        data = response_data.copy()
        symbol = data.get('symbol', '')
        fiscal_date = data.get('fiscal_date', '')
        fiscal_period = data.get('fiscal_period', '')
        currency = data.get('currency', 'USD')
        
        # Extract total assets for percentage calculations
        total_assets_value = data.get('total_assets', 0)
        
        # 1. Current Assets Section
        current_assets_items = []
        for item_name, api_key in [
            ("Cash and Cash Equivalents", "cash_and_cash_equivalents"),
            ("Short-term Investments", "short_term_investments"),
            ("Accounts Receivable", "accounts_receivable"),
            ("Inventory", "inventory"),
            ("Other Current Assets", "other_current_assets")
        ]:
            if api_key in data and data[api_key] is not None:
                current_assets_items.append(
                    BalanceSheetItem.from_api_response(item_name, data[api_key], total_assets_value)
                )
        
        total_current_assets = BalanceSheetItem.from_api_response(
            "Total Current Assets", 
            data.get('current_assets'),
            total_assets_value
        )
        
        current_assets_section = BalanceSheetSection(
            "Current Assets",
            current_assets_items,
            total_current_assets
        )
        
        # 2. Non-Current (Long-term) Assets Section
        non_current_assets_items = []
        for item_name, api_key in [
            ("Property, Plant and Equipment", "property_plant_equipment_net"),
            ("Goodwill", "goodwill"),
            ("Intangible Assets", "intangible_assets"),
            ("Long-term Investments", "long_term_investments"),
            ("Other Non-Current Assets", "other_non_current_assets")
        ]:
            if api_key in data and data[api_key] is not None:
                non_current_assets_items.append(
                    BalanceSheetItem.from_api_response(item_name, data[api_key], total_assets_value)
                )
        
        # Calculate total non-current assets
        non_current_assets_value = (
            float(total_assets_value) - float(data.get('current_assets', 0))
            if total_assets_value is not None and data.get('current_assets') is not None
            else None
        )
        
        total_non_current_assets = BalanceSheetItem.from_api_response(
            "Total Non-Current Assets", 
            non_current_assets_value,
            total_assets_value
        )
        
        non_current_assets_section = BalanceSheetSection(
            "Non-Current Assets",
            non_current_assets_items,
            total_non_current_assets
        )
        
        # Total Assets
        total_assets = BalanceSheetItem.from_api_response(
            "Total Assets", 
            total_assets_value
        )
        
        # 3. Current Liabilities Section
        total_liabilities_value = data.get('total_liabilities', 0) 
        
        current_liabilities_items = []
        for item_name, api_key in [
            ("Accounts Payable", "account_payables"),
            ("Short-term Debt", "short_term_debt"),
            ("Current Portion of Long-term Debt", "current_portion_of_long_term_debt"),
            ("Deferred Revenue", "deferred_revenue"),
            ("Other Current Liabilities", "other_current_liabilities")
        ]:
            if api_key in data and data[api_key] is not None:
                current_liabilities_items.append(
                    BalanceSheetItem.from_api_response(item_name, data[api_key], total_liabilities_value)
                )
        
        total_current_liabilities = BalanceSheetItem.from_api_response(
            "Total Current Liabilities", 
            data.get('current_liabilities'),
            total_liabilities_value
        )
        
        current_liabilities_section = BalanceSheetSection(
            "Current Liabilities",
            current_liabilities_items,
            total_current_liabilities
        )
        
        # 4. Non-Current (Long-term) Liabilities Section
        non_current_liabilities_items = []
        for item_name, api_key in [
            ("Long-term Debt", "long_term_debt"),
            ("Deferred Tax Liabilities", "deferred_tax_liabilities"),
            ("Pension and Other Post-Retirement Benefits", "pension_and_other_post_retirement_benefit"),
            ("Other Non-Current Liabilities", "other_non_current_liabilities")
        ]:
            if api_key in data and data[api_key] is not None:
                non_current_liabilities_items.append(
                    BalanceSheetItem.from_api_response(item_name, data[api_key], total_liabilities_value)
                )
        
        # Calculate total non-current liabilities
        non_current_liabilities_value = (
            float(total_liabilities_value) - float(data.get('current_liabilities', 0))
            if total_liabilities_value is not None and data.get('current_liabilities') is not None
            else None
        )
        
        total_non_current_liabilities = BalanceSheetItem.from_api_response(
            "Total Non-Current Liabilities", 
            non_current_liabilities_value,
            total_liabilities_value
        )
        
        non_current_liabilities_section = BalanceSheetSection(
            "Non-Current Liabilities",
            non_current_liabilities_items,
            total_non_current_liabilities
        )
        
        # Total Liabilities
        total_liabilities = BalanceSheetItem.from_api_response(
            "Total Liabilities", 
            total_liabilities_value,
            total_assets_value  # Use total assets for percentage calculation
        )
        
        # 5. Shareholders' Equity Section
        total_equity_value = data.get('total_shareholders_equity', 0)
        
        equity_items = []
        for item_name, api_key in [
            ("Common Stock", "common_stock"),
            ("Additional Paid-in Capital", "additional_paid_in_capital"),
            ("Retained Earnings", "retained_earnings"),
            ("Treasury Stock", "treasury_stock"),
            ("Accumulated Other Comprehensive Income", "accumulated_other_comprehensive_income")
        ]:
            if api_key in data and data[api_key] is not None:
                # For treasury stock, ensure it's shown as negative
                value = data[api_key]
                if api_key == "treasury_stock" and value is not None:
                    try:
                        value = -abs(float(value))
                    except (ValueError, TypeError):
                        pass
                    
                equity_items.append(
                    BalanceSheetItem.from_api_response(item_name, value, total_assets_value)
                )
        
        total_equity = BalanceSheetItem.from_api_response(
            "Total Shareholders' Equity", 
            total_equity_value,
            total_assets_value  # Use total assets for percentage calculation
        )
        
        equity_section = BalanceSheetSection(
            "Shareholders' Equity",
            equity_items,
            total_equity
        )
        
        return cls(
            symbol=symbol,
            fiscal_date=fiscal_date,
            fiscal_period=fiscal_period,
            currency=currency,
            current_assets=current_assets_section,
            non_current_assets=non_current_assets_section,
            current_liabilities=current_liabilities_section,
            non_current_liabilities=non_current_liabilities_section,
            shareholders_equity=equity_section,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            raw_data=data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "fiscal_date": self.fiscal_date,
            "fiscal_period": self.fiscal_period,
            "currency": self.currency,
            "assets": {
                "current_assets": self.current_assets.to_dict(),
                "non_current_assets": self.non_current_assets.to_dict(),
                "total_assets": self.total_assets.to_dict()
            },
            "liabilities": {
                "current_liabilities": self.current_liabilities.to_dict(),
                "non_current_liabilities": self.non_current_liabilities.to_dict(),
                "total_liabilities": self.total_liabilities.to_dict()
            },
            "shareholders_equity": self.shareholders_equity.to_dict(),
            "total_liabilities_and_equity": self.total_liabilities_and_equity.to_dict(),
            "ratios": {
                "current_ratio": self.current_ratio.to_dict(),
                "debt_to_equity": self.debt_to_equity.to_dict(),
                "debt_ratio": self.debt_ratio.to_dict()
            }
        }
        
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Create rows for CSV export"""
        rows = []
        
        # Basic info
        rows.append({"Item": "Symbol", "Value": self.symbol, "Percentage": ""})
        rows.append({"Item": "Fiscal Date", "Value": self.fiscal_date, "Percentage": ""})
        rows.append({"Item": "Fiscal Period", "Value": self.fiscal_period, "Percentage": ""})
        rows.append({"Item": "Currency", "Value": self.currency, "Percentage": ""})
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        
        # Assets section
        rows.append({"Item": "ASSETS", "Value": "", "Percentage": ""})
        rows.extend(self.current_assets.get_csv_rows())
        rows.extend(self.non_current_assets.get_csv_rows())
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        rows.append(self.total_assets.to_csv_row())
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        
        # Liabilities section
        rows.append({"Item": "LIABILITIES", "Value": "", "Percentage": ""})
        rows.extend(self.current_liabilities.get_csv_rows())
        rows.extend(self.non_current_liabilities.get_csv_rows())
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        rows.append(self.total_liabilities.to_csv_row())
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        
        # Shareholders' Equity section
        rows.append({"Item": "SHAREHOLDERS' EQUITY", "Value": "", "Percentage": ""})
        rows.extend(self.shareholders_equity.get_csv_rows())
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        
        # Total Liabilities and Equity
        rows.append(self.total_liabilities_and_equity.to_csv_row())
        rows.append({"Item": "", "Value": "", "Percentage": ""})  # Empty row as separator
        
        # Ratios
        rows.append({"Item": "KEY FINANCIAL RATIOS", "Value": "", "Percentage": ""})
        rows.append(self.current_ratio.to_csv_row())
        rows.append(self.debt_to_equity.to_csv_row())
        rows.append(self.debt_ratio.to_csv_row())
        
        return rows
    
    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get headers for CSV export"""
        return ["Item", "Value", "Percentage"]