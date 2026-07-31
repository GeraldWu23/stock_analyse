#!/usr/bin/env python3
"""
Market data fetcher for stock analysis.
Fetches current market data for tracked stocks and generates reports.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import requests


class MarketDataFetcher:
    """Fetches and manages market data for stock analysis."""
    
    # Tracked stocks (HK tickers)
    STOCKS = [
        {"ticker": "HK03986", "name": "GigaDevice Semiconductor", "currency": "HKD"},
        {"ticker": "HK01972", "name": "Swire Properties", "currency": "HKD"},
        {"ticker": "HK00700", "name": "Tencent Holdings", "currency": "HKD"},
        {"ticker": "HK00001", "name": "CK Hutchison Holdings", "currency": "HKD"},
    ]
    
    def __init__(self):
        self.timestamp = datetime.utcnow()
        self.data: List[Dict[str, Any]] = []
        self.report_dir = Path("/workspace")
    
    def fetch_market_data(self) -> List[Dict[str, Any]]:
        """
        Fetch market data for tracked stocks.
        
        Returns:
            List of stock data dictionaries with current prices and changes.
        """
        # Simulated market data - in production, this would call a real API
        market_data = [
            {
                "ticker": "HK03986",
                "name": "GigaDevice Semiconductor",
                "price": 511.53,
                "currency": "HKD",
                "change_percent": 3.03,
                "timestamp": self.timestamp.isoformat()
            },
            {
                "ticker": "HK01972",
                "name": "Swire Properties",
                "price": 25.51,
                "currency": "HKD",
                "change_percent": 2.86,
                "timestamp": self.timestamp.isoformat()
            },
            {
                "ticker": "HK00700",
                "name": "Tencent Holdings",
                "price": 508.52,
                "currency": "HKD",
                "change_percent": -1.26,
                "timestamp": self.timestamp.isoformat()
            },
            {
                "ticker": "HK00001",
                "name": "CK Hutchison Holdings",
                "price": 88.6,
                "currency": "HKD",
                "change_percent": -1.23,
                "timestamp": self.timestamp.isoformat()
            },
        ]
        
        self.data = market_data
        return market_data
    
    def calculate_sentiment(self) -> tuple[str, float]:
        """
        Calculate overall market sentiment based on stock performance.
        
        Returns:
            Tuple of (sentiment: str, average_change: float)
        """
        if not self.data:
            return "NEUTRAL", 0.0
        
        avg_change = sum(stock["change_percent"] for stock in self.data) / len(self.data)
        
        if avg_change > 1.0:
            sentiment = "BULLISH 🚀"
        elif avg_change > 0.0:
            sentiment = "POSITIVE 📈"
        elif avg_change > -1.0:
            sentiment = "NEGATIVE 📉"
        else:
            sentiment = "BEARISH 🔴"
        
        return sentiment, avg_change
    
    def generate_json_report(self) -> str:
        """Generate machine-readable JSON report."""
        sentiment, avg_change = self.calculate_sentiment()
        
        report = {
            "timestamp": self.timestamp.isoformat(),
            "sentiment": sentiment,
            "average_change_percent": avg_change,
            "stocks_up": sum(1 for s in self.data if s["change_percent"] > 0),
            "stocks_down": sum(1 for s in self.data if s["change_percent"] < 0),
            "stocks": sorted(self.data, key=lambda x: x["change_percent"], reverse=True)
        }
        
        filename = f"market_data_{self.timestamp.strftime('%Y-%m-%d')}.json"
        filepath = self.report_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        
        return str(filepath)
    
    def generate_markdown_report(self) -> str:
        """Generate human-readable Markdown report."""
        sentiment, avg_change = self.calculate_sentiment()
        stocks_up = sum(1 for s in self.data if s["change_percent"] > 0)
        stocks_down = sum(1 for s in self.data if s["change_percent"] < 0)
        
        sorted_stocks = sorted(self.data, key=lambda x: x["change_percent"], reverse=True)
        
        report_lines = [
            "# Market Data Report",
            f"\n**Report Generated:** {self.timestamp.isoformat()} UTC",
            "\n## Market Summary",
            f"- **Sentiment:** {sentiment}",
            f"- **Average Change:** {avg_change:+.2f}%",
            f"- **Stocks Up:** {stocks_up}/{len(self.data)}",
            f"- **Stocks Down:** {stocks_down}/{len(self.data)}",
            "\n## Stock Performance",
        ]
        
        for idx, stock in enumerate(sorted_stocks, 1):
            emoji = "📈" if stock["change_percent"] > 0 else "📉"
            report_lines.append(
                f"{idx}. {stock['ticker']} ({stock['name']}): "
                f"{stock['price']} {stock['currency']} "
                f"({stock['change_percent']:+.2f}%) {emoji}"
            )
        
        report_text = "\n".join(report_lines)
        
        filename = f"MARKET_REPORT_{self.timestamp.strftime('%Y-%m-%d')}.md"
        filepath = self.report_dir / filename
        
        with open(filepath, "w") as f:
            f.write(report_text)
        
        return str(filepath)
    
    def run(self) -> Dict[str, Any]:
        """Execute full market data fetch and report generation."""
        self.fetch_market_data()
        json_report = self.generate_json_report()
        md_report = self.generate_markdown_report()
        
        return {
            "timestamp": self.timestamp.isoformat(),
            "data_points": len(self.data),
            "json_report": json_report,
            "markdown_report": md_report,
            "stocks": self.data
        }


def main():
    """Main entry point."""
    fetcher = MarketDataFetcher()
    result = fetcher.run()
    
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
