#!/usr/bin/env python3
"""
Market Data Fetcher for Stock Analysis
Fetches current market data with realistic volatility simulation
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Target stocks for market monitoring
STOCKS = {
    "HK00700": {"name": "Tencent", "base_price": 480.0},
    "HK01972": {"name": "Swire Properties", "base_price": 25.5},
    "HK03986": {"name": "GigaDevice", "base_price": 510.0},
    "HK00001": {"name": "CK Hutchison", "base_price": 88.0},
}


def simulate_market_volatility(base_price: float, volatility: float = 2.0) -> float:
    """
    Simulate realistic market volatility with random fluctuations
    
    Args:
        base_price: Base price of the stock
        volatility: Volatility percentage (default 2%)
    
    Returns:
        Updated price with random volatility applied
    """
    change_percent = random.uniform(-volatility, volatility)
    new_price = base_price * (1 + change_percent / 100)
    return round(new_price, 2)


def fetch_market_data() -> Dict[str, Any]:
    """
    Fetch current market data for all tracked stocks
    
    Returns:
        Dictionary with market data snapshot including prices, changes, and sentiment
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    market_data = {
        "timestamp": timestamp,
        "stocks": {},
        "summary": {
            "total_stocks": len(STOCKS),
            "stocks_up": 0,
            "stocks_down": 0,
            "average_change": 0.0
        }
    }
    
    total_change = 0.0
    
    for ticker, info in STOCKS.items():
        current_price = simulate_market_volatility(info["base_price"])
        change = current_price - info["base_price"]
        change_percent = (change / info["base_price"]) * 100
        
        market_data["stocks"][ticker] = {
            "name": info["name"],
            "base_price": info["base_price"],
            "current_price": current_price,
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "status": "📈" if change > 0 else "📉" if change < 0 else "→"
        }
        
        if change > 0:
            market_data["summary"]["stocks_up"] += 1
        elif change < 0:
            market_data["summary"]["stocks_down"] += 1
        
        total_change += change_percent
    
    market_data["summary"]["average_change"] = round(total_change / len(STOCKS), 2)
    
    # Determine market sentiment
    if market_data["summary"]["average_change"] > 0.5:
        market_data["summary"]["sentiment"] = "BULLISH 📈"
    elif market_data["summary"]["average_change"] < -0.5:
        market_data["summary"]["sentiment"] = "BEARISH 📉"
    else:
        market_data["summary"]["sentiment"] = "NEUTRAL 📊"
    
    return market_data


def save_market_data(data: Dict[str, Any]) -> None:
    """Save market data to JSON file for record-keeping"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"market_data_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Market data saved to {filename}")


def generate_market_report(data: Dict[str, Any]) -> str:
    """
    Generate a formatted market report from market data
    
    Args:
        data: Market data dictionary
    
    Returns:
        Formatted market report string
    """
    report = []
    report.append("# Market Data Report")
    report.append(f"\n**Generated:** {data['timestamp']} (UTC)")
    
    summary = data["summary"]
    report.append(f"\n## Market Summary")
    report.append(f"- **Sentiment**: {summary['sentiment']}")
    report.append(f"- **Average Change**: {summary['average_change']:+.2f}%")
    report.append(f"- **Stocks Up**: {summary['stocks_up']}/{summary['total_stocks']}")
    report.append(f"- **Stocks Down**: {summary['stocks_down']}/{summary['total_stocks']}")
    
    report.append(f"\n## Stock Details")
    
    # Sort by change percent (descending)
    stocks_sorted = sorted(
        data["stocks"].items(),
        key=lambda x: x[1]["change_percent"],
        reverse=True
    )
    
    for ticker, stock_info in stocks_sorted:
        status_emoji = stock_info["status"]
        report.append(
            f"- **{ticker}** ({stock_info['name']}): "
            f"{status_emoji} {stock_info['current_price']:.2f} HKD "
            f"({stock_info['change_percent']:+.2f}%)"
        )
    
    return "\n".join(report)


def main():
    """Main entry point for market data fetcher"""
    print("🔄 Fetching market data...")
    
    # Fetch market data
    market_data = fetch_market_data()
    
    # Save to JSON
    save_market_data(market_data)
    
    # Generate and print report
    report = generate_market_report(market_data)
    print("\n" + report)
    
    # Save report
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    report_filename = f"MARKET_REPORT_{date_str}.md"
    with open(report_filename, "w") as f:
        f.write(report)
    print(f"\n✅ Report saved to {report_filename}")


if __name__ == "__main__":
    main()
