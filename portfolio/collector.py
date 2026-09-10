"""Collect market data for the personal book. No LLM, no 65-judge on ETFs.

Writes:
  - plugin `.cache/{ticker}/raw_data.json` for stocks (UZI collect-only)
  - `portfolio/collected/{date}.json` snapshot for the whole book
  - ETF baskets + quotes (price, IOPV, premium) without the equity pipeline
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
HOLDINGS_JSON = REPO_ROOT / "portfolio" / "holdings.json"
COLLECTED_DIR = REPO_ROOT / "portfolio" / "collected"
PLUGIN_SCRIPTS = (
    REPO_ROOT / ".cursor" / "plugins" / "stock-deep-analyzer" / "skills" / "deep-analysis" / "scripts"
)
PLUGIN_ROOT = REPO_ROOT / ".cursor" / "plugins" / "stock-deep-analyzer"

FUND_TYPES = {"场内基金", "ETF", "LOF"}
STOCK_TYPES = {"股票", "港股通"}


def load_holdings(path: Path | None = None) -> dict:
    target = path or HOLDINGS_JSON
    return json.loads(target.read_text(encoding="utf-8"))


def position_kind(row: dict) -> str:
    """stock | etf. ETFs are baskets; never send them through the 65-judge pipeline."""
    type_name = (row.get("type") or "").strip()
    if type_name in FUND_TYPES:
        return "etf"
    ticker = str(row.get("ticker") or row.get("code") or "")
    code = str(row.get("code") or "").strip()
    if not code and ticker:
        code = ticker.split(".")[0]
    if len(code) == 6 and code.isdigit():
        if code.startswith(("50", "51", "52", "56", "58", "159")):
            return "etf"
    return "stock"


def mark_to_market(shares: float, last_price: float | None) -> float | None:
    if last_price is None:
        return None
    return round(float(shares) * float(last_price), 2)


def holding_pnl(shares: float, cost: float | None, last_price: float | None) -> dict:
    if cost is None or last_price is None:
        return {"holding_pnl": None, "holding_pnl_pct": None}
    pnl = (float(last_price) - float(cost)) * float(shares)
    cost_total = float(cost) * float(shares)
    pct = (pnl / cost_total * 100.0) if cost_total else None
    return {
        "holding_pnl": round(pnl, 2),
        "holding_pnl_pct": None if pct is None else round(pct, 2),
    }


def _num(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").replace("亿", "").strip())
    except (TypeError, ValueError):
        return None


def _first_col(row: dict, names: tuple[str, ...]) -> Any:
    lower = {str(k).strip(): v for k, v in row.items()}
    for name in names:
        if name in lower:
            return lower[name]
    folded = {k.lower(): v for k, v in lower.items()}
    for name in names:
        if name.lower() in folded:
            return folded[name.lower()]
    return None


def fetch_etf_spot_table(ak_module: Any | None = None) -> list[dict]:
    """One East-Money ETF spot pull. Empty list on failure (never raises)."""
    ak = ak_module
    if ak is None:
        try:
            import akshare as ak  # type: ignore
        except ImportError:
            return []
    try:
        df = ak.fund_etf_spot_em()
    except Exception:
        return []
    if df is None or getattr(df, "empty", True):
        return []
    return df.to_dict("records")


def quote_from_etf_row(row: dict) -> dict:
    price = _num(_first_col(row, ("最新价", "最新", "close", "price")))
    iopv = _num(_first_col(row, ("IOPV实时净值", "IOPV", "净值", "实时净值")))
    premium = _num(_first_col(row, ("基金折溢价率", "折溢价率", "折价率", "溢价率")))
    if premium is None and price is not None and iopv not in (None, 0):
        premium = round((price / iopv - 1.0) * 100.0, 2)
    return {
        "last_price": price,
        "iopv": iopv,
        "premium_pct": premium,
        "volume": _num(_first_col(row, ("成交量", "volume"))),
        "amount": _num(_first_col(row, ("成交额", "amount"))),
        "name": str(_first_col(row, ("名称", "name")) or "") or None,
    }


def match_etf_row(table: list[dict], code6: str) -> dict | None:
    code6 = str(code6).zfill(6)
    for row in table:
        raw = _first_col(row, ("代码", "code", "基金代码"))
        if raw is None:
            continue
        got = str(raw).split(".")[0].zfill(6)
        if got == code6:
            return row
    return None


def fetch_fund_basket(code6: str, top_n: int = 10, ak_module: Any | None = None) -> list[dict]:
    """Latest disclosed top holdings. Names only in the output rows."""
    ak = ak_module
    if ak is None:
        try:
            import akshare as ak  # type: ignore
        except ImportError:
            return []
    try:
        df = ak.fund_portfolio_hold_em(symbol=str(code6))
    except Exception:
        return []
    if df is None or getattr(df, "empty", True):
        return []
    if "季度" in df.columns:
        latest = df["季度"].iloc[0]
        df = df[df["季度"] == latest]
    rows = []
    for i, rec in enumerate(df.head(top_n).to_dict("records"), start=1):
        name = str(_first_col(rec, ("股票名称", "name")) or "").strip()
        pct = _num(_first_col(rec, ("占净值比例", "比例", "weight")))
        code = str(_first_col(rec, ("股票代码", "code")) or "").strip()
        if not name:
            continue
        rows.append({
            "rank": i,
            "name": name,
            "weight_pct": pct,
            "code": code or None,
        })
    return rows


def fetch_stock_quote(ticker: str, fetch_basic_fn: Callable | None = None) -> dict:
    """Live quote for a stock via the plugin data_sources layer."""
    if fetch_basic_fn is None:
        from lib.market_router import parse_ticker
        from lib import data_sources as ds
        fetch_basic_fn = lambda t: ds.fetch_basic(parse_ticker(t))
    data = fetch_basic_fn(ticker) or {}
    return {
        "last_price": _num(data.get("price")),
        "name": data.get("name"),
        "pe_ttm": _num(data.get("pe_ttm")),
        "pb": _num(data.get("pb")),
        "market_cap": data.get("market_cap"),
        "change_pct": _num(data.get("change_pct")),
        "source": "plugin:fetch_basic",
    }


@contextmanager
def plugin_scripts_cwd() -> Iterator[None]:
    prev = Path.cwd()
    scripts = str(PLUGIN_SCRIPTS)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    os.chdir(scripts)
    try:
        yield
    finally:
        os.chdir(prev)


def collect_stock_raw(ticker: str, resume: bool = True) -> dict:
    """Run UZI collect-only (raw_data.json). Does not call an LLM or assemble HTML."""
    os.environ.setdefault("UZI_NO_AUTO_OPEN", "1")
    os.environ.setdefault("UZI_CLI_ONLY", "1")
    os.environ.setdefault("UZI_DEPTH", "lite")
    os.environ.setdefault("UZI_DISABLE_GLOBAL_PEERS", "1")
    with plugin_scripts_cwd():
        from lib.pipeline.run import run_pipeline
        path = run_pipeline(ticker, resume=resume, collect_only=True)
    return {
        "status": "ok",
        "raw_data": str(path),
        "llm": False,
    }


def collect_position(
    row: dict,
    *,
    etf_table: list[dict] | None = None,
    quotes_only: bool = False,
    resume: bool = True,
    ak_module: Any | None = None,
    fetch_basic_fn: Callable | None = None,
    collect_stock_fn: Callable | None = None,
) -> dict:
    name = row["name"]
    ticker = row["ticker"]
    code = str(row.get("code") or ticker.split(".")[0])
    shares = float(row["shares"])
    cost = row.get("cost_price")
    kind = position_kind(row)
    out: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "shares": shares,
        "cost_price": cost,
        "currency": row.get("currency"),
        "llm": False,
        "status": "ok",
    }

    if kind == "etf":
        table = etf_table if etf_table is not None else fetch_etf_spot_table(ak_module)
        match = match_etf_row(table, code)
        quote = quote_from_etf_row(match) if match else {}
        last = quote.get("last_price")
        if last is None:
            last = row.get("last_price")
            out["status"] = "quote_fallback_ledger"
        out.update(quote)
        out["last_price"] = last
        out["market_value"] = mark_to_market(shares, last)
        out.update(holding_pnl(shares, cost, last))
        if not quotes_only:
            try:
                out["top_holdings"] = fetch_fund_basket(code, ak_module=ak_module)
            except Exception as exc:
                out["top_holdings"] = []
                out["basket_error"] = f"{type(exc).__name__}: {exc}"[:160]
                out["status"] = "partial"
        return out

    # stock
    quote: dict = {}
    try:
        quote = fetch_stock_quote(ticker, fetch_basic_fn=fetch_basic_fn)
    except Exception as exc:
        out["quote_error"] = f"{type(exc).__name__}: {exc}"[:160]
        out["status"] = "quote_fallback_ledger"
    last = quote.get("last_price") if quote.get("last_price") is not None else row.get("last_price")
    out.update({k: v for k, v in quote.items() if k != "name" or v})
    out["last_price"] = last
    out["market_value"] = mark_to_market(shares, last)
    out.update(holding_pnl(shares, cost, last))
    if not quotes_only:
        fn = collect_stock_fn or collect_stock_raw
        try:
            collected = fn(ticker, resume=resume)
            out["plugin_collect"] = collected
        except Exception as exc:
            out["plugin_collect"] = {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:200],
            }
            out["status"] = "partial"
    return out


def collect_book(
    holdings: dict | None = None,
    *,
    only_name: str | None = None,
    quotes_only: bool = False,
    resume: bool = True,
    ak_module: Any | None = None,
    fetch_basic_fn: Callable | None = None,
    collect_stock_fn: Callable | None = None,
) -> dict:
    scripts = str(PLUGIN_SCRIPTS)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)

    book = holdings or load_holdings()
    rows = list(book.get("holdings") or [])
    if only_name:
        needle = only_name.strip()
        rows = [r for r in rows if r.get("name") == needle or r.get("ticker") == needle]
        if not rows:
            raise ValueError(f"持仓里没有叫 {only_name!r} 的标的")

    etf_table: list[dict] = []
    if any(position_kind(r) == "etf" for r in rows):
        etf_table = fetch_etf_spot_table(ak_module)

    positions = [
        collect_position(
            row,
            etf_table=etf_table,
            quotes_only=quotes_only,
            resume=resume,
            ak_module=ak_module,
            fetch_basic_fn=fetch_basic_fn,
            collect_stock_fn=collect_stock_fn,
        )
        for row in rows
    ]
    cash = (book.get("cash") or {}).get("account_cash_cny")
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "quotes-only" if quotes_only else "collect-only",
        "llm": False,
        "shares_are_sticky": True,
        "cash_cny": cash,
        "positions": positions,
        "ok": sum(1 for p in positions if p.get("status") == "ok"),
        "partial": sum(1 for p in positions if p.get("status") == "partial"),
        "failed": sum(1 for p in positions if p.get("status") not in ("ok", "partial", "quote_fallback_ledger")),
    }


def write_snapshot(snapshot: dict, collected_dir: Path | None = None) -> Path:
    dest = collected_dir or COLLECTED_DIR
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    path = dest / f"{stamp}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    latest = dest / "latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def format_table(snapshot: dict) -> str:
    lines = [
        f"采集 {snapshot.get('as_of')} · 模式 {snapshot.get('mode')} · 大模型={snapshot.get('llm')}",
        f"{'名称':<16} {'类型':<6} {'现价':>10} {'市值':>12} {'状态'}",
        "-" * 56,
    ]
    for p in snapshot.get("positions") or []:
        price = p.get("last_price")
        mv = p.get("market_value")
        price_s = "—" if price is None else f"{price:.3f}"
        mv_s = "—" if mv is None else f"{mv:,.0f}"
        extra = ""
        if p.get("kind") == "etf" and p.get("premium_pct") is not None:
            extra = f"  溢价{p['premium_pct']:.1f}%"
        lines.append(
            f"{p.get('name', ''):<16} {p.get('kind', ''):<6} {price_s:>10} {mv_s:>12} {p.get('status')}{extra}"
        )
    return "\n".join(lines)
