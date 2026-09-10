from __future__ import annotations

import json
from pathlib import Path

from portfolio.collector import (
    collect_book,
    collect_position,
    format_table,
    holding_pnl,
    mark_to_market,
    match_etf_row,
    parse_ticker,
    position_kind,
    quote_from_etf_row,
    write_snapshot,
)

SAMPLE_HOLDINGS = {
    "cash": {"account_cash_cny": 43452.12},
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


def test_etf_premium_from_eastmoney_discount_column():
    q = quote_from_etf_row({
        "最新价": 2.456,
        "IOPV实时估值": 2.2569,
        "基金折价率": -8.82,
        "名称": "纳斯达克ETF",
    })
    assert q["last_price"] == 2.456
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
        "IOPV实时估值": 1.39,
        "基金折价率": -0.72,
        "名称": "科创人工智能ETF易方达",
    }]

    def fake_basic(ticker: str):
        if ticker.endswith("HK"):
            return {"price": 24.8, "name": "太古地产", "pb": 0.52}
        return {"price": 5.02, "name": "南方航空", "pe_ttm": -12.26}

    class FakeAk:
        def fund_etf_spot_em(self):
            import pandas as pd
            return pd.DataFrame([{
                "代码": "588730",
                "最新价": 1.40,
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
    assert snap["mode"] == "collect"
    names = [p["name"] for p in snap["positions"]]
    assert "南方航空" in names
    assert "科创人工智能ETF易方达" in names
    csa = next(p for p in snap["positions"] if p["name"] == "南方航空")
    assert csa["last_price"] == 5.02
    assert csa["shares"] == 12500
    assert "plugin_collect" not in csa
    assert etf["kind"] == "etf"
    assert etf["last_price"] == 1.4
    assert etf["top_holdings"][0]["name"] == "芯原股份"

    path = write_snapshot(snap, collected_dir=tmp_path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["llm"] is False
    table = format_table(snap)
    assert "南方航空" in table
    assert "600029" not in table


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
