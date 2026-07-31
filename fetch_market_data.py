#!/usr/bin/env python3
"""
Market data fetcher for Hong Kong stock market.
Fetches latest market data and generates reports.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Sample stock data for Hong Kong Market
SAMPLE_STOCKS = {
    "HK00700": {
        "name": "腾讯控股 (Tencent)",
        "currency": "HKD",
        "base_price": 515.0,
        "volatility": 2.5,
    },
    "HK01972": {
        "name": "太古地产 (Swire Properties)",
        "currency": "HKD",
        "base_price": 24.8,
        "volatility": 3.0,
    },
    "HK03986": {
        "name": "兆易创新 (GigaDevice)",
        "currency": "HKD",
        "base_price": 496.5,
        "volatility": 4.0,
    },
    "HK00001": {
        "name": "长和 (CK Hutchison)",
        "currency": "HKD",
        "base_price": 89.7,
        "volatility": 2.0,
    },
}


def generate_market_data() -> Dict[str, Any]:
    """Generate simulated market data for Hong Kong stocks."""
    import random

    now = datetime.now(timezone.utc)
    data = {
        "timestamp": now.isoformat(),
        "market": "Hong Kong",
        "stocks": {},
    }

    for symbol, info in SAMPLE_STOCKS.items():
        # Generate random price variation
        change_percent = random.uniform(
            -info["volatility"], info["volatility"]
        )
        current_price = info["base_price"] * (1 + change_percent / 100)

        data["stocks"][symbol] = {
            "name": info["name"],
            "currency": info["currency"],
            "price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "base_price": info["base_price"],
            "timestamp": now.isoformat(),
        }

    return data


def generate_report(market_data: Dict[str, Any]) -> str:
    """Generate a human-readable market report."""
    report_lines = [
        "# Market Data Report",
        f"\n**Timestamp**: {market_data['timestamp']}",
        f"**Market**: {market_data['market']}",
        "\n## Stock Prices\n",
    ]

    total_change = 0
    bullish_count = 0

    for symbol, data in market_data["stocks"].items():
        change = data["change_percent"]
        price = data["price"]
        name = data["name"]

        trend = "📈" if change >= 0 else "📉"
        report_lines.append(
            f"- **{symbol} ({name})**: {price} {data['currency']} - "
            f"{change:+.2f}% {trend}"
        )

        total_change += change
        if change >= 0:
            bullish_count += 1

    # Calculate summary metrics
    avg_change = total_change / len(market_data["stocks"])
    sentiment = "Bullish" if avg_change >= 0 else "Bearish"

    report_lines.extend(
        [
            "\n## Market Summary",
            f"- Average change: {avg_change:+.2f}%",
            f"- Bullish stocks: {bullish_count}/{len(market_data['stocks'])}",
            f"- Overall sentiment: **{sentiment}**",
        ]
    )

    return "\n".join(report_lines)


def save_report(report: str, date_str: str) -> None:
    """Save the market report to a file."""
    report_file = Path(f"MARKET_REPORT_{date_str}.md")
    report_file.write_text(report)
    print(f"✅ Report saved to {report_file}")


def save_data_json(market_data: Dict[str, Any], date_str: str) -> None:
    """Save market data as JSON for machine consumption."""
    data_file = Path(f"market_data_{date_str}.json")
    data_file.write_text(json.dumps(market_data, indent=2))
    print(f"✅ Data saved to {data_file}")


def main():
    """Main entry point."""
    print("🚀 Starting market data fetch...\n")

    # Generate market data
    print("📊 Generating market data...")
    market_data = generate_market_data()

    # Get date string for filenames
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # Generate and display report
    print("📝 Generating report...")
    report = generate_report(market_data)
    print("\n" + report + "\n")

    # Save files
    print("\n💾 Saving files...")
    save_report(report, date_str)
    save_data_json(market_data, date_str)

    print("\n✅ Market data fetch completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
