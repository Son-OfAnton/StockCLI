# StockCLI

StockCLI is a command-line tool for fetching the latest stock exchange and financial market data from the TwelveData API. This application is designed for developers and data enthusiasts who rely on the command line for quick and efficient market data retrieval and analysis.

## Features

- **Real-time Stock Quotes:** Fetch current quotes for one or more stock symbols.
- **Auto-Refresh:** Enable live auto-refresh of quotes with configurable intervals.
- **Export Functionality:** Export fetched quotes, symbols, forex pairs, cryptocurrency and funds information to JSON and/or CSV files.
- **Multiple Data Categories:** List and filter available symbols, forex pairs, cryptocurrencies, and funds (ETFs and mutual funds).
- **Custom Output Directories:** Option to specify custom export locations or use the user’s home directory.
- **Rich Terminal Display:** Uses Rich library to display formatted tables and progress spinners.

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

- **Stop Auto-Refresh:**

  If auto-refresh is running, you can stop it:
  
  ```bash
  stockcli stock stop
  ```

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