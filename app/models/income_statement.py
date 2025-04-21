"""
Model for company income statement data from the TwelveData API.
"""
from datetime import datetime
from typing import Dict, List, Union, Optional, Any


class IncomeStatementItem:
    """
    Represents an individual line item in an income statement.
    """
    def __init__(self, name: str, value: Union[float, int], value_str: Optional[str] = None):
        self.name = name
        self.value = value
        self.value_str = value_str or f"{value:,.2f}"

    @classmethod
    def from_api_response(cls, name: str, value: Any) -> 'IncomeStatementItem':
        """Create an IncomeStatementItem from API response data"""
        # Handle null/None values from the API
        if value is None:
            return cls(name, 0, "N/A")
        
        # Try to convert to float, fallback to 0 if not possible
        try:
            float_value = float(value)
            return cls(name, float_value)
        except (ValueError, TypeError):
            return cls(name, 0, str(value) if value else "N/A")
            
    def to_dict(self) -> Dict[str, Union[str, float]]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "value": self.value,
            "value_str": self.value_str
        }
        
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        return {
            "Item": self.name,
            "Value": self.value_str
        }


class ExpenseItem(IncomeStatementItem):
    """
    Represents an expense item in an income statement, with additional
    percentage tracking relative to revenue.
    """
    def __init__(self, name: str, value: Union[float, int], 
                 percentage: Optional[float] = None, value_str: Optional[str] = None,
                 percentage_str: Optional[str] = None):
        super().__init__(name, value, value_str)
        self.percentage = percentage
        self.percentage_str = percentage_str or (f"{percentage:.2f}%" if percentage is not None else "N/A")
        
    @classmethod
    def from_api_response(cls, name: str, value: Any, 
                          total_revenue: Optional[float] = None) -> 'ExpenseItem':
        """Create an ExpenseItem from API response data with percentage of revenue"""
        item = super().from_api_response(name, value)
        
        # Calculate percentage if we have a valid total revenue
        percentage = None
        if total_revenue and total_revenue > 0 and item.value != 0:
            percentage = (item.value / total_revenue) * 100
            
        return cls(item.name, item.value, percentage, item.value_str)
    
    def to_dict(self) -> Dict[str, Union[str, float]]:
        """Convert to dictionary for serialization"""
        result = super().to_dict()
        result.update({
            "percentage": self.percentage,
            "percentage_str": self.percentage_str
        })
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Format for CSV export"""
        result = super().to_csv_row()
        result.update({
            "Percentage of Revenue": self.percentage_str
        })
        return result


class IncomeStatement:
    """
    Represents a company's income statement for a specific period.
    """
    def __init__(self, 
                 symbol: str,
                 fiscal_date: str,
                 fiscal_period: str,
                 currency: str,
                 revenue: IncomeStatementItem,
                 cost_of_revenue: ExpenseItem,
                 gross_profit: IncomeStatementItem,
                 operating_expenses: List[ExpenseItem],
                 operating_income: IncomeStatementItem,
                 non_operating_items: List[IncomeStatementItem],
                 income_before_tax: IncomeStatementItem,
                 income_tax: IncomeStatementItem,
                 net_income: IncomeStatementItem,
                 eps_basic: IncomeStatementItem,
                 eps_diluted: IncomeStatementItem,
                 shares_basic: IncomeStatementItem,
                 shares_diluted: IncomeStatementItem,
                 raw_data: Dict[str, Any]):
        
        self.symbol = symbol
        self.fiscal_date = fiscal_date
        self.fiscal_period = fiscal_period
        self.currency = currency
        
        # Key financial items
        self.revenue = revenue
        self.cost_of_revenue = cost_of_revenue
        self.gross_profit = gross_profit
        self.operating_expenses = operating_expenses
        self.operating_income = operating_income
        self.non_operating_items = non_operating_items
        self.income_before_tax = income_before_tax
        self.income_tax = income_tax
        self.net_income = net_income
        self.eps_basic = eps_basic
        self.eps_diluted = eps_diluted
        self.shares_basic = shares_basic
        self.shares_diluted = shares_diluted
        
        # Store the raw data for access to additional fields
        self.raw_data = raw_data
        
        # Calculate Total Operating Expenses
        self.total_operating_expenses = self._calculate_total_operating_expenses()
        
    def _calculate_total_operating_expenses(self) -> ExpenseItem:
        """Calculate the total operating expenses"""
        total = sum(item.value for item in self.operating_expenses)
        revenue_value = self.revenue.value if self.revenue.value != 0 else None
        percentage = (total / revenue_value) * 100 if revenue_value else None
        
        return ExpenseItem(
            "Total Operating Expenses", 
            total, 
            percentage
        )
    
    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> 'IncomeStatement':
        """Create an IncomeStatement object from API response"""
        # Extract basic information
        data = response_data.copy()
        symbol = data.get('symbol', '')
        fiscal_date = data.get('fiscal_date', '')
        fiscal_period = data.get('fiscal_period', '')
        currency = data.get('currency', 'USD')
        
        # Extract primary financial metrics
        revenue_value = data.get('revenue', 0)
        revenue = IncomeStatementItem.from_api_response("Revenue", revenue_value)
        
        # Create expense items with percentage of revenue
        cost_of_revenue = ExpenseItem.from_api_response(
            "Cost of Revenue", 
            data.get('cost_of_revenue'), 
            revenue.value
        )
        
        gross_profit = IncomeStatementItem.from_api_response(
            "Gross Profit", 
            data.get('gross_profit')
        )
        
        # Extract operating expenses
        operating_expenses = []
        for expense_name, api_key in [
            ("Research & Development", "research_and_development_expenses"),
            ("Selling, General & Administrative", "selling_general_and_administrative_expenses"),
            ("Depreciation & Amortization", "depreciation_and_amortization"),
            ("Restructuring Charges", "restructuring_charges"),
            ("Other Operating Expenses", "other_operating_expenses")
        ]:
            if api_key in data and data[api_key] is not None:
                expense = ExpenseItem.from_api_response(
                    expense_name, 
                    data[api_key],
                    revenue.value
                )
                operating_expenses.append(expense)
        
        # Extract other key metrics
        operating_income = IncomeStatementItem.from_api_response(
            "Operating Income", 
            data.get('operating_income')
        )
        
        # Non-operating items
        non_operating_items = []
        for item_name, api_key in [
            ("Interest Expense", "interest_expense"),
            ("Interest Income", "interest_income"),
            ("Other Non-Operating Income", "other_non_operating_income")
        ]:
            if api_key in data and data[api_key] is not None:
                item = IncomeStatementItem.from_api_response(item_name, data[api_key])
                non_operating_items.append(item)
        
        # Bottom line metrics
        income_before_tax = IncomeStatementItem.from_api_response(
            "Income Before Tax", 
            data.get('income_before_tax')
        )
        
        income_tax = IncomeStatementItem.from_api_response(
            "Income Tax Expense", 
            data.get('income_tax_expense')
        )
        
        net_income = IncomeStatementItem.from_api_response(
            "Net Income", 
            data.get('net_income')
        )
        
        # Per share metrics
        eps_basic = IncomeStatementItem.from_api_response(
            "EPS (Basic)", 
            data.get('eps_basic')
        )
        
        eps_diluted = IncomeStatementItem.from_api_response(
            "EPS (Diluted)", 
            data.get('eps_diluted')
        )
        
        shares_basic = IncomeStatementItem.from_api_response(
            "Weighted Average Shares (Basic)", 
            data.get('weighted_average_shares_outstanding_basic')
        )
        
        shares_diluted = IncomeStatementItem.from_api_response(
            "Weighted Average Shares (Diluted)", 
            data.get('weighted_average_shares_outstanding_diluted')
        )
        
        return cls(
            symbol=symbol,
            fiscal_date=fiscal_date,
            fiscal_period=fiscal_period,
            currency=currency,
            revenue=revenue,
            cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit,
            operating_expenses=operating_expenses,
            operating_income=operating_income,
            non_operating_items=non_operating_items,
            income_before_tax=income_before_tax,
            income_tax=income_tax,
            net_income=net_income,
            eps_basic=eps_basic,
            eps_diluted=eps_diluted,
            shares_basic=shares_basic,
            shares_diluted=shares_diluted,
            raw_data=data
        )
    
    def get_all_expenses(self) -> List[ExpenseItem]:
        """
        Get a consolidated list of all expenses in the income statement.
        """
        expenses = [self.cost_of_revenue]
        expenses.extend(self.operating_expenses)
        expenses.append(self.total_operating_expenses)
        
        # Add interest expense if it exists in non_operating_items
        interest_expense = next((item for item in self.non_operating_items 
                                if item.name == "Interest Expense"), None)
        if interest_expense and isinstance(interest_expense, ExpenseItem):
            expenses.append(interest_expense)
        elif interest_expense:
            # Convert to ExpenseItem if it's a regular IncomeStatementItem
            expenses.append(ExpenseItem.from_api_response(
                interest_expense.name, 
                interest_expense.value, 
                self.revenue.value
            ))
            
        return expenses
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "fiscal_date": self.fiscal_date,
            "fiscal_period": self.fiscal_period,
            "currency": self.currency,
            "revenue": self.revenue.to_dict(),
            "cost_of_revenue": self.cost_of_revenue.to_dict(),
            "gross_profit": self.gross_profit.to_dict(),
            "operating_expenses": [exp.to_dict() for exp in self.operating_expenses],
            "total_operating_expenses": self.total_operating_expenses.to_dict(),
            "operating_income": self.operating_income.to_dict(),
            "non_operating_items": [item.to_dict() for item in self.non_operating_items],
            "income_before_tax": self.income_before_tax.to_dict(),
            "income_tax": self.income_tax.to_dict(),
            "net_income": self.net_income.to_dict(),
            "eps_basic": self.eps_basic.to_dict(),
            "eps_diluted": self.eps_diluted.to_dict()
        }
        
    def get_csv_rows(self) -> List[Dict[str, str]]:
        """Create rows for CSV export"""
        rows = []
        
        # Basic info
        rows.append({"Item": "Symbol", "Value": self.symbol})
        rows.append({"Item": "Fiscal Date", "Value": self.fiscal_date})
        rows.append({"Item": "Fiscal Period", "Value": self.fiscal_period})
        rows.append({"Item": "Currency", "Value": self.currency})
        rows.append({"Item": "", "Value": ""})  # Empty row as separator
        
        # Main income statement items
        rows.append(self.revenue.to_csv_row())
        rows.append(self.cost_of_revenue.to_csv_row())
        rows.append(self.gross_profit.to_csv_row())
        rows.append({"Item": "", "Value": ""})  # Empty row as separator
        
        # Operating expenses
        rows.append({"Item": "Operating Expenses", "Value": ""})
        for expense in self.operating_expenses:
            rows.append(expense.to_csv_row())
        rows.append(self.total_operating_expenses.to_csv_row())
        rows.append({"Item": "", "Value": ""})  # Empty row as separator
        
        # Operating income and non-operating items
        rows.append(self.operating_income.to_csv_row())
        rows.append({"Item": "Non-operating Items", "Value": ""})
        for item in self.non_operating_items:
            rows.append(item.to_csv_row())
        rows.append({"Item": "", "Value": ""})  # Empty row as separator
        
        # Bottom line metrics
        rows.append(self.income_before_tax.to_csv_row())
        rows.append(self.income_tax.to_csv_row())
        rows.append(self.net_income.to_csv_row())
        rows.append({"Item": "", "Value": ""})  # Empty row as separator
        
        # Per share data
        rows.append(self.eps_basic.to_csv_row())
        rows.append(self.eps_diluted.to_csv_row())
        rows.append(self.shares_basic.to_csv_row())
        rows.append(self.shares_diluted.to_csv_row())
        
        return rows
    
    @staticmethod
    def get_csv_headers() -> List[str]:
        """Get headers for CSV export"""
        return ["Item", "Value", "Percentage of Revenue"]