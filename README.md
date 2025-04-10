# StockCLI

StockCLI is a command-line tool for fetching the latest stock exchange data from the TwelveData API. This application is designed for developers who rely on the command line to make data-driven investment decisions.

## Features

- Fetches real-time stock exchange data.
- Displays formatted output in the terminal using Rich.
- Configurable via environment variables (set `TWELVEDATA_API_KEY` and `TWELVEDATA_BASE_URL` in your `.env` file).

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

## Usage

To see the available commands, run:

```bash
stockcli --help
```

## Project Structure

Below is the current project structure:

```
StockCLI/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── twelvedata.py
│   ├── commands/
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       ├── formatting.py
│       └── config.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_commands.py
│   └── test_utils.py

```

## Author

Admas Terefe Girma  
Email: aadmasterefe00@gmail.com
