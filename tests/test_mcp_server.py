"""MCP 工具的离线测试 (mock 掉网络请求)。"""

from __future__ import annotations

import fetch_quotes as fq
from tools import quotes_mcp_server as server


def _fake_quote(code: str, name: str) -> fq.Quote:
    return fq.Quote(
        code=code,
        name=name,
        price=100.0,
        prev_close=90.0,
        open=95.0,
        high=105.0,
        low=88.0,
        volume=12345.0,
        time="2026-07-31 10:00:00",
        source="腾讯",
    )


def test_list_watchlist_matches_module_watchlist():
    wl = server.list_watchlist()
    assert {(e["name"], e["code"]) for e in wl} == set(fq.WATCHLIST)


def test_get_quotes_default_uses_friendly_names(monkeypatch):
    def fake_fetch(codes, timeout=10.0):
        return [_fake_quote(c, "源站名") for c in codes], []

    monkeypatch.setattr(server.fq, "fetch_quotes", fake_fetch)
    out = server.get_quotes()  # 用内置自选
    codes = [q["code"] for q in out["quotes"]]
    assert codes == [c for _, c in fq.WATCHLIST]
    # 默认自选应使用显示名, 而非源站名。
    names = {q["code"]: q["name"] for q in out["quotes"]}
    assert names["hk03986"] == "兆易创新H"
    assert out["failed"] == []
    # 含派生字段。
    first = out["quotes"][0]
    assert first["change"] == 10.0
    assert round(first["change_percent"], 4) == round(10.0 / 90.0 * 100, 4)


def test_get_quotes_explicit_codes_use_source_name(monkeypatch):
    def fake_fetch(codes, timeout=10.0):
        return [_fake_quote(c, "源站名") for c in codes], []

    monkeypatch.setattr(server.fq, "fetch_quotes", fake_fetch)
    out = server.get_quotes(["sh600029"])
    assert out["quotes"][0]["name"] == "源站名"


def test_mcp_server_registers_tools():
    # FastMCP 实例应能创建, 且工具函数可直接调用。
    assert server.mcp is not None
    assert callable(server.get_quotes)
    assert callable(server.list_watchlist)
