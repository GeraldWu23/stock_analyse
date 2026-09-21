"""Domestic last/prev-close quotes: Tencent first, Sina fallback.

Used by `portfolio.collect` for HK as the preferred last/prev-close source,
and for A-share / ETF last/prev-close when East Money is empty.

Does not replace ETF IOPV, premium, or baskets. No Yahoo. No LLM.
"""
from __future__ import annotations

from typing import Any, Callable

import requests

_TENCENT_URL = "https://qt.gtimg.cn/q={codes}"
_SINA_URL = "https://hq.sinajs.cn/list={codes}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.sina.com.cn/",
}


def ticker_to_cn_code(ticker: str) -> str:
    """01972.HK → hk01972; 600029.SH → sh600029; 159632.SZ → sz159632."""
    text = str(ticker).strip().upper()
    if "." in text:
        code, market = text.split(".", 1)
    else:
        code, market = text, "SH"
    market = market.upper()
    if market == "HK":
        return "hk" + str(int(code) if code.isdigit() else code).zfill(5)
    body = code.zfill(6) if code.isdigit() else code
    if market in {"SZ", "SHE"}:
        return "sz" + body
    return "sh" + body


def _is_hk(code: str) -> bool:
    return code.lower().startswith("hk")


def tencent_request_code(code: str) -> str:
    """HK uses r_hk for near-real-time; A-share/ETF stay as-is."""
    return f"r_{code}" if _is_hk(code) else code


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _http_get(url: str, timeout: float) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "gbk"
    return resp.text


def parse_tencent_line(code: str, payload: str) -> dict | None:
    line = payload.strip()
    if "=" not in line:
        return None
    body = line.split("=", 1)[1].strip().strip(";").strip('"')
    fields = body.split("~")
    if len(fields) < 35 or not fields[3]:
        return None
    last = _to_float(fields[3])
    previous_close = _to_float(fields[4])
    change_pct = None
    if last is not None and previous_close not in (None, 0):
        change_pct = round((last / previous_close - 1.0) * 100.0, 2)
    raw_time = fields[30] if len(fields) > 30 else ""
    time_str = raw_time
    if raw_time.isdigit() and len(raw_time) == 14:
        time_str = (
            f"{raw_time[0:4]}-{raw_time[4:6]}-{raw_time[6:8]} "
            f"{raw_time[8:10]}:{raw_time[10:12]}:{raw_time[12:14]}"
        )
    return {
        "last_price": last,
        "previous_close": previous_close,
        "change_pct": change_pct,
        "name": fields[1] or None,
        "quote_time": time_str or None,
        "source": "tencent:qt.gtimg.cn",
    }


def parse_sina_line(code: str, payload: str) -> dict | None:
    line = payload.strip()
    if '="' not in line:
        return None
    body = line.split('="', 1)[1].rstrip().rstrip(";").rstrip('"')
    fields = body.split(",")
    if len(fields) < 6 or not fields[0]:
        return None
    if _is_hk(code):
        if len(fields) < 12:
            return None
        last = _to_float(fields[6])
        previous_close = _to_float(fields[3])
        name = fields[1] or fields[0]
        time_str = f"{fields[17]} {fields[18]}" if len(fields) > 18 else None
    else:
        last = _to_float(fields[3])
        previous_close = _to_float(fields[2])
        name = fields[0]
        time_str = f"{fields[30]} {fields[31]}" if len(fields) > 31 else None
    if last is None:
        return None
    change_pct = None
    if previous_close not in (None, 0):
        change_pct = round((last / previous_close - 1.0) * 100.0, 2)
    return {
        "last_price": last,
        "previous_close": previous_close,
        "change_pct": change_pct,
        "name": name or None,
        "quote_time": time_str,
        "source": "sina:hq.sinajs.cn",
    }


def _fetch_from(
    url_tmpl: str,
    codes: list[str],
    parser: Callable[[str, str], dict | None],
    timeout: float,
    request_code: Callable[[str], str] | None = None,
) -> dict[str, dict]:
    if not codes:
        return {}
    req_codes = [request_code(c) if request_code else c for c in codes]
    text = _http_get(url_tmpl.format(codes=",".join(req_codes)), timeout=timeout)
    result: dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        head = line.split("=", 1)[0]
        matched = next((c for c in codes if head.endswith(c)), None)
        if matched is None:
            continue
        quote = parser(matched, line)
        if quote is not None and quote.get("last_price") is not None:
            result[matched] = quote
    return result


def fetch_cn_quotes(codes: list[str], *, timeout: float = 10.0) -> dict[str, dict]:
    """Tencent first (HK via r_ prefix), Sina fills gaps. Never raises."""
    quotes: dict[str, dict] = {}
    if not codes:
        return quotes
    try:
        quotes.update(
            _fetch_from(
                _TENCENT_URL,
                codes,
                parse_tencent_line,
                timeout,
                request_code=tencent_request_code,
            )
        )
    except (requests.RequestException, UnicodeError, ValueError):
        pass
    missing = [c for c in codes if c not in quotes]
    if missing:
        try:
            quotes.update(_fetch_from(_SINA_URL, missing, parse_sina_line, timeout))
        except (requests.RequestException, UnicodeError, ValueError):
            pass
    return quotes


def fetch_cn_quote(code: str, *, timeout: float = 10.0) -> dict | None:
    return fetch_cn_quotes([code], timeout=timeout).get(code)
