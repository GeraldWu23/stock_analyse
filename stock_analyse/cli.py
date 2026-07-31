"""命令行入口: 打印一张行情表格。

用法::

    python -m stock_analyse 600519.SS 000001.SZ AAPL
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime, timezone

from .quotes import Quote, QuoteError, fetch_quote

_COLUMNS = ["代码", "名称", "现价", "涨跌", "涨跌幅", "最高", "最低", "成交量", "币种"]


def _fmt_num(value: object, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:,.{digits}f}"
    return str(value)


def _fmt_int(value: object) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}"


def _quote_to_row(quote: Quote) -> list[str]:
    change = quote.change
    pct = quote.change_percent
    return [
        quote.symbol,
        (quote.name or "-")[:12],
        _fmt_num(quote.price),
        (f"{change:+,.2f}" if change is not None else "-"),
        (f"{pct:+.2f}%" if pct is not None else "-"),
        _fmt_num(quote.day_high),
        _fmt_num(quote.day_low),
        _fmt_int(quote.volume),
        quote.currency or "-",
    ]


def _display_width(text: str) -> int:
    """按东亚宽字符占 2 列估算显示宽度, 使表格对齐。"""
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 0x2E7F else 1
    return width


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def render_table(quotes: Sequence[Quote]) -> str:
    rows = [_quote_to_row(q) for q in quotes]
    widths = [
        max(_display_width(_COLUMNS[i]), *(_display_width(r[i]) for r in rows))
        if rows
        else _display_width(_COLUMNS[i])
        for i in range(len(_COLUMNS))
    ]
    lines = [
        "  ".join(_pad(_COLUMNS[i], widths[i]) for i in range(len(_COLUMNS))),
        "  ".join("-" * widths[i] for i in range(len(_COLUMNS))),
    ]
    for row in rows:
        lines.append("  ".join(_pad(row[i], widths[i]) for i in range(len(_COLUMNS))))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stock_analyse",
        description="抓取并展示股票行情 (Yahoo Finance 数据源)",
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        default=["600519.SS", "000001.SZ", "AAPL"],
        help="股票代码, 支持 A股(.SS/.SZ)、港股(.HK)、美股。默认演示几只标的。",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="单次请求超时秒数")
    parser.add_argument("--retries", type=int, default=3, help="失败重试次数")
    args = parser.parse_args(argv)

    quotes: list[Quote] = []
    failures: list[str] = []
    for symbol in args.symbols:
        try:
            quotes.append(
                fetch_quote(symbol, timeout=args.timeout, retries=args.retries)
            )
        except QuoteError as exc:
            failures.append(str(exc))

    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"行情快照 @ {now}\n")
    if quotes:
        print(render_table(quotes))
    if failures:
        print("\n抓取失败:", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)

    return 0 if quotes and not failures else (0 if quotes else 1)


if __name__ == "__main__":
    raise SystemExit(main())
