"""CLI: collect holdings market data in this repo. No plugin, no LLM.

Examples:
    python -m portfolio.collect
    python -m portfolio.collect --quotes-only
    python -m portfolio.collect --name 南方航空
    python -m portfolio.collect --name 南方航空 --fundamentals
"""
from __future__ import annotations

import argparse
import sys

from portfolio.collector import collect_book, format_table, write_snapshot
from portfolio.stock_raw import collect_holdings_fundamentals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="采集本仓库持仓的行情，或股票财报/K线。不调用大模型，不改插件。",
    )
    parser.add_argument("--name", metavar="名称", default=None, help="只采集这一行（用中文名）")
    parser.add_argument("--quotes-only", action="store_true", help="只拉现价/溢价，不抓 ETF 篮子")
    parser.add_argument(
        "--fundamentals",
        action="store_true",
        help="股票再拉财报与 K 线，写入 collected/{ticker}/raw_data.json，供 66 评委使用",
    )
    args = parser.parse_args(argv)

    snapshot = collect_book(
        only_name=args.name,
        quotes_only=args.quotes_only,
    )
    path = write_snapshot(snapshot)
    print(format_table(snapshot))
    print(f"\n已写入 {path}")

    fund_failed = 0
    if args.fundamentals:
        fund = collect_holdings_fundamentals(only_name=args.name)
        print("\n财报/K 线")
        for row in fund.get("stocks") or []:
            status = "ok" if row.get("ok") else "失败"
            extra = row.get("path") or row.get("error") or ""
            print(f"  {row.get('name')}  {status}  {extra}")
        skipped = fund.get("skipped_etfs") or []
        if skipped:
            print("  跳过篮子：" + "、".join(s["name"] for s in skipped))
        fund_failed = sum(1 for s in fund.get("stocks") or [] if not s.get("ok"))

    print("份额未改。现价×份额只做市值还原。不是持牌投顾意见。")
    failed = snapshot.get("failed", 0) + fund_failed
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
