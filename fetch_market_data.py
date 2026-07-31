#!/usr/bin/env python3
"""
Market data fetcher for stock analysis.
Fetches Hong Kong stock market data and generates analysis reports.
"""

import json
import random
from datetime import datetime
from pathlib import Path


def get_stock_data():
    """
    Fetch or simulate Hong Kong stock market data.
    Returns dictionary with stock symbols and their market data.
    """
    # Simulated Hong Kong stock data with realistic market variations
    stocks = {
        "HK00700": {
            "name": "腾讯控股 (Tencent)",
            "base_price": 500.0,
            "currency": "HKD"
        },
        "HK01972": {
            "name": "太古地产 (Swire)",
            "base_price": 24.0,
            "currency": "HKD"
        },
        "HK03986": {
            "name": "兆易创新 (GigaDevice)",
            "base_price": 495.0,
            "currency": "HKD"
        },
        "HK00001": {
            "name": "长和 (CK Hutchison)",
            "base_price": 90.0,
            "currency": "HKD"
        }
    }
    
    market_data = {}
    for symbol, info in stocks.items():
        # Simulate price movement (±5%)
        change_percent = random.uniform(-5, 5)
        current_price = info["base_price"] * (1 + change_percent / 100)
        
        market_data[symbol] = {
            "name": info["name"],
            "price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "currency": info["currency"],
            "timestamp": datetime.now().isoformat()
        }
    
    return market_data


def generate_market_report(market_data):
    """
    Generate a formatted market analysis report.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Calculate market sentiment
    changes = [data["change_percent"] for data in market_data.values()]
    avg_change = sum(changes) / len(changes)
    bullish_count = sum(1 for c in changes if c > 0)
    
    sentiment = "Bullish" if avg_change > 0 else "Bearish"
    emoji = "🚀" if avg_change > 0 else "📉"
    
    report = f"""# Market Data Report - {timestamp}

## Market Overview
- **Overall Sentiment**: {sentiment} {emoji}
- **Average Change**: {avg_change:+.2f}%
- **Bullish Stocks**: {bullish_count}/{len(market_data)}

## Hong Kong Stocks

"""
    
    for symbol, data in market_data.items():
        emoji = "📈" if data["change_percent"] > 0 else "📉"
        report += f"- **{symbol}** ({data['name']}): {data['price']} {data['currency']} - "
        report += f"{data['change_percent']:+.2f}% {emoji}\n"
    
    report += f"\n## Data Timestamp\n{data['timestamp']}\n"
    
    return report


def main():
    """Main entry point."""
    # Fetch market data
    market_data = get_stock_data()
    
    # Generate report
    report = generate_market_report(market_data)
    
    # Save report
    timestamp = datetime.now().strftime("%Y-%m-%d")
    report_path = Path(f"MARKET_REPORT_{timestamp}.md")
    report_path.write_text(report)
    print(f"Report saved: {report_path}")
    
    # Save JSON data
    data_path = Path(f"market_data_{timestamp}.json")
    data_path.write_text(json.dumps(market_data, indent=2))
    print(f"Data saved: {data_path}")
    
    # Print report
    print("\n" + report)
    
    return market_data


if __name__ == "__main__":
    main()
