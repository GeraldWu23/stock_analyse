from __future__ import annotations

import json
from pathlib import Path

from portfolio.collector import (
    SIMULATED_HOLDINGS_JSON,
    collect_book,
    collect_position,
    daily_pnl,
    fetch_alt_quote,
    format_table,
    holding_pnl,
    load_holdings,
    mark_to_market,
    match_etf_row,
    parse_sina_quote,
    parse_tencent_quote,
    parse_ticker,
    position_kind,
    quote_from_etf_row,
    write_snapshot,
)

SAMPLE_HOLDINGS = {
    "account": "测试账户",
    "cash": {"account_cash_cny": 43452.12},
    "totals": {"hkd_to_cny": 0.84},
    "holdings": [
        {
            "name": "科创人工智能ETF易方达",
            "ticker": "588730.SH",
            "code": "588730",
            "type": "场内基金",
            "shares": 70000,
            "cost_price": 1.506,
            "last_price": 1.396,
            "currency": "CNY",
        },
        {
            "name": "南方航空",
            "ticker": "600029.SH",
            "code": "600029",
            "type": "股票",
            "shares": 12500,
            "cost_price": 5.181,
            "last_price": 5.00,
            "currency": "CNY",
        },
        {
            "name": "太古地产",
            "ticker": "01972.HK",
            "code": "01972",
            "type": "港股通",
            "shares": 1200,
            "cost_price": 19.865,
            "last_price": 24.64,
            "currency": "HKD",
        },
    ],
}


def test_real_and_assistant_simulated_books_stay_separate():
    real = load_holdings()
    simulated = load_holdings(SIMULATED_HOLDINGS_JSON)
    real_rows = {row["name"]: row for row in real["holdings"]}
    simulated_rows = {row["name"]: row for row in simulated["holdings"]}

    assert real["account"] == "普通账户"
    assert real["cash"]["account_cash_cny"] == 43452.12
    assert real_rows["南方航空"]["shares"] == 12500
    assert simulated["account_owner"] == "assistant"
    assert simulated["cash"]["account_cash_cny"] == 215970.75
    assert simulated_rows["美的集团"]["shares"] == 200
    assert simulated_rows["科创人工智能ETF易方达"]["shares"] == 49900
    assert simulated_rows["电网设备ETF国泰"]["shares"] == 66600
    assert simulated_rows["绿色电力ETF富国"]["shares"] == 42400
    assert simulated_rows["南方航空"]["shares"] == 3800
    assert "纳斯达克ETF华安" not in simulated_rows
    assert "电力ETF博时" in real_rows
    assert "电力ETF博时" not in simulated_rows


def test_etf_vs_stock_kind():
    assert position_kind(SAMPLE_HOLDINGS["holdings"][0]) == "etf"
    assert position_kind(SAMPLE_HOLDINGS["holdings"][1]) == "stock"
    assert position_kind(SAMPLE_HOLDINGS["holdings"][2]) == "stock"


def test_parse_ticker_in_project():
    assert parse_ticker("01972.HK") == ("01972", "HK")
    assert parse_ticker("600029.SH") == ("600029", "SH")


def test_mark_to_market_keeps_shares_sticky():
    assert mark_to_market(12500, 5.0) == 62500.0
    pnl = holding_pnl(12500, 5.181, 5.0)
    assert pnl["holding_pnl"] < 0


def test_daily_pnl_uses_previous_close_not_cost():
    pnl = daily_pnl(1000, 5.10, 5.00)
    assert pnl == {"today_pnl": 100.0, "today_pnl_pct": 2.0}
    assert daily_pnl(1000, 5.10, None)["today_pnl"] is None


def test_etf_premium_from_eastmoney_discount_column():
    q = quote_from_etf_row({
        "最新价": 2.456,
        "昨收": 2.400,
        "涨跌幅": 2.33,
        "IOPV实时估值": 2.2569,
        "基金折价率": -8.82,
        "名称": "纳斯达克ETF",
    })
    assert q["last_price"] == 2.456
    assert q["previous_close"] == 2.4
    assert q["change_pct"] == 2.33
    assert q["iopv"] == 2.2569
    assert q["premium_pct"] == 8.82
    assert q["discount_pct"] == -8.82


def test_match_etf_row_by_code():
    table = [{"代码": "588730", "最新价": 1.4, "IOPV实时估值": 1.4, "基金折价率": 0.0, "名称": "科创人工智能ETF"}]
    row = match_etf_row(table, "588730")
    assert row is not None
    assert quote_from_etf_row(row)["last_price"] == 1.4


