#!/usr/bin/env python3
"""行情 MCP server (stdio)。

把 ``fetch_quotes.py`` 的能力暴露成一个结构化 MCP 工具, 供 Cursor 等 MCP 客户端
自动调用。使用官方 ``mcp`` (FastMCP) SDK。

在 Cursor 中通过 ``.cursor/mcp.json`` 注册后, agent 可自动调用 ``get_quotes`` 工具。
本地手动运行(调试用)::

    python tools/quotes_mcp_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让本文件无论从哪个工作目录启动都能 import 到仓库根目录的 fetch_quotes。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# 注意: 以下两个 import 必须在上面的 sys.path 调整之后, 故不放到文件顶部。
from mcp.server.fastmcp import FastMCP

import fetch_quotes as fq

mcp = FastMCP("quotes")


def _quote_to_dict(q: fq.Quote, name_override: str | None = None) -> dict:
    return {
        "code": q.code,
        "name": name_override or q.name,
        "price": q.price,
        "prev_close": q.prev_close,
        "change": q.change,
        "change_percent": q.change_percent,
        "high": q.high,
        "low": q.low,
        "volume": q.volume,
        "time": q.time,
        "source": q.source,  # "腾讯" 或 "新浪"
    }


@mcp.tool()
def get_quotes(codes: list[str] | None = None, timeout: float = 10.0) -> dict:
    """拉取股票实时行情(腾讯优先、新浪兜底)。

    参数:
        codes: 标的代码列表, 如 ["sh600029", "hk01972"]。
               前缀: 上交所 sh、深交所 sz、港股 hk(补足 5 位, 如 hk01972)。
               省略时使用内置自选(南方航空A/太古地产H/兆易创新H/电力ETF/电网设备ETF)。
        timeout: 单次请求超时秒数。

    返回:
        {"quotes": [ {code,name,price,change,change_percent,high,low,volume,time,source}, ... ],
         "failed": [未取到的代码...]}
    """
    if codes:
        want = list(codes)
        # 显式传入代码时用数据源返回的真实名称。
        name_map: dict[str, str] = {}
    else:
        want = [code for _, code in fq.WATCHLIST]
        name_map = {code: name for name, code in fq.WATCHLIST}

    quotes, failed = fq.fetch_quotes(want, timeout=timeout)
    return {
        "quotes": [_quote_to_dict(q, name_map.get(q.code)) for q in quotes],
        "failed": failed,
    }


@mcp.tool()
def list_watchlist() -> list[dict]:
    """返回内置自选列表 (显示名 + 代码)。"""
    return [{"name": name, "code": code} for name, code in fq.WATCHLIST]


# 便于其它模块引用 (测试里用)。
__all__ = ["get_quotes", "list_watchlist", "mcp"]


def main() -> None:
    mcp.run()  # 默认 stdio 传输


if __name__ == "__main__":
    main()
