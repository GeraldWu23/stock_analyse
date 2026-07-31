#!/usr/bin/env python3
"""
Market Data Fetcher
Fetches and analyzes market data for tracked Hong Kong stocks
"""

import json
import random
from datetime import datetime
from pathlib import Path


class MarketDataFetcher:
    """Fetches and analyzes market data for Hong Kong stocks"""
    
    # Stock configurations with base prices
    STOCKS = {
        'HK03986': {'name': 'GigaDevice', 'base_price': 510.0},
        'HK00001': {'name': 'CK Hutchison', 'base_price': 88.0},
        'HK01972': {'name': 'Swire Properties', 'base_price': 25.5},
        'HK00700': {'name': 'Tencent', 'base_price': 480.0},
    }
    
    def __init__(self):
        self.timestamp = datetime.utcnow()
        self.market_data = {}
    
    def fetch_data(self):
        """Fetch market data with simulated price movements"""
        for stock_code, stock_info in self.STOCKS.items():
            # Simulate realistic price movement (-2% to +2%)
            change_percent = random.uniform(-2.0, 2.0)
            base_price = stock_info['base_price']
            current_price = base_price * (1 + change_percent / 100)
            
            self.market_data[stock_code] = {
                'code': stock_code,
                'name': stock_info['name'],
                'base_price': base_price,
                'current_price': round(current_price, 2),
                'change_percent': round(change_percent, 2),
                'timestamp': self.timestamp.isoformat()
            }
    
    def analyze_sentiment(self):
        """Analyze overall market sentiment"""
        if not self.market_data:
            return 'UNKNOWN'
        
        changes = [stock['change_percent'] for stock in self.market_data.values()]
        avg_change = sum(changes) / len(changes)
        
        if avg_change > 0.5:
            return 'BULLISH'
        elif avg_change < -0.5:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
    
    def get_stats(self):
        """Get market statistics"""
        if not self.market_data:
            return {}
        
        changes = [stock['change_percent'] for stock in self.market_data.values()]
        stocks_up = sum(1 for c in changes if c > 0)
        stocks_down = sum(1 for c in changes if c < 0)
        avg_change = sum(changes) / len(changes)
        
        return {
            'average_change': round(avg_change, 2),
            'stocks_up': stocks_up,
            'stocks_down': stocks_down,
            'total_stocks': len(self.market_data),
            'sentiment': self.analyze_sentiment()
        }
    
    def generate_json_report(self, filename=None):
        """Generate JSON format report"""
        if filename is None:
            filename = f"market_data_{self.timestamp.isoformat()}.json"
        
        report = {
            'timestamp': self.timestamp.isoformat(),
            'stocks': list(self.market_data.values()),
            'stats': self.get_stats()
        }
        
        filepath = Path(filename)
        filepath.write_text(json.dumps(report, indent=2))
        return filename
    
    def generate_markdown_report(self, filename=None):
        """Generate Markdown format report"""
        if filename is None:
            date_str = self.timestamp.strftime('%Y-%m-%d')
            filename = f"MARKET_REPORT_{date_str}.md"
        
        stats = self.get_stats()
        
        report_lines = [
            "# Market Data Report",
            f"**Generated:** {self.timestamp.isoformat()}",
            "",
            "## Market Summary",
            f"- **Sentiment:** {stats['sentiment']}",
            f"- **Average Change:** {stats['average_change']:+.2f}%",
            f"- **Stocks Up:** {stats['stocks_up']}/{stats['total_stocks']}",
            f"- **Stocks Down:** {stats['stocks_down']}/{stats['total_stocks']}",
            "",
            "## Stock Details",
            ""
        ]
        
        for stock in sorted(self.market_data.values(), key=lambda x: x['change_percent'], reverse=True):
            direction = "📈" if stock['change_percent'] > 0 else "📉" if stock['change_percent'] < 0 else "➡️"
            report_lines.append(
                f"- **{stock['code']}** ({stock['name']}): "
                f"{stock['change_percent']:+.2f}% @ {stock['current_price']:.2f} HKD {direction}"
            )
        
        filepath = Path(filename)
        filepath.write_text('\n'.join(report_lines))
        return filename


def main():
    """Main entry point"""
    fetcher = MarketDataFetcher()
    fetcher.fetch_data()
    
    # Generate reports
    json_file = fetcher.generate_json_report()
    md_file = fetcher.generate_markdown_report()
    
    print(f"✅ JSON report: {json_file}")
    print(f"✅ Markdown report: {md_file}")
    
    # Print summary
    stats = fetcher.get_stats()
    print(f"\n📊 Market Summary:")
    print(f"   Sentiment: {stats['sentiment']}")
    print(f"   Average Change: {stats['average_change']:+.2f}%")
    print(f"   Stocks Up/Down: {stats['stocks_up']}/{stats['stocks_down']}")


if __name__ == '__main__':
    main()
