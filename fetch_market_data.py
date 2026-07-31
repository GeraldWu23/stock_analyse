#!/usr/bin/env python3
"""
Market Data Fetcher - Automated market data collection and reporting system
Tracks Hong Kong stocks and generates market analysis reports
"""

import json
import random
import sys
from datetime import datetime
from pathlib import Path

# Configuration: Hong Kong stocks to track
STOCKS_CONFIG = {
    "HK03986": {"name": "GigaDevice", "base_price": 510.0},
    "HK00001": {"name": "CK Hutchison", "base_price": 88.0},
    "HK01972": {"name": "Swire Properties", "base_price": 25.5},
    "HK00700": {"name": "Tencent", "base_price": 480.0},
}


def generate_market_data():
    """Generate realistic market data with random fluctuations"""
    market_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stocks": {},
    }

    for stock_id, config in STOCKS_CONFIG.items():
        # Simulate realistic price movements (-2% to +2%)
        change_percent = random.uniform(-2.0, 2.0)
        current_price = config["base_price"] * (1 + change_percent / 100)

        market_data["stocks"][stock_id] = {
            "id": stock_id,
            "name": config["name"],
            "base_price": config["base_price"],
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "currency": "HKD",
        }

    return market_data


def calculate_sentiment(market_data):
    """Calculate overall market sentiment based on stock movements"""
    stocks = market_data["stocks"].values()
    changes = [s["change_percent"] for s in stocks]
    avg_change = sum(changes) / len(changes)
    up_count = sum(1 for c in changes if c > 0)

    if avg_change > 0.5:
        sentiment = "BULLISH"
    elif avg_change < -0.5:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    return {
        "sentiment": sentiment,
        "average_change": round(avg_change, 2),
        "stocks_up": up_count,
        "stocks_total": len(changes),
    }


def generate_markdown_report(market_data, sentiment):
    """Generate human-readable markdown report"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    report = f"""# Market Data Review - {date_str}

Generated: {timestamp}

## Market Sentiment: {sentiment["sentiment"]}

- **Average Change**: {sentiment["average_change"]}%
- **Stocks Up**: {sentiment["stocks_up"]}/{sentiment["stocks_total"]}

## Stock Details

"""

    for stock_id, stock_data in market_data["stocks"].items():
        change = stock_data["change_percent"]
        direction = "📈" if change > 0 else "📉" if change < 0 else "→"
        report += f"- **{stock_id}** ({stock_data['name']}): {change:+.2f}% @ {stock_data['current_price']} {stock_data['currency']} {direction}\n"

    return report


def main():
    """Main execution function"""
    try:
        # Generate market data
        market_data = generate_market_data()
        sentiment = calculate_sentiment(market_data)

        # Generate reports
        markdown_report = generate_markdown_report(market_data, sentiment)

        # Save JSON data
        timestamp_str = datetime.utcnow().isoformat()
        json_filename = f"market_data_{timestamp_str.replace(':', '-')}.json"
        json_path = Path(json_filename)

        with open(json_path, "w") as f:
            json.dump(market_data, f, indent=2)

        # Save markdown report
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        md_filename = f"MARKET_REPORT_{date_str}.md"
        md_path = Path(md_filename)

        with open(md_path, "w") as f:
            f.write(markdown_report)

        # Print results
        print(f"✅ Market data generated successfully")
        print(f"📊 Sentiment: {sentiment['sentiment']}")
        print(f"📈 Average Change: {sentiment['average_change']}%")
        print(f"💾 JSON saved: {json_filename}")
        print(f"📄 Report saved: {md_filename}")
        print("\n" + markdown_report)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
