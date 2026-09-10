"""CLI: collect holdings market data in this repo. No plugin, no LLM.

Examples:
    python -m portfolio.collect
    python -m portfolio.collect --quotes-only
    python -m portfolio.collect --name 南方航空
"""
from __future__ import annotations

import argparse
import sys

from portfolio.collector import collect_book, format_table, write_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="采集本仓库持仓的行情与 ETF 篮子。不调用大模型，不改插件。",
    )
    parser.add_argument("--name", metavar="名称", default=None, help="只采集这一行（用中文名）")
    parser.add_argument("--quotes-only", action="store_true", help="只拉现价/溢价，不抓 ETF 篮子")
    args = parser.parse_args(argv)

    snapshot = collect_book(
        only_name=args.name,
        quotes_only=args.quotes_only,
    )
    path = write_snapshot(snapshot)
    print(format_table(snapshot))
    print(f"\n已写入 {path}")
    print("份额未改。现价×份额只做市值还原。不是持牌投顾意见。")
    return 0 if snapshot.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
