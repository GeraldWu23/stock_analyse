#!/usr/bin/env python3
"""
Market Data Fetcher
Fetches current stock market data for Hong Kong and Chinese stocks.
"""

import json
import requests
from datetime import datetime
from pathlib import Path

# Stock list to monitor (Hong Kong and Chinese stocks)
STOCKS = {
    'HK03986': {'name': 'GigaDevice Semiconductor', 'market': 'HKG'},
    'HK00001': {'name': 'CK Hutchison Holdings', 'market': 'HKG'},
    'HK01972': {'name': 'Swire Properties', 'market': 'HKG'},
    'HK00700': {'name': 'Tencent Holdings', 'market': 'HKG'},
}

def fetch_stock_data():
    """Fetch real-time stock data from market API."""
    market_data = []
    
    for symbol, info in STOCKS.items():
        try:
            # Use a free stock API (example with mock data for demonstration)
            # In production, use a real API like Alpha Vantage, IEX Cloud, etc.
            price = get_stock_price(symbol)
            change_percent = get_stock_change(symbol)
            
            market_data.append({
                'symbol': symbol,
                'name': info['name'],
                'price': price,
                'change_percent': change_percent,
                'market': info['market'],
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    
    return market_data

def get_stock_price(symbol):
    """Get current stock price. Using mock data for demonstration."""
    prices = {
        'HK03986': 513.42,
        'HK00001': 88.6,
        'HK01972': 25.71,
        'HK00700': 484.53,
    }
    return prices.get(symbol, 0.0)

def get_stock_change(symbol):
    """Get stock price change percentage. Using mock data for demonstration."""
    changes = {
        'HK03986': 0.67,
        'HK00001': 0.68,
        'HK01972': 0.81,
        'HK00700': 0.94,
    }
    return changes.get(symbol, 0.0)

def calculate_market_sentiment(data):
    """Calculate overall market sentiment based on price changes."""
    if not data:
        return 'NEUTRAL', 0.0
    
    positive_count = sum(1 for item in data if item['change_percent'] > 0)
    total_count = len(data)
    avg_change = sum(item['change_percent'] for item in data) / total_count
    
    if positive_count == total_count and avg_change > 0.5:
        sentiment = 'BULLISH'
    elif positive_count >= total_count / 2 and avg_change > 0:
        sentiment = 'MODERATELY BULLISH'
    elif positive_count > 0 and avg_change > 0:
        sentiment = 'MIXED POSITIVE'
    elif positive_count == 0:
        sentiment = 'BEARISH'
    else:
        sentiment = 'NEUTRAL'
    
    return sentiment, avg_change

def generate_report(data, timestamp):
    """Generate a human-readable market report."""
    sentiment, avg_change = calculate_market_sentiment(data)
    
    report = []
    report.append("# Market Data Report\n")
    report.append(f"**Generated:** {timestamp}\n")
    report.append(f"**Sentiment:** {sentiment}\n")
    report.append(f"**Average Change:** {avg_change:+.2f}%\n")
    report.append(f"**Stocks Up:** {sum(1 for d in data if d['change_percent'] > 0)}/{len(data)}\n")
    report.append(f"**Stocks Down:** {sum(1 for d in data if d['change_percent'] < 0)}/{len(data)}\n\n")
    
    report.append("## Stock Performance\n\n")
    sorted_data = sorted(data, key=lambda x: x['change_percent'], reverse=True)
    for idx, stock in enumerate(sorted_data, 1):
        report.append(f"{idx}. {stock['symbol']} ({stock['name']}): {stock['price']:.2f} HKD ({stock['change_percent']:+.2f}%)\n")
    
    report.append("\n## Market Analysis\n\n")
    if sentiment == 'BULLISH':
        report.append("Market is showing strong bullish momentum with all stocks in positive territory.\n")
    elif 'BULLISH' in sentiment:
        report.append("Market sentiment is moderately positive with most stocks gaining.\n")
    elif 'MIXED' in sentiment:
        report.append("Market shows mixed signals with both gainers and losers.\n")
    else:
        report.append("Market is showing bearish pressure with most stocks declining.\n")
    
    return ''.join(report)

def save_data(data, timestamp_str):
    """Save market data to JSON file."""
    filename = f"market_data_{timestamp_str}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    return filename

def main():
    """Main function to fetch and report market data."""
    now = datetime.utcnow()
    timestamp_str = now.strftime("%Y-%m-%dT%H-%M-%S")
    
    print(f"Fetching market data at {now.isoformat()}...")
    
    # Fetch market data
    market_data = fetch_stock_data()
    
    # Generate report
    report = generate_report(market_data, now.isoformat())
    
    # Save JSON data
    json_file = save_data(market_data, timestamp_str)
    print(f"✓ Saved market data to {json_file}")
    
    # Save markdown report
    report_file = f"MARKET_REPORT_{now.strftime('%Y-%m-%d')}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"✓ Saved market report to {report_file}")
    
    # Print report to console
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    return market_data

if __name__ == '__main__':
    main()
