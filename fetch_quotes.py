#!/usr/bin/env python3
"""行情脚本 fetch_quotes.py

拉取自选标的的实时行情:
  - 南方航空A   sh600029   (上交所 A 股)
  - 太古地产H   hk01972    (港股)
  - 兆易创新H   hk03986    (港股 H 股; 兆易创新 A+H 两地上市, A 股为 sh603986)
  - 大陆ETF     sh510300   (沪深300ETF 华泰柏瑞, 代表大陆宽基 ETF)

数据源: **腾讯 qt.gtimg.cn 优先, 新浪 hq.sinajs.cn 兜底**。
两个接口都返回 GBK 编码的文本; 新浪需要携带 Referer 头。

用法::

    python fetch_quotes.py                     # 拉取默认自选
    python fetch_quotes.py sh600029 hk01972    # 指定代码

代码前缀规则: 上交所 ``sh``、深交所 ``sz``、港股 ``hk`` (港股代码补足 5 位, 如 ``hk01972``)。
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from datetime import datetime, timezone

import requests

# 默认自选列表: (显示名, 代码)。可按需增删。
WATCHLIST: list[tuple[str, str]] = [
    ("南方航空A", "sh600029"),
    ("太古地产H", "hk01972"),
    # 兆易创新 A+H 两地上市: H 股为 hk03986 (A 股为 sh603986)。此处按需求取 H 股。
    ("兆易创新H", "hk03986"),
    # "大陆ETF": 取沪深300ETF(华泰柏瑞)作为大陆宽基 ETF 代表。
    ("大陆ETF", "sh510300"),
]

_TENCENT_URL = "https://qt.gtimg.cn/q={codes}"
_SINA_URL = "https://hq.sinajs.cn/list={codes}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    # 新浪接口校验来源, 缺失会返回 403。
    "Referer": "https://finance.sina.com.cn/",
}


@dataclasses.dataclass
class Quote:
    """归一化后的行情快照。"""

    code: str
    name: str
    price: float | None
    prev_close: float | None
    open: float | None
    high: float | None
    low: float | None
    volume: float | None  # 归一化为"股"
    time: str | None
    source: str  # "腾讯" 或 "新浪"

    @property
    def change(self) -> float | None:
        if self.price is None or self.prev_close is None:
            return None
        return self.price - self.prev_close

    @property
    def change_percent(self) -> float | None:
        chg = self.change
        if chg is None or not self.prev_close:
            return None
        return chg / self.prev_close * 100.0


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_hk(code: str) -> bool:
    return code.lower().startswith("hk")


def _http_get(url: str, timeout: float) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    # 两个接口均为 GBK 编码。
    resp.encoding = "gbk"
    return resp.text


# --------------------------- 腾讯解析 --------------------------- #
def _parse_tencent(code: str, payload: str) -> Quote | None:
    """解析形如 ``v_sh600029="1~名称~代码~现价~昨收~今开~...";`` 的一行。"""
    line = payload.strip()
    if "=" not in line:
        return None
    body = line.split("=", 1)[1].strip().strip(";").strip('"')
    fields = body.split("~")
    if len(fields) < 35 or not fields[3]:
        return None

    volume = _to_float(fields[6])
    if volume is not None and not _is_hk(code):
        volume *= 100  # A 股/ETF 腾讯成交量单位是"手", 换算成"股"

    raw_time = fields[30] if len(fields) > 30 else ""
    time_str = raw_time
    if raw_time.isdigit() and len(raw_time) == 14:  # yyyymmddHHMMSS
        time_str = (
            f"{raw_time[0:4]}-{raw_time[4:6]}-{raw_time[6:8]} "
            f"{raw_time[8:10]}:{raw_time[10:12]}:{raw_time[12:14]}"
        )

    return Quote(
        code=code,
        name=fields[1],
        price=_to_float(fields[3]),
        prev_close=_to_float(fields[4]),
        open=_to_float(fields[5]),
        high=_to_float(fields[33]),
        low=_to_float(fields[34]),
        volume=volume,
        time=time_str or None,
        source="腾讯",
    )


# --------------------------- 新浪解析 --------------------------- #
def _parse_sina(code: str, payload: str) -> Quote | None:
    """解析形如 ``var hq_str_sh600029="名称,今开,昨收,现价,...";`` 的一行。"""
    line = payload.strip()
    if '="' not in line:
        return None
    body = line.split('="', 1)[1].rstrip().rstrip(";").rstrip('"')
    fields = body.split(",")
    if len(fields) < 6 or not fields[0]:
        return None

    if _is_hk(code):
        # 港股: 英文名,中文名,今开,昨收,最高,最低,现价,涨跌,涨跌幅,买,卖,成交量,成交额,...,日期,时间
        if len(fields) < 12:
            return None
        return Quote(
            code=code,
            name=fields[1] or fields[0],
            price=_to_float(fields[6]),
            prev_close=_to_float(fields[3]),
            open=_to_float(fields[2]),
            high=_to_float(fields[4]),
            low=_to_float(fields[5]),
            volume=_to_float(fields[11]),
            time=(f"{fields[17]} {fields[18]}" if len(fields) > 18 else None),
            source="新浪",
        )

    # A 股/ETF: 名称,今开,昨收,现价,最高,最低,买一,卖一,成交量(股),成交额,...,日期,时间
    return Quote(
        code=code,
        name=fields[0],
        price=_to_float(fields[3]),
        prev_close=_to_float(fields[2]),
        open=_to_float(fields[1]),
        high=_to_float(fields[4]),
        low=_to_float(fields[5]),
        volume=_to_float(fields[8]) if len(fields) > 8 else None,
        time=(f"{fields[30]} {fields[31]}" if len(fields) > 31 else None),
        source="新浪",
    )


def _fetch_from(url_tmpl: str, codes: list[str], parser, timeout: float) -> dict[str, Quote]:
    """批量请求某个数据源, 返回 {code: Quote} (仅含解析成功的)。"""
    if not codes:
        return {}
    text = _http_get(url_tmpl.format(codes=",".join(codes)), timeout=timeout)
    result: dict[str, Quote] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 从 v_sh600029=... 或 var hq_str_sh600029=... 中取出代码。
        head = line.split("=", 1)[0]
        matched = next((c for c in codes if head.endswith(c)), None)
        if matched is None:
            continue
        quote = parser(matched, line)
        if quote is not None and quote.price is not None:
            result[matched] = quote
    return result


def fetch_quotes(codes: list[str], *, timeout: float = 10.0) -> tuple[list[Quote], list[str]]:
    """腾讯优先、新浪兜底地抓取一组代码。

    返回 ``(quotes, failed_codes)``。
    """
    quotes: dict[str, Quote] = {}

    # 1) 腾讯优先。
    try:
        quotes.update(_fetch_from(_TENCENT_URL, codes, _parse_tencent, timeout))
    except requests.RequestException as exc:
        print(f"[腾讯] 请求失败, 转用新浪兜底: {exc}", file=sys.stderr)

    # 2) 新浪兜底: 只补腾讯没拿到的代码。
    missing = [c for c in codes if c not in quotes]
    if missing:
        try:
            quotes.update(_fetch_from(_SINA_URL, missing, _parse_sina, timeout))
        except requests.RequestException as exc:
            print(f"[新浪] 兜底请求失败: {exc}", file=sys.stderr)

    ordered = [quotes[c] for c in codes if c in quotes]
    failed = [c for c in codes if c not in quotes]
    return ordered, failed


# --------------------------- 展示 --------------------------- #
_COLUMNS = ["代码", "名称", "现价", "涨跌", "涨跌幅", "最高", "最低", "成交量", "时间", "来源"]


def _display_width(text: str) -> int:
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def _row(q: Quote, name_override: str | None = None) -> list[str]:
    chg = q.change
    pct = q.change_percent
    return [
        q.code,
        (name_override or q.name or "-")[:10],
        f"{q.price:,.3f}" if q.price is not None else "-",
        f"{chg:+,.3f}" if chg is not None else "-",
        f"{pct:+.2f}%" if pct is not None else "-",
        f"{q.high:,.3f}" if q.high is not None else "-",
        f"{q.low:,.3f}" if q.low is not None else "-",
        f"{q.volume:,.0f}" if q.volume is not None else "-",
        q.time or "-",
        q.source,
    ]


def render_table(rows: list[list[str]]) -> str:
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
    for r in rows:
        lines.append("  ".join(_pad(r[i], widths[i]) for i in range(len(_COLUMNS))))
    return "\n".join(lines)


def print_snapshot(
    codes: list[str], name_map: dict[str, str], *, timeout: float
) -> tuple[list[Quote], list[str]]:
    """抓取一次并打印一张行情表, 返回 (quotes, failed)。"""
    quotes, failed = fetch_quotes(codes, timeout=timeout)

    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"行情快照 @ {now}\n")
    if quotes:
        print(render_table([_row(q, name_map.get(q.code)) for q in quotes]))
    if failed:
        print("\n未获取到行情:", ", ".join(failed), file=sys.stderr)
    # 立即刷新, 便于在管道/日志中实时查看。
    sys.stdout.flush()
    return quotes, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch_quotes.py",
        description="行情脚本: 腾讯优先、新浪兜底 (A股/港股/ETF)",
    )
    parser.add_argument("codes", nargs="*", help="标的代码, 如 sh600029 hk01972; 缺省则用内置自选")
    parser.add_argument("--timeout", type=float, default=10.0, help="请求超时秒数")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        metavar="秒",
        help="轮询间隔秒数; >0 则循环拉取 (每5分钟填 300)。默认 0 表示只拉一次。",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        metavar="次数",
        help="配合 --interval 使用: 最多拉取多少次; 0 表示无限循环, 直到 Ctrl+C。",
    )
    args = parser.parse_args(argv)

    if args.codes:
        watch = [(c, c) for c in args.codes]
    else:
        watch = WATCHLIST
    codes = [code for _, code in watch]
    name_map = {code: name for name, code in watch}

    # 单次模式。
    if args.interval <= 0:
        quotes, _ = print_snapshot(codes, name_map, timeout=args.timeout)
        return 0 if quotes else 1

    # 轮询模式。
    got_any = False
    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"===== 第 {iteration} 次 =====")
            quotes, _ = print_snapshot(codes, name_map, timeout=args.timeout)
            got_any = got_any or bool(quotes)
            if args.count and iteration >= args.count:
                break
            print(f"\n(等待 {args.interval:.0f} 秒后再次拉取, 按 Ctrl+C 结束)\n")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n已停止轮询。", file=sys.stderr)
    return 0 if got_any else 1

    return 0 if quotes else 1


if __name__ == "__main__":
    raise SystemExit(main())
