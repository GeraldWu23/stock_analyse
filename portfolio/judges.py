"""Run the 9-school / 66-judge rule panel on stocks in this repo.

Reads `portfolio/collected/{ticker}/raw_data.json` written by
`python -m portfolio.collect --fundamentals`. No plugin, no LLM, no HTML.
ETF rows are skipped: they are baskets, not equity-judge targets.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from portfolio.collector import COLLECTED_DIR, load_holdings, position_kind
from portfolio.engine.score import generate_panel, score_dimensions
from portfolio.stock_raw import raw_data_path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHOOL_LABELS = {
    "A": "经典价值派",
    "B": "成长派",
    "C": "宏观派",
    "D": "技术派",
    "E": "中式价投",
    "F": "A 股游资",
    "G": "量化派",
    "H": "科技领袖派",
    "I": "AI 卡位/瓶颈猎手",
}


def summarize_panel(panel: dict, *, name: str, ticker: str) -> dict:
    investors = panel.get("investors") or []
    schools = panel.get("school_scores") or {}
    school_rows = []
    for key in SCHOOL_LABELS:
        block = schools.get(key) or {}
        school_rows.append({
            "group": key,
            "label": block.get("label") or SCHOOL_LABELS[key],
            "verdict": block.get("verdict"),
            "score": block.get("consensus") if block.get("consensus") is not None else block.get("score"),
            "n": block.get("n_active") or block.get("n_members"),
        })
    top_bull = sorted(
        [i for i in investors if i.get("signal") == "bullish"],
        key=lambda i: i.get("score") or 0,
        reverse=True,
    )[:3]
    top_bear = sorted(
        [i for i in investors if i.get("signal") == "bearish"],
        key=lambda i: i.get("score") if i.get("score") is not None else 999,
    )[:3]
    return {
        "name": name,
        "ticker": ticker,
        "kind": "stock",
        "llm": False,
        "n_judges": len(investors),
        "n_schools": len(SCHOOL_LABELS),
        "panel_consensus": panel.get("panel_consensus"),
        "signal_distribution": panel.get("signal_distribution"),
        "vote_distribution": panel.get("vote_distribution"),
        "schools": school_rows,
        "top_bull": [{"name": i.get("name"), "score": i.get("score"), "headline": i.get("headline")} for i in top_bull],
        "top_bear": [{"name": i.get("name"), "score": i.get("score"), "headline": i.get("headline")} for i in top_bear],
    }


def score_stock_from_cache(ticker: str, collected_dir: Path | None = None) -> dict:
    """Rule-engine 66 judges from project raw_data.json. No LLM, no HTML."""
    dest = collected_dir or COLLECTED_DIR
    path = raw_data_path(ticker, dest)
    if not path.exists():
        raise FileNotFoundError(
            f"没有采集缓存: {path}。先跑 python -m portfolio.collect --name <中文名> --fundamentals"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    dims = score_dimensions(raw)
    panel = generate_panel(dims, raw)
    cache = path.parent
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "dimensions.json").write_text(
        json.dumps(dims, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    (cache / "panel.json").write_text(
        json.dumps(panel, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return {"dimensions": dims, "panel": panel, "raw_path": str(path)}


def run_book_judges(
    holdings: dict | None = None,
    *,
    only_name: str | None = None,
    score_fn=None,
    collected_dir: Path | None = None,
) -> dict:
    book = holdings or load_holdings()
    rows = list(book.get("holdings") or [])
    if only_name:
        needle = only_name.strip()
        rows = [r for r in rows if r.get("name") == needle]
        if not rows:
            raise ValueError(f"持仓里没有叫 {only_name!r} 的标的")

    def _score(ticker: str) -> dict:
        if score_fn is not None:
            return score_fn(ticker)
        return score_stock_from_cache(ticker, collected_dir=collected_dir)

    results: list[dict] = []
    skipped: list[dict] = []
    for row in rows:
        name = row["name"]
        ticker = row["ticker"]
        if position_kind(row) == "etf":
            skipped.append({"name": name, "reason": "ETF 是篮子，不跑 66 评委"})
            continue
        try:
            scored = _score(ticker)
            panel = scored["panel"] if isinstance(scored, dict) and "panel" in scored else scored
            results.append(summarize_panel(panel, name=name, ticker=ticker))
        except Exception as exc:
            results.append({
                "name": name,
                "ticker": ticker,
                "kind": "stock",
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:240],
            })

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "66-judges",
        "llm": False,
        "schools": SCHOOL_LABELS,
        "stocks": results,
        "skipped_etfs": skipped,
    }
    return payload


def write_judges_snapshot(payload: dict, collected_dir: Path | None = None) -> Path:
    dest = collected_dir or COLLECTED_DIR
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "judges-latest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def format_judges(payload: dict) -> str:
    lines = [
        f"66 评委 · 9 流派 · {payload.get('as_of')} · 大模型={payload.get('llm')}",
        "",
    ]
    for stock in payload.get("stocks") or []:
        if stock.get("status") == "error":
            lines.append(f"## {stock.get('name')}")
            lines.append(f"失败：{stock.get('error')}")
            lines.append("")
            continue
        sig = stock.get("signal_distribution") or {}
        lines.append(f"## {stock.get('name')}")
        lines.append(
            f"评委 {stock.get('n_judges')} 人 · 共识 {stock.get('panel_consensus')} · "
            f"看多 {sig.get('bullish', 0)} / 中性 {sig.get('neutral', 0)} / "
            f"看空 {sig.get('bearish', 0)} / 跳过 {sig.get('skip', 0)}"
        )
        lines.append(f"{'流派':<12} {'结论':<8} {'分数'}")
        for s in stock.get("schools") or []:
            score = s.get("score")
            score_s = "—" if score is None else f"{score:.1f}" if isinstance(score, float) else str(score)
            lines.append(f"{s.get('label', ''):<12} {str(s.get('verdict') or '—'):<8} {score_s}")
        if stock.get("top_bear"):
            lines.append("偏空代表：" + "；".join(
                f"{i['name']}({i.get('score')})" for i in stock["top_bear"]
            ))
        if stock.get("top_bull"):
            lines.append("偏多代表：" + "；".join(
                f"{i['name']}({i.get('score')})" for i in stock["top_bull"]
            ))
        lines.append("")
    skipped = payload.get("skipped_etfs") or []
    if skipped:
        lines.append("未跑评委的篮子：" + "、".join(s["name"] for s in skipped))
    return "\n".join(lines).rstrip() + "\n"


def format_markdown(payload: dict) -> str:
    parts = [
        "# 持仓股票 · 9 流派 66 评委",
        "",
        f"日期：{payload.get('as_of')}。规则引擎投票，不是大模型金句，也不是持牌投顾意见。ETF 不进评委。",
        "",
    ]
    for stock in payload.get("stocks") or []:
        parts.append(f"## {stock.get('name')}")
        if stock.get("status") == "error":
            parts.append(stock.get("error") or "失败")
            parts.append("")
            continue
        sig = stock.get("signal_distribution") or {}
        parts.append(
            f"{stock.get('n_judges')} 位评委 · 共识 **{stock.get('panel_consensus')}** · "
            f"看多 {sig.get('bullish', 0)}、中性 {sig.get('neutral', 0)}、"
            f"看空 {sig.get('bearish', 0)}、跳过 {sig.get('skip', 0)}。"
        )
        parts.append("")
        parts.append("| 流派 | 结论 | 分数 |")
        parts.append("| --- | --- | ---: |")
        for s in stock.get("schools") or []:
            score = s.get("score")
            score_s = "—" if score is None else (f"{score:.1f}" if isinstance(score, float) else str(score))
            parts.append(f"| {s.get('label')} | {s.get('verdict') or '—'} | {score_s} |")
        parts.append("")
        if stock.get("top_bear"):
            parts.append("偏空：" + "、".join(f"{i['name']} {i.get('score')}" for i in stock["top_bear"]))
        if stock.get("top_bull"):
            parts.append("偏多：" + "、".join(f"{i['name']} {i.get('score')}" for i in stock["top_bull"]))
        parts.append("")
    skipped = payload.get("skipped_etfs") or []
    if skipped:
        parts.append("篮子未跑评委：" + "、".join(s["name"] for s in skipped) + "。")
        parts.append("")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="对持仓里的股票跑 9 流派 66 评委（规则引擎，不大模型）。")
    parser.add_argument("--name", metavar="名称", default=None, help="只跑这一只股票")
    args = parser.parse_args(argv)

    payload = run_book_judges(only_name=args.name)
    path = write_judges_snapshot(payload)
    note = REPO_ROOT / "portfolio" / "analysis" / "judges-latest.md"
    dated = REPO_ROOT / "portfolio" / "analysis" / f"judges-{datetime.now().strftime('%Y-%m-%d')}.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    md = format_markdown(payload)
    note.write_text(md, encoding="utf-8")
    dated.write_text(md, encoding="utf-8")
    print(format_judges(payload))
    print(f"JSON {path}")
    print(f"笔记 {note}")
    print("不是持牌投顾意见。")
    errors = sum(1 for s in payload.get("stocks") or [] if s.get("status") == "error")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
