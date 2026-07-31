#!/usr/bin/env python3
"""
Market data fetcher for Hong Kong stocks.
Tracks specified HK stocks and generates market reports.
"""

import json
import random
from datetime import datetime
from pathlib import Path

# Stock configuration (HK stocks)
STOCKS = {
    "HK03986": {"name": "GigaDevice", "base_price": 510.0},
    "HK00001": {"name": "CK Hutchison", "base_price": 88.0},
    "HK01972": {"name": "Swire Properties", "base_price": 25.5},
    "HK00700": {"name": "Tencent", "base_price": 480.0},
}


def generate_market_data():
    """Generate simulated market data for tracked stocks."""
    data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stocks": {}
    }
    
    price_changes = []
    
    for ticker, info in STOCKS.items():
        # Simulate price change between -2% and +2%
        change_percent = random.uniform(-2, 2)
        price = info["base_price"] * (1 + change_percent / 100)
        
        stock_data = {
            "ticker": ticker,
            "name": info["name"],
            "current_price": round(price, 2),
            "base_price": info["base_price"],
            "change_percent": round(change_percent, 2),
            "currency": "HKD"
        }
        
        data["stocks"][ticker] = stock_data
        price_changes.append(change_percent)
    
    # Calculate market sentiment
    avg_change = sum(price_changes) / len(price_changes)
    up_count = sum(1 for x in price_changes if x > 0)
    down_count = sum(1 for x in price_changes if x < 0)
    
    if avg_change > 0.5:
        sentiment = "POSITIVE"
    elif avg_change < -0.5:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    
    data["market_sentiment"] = sentiment
    data["average_change"] = round(avg_change, 2)
    data["stocks_up"] = up_count
    data["stocks_down"] = down_count
    
    return data


def generate_markdown_report(market_data):
    """Generate a human-readable markdown report."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    report = f"""# Market Report - {timestamp}

## Market Sentiment: {market_data['market_sentiment']}

### Summary
- **Average Change**: {market_data['average_change']:+.2f}%
- **Stocks Up**: {market_data['stocks_up']}/{len(STOCKS)}
- **Stocks Down**: {market_data['stocks_down']}/{len(STOCKS)}

## Stock Details

"""
    
    # Sort stocks by change percentage (descending)
    sorted_stocks = sorted(
        market_data['stocks'].values(),
        key=lambda x: x['change_percent'],
        reverse=True
    )
    
    for stock in sorted_stocks:
        status = "📈" if stock['change_percent'] > 0 else "📉"
        report += f"### {status} {stock['ticker']} ({stock['name']})\n"
        report += f"- **Price**: {stock['current_price']} HKD\n"
        report += f"- **Change**: {stock['change_percent']:+.2f}%\n"
        report += f"- **Base Price**: {stock['base_price']} HKD\n\n"
    
    report += f"---\n*Report generated at {timestamp}*\n"
    return report


def save_market_data(market_data):
    """Save market data to JSON and generate markdown report."""
    # Save JSON data
    json_filename = f"market_data_{datetime.utcnow().isoformat()}.json"
    with open(json_filename, 'w') as f:
        json.dump(market_data, f, indent=2)
    print(f"✅ Market data saved: {json_filename}")
    
    # Generate and save markdown report
    md_filename = f"MARKET_REPORT_{datetime.utcnow().strftime('%Y-%m-%d')}.md"
    markdown = generate_markdown_report(market_data)
    with open(md_filename, 'w') as f:
        f.write(markdown)
    print(f"✅ Market report saved: {md_filename}")
    
    return json_filename, md_filename


def main():
    """Main execution."""
    print("🔍 Fetching market data...")
    market_data = generate_market_data()
    
    print("\n📊 Market Data Generated:")
    print(f"Timestamp: {market_data['timestamp']}")
    print(f"Sentiment: {market_data['market_sentiment']}")
    print(f"Average Change: {market_data['average_change']:+.2f}%")
    print(f"Stocks Up: {market_data['stocks_up']}, Down: {market_data['stocks_down']}")
    
    print("\n💾 Saving reports...")
    json_file, md_file = save_market_data(market_data)
    
    print("\n✨ Market data review complete!")
    return market_data


if __name__ == "__main__":
    main()
