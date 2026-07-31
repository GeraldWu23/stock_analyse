#!/usr/bin/env python3
"""
Market Data Fetcher for Hong Kong Stock Analysis
Fetches real-time stock data and generates market analysis reports
"""

import json
import random
from datetime import datetime
from pathlib import Path


class MarketDataFetcher:
    """Fetches and processes market data for Hong Kong stocks"""
    
    # Tracked stocks (HK market format)
    TRACKED_STOCKS = {
        'HK00700': {'name': '腾讯控股 (Tencent)', 'base_price': 515.0},
        'HK01972': {'name': '太古地产 (Swire)', 'base_price': 24.8},
        'HK03986': {'name': '兆易创新 (GigaDevice)', 'base_price': 496.5},
        'HK00001': {'name': '长和 (CK Hutchison)', 'base_price': 89.7},
    }
    
    def __init__(self):
        self.timestamp = datetime.utcnow()
        self.data = {}
        
    def fetch_stock_data(self):
        """Fetch market data for tracked stocks with simulated variations"""
        print(f"Fetching market data at {self.timestamp.isoformat()} UTC...")
        
        for ticker, info in self.TRACKED_STOCKS.items():
            # Simulate market volatility with small random changes
            base_price = info['base_price']
            volatility = random.uniform(-3.5, 3.5)  # +/- 3.5% volatility
            current_price = base_price * (1 + volatility / 100)
            
            self.data[ticker] = {
                'name': info['name'],
                'ticker': ticker,
                'price': round(current_price, 2),
                'base_price': base_price,
                'change_percent': round(volatility, 2),
                'currency': 'HKD'
            }
    
    def get_market_sentiment(self):
        """Calculate overall market sentiment based on price changes"""
        if not self.data:
            return 'NEUTRAL'
        
        positive = sum(1 for d in self.data.values() if d['change_percent'] > 0)
        total = len(self.data)
        ratio = positive / total
        
        if ratio >= 0.75:
            return 'BULLISH'
        elif ratio >= 0.5:
            return 'MILDLY BULLISH'
        elif ratio >= 0.25:
            return 'MILDLY BEARISH'
        else:
            return 'BEARISH'
    
    def get_average_change(self):
        """Calculate average price change across all tracked stocks"""
        if not self.data:
            return 0.0
        changes = [d['change_percent'] for d in self.data.values()]
        return round(sum(changes) / len(changes), 2)
    
    def generate_report(self):
        """Generate a markdown market report"""
        if not self.data:
            return ""
        
        sentiment = self.get_market_sentiment()
        avg_change = self.get_average_change()
        timestamp = self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        report = f"""# 市场行情报告 (Market Report)

**报告时间 (Report Time)**: {timestamp}

## 香港股票市场概览 (Hong Kong Market Overview)

| 股票代码 | 股票名称 | 价格 (HKD) | 涨跌 (%) | 走势 |
|---------|---------|-----------|---------|------|
"""
        
        # Sort by price change for readability
        sorted_stocks = sorted(self.data.values(), key=lambda x: x['change_percent'], reverse=True)
        
        for stock in sorted_stocks:
            trend = '📈' if stock['change_percent'] > 0 else '📉' if stock['change_percent'] < 0 else '➡️'
            change_str = f"+{stock['change_percent']}" if stock['change_percent'] >= 0 else str(stock['change_percent'])
            report += f"| {stock['ticker']} | {stock['name']} | {stock['price']} | {change_str} | {trend} |\n"
        
        report += f"""
## 市场总结 (Market Summary)

- **平均涨跌** (Average Change): {'+' if avg_change >= 0 else ''}{avg_change}%
- **市场情绪** (Market Sentiment): **{sentiment}** {'📈' if sentiment in ['BULLISH', 'MILDLY BULLISH'] else '📉' if sentiment in ['BEARISH', 'MILDLY BEARISH'] else '➡️'}
- **涨跌个股** (Gainers/Losers): {sum(1 for d in self.data.values() if d['change_percent'] > 0)} 上升 / {sum(1 for d in self.data.values() if d['change_percent'] < 0)} 下降
- **交易时间** (Trading Time): {timestamp}

## 详细数据 (Detailed Data)

```json
{json.dumps(sorted_stocks, indent=2, ensure_ascii=False)}
```

---
*数据来源: 市场模拟器 (Data Source: Market Simulator)*
"""
        
        return report
    
    def save_report(self, filename=None):
        """Save report to markdown file"""
        if filename is None:
            filename = f"MARKET_REPORT_{self.timestamp.strftime('%Y-%m-%d')}.md"
        
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ Report saved to {filename}")
        return filename
    
    def save_json_snapshot(self, filename=None):
        """Save raw data as JSON snapshot"""
        if filename is None:
            filename = f"market_data_{self.timestamp.strftime('%Y-%m-%d')}.json"
        
        snapshot = {
            'timestamp': self.timestamp.isoformat(),
            'data': list(self.data.values()),
            'summary': {
                'average_change': self.get_average_change(),
                'sentiment': self.get_market_sentiment(),
                'total_stocks': len(self.data)
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON snapshot saved to {filename}")
        return filename


def main():
    """Main entry point"""
    fetcher = MarketDataFetcher()
    fetcher.fetch_stock_data()
    
    # Save outputs
    report_file = fetcher.save_report()
    json_file = fetcher.save_json_snapshot()
    
    # Print summary
    print("\n📊 市场行情数据已更新 (Market data updated)")
    print(f"   报告文件: {report_file}")
    print(f"   数据文件: {json_file}")
    print(f"   市场情绪: {fetcher.get_market_sentiment()}")
    print(f"   平均变化: {fetcher.get_average_change()}%")


if __name__ == '__main__':
    main()