def test_collector_module_does_not_touch_plugin():
    from pathlib import Path
    src = Path("portfolio/collector.py").read_text(encoding="utf-8")
    assert "stock-deep-analyzer" not in src
    assert "run_pipeline" not in src
    assert "collect_only" not in src


def test_collect_book_mocked_no_llm(tmp_path: Path):
    etf_table = [{
        "代码": "588730",
        "最新价": 1.40,
        "昨收": 1.39,
        "涨跌幅": 0.72,
        "IOPV实时估值": 1.39,
        "基金折价率": -0.72,
        "名称": "科创人工智能ETF易方达",
    }]

    def fake_basic(ticker: str):
        if ticker.endswith("HK"):
            return {"price": 24.8, "previous_close": 24.5, "name": "太古地产", "pb": 0.52}
        return {
            "price": 5.02,
            "previous_close": 5.00,
            "name": "南方航空",
            "pe_ttm": -12.26,
        }

    class FakeAk:
        def fund_etf_spot_em(self):
            import pandas as pd
            return pd.DataFrame([{
                "代码": "588730",
                "最新价": 1.40,
                "昨收": 1.39,
                "涨跌幅": 0.72,
                "IOPV实时估值": 1.39,
                "基金折价率": -0.72,
                "名称": "科创人工智能ETF易方达",
            }])

        def fund_portfolio_hold_em(self, symbol, date=None):
            import pandas as pd
            return pd.DataFrame([
                {"季度": "2026年2季度股票投资明细", "股票名称": "芯原股份", "占净值比例": 12.1, "股票代码": "688521"},
            ])

        def stock_bid_ask_em(self, symbol):
            raise AssertionError("injected fetch_basic_fn should be used for stocks")

    snap = collect_book(
        SAMPLE_HOLDINGS,
        ak_module=FakeAk(),
        fetch_basic_fn=fake_basic,
    )
    etf = collect_position(
        SAMPLE_HOLDINGS["holdings"][0],
        etf_table=etf_table,
        quotes_only=False,
        ak_module=FakeAk(),
    )
    assert snap["llm"] is False
    assert snap["account"] == "测试账户"
    assert snap["mode"] == "collect"
    names = [p["name"] for p in snap["positions"]]
    assert "南方航空" in names
    assert "科创人工智能ETF易方达" in names
    csa = next(p for p in snap["positions"] if p["name"] == "南方航空")
    assert csa["last_price"] == 5.02
    assert csa["shares"] == 12500
    assert csa["today_pnl"] == 250.0
    assert "plugin_collect" not in csa
    assert etf["kind"] == "etf"
    assert etf["last_price"] == 1.4
    assert etf["today_pnl"] == 700.0
    assert etf["top_holdings"][0]["name"] == "芯原股份"

    path = write_snapshot(snap, collected_dir=tmp_path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["llm"] is False
    table = format_table(snap)
    assert "南方航空" in table
    assert "600029" not in table
    assert "名称 | 今日盈亏 | 成本价 | 现价 | 持仓金额 | 持仓量 | 仓位" in table
    assert "现金：" in table
    assert "总资产：" in table


def test_quotes_only_skips_baskets():
    class Ak:
        def fund_etf_spot_em(self):
            import pandas as pd
            return pd.DataFrame([{
                "代码": "588730", "最新价": 1.41, "IOPV实时估值": 1.40, "基金折价率": -0.71,
            }])

        def fund_portfolio_hold_em(self, symbol, date=None):
            raise AssertionError("quotes-only must not pull baskets")

    snap = collect_book(
        SAMPLE_HOLDINGS,
        quotes_only=True,
        ak_module=Ak(),
        fetch_basic_fn=lambda t: {"price": 5.0, "name": "x"},
    )
    assert snap["mode"] == "quotes-only"
    assert snap["llm"] is False
    etf = next(p for p in snap["positions"] if p["kind"] == "etf")
    assert "top_holdings" not in etf


def test_only_name_filters_row():
    snap = collect_book(
        SAMPLE_HOLDINGS,
        only_name="南方航空",
        quotes_only=True,
        fetch_basic_fn=lambda t: {"price": 5.01},
        ak_module=type("Ak", (), {"fund_etf_spot_em": lambda self: []})(),
    )
    assert len(snap["positions"]) == 1
    assert snap["positions"][0]["name"] == "南方航空"
    assert snap["positions"][0]["shares"] == 12500


def test_fund_basket_tries_year_then_picks_latest_quarter():
    from datetime import datetime
    from portfolio.collector import fetch_fund_basket

    class Ak:
        def fund_portfolio_hold_em(self, symbol, date=None):
            import pandas as pd
            if date == str(datetime.now().year):
                return pd.DataFrame([
                    {"季度": "2026年1季度股票投资明细", "股票名称": "旧持仓", "占净值比例": 9.0, "股票代码": "1"},
                    {"季度": "2026年2季度股票投资明细", "股票名称": "芯原股份", "占净值比例": 10.16, "股票代码": "688521"},
                    {"季度": "2026年2季度股票投资明细", "股票名称": "寒武纪", "占净值比例": 10.10, "股票代码": "688256"},
                ])
            return pd.DataFrame()

    rows = fetch_fund_basket("588730", ak_module=Ak())
    assert [r["name"] for r in rows] == ["芯原股份", "寒武纪"]


def _tencent_etf_text() -> str:
    fields = [""] * 40
    fields[1] = "科创人工智能ETF易方达"
    fields[2] = "588730"
    fields[3] = "1.514"
    fields[4] = "1.519"
    fields[30] = "20260923103952"
    fields[32] = "-0.33"
    body = "~".join(fields) + "~-0.01~1.5142~-1.43~0.00~1.5181~CNY~0"
    return f'v_sh588730="{body}";'


def test_parse_tencent_etf_quote_includes_iopv():
    quote = parse_tencent_quote(_tencent_etf_text(), "588730", "SH", kind="etf")
    assert quote["last_price"] == 1.514
    assert quote["previous_close"] == 1.519
    assert quote["change_pct"] == -0.33
    assert quote["iopv"] == 1.5142
    assert quote["premium_pct"] == round((1.514 / 1.5142 - 1.0) * 100.0, 2)
    assert quote["quote_at"] == "20260923103952"
    assert quote["source"].startswith("tencent:qt:")


def test_parse_sina_a_share_quote():
    text = 'var hq_str_sh600029="南方航空,4.97,4.96,4.97,5.00,4.96,4.97,4.98,100,1000,2026-09-23,10:40:00,00,";'
    quote = parse_sina_quote(text, "600029", "SH")
    assert quote["last_price"] == 4.97
    assert quote["previous_close"] == 4.96
    assert quote["name"] == "南方航空"


def test_etf_502_uses_tencent_instead_of_ledger(monkeypatch):
    monkeypatch.setattr(
        "portfolio.collector.fetch_alt_quote",
        lambda code, market, kind="stock": parse_tencent_quote(_tencent_etf_text(), code, market, kind=kind),
    )
    position = collect_position(
        SAMPLE_HOLDINGS["holdings"][0],
        etf_table=[],
        quotes_only=True,
    )
    assert position["last_price"] == 1.514
    assert position["last_price"] != 1.396
    assert position["previous_close"] == 1.519
    assert position["today_pnl"] == round((1.514 - 1.519) * 70000, 2)
    assert position["status"] == "ok"
    assert position["quote_supplement"].startswith("tencent:qt:")
    assert position.get("needs_web_search") is not True


def test_etf_502_ledger_only_after_tencent_and_sina_fail(monkeypatch):
    monkeypatch.setattr(
        "portfolio.collector.fetch_alt_quote",
        lambda code, market, kind="stock": {
            "last_price": None,
            "needs_web_search": True,
            "alt_errors": ["tencent:HTTPError", "sina:HTTPError"],
            "source": "unavailable",
        },
    )
    position = collect_position(
        SAMPLE_HOLDINGS["holdings"][0],
        etf_table=[],
        quotes_only=True,
    )
    assert position["last_price"] == 1.396
    assert position["status"] == "quote_fallback_ledger"
    assert position["needs_web_search"] is True
    table = format_table({
        "as_of": "t",
        "account": "测试",
        "mode": "quotes-only",
        "llm": False,
        "positions": [position],
        "summary": {
            "securities_cny": 1,
            "cash_cny": 0,
            "total_assets_cny": 1,
            "today_pnl_cny": 0,
            "cash_weight_pct": 0,
            "today_pnl_missing": [position["name"]],
        },
    })
    assert "需上网核对" in table
    assert "科创人工智能ETF易方达" in table


def test_fetch_alt_quote_order_is_tencent_then_sina(monkeypatch):
    calls = []

    def fake_http(url, referer=None):
        calls.append(url)
        if "gtimg" in url:
            raise RuntimeError("502")
        return 'var hq_str_sh588730="科创人工智能ETF易方达,1.517,1.519,1.514,1.527,1.508";'

    monkeypatch.setattr("portfolio.collector._http_text", fake_http)
    quote = fetch_alt_quote("588730", "SH", kind="etf")
    assert calls[0].startswith("https://qt.gtimg.cn/q=sh588730")
    assert calls[1].startswith("http://hq.sinajs.cn/list=sh588730")
    assert quote["last_price"] == 1.514
    assert quote["needs_web_search"] is True
    assert quote["iopv_missing"] is True
