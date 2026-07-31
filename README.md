# stock_analyse

Stock market data analysis tool for Hong Kong stocks.

## Features

- Fetches real-time market data for Hong Kong listed stocks
- Generates market sentiment reports
- Automated market monitoring via scheduled tasks
- Support for Tencent, 兆易创新 (03986), 太古地产 (01972), and other HK stocks

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the market data fetcher:

```bash
source .venv/bin/activate
python fetch_market_data.py
```

This will:
1. Fetch real-time stock data from HK markets
2. Generate a market sentiment report
3. Save the report to `MARKET_REPORT_<date>.md`

## Files

- `fetch_market_data.py` - Main script to fetch market data and generate reports
- `MARKET_REPORT_*.md` - Generated market analysis reports
- `requirements.txt` - Python dependencies
