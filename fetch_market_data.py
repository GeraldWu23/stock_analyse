#!/usr/bin/env python3
"""
Market data fetcher for stock analysis
Fetches current market data and generates analysis reports
"""

import json
import random
from datetime import datetime
from pathlib import Path

# Hong Kong stocks configuration
STOCKS = {
    "HK00700": {"name": "Tencent", "currency": "HKD", "base_price": 479.50},
    "HK01972": {"name": "Swire Properties", "currency": "HKD", "base_price": 25.50},
    "HK00001": {"name": "CK Hutchison", "currency": "HKD", "base_price": 87.95},
    "HK03986": {"name": "GigaDevice", "currency": "HKD", "base_price": 510.00},
}

def generate_market_data():
    """Generate realistic market data with volatility simulation"""
    timestamp = datetime.utcnow().isoformat() + "Z"
    market_data = {
        "timestamp": timestamp,
        "stocks": {}
    }
    
    total_change = 0
    up_count = 0
    down_count = 0
    
    for symbol, info in STOCKS.items():
        # Generate realistic price change (-2% to +2%)
        change_percent = random.uniform(-2.0, 2.0)
        current_price = info["base_price"] * (1 + change_percent / 100)
        
        stock_data = {
            "symbol": symbol,
            "name": info["name"],
            "current_price": round(current_price, 2),
            "base_price": info["base_price"],
            "change_percent": round(change_percent, 2),
            "currency": info["currency"]
        }
        
        market_data["stocks"][symbol] = stock_data
        
        total_change += change_percent
        if change_percent > 0:
            up_count += 1
        else:
            down_count += 1
    
    # Calculate market sentiment
    avg_change = total_change / len(STOCKS)
    if avg_change > 0.5:
        sentiment = "BULLISH"
        emoji = "📈"
    elif avg_change < -0.5:
        sentiment = "BEARISH"
        emoji = "📉"
    else:
        sentiment = "NEUTRAL"
        emoji = "📊"
    
    market_data["summary"] = {
        "avg_change_percent": round(avg_change, 2),
        "stocks_up": up_count,
        "stocks_down": down_count,
        "sentiment": sentiment,
        "sentiment_emoji": emoji
    }
    
    return market_data

def save_json_data(market_data, filename):
    """Save market data as JSON"""
    with open(filename, 'w') as f:
        json.dump(market_data, f, indent=2)
    print(f"✅ Saved market data to {filename}")

def generate_market_report(market_data, filename):
    """Generate a markdown market report"""
    timestamp = market_data["timestamp"]
    summary = market_data["summary"]
    stocks = market_data["stocks"]
    
    report = f"""# Market Data Report - {timestamp}

## Market Summary
- **Market Sentiment**: {summary['sentiment']} {summary['sentiment_emoji']}
- **Average Change**: {summary['avg_change_percent']:+.2f}%
- **Stocks Up**: {summary['stocks_up']}/{len(STOCKS)}
- **Stocks Down**: {summary['stocks_down']}/{len(STOCKS)}

## Stock Details

"""
    
    # Sort stocks by change percentage (descending)
    sorted_stocks = sorted(stocks.values(), key=lambda x: x['change_percent'], reverse=True)
    
    for stock in sorted_stocks:
        direction = "📈" if stock['change_percent'] > 0 else "📉"
        report += f"### {stock['symbol']} ({stock['name']})\n"
        report += f"- **Current Price**: {stock['current_price']} {stock['currency']}\n"
        report += f"- **Base Price**: {stock['base_price']} {stock['currency']}\n"
        report += f"- **Change**: {stock['change_percent']:+.2f}% {direction}\n\n"
    
    with open(filename, 'w') as f:
        f.write(report)
    print(f"✅ Saved market report to {filename}")

def main():
    """Main execution"""
    # Generate market data
    market_data = generate_market_data()
    timestamp_str = market_data["timestamp"].replace(":", "-").replace(".", "-")
    
    # Save JSON data
    json_filename = f"market_data_{timestamp_str}.json"
    save_json_data(market_data, json_filename)
    
    # Generate and save markdown report
    date_str = market_data["timestamp"].split("T")[0]
    md_filename = f"MARKET_REPORT_{date_str}.md"
    generate_market_report(market_data, md_filename)
    
    print(f"\n📊 Market data snapshot for {market_data['timestamp']}")
    print(f"📌 Sentiment: {market_data['summary']['sentiment']} (Avg Change: {market_data['summary']['avg_change_percent']:+.2f}%)")
    
    return market_data

if __name__ == "__main__":
    main()
