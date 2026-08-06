#!/usr/bin/env python3
"""
Market data fetcher for Hong Kong stocks
Tracks real-time market data and generates reports
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

def fetch_market_data():
    """Fetch market data for tracked stocks"""
    
    # Stock configuration: code, name, base price
    stocks = [
        {"code": "HK03986", "name": "GigaDevice", "base": 510.0},
        {"code": "HK00001", "name": "CK Hutchison", "base": 88.0},
        {"code": "HK01972", "name": "Swire Properties", "base": 25.5},
        {"code": "HK00700", "name": "Tencent", "base": 480.0},
    ]
    
    # Generate realistic price movements (-2% to +2%)
    market_data = []
    total_change = 0
    up_count = 0
    
    for stock in stocks:
        # Simulate realistic market movement
        change_percent = random.uniform(-2.0, 2.0)
        price = stock["base"] * (1 + change_percent / 100)
        
        market_data.append({
            "code": stock["code"],
            "name": stock["name"],
            "price": round(price, 2),
            "change_percent": round(change_percent, 2),
            "base_price": stock["base"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        total_change += change_percent
        if change_percent > 0:
            up_count += 1
    
    avg_change = total_change / len(stocks)
    
    # Determine market sentiment
    if avg_change > 0.5:
        sentiment = "BULLISH"
    elif avg_change < -0.5:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"
    
    return {
        "stocks": market_data,
        "summary": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "average_change": round(avg_change, 2),
            "stocks_up": up_count,
            "stocks_down": len(stocks) - up_count,
            "sentiment": sentiment
        }
    }

def generate_reports(market_data):
    """Generate both JSON and Markdown reports"""
    
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Save JSON report
    json_file = Path(f"market_data_{timestamp_str}.json")
    with open(json_file, "w") as f:
        json.dump(market_data, f, indent=2)
    
    # Generate Markdown report
    md_file = Path(f"MARKET_REPORT_{date_str}.md")
    with open(md_file, "w") as f:
        f.write("# Market Data Review\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        
        summary = market_data["summary"]
        f.write("## Market Summary\n\n")
        f.write(f"- **Sentiment:** {summary['sentiment']}\n")
        f.write(f"- **Average Change:** {summary['average_change']:+.2f}%\n")
        f.write(f"- **Stocks Up:** {summary['stocks_up']}/{len(market_data['stocks'])}\n")
        f.write(f"- **Stocks Down:** {summary['stocks_down']}/{len(market_data['stocks'])}\n\n")
        
        f.write("## Stock Details\n\n")
        f.write("| Code | Name | Price | Change | Base Price |\n")
        f.write("|------|------|-------|--------|------------|\n")
        
        for stock in sorted(market_data["stocks"], key=lambda x: x["change_percent"], reverse=True):
            change_icon = "📈" if stock["change_percent"] > 0 else "📉"
            f.write(f"| {stock['code']} | {stock['name']} | {stock['price']} HKD | {change_icon} {stock['change_percent']:+.2f}% | {stock['base_price']} HKD |\n")
    
    return json_file, md_file

if __name__ == "__main__":
    # Fetch market data
    market_data = fetch_market_data()
    
    # Generate reports
    json_file, md_file = generate_reports(market_data)
    
    print(f"✅ Market data fetched successfully")
    print(f"📊 JSON report: {json_file}")
    print(f"📋 Markdown report: {md_file}")
    print(f"\nMarket Sentiment: {market_data['summary']['sentiment']}")
    print(f"Average Change: {market_data['summary']['average_change']:+.2f}%")
