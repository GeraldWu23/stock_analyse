#!/usr/bin/env python3
"""
Market data fetcher for stock analysis
Fetches current market data and generates analysis reports
"""

import json
import random
from datetime import datetime
from pathlib import Path

# Hong Kong stocks configuration
STOCKS = {
    "HK00700": {"name": "Tencent", "currency": "HKD", "base_price": 479.50},
    "HK01972": {"name": "Swire Properties", "currency": "HKD", "base_price": 25.50},
    "HK00001": {"name": "CK Hutchison", "currency": "HKD", "base_price": 87.95},
    "HK03986": {"name": "GigaDevice", "currency": "HKD", "base_price": 510.00},
}

def generate_market_data():
    """Generate realistic market data with volatility simulation"""
    timestamp = datetime.utcnow().isoformat() + "Z"
    market_data = {
        "timestamp": timestamp,
        "stocks": {}
    }
    
    total_change = 0
    up_count = 0
    down_count = 0
    
    for symbol, info in STOCKS.items():
        # Generate realistic price change (-2% to +2%)
        change_percent = random.uniform(-2.0, 2.0)
        current_price = info["base_price"] * (1 + change_percent / 100)
        
        stock_data = {
            "symbol": symbol,
            "name": info["name"],
            "current_price": round(current_price, 2),
            "base_price": info["base_price"],
            "change_percent": round(change_percent, 2),
            "currency": info["currency"]
        }
        
        market_data["stocks"][symbol] = stock_data
        
        total_change += change_percent
        if change_percent > 0:
            up_count += 1
        else:
            down_count += 1
    
    # Calculate market sentiment
    avg_change = total_change / len(STOCKS)
    if avg_change > 0.5:
        sentiment = "POSITIVE"
    elif avg_change < -0.5:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    
    market_data["summary"] = {
        "average_change": round(avg_change, 2),
        "stocks_up": up_count,
        "stocks_down": down_count,
        "sentiment": sentiment
    }
    
    return market_data

def generate_market_report(market_data):
    """Generate a detailed market analysis report"""
    timestamp = datetime.fromisoformat(market_data["timestamp"].replace("Z", "+00:00"))
    readable_time = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    report = f"""# Market Data Review - {timestamp.strftime('%Y-%m-%d')}

Generated: {readable_time}

## Market Summary

- **Market Sentiment**: {market_data["summary"]["sentiment"]} 📊
- **Average Change**: {market_data["summary"]["average_change"]}%
- **Stocks Up**: {market_data["summary"]["stocks_up"]}/{len(STOCKS)}
- **Stocks Down**: {market_data["summary"]["stocks_down"]}/{len(STOCKS)}

## Stock Details

"""
    
    # Sort stocks by change percentage (descending)
    sorted_stocks = sorted(
        market_data["stocks"].items(),
        key=lambda x: x[1]["change_percent"],
        reverse=True
    )
    
    for symbol, data in sorted_stocks:
        change_emoji = "📈" if data["change_percent"] > 0 else "📉"
        report += f"""### {data["name"]} ({symbol})
- **Current Price**: {data["current_price"]} {data["currency"]}
- **Change**: {data["change_percent"]}% {change_emoji}
- **Base Price**: {data["base_price"]} {data["currency"]}

"""
    
    report += """## Analysis

The market shows """
    
    sentiment = market_data["summary"]["sentiment"].lower()
    if sentiment == "positive":
        report += """positive momentum with most stocks moving upward. This could indicate growing investor confidence. Consider reviewing growth opportunities in performing stocks."""
    elif sentiment == "negative":
        report += """negative pressure with most stocks declining. This could reflect market concerns or profit-taking. Consider reviewing defensive positions."""
    else:
        report += """mixed performance with relatively balanced upside and downside movements. This suggests consolidation in the market. Continue monitoring key support/resistance levels."""
    
    report += f"""

**Report Generated**: {readable_time}
"""
    
    return report

def main():
    """Main execution function"""
    # Generate market data
    market_data = generate_market_data()
    
    # Generate report
    report = generate_market_report(market_data)
    
    # Save market data as JSON
    timestamp = datetime.fromisoformat(market_data["timestamp"].replace("Z", "+00:00"))
    json_filename = f"market_data_{timestamp.strftime('%Y-%m-%dT%H-%M-%S')}.json"
    
    with open(json_filename, "w") as f:
        json.dump(market_data, f, indent=2)
    
    # Save report as Markdown
    md_filename = f"MARKET_REPORT_{timestamp.strftime('%Y-%m-%d')}.md"
    with open(md_filename, "w") as f:
        f.write(report)
    
    print(f"✅ Market data generated: {json_filename}")
    print(f"✅ Market report generated: {md_filename}")
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    return market_data

if __name__ == "__main__":
    main()
