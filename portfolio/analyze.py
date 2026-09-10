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
from portfolio.engine.stock_features import extract_features
from portfolio.judges import (
    format_judges,
    run_book_judges,
    write_judges_snapshot,
)
from portfolio.stock_raw import collect_holdings_fundamentals, raw_data_path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = REPO_ROOT / "portfolio" / "analysis"


def format_stock_report(name: str, quote: dict, scored: dict, panel_summary: dict) -> str:
    raw = scored.get("raw") or {}
    features = extract_features(raw, raw.get("dimensions") or {})
    dims = (scored.get("dimensions") or {}).get("dimensions") or {}
    sig = panel_summary.get("signal_distribution") or {}
    lines = [
        f"# {name} · 规则引擎分析",
        "",
        f"日期：{datetime.now().strftime('%Y-%m-%d')}。"
        "本仓库采集 + 66 评委规则投票，**没有调用大模型**，也不是持牌投顾意见。",
        "",
        "## 采集摘要",
        "",
        f"- 现价 {quote.get('last_price') if quote.get('last_price') is not None else '—'}"
        f"；涨跌 {quote.get('change_pct') if quote.get('change_pct') is not None else '—'}%",
        f"- PE(TTM) {features.get('pe') or '—'}；PB {features.get('pb') or '—'}"
        f"；市值约 {features.get('market_cap_yi') or '—'} 亿",
        f"- ROE 最新 {features.get('roe_latest')}%；负债率 {features.get('debt_ratio')}%"
        f"；营收增速 {features.get('revenue_growth_latest')}%",
        f"- 净利润增速 {features.get('net_profit_growth_latest')}%；净利率 {features.get('net_margin')}",
        f"- K 线 {features.get('stage')}；均线 {features.get('ma_align')}；RSI {features.get('rsi')}",
        "",
        "## 九派 66 评委",
        "",
        f"{panel_summary.get('n_judges')} 位评委 · 共识 **{panel_summary.get('panel_consensus')}** · "
        f"看多 {sig.get('bullish', 0)}、中性 {sig.get('neutral', 0)}、"
        f"看空 {sig.get('bearish', 0)}、跳过 {sig.get('skip', 0)}。",
        "",
        "| 流派 | 结论 | 分数 |",
        "| --- | --- | ---: |",
    ]
    for s in panel_summary.get("schools") or []:
        score = s.get("score")
        score_s = "—" if score is None else (f"{score:.1f}" if isinstance(score, float) else str(score))
        lines.append(f"| {s.get('label')} | {s.get('verdict') or '—'} | {score_s} |")
    lines.append("")
    if panel_summary.get("top_bear"):
        lines.append("偏空：" + "、".join(f"{i['name']} {i.get('score')}" for i in panel_summary["top_bear"]))
    if panel_summary.get("top_bull"):
        lines.append("偏多：" + "、".join(f"{i['name']} {i.get('score')}" for i in panel_summary["top_bull"]))
    lines.append("")
    fin = dims.get("1_financials") or {}
    kline = dims.get("2_kline") or {}
    if fin.get("label") or kline.get("label"):
        lines.extend(["## 维度分（规则，不是模型）", ""])
        if fin.get("label"):
            lines.append(f"- 财报：{fin.get('score')} 分 · {fin.get('label')}")
        if kline.get("label"):
            lines.append(f"- K 线：{kline.get('score')} 分 · {kline.get('label')}")
        lines.append("")
    lines.extend([
        "## 怎么读",
        "",
        "游资 / 科技领袖 / AI 卡位 得 0 分且「跳过」，多半是规则判定不在能力圈，不是模型看空。",
        "研报、护城河、龙虎榜等维度本采集未拉，对应规则会因缺数据跳过，不记失败。",
        "份额未改。现金已在账户总值里。",
        "",
    ])
    return "\n".join(lines)


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
