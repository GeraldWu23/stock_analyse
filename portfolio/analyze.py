"""No-LLM stock analysis in this repo: collect → 66 judges → markdown.

Tomorrow, from the repo root:

    python -m portfolio.collect --name 南方航空 --quotes-only
    python -m portfolio.collect --name 南方航空 --fundamentals
    python -m portfolio.judges --name 南方航空

Or one shot:

    python -m portfolio.analyze --name 南方航空
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from portfolio.collector import collect_book, format_table, write_snapshot
from portfolio.judges import (
    format_judges,
    format_stock_report,
    run_book_judges,
    write_judges_snapshot,
)
from portfolio.stock_raw import collect_holdings_fundamentals, raw_data_path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = REPO_ROOT / "portfolio" / "analysis"


def run_analyze(name: str) -> dict:
    print(f"[1/3] 采集现价 · {name} · 不大模型")
    snapshot = collect_book(only_name=name, quotes_only=True)
    write_snapshot(snapshot)
    print(format_table(snapshot))

    print(f"\n[2/3] 采集财报与 K 线 · {name}")
    fund = collect_holdings_fundamentals(only_name=name)
    for row in fund.get("stocks") or []:
        print(f"  {row.get('name')}  {'ok' if row.get('ok') else '失败'}  {row.get('path') or row.get('error')}")
    if not (fund.get("stocks") or []):
        raise RuntimeError(f"{name} 没有采集到股票财报（ETF 不会走这一步）")

    print(f"\n[3/3] 66 评委规则引擎 · {name}")
    payload = run_book_judges(only_name=name)
    write_judges_snapshot(payload)
    print(format_judges(payload))

    stock = (payload.get("stocks") or [None])[0]
    if not stock or stock.get("status") == "error":
        raise RuntimeError((stock or {}).get("error") or "评委失败")

    ticker = stock["ticker"]
    raw_path = raw_data_path(ticker)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    dims_path = raw_path.parent / "dimensions.json"
    dims = json.loads(dims_path.read_text(encoding="utf-8")) if dims_path.exists() else {}
    quote = (snapshot.get("positions") or [{}])[0]
    report = format_stock_report(
        name,
        quote,
        {"raw": raw, "dimensions": dims},
        stock,
    )
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    dated = ANALYSIS_DIR / f"{name}-规则引擎-{datetime.now().strftime('%Y-%m-%d')}.md"
    latest = ANALYSIS_DIR / f"{name}-规则引擎-latest.md"
    dated.write_text(report, encoding="utf-8")
    latest.write_text(report, encoding="utf-8")
    return {
        "report": str(dated),
        "raw": str(raw_path),
        "payload": payload,
        "snapshot": snapshot,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="不使用大模型：采集 + 66 评委分析一只持仓股票。")
    parser.add_argument("--name", metavar="名称", required=True, help="持仓中文名，例如 南方航空")
    args = parser.parse_args(argv)
    try:
        result = run_analyze(args.name)
    except Exception as exc:
        print(f"失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"笔记 {result['report']}")
    print(f"缓存 {result['raw']}")
    print("不是持牌投顾意见。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
