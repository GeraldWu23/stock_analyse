#!/usr/bin/env python3
"""
Market Data Fetcher
Fetches stock market data for Hong Kong stocks and generates analysis reports.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Warning: requests library not found. Using simulated data.")
    requests = None


def fetch_stock_data(stock_code):
    """
    Fetch stock data from market data source.
    Falls back to simulated data if API is unavailable.
    """
    simulated_data = {
        "hk03986": {
            "name": "兆易创新",
            "price": 492.40,
            "change_percent": 0.49,
            "currency": "HKD"
        },
        "hk01972": {
            "name": "太古地产",
            "price": 24.06,
            "change_percent": 2.39,
            "currency": "HKD"
        },
        "hk00700": {
            "name": "腾讯控股",
            "price": 477.80,
            "change_percent": 4.91,
            "currency": "HKD"
        }
    }
    
    if requests is None:
        return simulated_data.get(stock_code, None)
    
    try:
        # Try to fetch from API (placeholder URL)
        url = f"https://api.example.com/stock/{stock_code}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"API fetch failed: {e}, using simulated data")
    
    return simulated_data.get(stock_code, None)


def generate_market_report(stocks):
    """Generate a market analysis report."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    report = f"""# Market Report - {datetime.utcnow().strftime('%Y-%m-%d')}

Generated: {timestamp}

## Hong Kong Stock Market Overview

"""
    
    total_change = 0
    count = 0
    
    for stock_code, data in stocks.items():
        if data:
            report += f"### {data['name']} ({stock_code.upper()})\n"
            report += f"- **Price**: {data['price']} {data['currency']}\n"
            report += f"- **Change**: {data['change_percent']:+.2f}%\n"
            report += f"- **Status**: {'📈 Up' if data['change_percent'] > 0 else '📉 Down'}\n\n"
            
            total_change += data['change_percent']
            count += 1
    
    if count > 0:
        avg_change = total_change / count
        sentiment = "🚀 Bullish" if avg_change > 0 else "📉 Bearish"
        
        report += f"## Market Summary\n"
        report += f"- **Average Change**: {avg_change:+.2f}%\n"
        report += f"- **Market Sentiment**: {sentiment}\n"
        report += f"- **Stocks Tracked**: {count}\n"
    
    return report


def main():
    """Main function to fetch market data and generate report."""
    stocks = {
        "hk03986": None,
        "hk01972": None,
        "hk00700": None,
    }
    
    print(f"Fetching market data at {datetime.utcnow().isoformat()}Z...")
    
    for code in stocks:
        data = fetch_stock_data(code)
        stocks[code] = data
        if data:
            print(f"✓ {data['name']} ({code}): {data['price']} {data['currency']} ({data['change_percent']:+.2f}%)")
    
    # Generate report
    report = generate_market_report(stocks)
    
    # Save report with timestamp
    report_filename = f"MARKET_REPORT_{datetime.utcnow().strftime('%Y-%m-%d')}.md"
    report_path = Path("/workspace") / report_filename
    
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n✓ Report saved: {report_filename}")
    print("\n" + "="*50)
    print(report)
    print("="*50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
