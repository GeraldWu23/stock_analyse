#!/usr/bin/env python3
"""
Market data fetcher for Hong Kong stocks.
Fetches real-time or simulated market data and generates reports.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


class MarketDataFetcher:
    """Fetch and analyze Hong Kong stock market data."""
    
    # Hong Kong stock tickers with names
    STOCKS = {
        "HK00700": {"name": "腾讯控股 (Tencent)", "category": "Technology"},
        "HK01972": {"name": "太古地产 (Swire Properties)", "category": "Real Estate"},
        "HK03986": {"name": "兆易创新 (GigaDevice)", "category": "Semiconductors"},
        "HK00001": {"name": "长和 (CK Hutchison)", "category": "Conglomerate"},
    }
    
    # Base prices in HKD (for simulation)
    BASE_PRICES = {
        "HK00700": 490.0,
        "HK01972": 25.50,
        "HK03986": 510.0,
        "HK00001": 88.0,
    }
    
    def __init__(self):
        self.timestamp = datetime.utcnow()
        self.market_data = {}
    
    def fetch_market_data(self):
        """Fetch market data with realistic volatility simulation."""
        for ticker, base_price in self.BASE_PRICES.items():
            # Simulate realistic daily volatility (±2%)
            volatility = random.uniform(-0.02, 0.02)
            current_price = base_price * (1 + volatility)
            change_percent = volatility * 100
            
            self.market_data[ticker] = {
                "name": self.STOCKS[ticker]["name"],
                "category": self.STOCKS[ticker]["category"],
                "price": round(current_price, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": self.timestamp.isoformat() + "Z",
            }
        
        return self.market_data
    
    def generate_market_report(self):
        """Generate a human-readable market report."""
        if not self.market_data:
            self.fetch_market_data()
        
        # Calculate market statistics
        changes = [data["change_percent"] for data in self.market_data.values()]
        avg_change = sum(changes) / len(changes)
        ups = sum(1 for c in changes if c > 0)
        downs = sum(1 for c in changes if c < 0)
        
        # Determine market sentiment
        if avg_change > 0.5:
            sentiment = "BULLISH 📈"
        elif avg_change < -0.5:
            sentiment = "BEARISH 📉"
        else:
            sentiment = "NEUTRAL ➡️"
        
        report = f"""# 市场数据报告 (Market Report)
Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC

## 市场概况 (Market Overview)

### 股票行情 (Stock Quotes)
"""
        
        for ticker, data in sorted(self.market_data.items()):
            direction = "📈 UP" if data["change_percent"] > 0 else "📉 DOWN"
            report += f"\n- **{ticker} ({data['name']})**: {data['price']} HKD - {direction} {data['change_percent']:+.2f}%"
        
        report += f"""

## 市场分析 (Market Analysis)

- **市场情绪 (Market Sentiment)**: {sentiment}
- **平均涨跌幅 (Average Change)**: {avg_change:+.2f}%
- **上涨股票 (Stocks Up)**: {ups} out of {len(self.market_data)}
- **下跌股票 (Stocks Down)**: {downs} out of {len(self.market_data)}
- **市场状态 (Market Status)**: {'Strong upward momentum' if avg_change > 1 else 'Moderate pressure' if avg_change < -0.5 else 'Neutral with balanced activity'}

## 数据来源 (Data Source)
This report is generated from simulated market data for demonstration purposes.
Timestamp: {self.timestamp.isoformat()}Z
"""
        return report
    
    def save_json_snapshot(self):
        """Save machine-readable JSON snapshot."""
        if not self.market_data:
            self.fetch_market_data()
        
        snapshot = {
            "timestamp": self.timestamp.isoformat() + "Z",
            "market_data": self.market_data,
            "summary": {
                "total_stocks": len(self.market_data),
                "average_change": round(
                    sum(d["change_percent"] for d in self.market_data.values()) / len(self.market_data),
                    2
                ),
            }
        }
        return snapshot


def main():
    """Main entry point."""
    fetcher = MarketDataFetcher()
    
    # Fetch market data
    print("📊 Fetching market data...")
    fetcher.fetch_market_data()
    
    # Generate report
    report = fetcher.generate_market_report()
    timestamp_str = fetcher.timestamp.strftime("%Y-%m-%d")
    report_filename = f"MARKET_REPORT_{timestamp_str}.md"
    
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Report saved: {report_filename}")
    
    # Save JSON snapshot
    snapshot = fetcher.save_json_snapshot()
    timestamp_str_full = fetcher.timestamp.strftime("%Y-%m-%dT%H-%M-%S")
    json_filename = f"market_data_{timestamp_str_full}.json"
    
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON data saved: {json_filename}")
    
    # Print summary to stdout
    print("\n" + report)
    print(f"\n✅ Market data check completed at {fetcher.timestamp.isoformat()}Z")


if __name__ == "__main__":
    main()
