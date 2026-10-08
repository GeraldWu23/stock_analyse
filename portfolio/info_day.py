"""一天一只证券的客观信息。

目录是 data/info/<YYYY-MM-DD>/<代码>.json。
跟持仓类无关：不读份额，不改账本。
必填项缺值则 ready 为 false。分析前先看 ready，缺了就不要分析。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "info"

# 静态必填项。个股和 ETF 分开，缺任何一项都不算齐。
REQUIRED = {
    "stock": ("last_price", "prev_close", "financials", "kline"),
    "etf": (
        "last_price",
        "prev_close",
        "iopv",
        "premium_pct",
        "top_holdings",
        "holdings_report_date",
    ),
}


def field(value, as_of, source, error=None) -> dict:
    """一个指标：内容、时点、来源。没有内容时 value 用 null。"""
    item = {"value": _clean(value), "as_of": as_of, "source": source}
    if error:
        item["error"] = error
    return item


def missing_of(kind: str, fields: dict) -> list[str]:
    """必填项里 value 为空的名字。0 是有效数字，空列表和空对象算缺。"""
    if kind not in REQUIRED:
        raise ValueError(f"没有这种证券的必填项: {kind}")
    absent = []
    for key in REQUIRED[kind]:
        item = fields.get(key) or {}
        if item.get("value") in (None, "", [], {}):
            absent.append(key)
    return absent


def save(date: str, ticker: str, name: str, kind: str, fields: dict, root: Path | None = None) -> dict:
    """写成 data/info/<日期>/<代码>.json。ready 由必填项计算，不另传。"""
    absent = missing_of(kind, fields)
    record = {
        "date": date,
        "ticker": ticker,
        "name": name,
        "kind": kind,
        "ready": not absent,
        "missing": absent,
        "fields": fields,
    }
    folder = (root or DATA_DIR) / date
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{ticker}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def load(date: str, ticker: str, root: Path | None = None) -> dict:
    """读出某一天某一只。文件不存在就抛错，不当成空的已就绪。"""
    path = (root or DATA_DIR) / date / f"{ticker}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def universe(root: Path | None = None) -> list[dict]:
    """检查和分析的名单。读 data/info/universe.json，不读任何持仓账。"""
    path = (root or DATA_DIR) / "universe.json"
    return json.loads(path.read_text(encoding="utf-8"))["names"]


def write_collected_day(
    snapshot_path: Path,
    holdings_path: Path,
    raw_root: Path,
    date: str,
    root: Path | None = None,
) -> list[dict]:
    """把已采到的快照和财报写进注册目录。不重新下载，也不写份额。"""
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    book = json.loads(holdings_path.read_text(encoding="utf-8"))
    tickers = {row["name"]: row["ticker"] for row in book["holdings"]}
    written = []
    for position in snapshot["positions"]:
        ticker = tickers[position["name"]]
        if position["kind"] == "etf":
            fields = _etf_fields(position)
        else:
            raw = json.loads((raw_root / ticker / "raw_data.json").read_text(encoding="utf-8"))
            fields = _stock_fields(position, raw)
        written.append(save(date, ticker, position["name"], position["kind"], fields, root))
    return written


def _etf_fields(position: dict) -> dict:
    quote_time = position.get("quote_time")
    source = position.get("source")
    holdings = position.get("top_holdings") or []
    return {
        "last_price": field(position.get("last_price"), quote_time, source),
        "prev_close": field(position.get("previous_close"), quote_time, source),
        "iopv": field(position.get("iopv"), quote_time, source, _absent(position.get("iopv"), "行情源没有 IOPV")),
        "premium_pct": field(
            position.get("premium_pct"), quote_time, source, _absent(position.get("premium_pct"), "行情源没有溢折价")
        ),
        "top_holdings": field(
            holdings or None,
            None,
            "akshare:fund_portfolio_hold_em",
            None if holdings else "没有成分",
        ),
        "holdings_report_date": field(
            None,
            None,
            "akshare:fund_portfolio_hold_em",
            "采集时筛过季度，快照没有留下报告期",
        ),
    }


def _stock_fields(position: dict, raw: dict) -> dict:
    quote_time = position.get("quote_time")
    source = position.get("source")
    financials = raw["dimensions"]["1_financials"]
    kline = raw["dimensions"]["2_kline"]
    fin_data = financials.get("data") or {}
    kline_data = kline.get("data") or {}
    fin_ok = bool(fin_data.get("revenue_history") or fin_data.get("roe_history"))
    candles = kline_data.get("candles_60d") or []
    kline_as_of = candles[-1]["date"] if candles else None
    fin_error = fin_data.get("_abstract_error") or fin_data.get("_cash_flow_error")
    return {
        "last_price": field(position.get("last_price"), quote_time, source),
        "prev_close": field(position.get("previous_close"), quote_time, source),
        "financials": field(
            fin_data if fin_ok else None,
            raw.get("fetched_at"),
            financials.get("source"),
            None if fin_ok else (fin_error or "没有财报"),
        ),
        "kline": field(
            kline_data if (kline_data.get("kline_count") or candles) else None,
            kline_as_of,
            kline.get("source"),
        ),
    }


def _absent(value, message: str) -> str | None:
    return None if value is not None else message


def _clean(value):
    """NaN 不能进 JSON。空着，不当成一个数。"""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value
