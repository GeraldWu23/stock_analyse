#!/usr/bin/env python3
"""
Market data fetcher using Tencent Finance API.
Fetches Hong Kong stock data and generates market reports.
"""

import requests
import json
from datetime import datetime, timezone
from pathlib import Path

# Hong Kong stocks to monitor
STOCKS_TO_MONITOR = [
    {"code": "hk03986", "name": "兆易创新"},
    {"code": "hk01972", "name": "太古地产"},
    {"code": "hk00700", "name": "腾讯控股"},
]

def fetch_stock_price(stock_code):
    """Fetch current stock price from Tencent Finance API."""
    try:
        url = f"https://qt.gtimg.cn/q={stock_code}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Parse Tencent Finance response format
            data = response.text
            parts = data.split('~')
            if len(parts) >= 4:
                # Extract price and change percentage
                current_price = float(parts[3]) if parts[3] else 0
                change_percent = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                return {
                    "price": current_price,
                    "change_percent": change_percent,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
    except Exception as e:
        print(f"Error fetching {stock_code}: {e}")
    return None

def generate_market_report(market_data):
    """Generate a markdown market report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    report = f"""# Market Data Report
Generated: {timestamp}

## Hong Kong Stocks

"""
    
    for stock in market_data:
        if stock["data"]:
            price = stock["data"]["price"]
            change = stock["data"]["change_percent"]
            direction = "📈 Up" if change > 0 else "📉 Down" if change < 0 else "➡️ Flat"
            report += f"- **{stock['name']} ({stock['code']})**: {price:.2f} HKD - {direction} {abs(change):.2f}%\n"
        else:
            report += f"- **{stock['name']} ({stock['code']})**: Data unavailable\n"
    
    # Calculate market sentiment
    positive_stocks = sum(1 for s in market_data if s["data"] and s["data"]["change_percent"] > 0)
    total_stocks = len(market_data)
    
    report += f"\n## Market Summary\n"
    report += f"- Positive stocks: {positive_stocks}/{total_stocks}\n"
    
    if positive_stocks == total_stocks:
        report += "- Overall sentiment: **Bullish 🚀** - All tracked stocks showing gains\n"
    elif positive_stocks > total_stocks / 2:
        report += "- Overall sentiment: **Positive ✅** - Majority of stocks gaining\n"
    elif positive_stocks > 0:
        report += "- Overall sentiment: **Mixed ⚖️** - Some stocks gaining, others declining\n"
    else:
        report += "- Overall sentiment: **Bearish 📉** - All stocks in decline\n"
    
    return report

def main():
    """Main execution function."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching market data...")
    
    # Fetch data for all stocks
    market_data = []
    for stock in STOCKS_TO_MONITOR:
        data = fetch_stock_price(stock["code"])
        market_data.append({
            "code": stock["code"],
            "name": stock["name"],
            "data": data
        })
        if data:
            print(f"✅ {stock['name']}: {data['price']:.2f} HKD ({data['change_percent']:+.2f}%)")
        else:
            print(f"❌ {stock['name']}: Failed to fetch data")
    
    # Generate report
    report = generate_market_report(market_data)
    
    # Save report with timestamp
    report_filename = f"MARKET_REPORT_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    report_path = Path("/workspace") / report_filename
    
    report_path.write_text(report)
    print(f"\n📊 Report saved: {report_filename}")
    
    # Print report
    print("\n" + "="*50)
    print(report)
    print("="*50)

if __name__ == "__main__":
    main()
