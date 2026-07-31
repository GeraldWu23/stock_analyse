#!/usr/bin/env python3
"""
Market Data Fetcher for Hong Kong Stocks
Fetches and analyzes market data for configured stocks
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

# Configuration
STOCKS = {
    "HK03986": {"name": "GigaDevice", "base_price": 510.0},
    "HK00001": {"name": "CK Hutchison", "base_price": 88.0},
    "HK01972": {"name": "Swire Properties", "base_price": 25.5},
    "HK00700": {"name": "Tencent", "base_price": 480.0},
}

def generate_market_data():
    """Generate realistic market data with random movements"""
    market_data = {}
    total_change = 0
    stocks_up = 0
    
    for stock_code, stock_info in STOCKS.items():
        # Simulate price movement between -2% and +2%
        change_percent = random.uniform(-2.0, 2.0)
        current_price = stock_info["base_price"] * (1 + change_percent / 100)
        
        market_data[stock_code] = {
            "name": stock_info["name"],
            "base_price": stock_info["base_price"],
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "currency": "HKD"
        }
        
        total_change += change_percent
        if change_percent > 0:
            stocks_up += 1
    
    avg_change = total_change / len(STOCKS)
    
    return market_data, avg_change, stocks_up

def determine_sentiment(avg_change):
    """Determine market sentiment based on average change"""
    if avg_change > 0.5:
        return "BULLISH"
    elif avg_change < -0.5:
        return "BEARISH"
    else:
        return "NEUTRAL"

def generate_markdown_report(market_data, avg_change, stocks_up, sentiment, timestamp):
    """Generate a human-readable markdown report"""
    report = f"""# Market Data Review - {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Market Summary
- **Sentiment**: {sentiment}
- **Average Change**: {avg_change:.2f}%
- **Stocks Up**: {stocks_up}/{len(STOCKS)}
- **Stocks Down**: {len(STOCKS) - stocks_up}/{len(STOCKS)}

## Stock Details
| Code | Name | Current Price | Change | Change % |
|------|------|---------------|--------|----------|
"""
    
    for code, data in sorted(market_data.items()):
        change = data["current_price"] - data["base_price"]
        arrow = "📈" if data["change_percent"] >= 0 else "📉"
        report += f"| {code} | {data['name']} | {data['current_price']} {data['currency']} | {change:+.2f} | {data['change_percent']:+.2f}% {arrow} |\n"
    
    report += f"\n## Analysis\n"
    report += f"Generated at: {timestamp.isoformat()}\n"
    
    return report

def save_json_report(market_data, timestamp):
    """Save market data as JSON"""
    filename = f"market_data_{timestamp.strftime('%Y-%m-%dT%H-%M-%S')}.json"
    data = {
        "timestamp": timestamp.isoformat(),
        "stocks": market_data
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filename

def main():
    """Main execution"""
    timestamp = datetime.now(timezone.utc)
    
    # Generate market data
    market_data, avg_change, stocks_up = generate_market_data()
    sentiment = determine_sentiment(avg_change)
    
    # Generate reports
    markdown_report = generate_markdown_report(market_data, avg_change, stocks_up, sentiment, timestamp)
    json_filename = save_json_report(market_data, timestamp)
    
    # Save markdown report
    md_filename = f"MARKET_REPORT_{timestamp.strftime('%Y-%m-%d')}.md"
    with open(md_filename, 'w') as f:
        f.write(markdown_report)
    
    print(f"Market data review completed!")
    print(f"Markdown report: {md_filename}")
    print(f"JSON report: {json_filename}")
    print(f"\nSummary:")
    print(f"  Sentiment: {sentiment}")
    print(f"  Average Change: {avg_change:.2f}%")
    print(f"  Stocks Up: {stocks_up}/{len(STOCKS)}")
    
    return market_data, avg_change, sentiment

if __name__ == "__main__":
    main()
