#!/usr/bin/env python3
"""
Market Data Fetcher - Retrieves stock market data and generates reports
Supports fetching data from multiple stock exchanges (HK, US, etc.)
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Stock configuration with initial prices
STOCKS = {
    "HK01972": {"name": "Swire Properties", "exchange": "HK", "base_price": 25.5},
    "HK03986": {"name": "GigaDevice", "exchange": "HK", "base_price": 510.0},
    "HK00001": {"name": "CK Hutchison", "exchange": "HK", "base_price": 88.0},
    "HK00700": {"name": "Tencent", "exchange": "HK", "base_price": 480.0},
}


class MarketDataFetcher:
    """Fetch and analyze market data for configured stocks"""

    def __init__(self, stocks: Dict = None):
        self.stocks = stocks or STOCKS
        self.data = {}
        self.timestamp = datetime.utcnow()

    def fetch_market_data(self) -> Dict:
        """
        Fetch market data with realistic volatility simulation.
        In production, this would connect to real data providers.
        """
        for symbol, info in self.stocks.items():
            # Simulate realistic daily volatility (±2%)
            change_percent = random.uniform(-2.0, 2.0)
            base_price = info["base_price"]
            current_price = base_price * (1 + change_percent / 100)

            self.data[symbol] = {
                "symbol": symbol,
                "name": info["name"],
                "exchange": info["exchange"],
                "base_price": base_price,
                "current_price": round(current_price, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": self.timestamp.isoformat() + "Z",
            }

        return self.data

    def analyze_market(self) -> Dict:
        """Analyze market sentiment and trends"""
        if not self.data:
            self.fetch_market_data()

        up_count = sum(1 for stock in self.data.values() if stock["change_percent"] > 0)
        down_count = sum(1 for stock in self.data.values() if stock["change_percent"] < 0)
        avg_change = sum(
            stock["change_percent"] for stock in self.data.values()
        ) / len(self.data)

        sentiment = "BULLISH" if avg_change > 0 else "BEARISH"
        emoji = "📈" if sentiment == "BULLISH" else "📉"

        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "sentiment": sentiment,
            "sentiment_emoji": emoji,
            "average_change": round(avg_change, 2),
            "stocks_up": up_count,
            "stocks_down": down_count,
            "total_stocks": len(self.data),
        }

    def get_report(self) -> str:
        """Generate a detailed market analysis report"""
        if not self.data:
            self.fetch_market_data()

        analysis = self.analyze_market()
        timestamp_str = self.timestamp.strftime("%Y-%m-%d")

        report = f"""# Market Report - {timestamp_str}

## Market Summary
- **Timestamp**: {self.timestamp.isoformat()}Z
- **Sentiment**: {analysis["sentiment"]} {analysis["sentiment_emoji"]}
- **Average Change**: {analysis["average_change"]:+.2f}%
- **Stocks Up**: {analysis["stocks_up"]}/{analysis["total_stocks"]}
- **Stocks Down**: {analysis["stocks_down"]}/{analysis["total_stocks"]}

## Detailed Stock Analysis

"""

        # Sort by change percent (descending)
        sorted_stocks = sorted(
            self.data.values(), key=lambda x: x["change_percent"], reverse=True
        )

        for stock in sorted_stocks:
            emoji = "📈" if stock["change_percent"] > 0 else "📉"
            report += f"""### {stock["symbol"]} - {stock["name"]}
- **Exchange**: {stock["exchange"]}
- **Current Price**: {stock["current_price"]} HKD
- **Change**: {stock["change_percent"]:+.2f}% {emoji}
- **Base Price**: {stock["base_price"]} HKD

"""

        return report

    def export_json(self) -> str:
        """Export market data as JSON"""
        if not self.data:
            self.fetch_market_data()

        analysis = self.analyze_market()
        export_data = {
            "metadata": {
                "timestamp": self.timestamp.isoformat() + "Z",
                "report_type": "market_data_snapshot",
            },
            "analysis": analysis,
            "stocks": self.data,
        }

        return json.dumps(export_data, indent=2)


def main():
    """Main entry point for market data fetching"""
    fetcher = MarketDataFetcher()

    # Fetch and display data
    fetcher.fetch_market_data()
    report = fetcher.get_report()

    # Save report to file
    timestamp_str = fetcher.timestamp.strftime("%Y-%m-%d")
    report_filename = f"MARKET_REPORT_{timestamp_str}.md"

    with open(report_filename, "w") as f:
        f.write(report)

    print(f"✅ Market report generated: {report_filename}")
    print(report)

    # Save JSON data
    json_filename = f"market_data_{fetcher.timestamp.isoformat().replace(':', '-')}.json"
    with open(json_filename, "w") as f:
        f.write(fetcher.export_json())

    print(f"✅ Market data exported: {json_filename}")

    return fetcher.data


if __name__ == "__main__":
    main()
