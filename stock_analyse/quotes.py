"""行情抓取核心逻辑 (core market-quote fetching logic).

数据源使用 Yahoo Finance 的公开 chart 接口, 同时支持:
  - A 股: 上交所后缀 ``.SS`` (如 ``600519.SS`` 贵州茅台), 深交所后缀 ``.SZ``
  - 港股: 后缀 ``.HK`` (如 ``0700.HK`` 腾讯控股)
  - 美股: 直接使用代码 (如 ``AAPL``)
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Iterable

import requests

_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Yahoo 会对缺失 UA 的请求返回 429, 因此必须携带浏览器 UA。
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class QuoteError(RuntimeError):
    """抓取或解析行情失败时抛出。"""


@dataclasses.dataclass
class Quote:
    """单只标的的行情快照。"""

    symbol: str
    name: str | None
    currency: str | None
    price: float | None
    previous_close: float | None
    day_high: float | None
    day_low: float | None
    volume: int | None
    market_time: int | None

    @property
    def change(self) -> float | None:
        """相对前收盘的涨跌额。"""
        if self.price is None or self.previous_close is None:
            return None
        return self.price - self.previous_close

    @property
    def change_percent(self) -> float | None:
        """相对前收盘的涨跌幅 (百分比)。"""
        change = self.change
        if change is None or not self.previous_close:
            return None
        return change / self.previous_close * 100.0


def _parse_chart_payload(symbol: str, payload: dict) -> Quote:
    """把 Yahoo chart 接口的 JSON 解析为 :class:`Quote`。"""
    chart = payload.get("chart") or {}
    error = chart.get("error")
    if error:
        raise QuoteError(f"{symbol}: {error.get('description', error)}")

    results = chart.get("result") or []
    if not results:
        raise QuoteError(f"{symbol}: 接口未返回数据 (可能是无效代码)")

    meta = results[0].get("meta") or {}
    return Quote(
        symbol=meta.get("symbol", symbol),
        name=meta.get("longName") or meta.get("shortName"),
        currency=meta.get("currency"),
        price=meta.get("regularMarketPrice"),
        previous_close=meta.get("chartPreviousClose") or meta.get("previousClose"),
        day_high=meta.get("regularMarketDayHigh"),
        day_low=meta.get("regularMarketDayLow"),
        volume=meta.get("regularMarketVolume"),
        market_time=meta.get("regularMarketTime"),
    )


def fetch_quote(
    symbol: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 10.0,
    retries: int = 3,
    backoff: float = 1.5,
) -> Quote:
    """抓取单只标的的实时行情。

    对 429/5xx 采用指数退避重试, 提高在受限网络下的成功率。
    """
    symbol = symbol.strip()
    if not symbol:
        raise QuoteError("代码不能为空")

    owns_session = session is None
    session = session or requests.Session()
    url = _YAHOO_CHART_URL.format(symbol=symbol)

    last_error: Exception | None = None
    try:
        for attempt in range(retries):
            try:
                resp = session.get(
                    url,
                    headers=_DEFAULT_HEADERS,
                    params={"range": "1d", "interval": "1d"},
                    timeout=timeout,
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise QuoteError(f"{symbol}: HTTP {resp.status_code}")
                resp.raise_for_status()
                return _parse_chart_payload(symbol, resp.json())
            except (requests.RequestException, QuoteError, ValueError) as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(backoff * (2 ** attempt))
    finally:
        if owns_session:
            session.close()

    raise QuoteError(f"抓取 {symbol} 失败: {last_error}")


def fetch_quotes(
    symbols: Iterable[str],
    *,
    timeout: float = 10.0,
    retries: int = 3,
) -> list[Quote]:
    """批量抓取多只标的的行情, 复用同一个 HTTP 会话。"""
    session = requests.Session()
    quotes: list[Quote] = []
    try:
        for symbol in symbols:
            quotes.append(
                fetch_quote(symbol, session=session, timeout=timeout, retries=retries)
            )
    finally:
        session.close()
    return quotes
