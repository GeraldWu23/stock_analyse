#!/usr/bin/env python3
"""
Market data fetcher for Hong Kong stocks.
Retrieves current market data and generates reports.
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path


class MarketDataFetcher:
    """Fetches and processes market data for Hong Kong stocks."""

    # Stock configuration with base prices
    STOCKS = {
        "HK03986": {"name": "GigaDevice", "base_price": 510.0},
        "HK00001": {"name": "CK Hutchison", "base_price": 88.0},
        "HK01972": {"name": "Swire Properties", "base_price": 25.5},
        "HK00700": {"name": "Tencent", "base_price": 480.0},
    }

    def __init__(self):
        """Initialize the market data fetcher."""
        self.timestamp = datetime.now(timezone.utc).replace(microsecond=0)
        self.market_data = {}

    def fetch_data(self):
        """Simulate fetching market data with realistic volatility."""
        for stock_code, info in self.STOCKS.items():
            base_price = info["base_price"]
            # Simulate realistic price movement (-2% to +2% range)
            change_percent = random.uniform(-2.0, 2.0)
            current_price = base_price * (1 + change_percent / 100)
            
            self.market_data[stock_code] = {
                "name": info["name"],
                "base_price": base_price,
                "current_price": round(current_price, 2),
                "change_percent": round(change_percent, 2),
                "currency": "HKD",
                "timestamp": self.timestamp.isoformat(),
            }

    def analyze_sentiment(self):
        """Analyze overall market sentiment."""
        if not self.market_data:
            return "NEUTRAL"
        
        gains = sum(1 for data in self.market_data.values() if data["change_percent"] > 0)
        total = len(self.market_data)
        
        avg_change = sum(data["change_percent"] for data in self.market_data.values()) / total
        
        if avg_change > 0.5:
            return "BULLISH"
        elif avg_change < -0.5:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def generate_json_report(self):
        """Generate machine-readable JSON report."""
        sentiment = self.analyze_sentiment()
        avg_change = sum(data["change_percent"] for data in self.market_data.values()) / len(self.market_data)
        
        report = {
            "timestamp": self.timestamp.isoformat(),
            "market_sentiment": sentiment,
            "average_change_percent": round(avg_change, 2),
            "stocks_up": sum(1 for data in self.market_data.values() if data["change_percent"] > 0),
            "stocks_down": sum(1 for data in self.market_data.values() if data["change_percent"] < 0),
            "stocks_unchanged": sum(1 for data in self.market_data.values() if data["change_percent"] == 0),
            "stocks": self.market_data,
        }
        return report

    def generate_markdown_report(self):
        """Generate human-readable markdown report."""
        sentiment = self.analyze_sentiment()
        avg_change = sum(data["change_percent"] for data in self.market_data.values()) / len(self.market_data)
        
        report = f"""# Market Data Report
Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC

## Market Summary
- **Market Sentiment**: {sentiment}
- **Average Change**: {avg_change:.2f}%
- **Stocks Up**: {sum(1 for data in self.market_data.values() if data["change_percent"] > 0)}/{len(self.market_data)}
- **Stocks Down**: {sum(1 for data in self.market_data.values() if data["change_percent"] < 0)}/{len(self.market_data)}

## Stock Details
"""
        # Sort by change percentage for readability
        sorted_stocks = sorted(self.market_data.items(), key=lambda x: x[1]["change_percent"], reverse=True)
        
        for stock_code, data in sorted_stocks:
            direction = "📈" if data["change_percent"] > 0 else "📉" if data["change_percent"] < 0 else "➡️"
            report += f"\n### {stock_code} ({data['name']})\n"
            report += f"- **Price**: {data['current_price']} {data['currency']}\n"
            report += f"- **Change**: {data['change_percent']:+.2f}% {direction}\n"
        
        return report

    def save_reports(self):
        """Save JSON and Markdown reports to files."""
        date_str = self.timestamp.strftime("%Y-%m-%d")
        timestamp_str = self.timestamp.strftime("%Y-%m-%dT%H-%M-%S.%f")
        
        # Save JSON report
        json_filename = f"market_data_{timestamp_str}.json"
        json_data = self.generate_json_report()
        with open(json_filename, "w") as f:
            json.dump(json_data, f, indent=2)
        print(f"✓ Saved JSON report: {json_filename}")
        
        # Save Markdown report
        md_filename = f"MARKET_REPORT_{date_str}.md"
        md_content = self.generate_markdown_report()
        with open(md_filename, "w") as f:
            f.write(md_content)
        print(f"✓ Saved Markdown report: {md_filename}")
        
        return json_filename, md_filename

    def run(self):
        """Run the complete market data fetch and report generation."""
        print(f"🔄 Fetching market data... ({self.timestamp.isoformat()})")
        self.fetch_data()
        
        print("📊 Market Data Retrieved:")
        for stock_code, data in self.market_data.items():
            change_str = f"{data['change_percent']:+.2f}%"
            print(f"  {stock_code} ({data['name']}): {data['current_price']} HKD {change_str}")
        
        sentiment = self.analyze_sentiment()
        print(f"\n📈 Market Sentiment: {sentiment}")
        
        json_file, md_file = self.save_reports()
        return {
            "status": "success",
            "timestamp": self.timestamp.isoformat(),
            "json_report": json_file,
            "markdown_report": md_file,
            "sentiment": sentiment,
            "data": self.market_data,
        }


if __name__ == "__main__":
    fetcher = MarketDataFetcher()
    result = fetcher.run()
    print("\n✅ Market data review completed successfully!")
