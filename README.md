# StockCLI

StockCLI is a command-line tool for fetching the latest stock exchange and financial market data from the TwelveData API. This application is designed for developers and data enthusiasts who rely on the command line for quick and efficient market data retrieval and analysis.

## Features

- **Real-time Stock Quotes:** Fetch current quotes for one or more stock symbols.
- **Auto-Refresh:** Enable live auto-refresh of quotes with configurable intervals and a stop command.
- **Export Functionality:** Export fetched quotes, symbols, forex pairs, cryptocurrency, fund data (ETFs and mutual funds), and bond data to JSON and/or CSV files.
- **Multiple Data Categories:** List and filter available stocks, forex pairs, cryptocurrencies, funds, bonds, and commodities.
- **Exchange Details & Trading Hours:** Fetch detailed exchange information along with trading schedules.
- **Fund Data & Company Profiles:** View detailed profiles for ETFs, mutual funds (including mutual fund type details), and company profiles.
- **Custom Output Directories:** Specify custom export locations or use the user’s home directory.
- **Rich Terminal Display:** Enjoy formatted tables, panels, and progress spinners for an enhanced terminal experience.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/Son-OfAnton/StockCLI.git
   cd StockCLI
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**

   Copy the example environment file and update it with your API credentials:
   
   ```bash
   cp .env.example .env
   # Then edit .env to set your TWELVEDATA_API_KEY and TWELVEDATA_BASE_URL
   ```

## Usage

After installation, you can explore the available commands:

- **Show Help:**
  
  ```bash
  stockcli --help
  ```

- **Get Stock Quotes:**

  Get a single or multiple stock quotes and optionally enable auto-refresh or export:
  
  ```bash
  stockcli quote AAPL MSFT --refresh --interval 5
  ```

- **Export Last Fetched Quotes:**

  ```bash
  stockcli export-last --format both [--output-dir <your_path>] [--use-home-dir]
  ```

- **Symbol Information:**

  List all available symbols, filter by exchange, type or country:
  
  ```bash
  stockcli symbols list --exchange NASDAQ --detailed
  ```

- **Forex Data:**

  List forex pairs or currencies:
  
  ```bash
  stockcli forex pairs --base USD
  stockcli forex currencies --export json
  ```

- **Cryptocurrency Data:**

  List available cryptocurrency pairs and exchanges:
  
  ```bash
  stockcli crypto list --quote USD --detailed
  stockcli crypto exchanges --export csv
  ```

- **Fund Data:**

  List ETFs or mutual funds with filtering options:
  
  ```bash
  stockcli funds list --type etf --detailed
  stockcli funds mutual --search Vanguard
  ```

- **Bond Data:**

  List bonds with detailed information:
  
  ```bash
  stockcli bonds list --detailed --export json
  ```

- **Exchange Details & Trading Hours:**

  Get detailed exchange information and trading hours:
  
  ```bash
  stockcli symbols exchange-details <exchange_code> [--export csv]
  stockcli exchange-schedule <exchange_code> --detailed
  ```

- **Commodity Data:**

  List commodity pairs and groups:
  
  ```bash
  stockcli commodities list --detailed
  ```

- **Stop Auto-Refresh:**

  Stop any running auto-refresh processes:
  
  ```bash
  stockcli stock stop
  ```

## Available Commands

- **stock version**  
  Show the application version.

- **stock quote**  
  Fetch current stock quotes for one or more symbols with options for auto‑refresh, detailed view, and export.

- **stock export-last**  
  Export the most recently fetched quotes to JSON, CSV, or both.

- **stock symbols list**  
  List available financial symbols with optional filtering (by exchange, type, country, search, etc.).

- **stock symbols types**  
  List available symbol types.

- **stock symbols exchanges**  
  Display exchanges (with an option to export results).

- **stock symbols exchange-details / trading-hours / all-trading-hours / instrument-types / search / cross-list**  
  Get detailed exchange information (including trading hours) or search/cross‑list symbols.

- **stock time-series**  
  Fetch historical price and meta data for a specified symbol with options for interval, date range, and export.

- **stock forex rate**  
  Get the real‑time exchange rate for a currency pair.

- **stock forex pairs / currencies**  
  List available forex pairs or currencies with export options.

- **stock crypto list / exchanges**  
  List available cryptocurrency pairs or exchanges.

- **stock latest-quote**  
  Retrieve the most recent quote for a specified symbol with options for simplified view and auto‑refresh.

- **stock eod**  
  Obtain end‑of‑day price data for a specific symbol.

- **stock gainers / losers**  
  Show top gaining or losing stocks for the day.

- **stock mutual-funds list**  
  List available mutual funds (ETFs and/or mutual funds) with filtering and detailed information.

- **stock mutual-funds info**  
  Get detailed profile information for a specific mutual fund.

- **stock mutual-funds families / family**  
  List available fund families or get details of a specific fund family.

- **stock mutual-funds types / type**  
  List available mutual fund types or get detailed information about a specific mutual fund type.

- **stock funds list / etfs / mutual**  
  List funds with filtering options.

- **stock company profile**  
  Retrieve detailed company profile information.

- **stock dividends history / compare / calendar**  
  Retrieve dividend history, compare histories for multiple symbols, or display a dividend calendar.

- **stock splits history / compare / calendar**  
  Show stock splits history, compare splits, or view a splits calendar.

- **stock income-statement get / compare / expenses**  
  Retrieve an income statement, compare statements across periods, or show expense breakdown.

- **stock balance-sheet get / compare / structure**  
  Fetch a company’s balance sheet, compare multiple sheets, or display the structure breakdown.

- **stock consolidated-balance-sheet get / compare / structure**  
  Retrieve a consolidated balance sheet (across subsidiaries), compare them, or show structure.

- **stock cash-flow get / compare / analyze**  
  Obtain cash flow statements, compare multiple periods, or analyze cash flow trends.

- **stock executives list / profile / compensation**  
  List a company’s executives, get an executive profile, or analyze compensation structure.

- **stock market-cap history / compare**  
  Retrieve or compare market capitalization history (with charting options).

- **stock analysts estimates / eps-compare / revenue / revenue-compare**  
  Show analyst estimates, compare EPS or revenue estimates across periods.

**Shortcut Commands:**  
Additionally, shortcuts are provided (e.g., `quote`, `export-last`, `symbols`, `forex`, `crypto`, `funds`, `bonds`, `etfs`, `commodities`, `mutual-funds`, `company`, `dividends`, `splits`, `income-statement`, `balance-sheet`, `cash-flow`, `executives`, `market-cap`, and `analysts`) with corresponding subcommands.

## Project Structure

Below is the current project structure:

```
StockCLI/
├── .env                 # Environment variables for API key and base URL
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py
├── app/
│   ├── __init__.py
│   ├── main.py         # Main entry point that sets up CLI commands
│   ├── api/
│   │   ├── __init__.py
│   │   └── twelvedata.py  # API client for TwelveData
│   ├── commands/
│   │   └── __init__.py   # Contains all CLI command groups and commands
│   └── utils/
│       ├── __init__.py
│       ├── formatting.py  # Formatting functions for CLI display
│       └── config.py      # (Optional) Additional configuration utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # Test configuration file
│   ├── test_api.py      # API client tests
│   ├── test_commands.py # CLI commands tests
│   └── test_utils.py    # Utility functions tests
├── GDrive/              # Contains metadata and conversation histories
│   ├── Conversation-1/
│   │   └── metadata.json
│   └── Conversation-2/
│       └── metadata.json
```

## Author

Admas Terefe Girma  
Email: aadmasterefe00@gmail.com