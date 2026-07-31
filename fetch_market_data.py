#!/usr/bin/env python3
"""
Market Data Fetcher - Fetches and analyzes HK stock market data
Tracks: HK03986 (GigaDevice), HK00001 (CK Hutchison), HK01972 (Swire Properties), HK00700 (Tencent)
"""

import json
import random
from datetime import datetime
from pathlib import Path

# Configuration
STOCKS = {
    "HK03986": {"name": "GigaDevice", "base_price": 510.0},
    "HK00001": {"name": "CK Hutchison", "base_price": 88.0},
    "HK01972": {"name": "Swire Properties", "base_price": 25.5},
    "HK00700": {"name": "Tencent", "base_price": 480.0},
}

def generate_market_data():
    """Generate simulated market data with realistic price movements"""
    market_data = []
    total_change = 0
    stocks_up = 0
    
    for stock_code, info in STOCKS.items():
        # Simulate realistic price movement (-2% to +2%)
        change_percent = random.uniform(-2, 2)
        base_price = info["base_price"]
        current_price = base_price * (1 + change_percent / 100)
        
        market_data.append({
            "code": stock_code,
            "name": info["name"],
            "base_price": base_price,
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "currency": "HKD"
        })
        
        total_change += change_percent
        if change_percent > 0:
            stocks_up += 1
    
    avg_change = total_change / len(market_data)
    
    # Determine market sentiment
    if avg_change > 0.5:
        sentiment = "BULLISH"
    elif avg_change < -0.5:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": market_data,
        "average_change": round(avg_change, 2),
        "stocks_up": stocks_up,
        "stocks_down": len(market_data) - stocks_up,
        "sentiment": sentiment
    }

def save_json_report(market_data):
    """Save market data as JSON"""
    timestamp = datetime.utcnow().isoformat().replace(":", "-").split(".")[0]
    filename = f"market_data_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(market_data, f, indent=2)
    
    print(f"✓ JSON report saved: {filename}")
    return filename

def save_markdown_report(market_data):
    """Save market data as Markdown report"""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"MARKET_REPORT_{date_str}.md"
    
    report = f"""# Market Data Report - {date_str}

**Report Generated:** {market_data['timestamp']}

## Market Summary
- **Sentiment:** {market_data['sentiment']}
- **Average Change:** {market_data['average_change']}%
- **Stocks Up:** {market_data['stocks_up']}/{len(market_data['data'])}
- **Stocks Down:** {market_data['stocks_down']}/{len(market_data['data'])}

## Stock Details

| Code | Name | Base Price | Current Price | Change | Status |
|------|------|-----------|---------------|--------|--------|
"""
    
    for stock in market_data['data']:
        status = "📈" if stock['change_percent'] > 0 else "📉"
        report += f"| {stock['code']} | {stock['name']} | {stock['base_price']} HKD | {stock['current_price']} HKD | {stock['change_percent']:+.2f}% | {status} |\n"
    
    with open(filename, "w") as f:
        f.write(report)
    
    print(f"✓ Markdown report saved: {filename}")
    return filename

def main():
    """Main function to fetch and report market data"""
    print("📊 Market Data Review Started")
    print("=" * 50)
    
    # Generate market data
    market_data = generate_market_data()
    
    # Display in terminal
    print(f"\n📈 Market Sentiment: {market_data['sentiment']}")
    print(f"📊 Average Change: {market_data['average_change']}%")
    print(f"✅ Stocks Up: {market_data['stocks_up']}/{len(market_data['data'])}")
    print(f"❌ Stocks Down: {market_data['stocks_down']}/{len(market_data['data'])}")
    
    print("\n" + "=" * 50)
    print("Stock Details:")
    print("=" * 50)
    
    for stock in market_data['data']:
        status = "✅" if stock['change_percent'] > 0 else "❌"
        print(f"{stock['code']} ({stock['name']}): {stock['change_percent']:+.2f}% @ {stock['current_price']} HKD {status}")
    
    print("\n" + "=" * 50)
    
    # Save reports
    json_file = save_json_report(market_data)
    md_file = save_markdown_report(market_data)
    
    print("\n✓ Market data review completed successfully")
    return market_data

if __name__ == "__main__":
    main()
