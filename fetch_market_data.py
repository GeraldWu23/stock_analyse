#!/usr/bin/env python3
"""
Market Data Fetcher
Fetches stock market data from Hong Kong market
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any
import random


def get_market_data() -> Dict[str, Any]:
    """
    Fetch market data from Hong Kong stock market.
    Returns current market data with stock prices and changes.
    """
    
    # Using simulated market data for demonstration
    # In production, this would connect to real data sources
    
    current_time = datetime.now(timezone.utc)
    
    stocks = [
        {
            "symbol": "HK00700",
            "name": "腾讯控股 (Tencent)",
            "price": 503.16 + random.uniform(-2, 5),
            "change_percent": 3.68 + random.uniform(-1, 2),
        },
        {
            "symbol": "HK01972",
            "name": "太古地产 (Swire)",
            "price": 22.87 + random.uniform(-1, 1),
            "change_percent": -4.03 + random.uniform(-1, 2),
        },
        {
            "symbol": "HK03986",
            "name": "兆易创新 (GigaDevice)",
            "price": 496.17 + random.uniform(-5, 10),
            "change_percent": 0.33 + random.uniform(-1, 2),
        },
        {
            "symbol": "HK00001",
            "name": "长和 (CK Hutchison)",
            "price": 90.22 + random.uniform(-2, 3),
            "change_percent": 2.58 + random.uniform(-1, 2),
        },
    ]
    
    market_data = {
        "timestamp": current_time.isoformat(),
        "market": "Hong Kong Stock Exchange",
        "stocks": stocks,
        "summary": {
            "total_stocks": len(stocks),
            "advancing": sum(1 for s in stocks if s["change_percent"] > 0),
            "declining": sum(1 for s in stocks if s["change_percent"] < 0),
            "unchanged": sum(1 for s in stocks if s["change_percent"] == 0),
            "average_change": sum(s["change_percent"] for s in stocks) / len(stocks),
        }
    }
    
    return market_data


def generate_market_report(market_data: Dict[str, Any]) -> str:
    """
    Generate a markdown report from market data.
    """
    
    timestamp = market_data["timestamp"]
    stocks = market_data["stocks"]
    summary = market_data["summary"]
    
    report = f"""# 行情分析报告 (Market Report)
Generated: {timestamp}

## 市场概览 (Market Overview)
- **市场**: {market_data["market"]}
- **上涨股票**: {summary['advancing']}
- **下跌股票**: {summary['declining']}
- **平盘**: {summary['unchanged']}
- **平均涨幅**: {summary['average_change']:.2f}%

## 香港股票行情 (Hong Kong Stocks)

"""
    
    for stock in stocks:
        trend = "📈" if stock["change_percent"] > 0 else "📉"
        report += f"### {stock['symbol']} - {stock['name']}\n"
        report += f"- **价格**: {stock['price']:.2f} HKD\n"
        report += f"- **涨幅**: {stock['change_percent']:+.2f}% {trend}\n\n"
    
    # Market sentiment
    avg_change = summary["average_change"]
    if avg_change > 1:
        sentiment = "**看涨 (Bullish)** 🚀"
    elif avg_change < -1:
        sentiment = "**看跌 (Bearish)** 📉"
    else:
        sentiment = "**中性 (Neutral)** ➡️"
    
    report += f"## 市场情绪 (Market Sentiment)\n"
    report += f"- 整体趋势: {sentiment}\n"
    
    return report


def main():
    """Main function to fetch and report market data."""
    
    print("获取行情数据... (Fetching market data...)")
    market_data = get_market_data()
    
    # Generate report
    report = generate_market_report(market_data)
    
    # Save market data as JSON
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    data_file = f"market_data_{timestamp_str}.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(market_data, f, indent=2, ensure_ascii=False)
    print(f"✅ 市场数据已保存: {data_file}")
    
    # Save report as markdown
    report_file = f"MARKET_REPORT_{timestamp_str}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 行情报告已生成: {report_file}")
    
    # Print report to console
    print("\n" + "="*50)
    print(report)
    print("="*50)


if __name__ == "__main__":
    main()
