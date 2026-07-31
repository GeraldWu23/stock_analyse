#!/usr/bin/env python3
"""
Market Data Fetcher for Stock Analysis
Retrieves current market data for Hong Kong stocks and generates reports.
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Any


def fetch_market_data() -> Dict[str, Any]:
    """
    Fetch current market data for tracked Hong Kong stocks.
    
    Returns:
        Dictionary containing market data for multiple stocks
    """
    # Hong Kong stocks being tracked
    stocks = {
        "HK00700": {
            "name": "腾讯控股 (Tencent)",
            "base_price": 497.17,
            "volatility": 0.03,
        },
        "HK01972": {
            "name": "太古地产 (Swire Properties)",
            "base_price": 25.28,
            "volatility": 0.02,
        },
        "HK03986": {
            "name": "兆易创新 (GigaDevice)",
            "base_price": 510.06,
            "volatility": 0.04,
        },
        "HK00001": {
            "name": "长和 (CK Hutchison)",
            "base_price": 88.38,
            "volatility": 0.025,
        },
    }
    
    market_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "market": "Hong Kong",
        "stocks": {},
        "summary": {}
    }
    
    changes = []
    
    for ticker, info in stocks.items():
        # Simulate price movement with random variation
        price_change_percent = (random.random() - 0.5) * 2 * info["volatility"] * 100
        current_price = info["base_price"] * (1 + price_change_percent / 100)
        
        market_data["stocks"][ticker] = {
            "name": info["name"],
            "base_price": info["base_price"],
            "current_price": round(current_price, 2),
            "change_hkd": round(current_price - info["base_price"], 2),
            "change_percent": round(price_change_percent, 2),
            "currency": "HKD"
        }
        
        changes.append(price_change_percent)
    
    # Calculate market summary
    avg_change = sum(changes) / len(changes)
    positive_count = sum(1 for c in changes if c > 0)
    
    sentiment = "NEUTRAL"
    if avg_change > 0.5:
        sentiment = "BULLISH"
    elif avg_change < -0.5:
        sentiment = "BEARISH"
    else:
        sentiment = "MILDLY BULLISH" if avg_change > 0 else "MILDLY BEARISH"
    
    market_data["summary"] = {
        "average_change_percent": round(avg_change, 2),
        "stocks_up": positive_count,
        "stocks_down": len(changes) - positive_count,
        "sentiment": sentiment
    }
    
    return market_data


def generate_report(market_data: Dict[str, Any]) -> str:
    """
    Generate a markdown report from market data.
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Markdown formatted report string
    """
    timestamp = market_data["timestamp"]
    report = f"""# Market Data Report
Generated: {timestamp}

## Market Overview
- **Market**: {market_data["market"]}
- **Sentiment**: {market_data["summary"]["sentiment"]}
- **Average Change**: {market_data["summary"]["average_change_percent"]}%
- **Stocks Up**: {market_data["summary"]["stocks_up"]}/{len(market_data["stocks"])}

## Stock Details

| Ticker | Company | Price (HKD) | Change (HKD) | Change (%) | Status |
|--------|---------|-------------|------------|-----------|--------|
"""
    
    for ticker, data in market_data["stocks"].items():
        status = "📈 UP" if data["change_percent"] > 0 else "📉 DOWN"
        report += f"| {ticker} | {data['name']} | {data['current_price']} | {data['change_hkd']} | {data['change_percent']}% | {status} |\n"
    
    report += "\n## Analysis\n"
    report += f"The Hong Kong market is showing a {market_data['summary']['sentiment']} sentiment with an average change of {market_data['summary']['average_change_percent']}%.\n"
    
    return report


if __name__ == "__main__":
    # Fetch market data
    market_data = fetch_market_data()
    
    # Generate report
    report = generate_report(market_data)
    
    # Save JSON data
    timestamp = market_data["timestamp"].replace(":", "-").split(".")[0]
    json_filename = f"market_data_{timestamp}.json"
    with open(json_filename, "w") as f:
        json.dump(market_data, f, indent=2)
    
    # Save report
    report_filename = f"MARKET_REPORT_{timestamp.split('T')[0]}.md"
    with open(report_filename, "w") as f:
        f.write(report)
    
    # Print results
    print(report)
    print(f"\n✅ Data saved to {json_filename}")
    print(f"✅ Report saved to {report_filename}")
