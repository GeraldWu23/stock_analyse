from __future__ import annotations

import json
from pathlib import Path

from portfolio.engine import INVESTORS, assert_count, generate_panel, score_dimensions
from portfolio.judges import run_book_judges, score_stock_from_cache
from portfolio.stock_raw import assemble_raw, collect_stock_raw, write_raw_data

FIXTURE = Path(__file__).parent / "fixtures" / "csair_raw.json"


def test_kline_from_records_sets_stage():
    from portfolio.stock_raw import _kline_from_records

    records = []
    price = 5.0
    for i in range(260):
        price = price * 0.999  # drifting down → stage 4
        records.append({
            "日期": f"2025-01-{(i % 28) + 1:02d}",
            "开盘": price,
            "最高": price + 0.02,
            "最低": price - 0.02,
            "收盘": price,
            "成交量": 1000,
        })
    out = _kline_from_records(records)
    assert out["kline_count"] == 260
    assert "Stage" in out["stage"] or out["stage"] == "—"
    assert out["kline_stats"].get("max_drawdown")


def test_engine_has_66_judges():
    assert_count()
    assert len(INVESTORS) == 66
    groups = {i["group"] for i in INVESTORS}
    assert groups == set("ABCDEFGHI")


def test_fixture_panel_scores_csair_without_llm():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    dims = score_dimensions(raw)
    panel = generate_panel(dims, raw)
    assert len(panel["investors"]) == 66
    assert len(panel["school_scores"]) == 9
    assert panel["panel_consensus"] is not None
    assert dims["fundamental_score"] > 0
    names = [i["name"] for i in panel["investors"]]
    assert "巴菲特" in names
    assert "Serenity" in names


def test_score_from_project_cache(tmp_path):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    write_raw_data(raw, collected_dir=tmp_path)
    scored = score_stock_from_cache("600029.SH", collected_dir=tmp_path)
    assert "panel" in scored
    assert (tmp_path / "600029.SH" / "panel.json").exists()
    payload = run_book_judges(
        {"holdings": [{"name": "南方航空", "ticker": "600029.SH", "type": "股票"}]},
        only_name="南方航空",
        collected_dir=tmp_path,
    )
    assert payload["llm"] is False
    assert payload["stocks"][0]["name"] == "南方航空"
    assert payload["stocks"][0]["n_judges"] == 66
    text = json.dumps(payload, ensure_ascii=False)
    assert "600029" not in json.dumps(payload["stocks"][0]["schools"], ensure_ascii=False)


def test_assemble_raw_marks_no_llm():
    raw = assemble_raw(
        "600029.SH",
        "南方航空",
        basic={"name": "南方航空", "price": 5.0, "pe_ttm": -69.0},
        financials={"roe_history": [2.44], "revenue_history": [100, 110]},
        kline={"stage": "Stage 4 下跌", "ma_align": "非多头"},
    )
    assert raw["llm"] is False
    assert raw["name"] == "南方航空"
    assert "1_financials" in raw["dimensions"]


def test_collect_stock_raw_rejects_etf():
    try:
        collect_stock_raw("588730.SH", "科创人工智能ETF易方达", kind="etf")
        assert False, "should have raised"
    except ValueError as exc:
        assert "篮子" in str(exc)


def test_holdings_fundamentals_skips_etf(tmp_path):
    from portfolio.stock_raw import collect_holdings_fundamentals

    def fake(ticker, name, kind=None, ak_module=None, **kwargs):
        return assemble_raw(
            ticker,
            name,
            basic={"name": name, "price": 5.0},
            financials={"roe_history": [2.4], "revenue_history": [1, 2]},
            kline={"stage": "Stage 4 下跌"},
        )

    book = {
        "holdings": [
            {"name": "科创人工智能ETF易方达", "ticker": "588730.SH", "type": "场内基金"},
            {"name": "南方航空", "ticker": "600029.SH", "type": "股票"},
        ]
    }
    out = collect_holdings_fundamentals(
        book,
        collect_fn=fake,
        collected_dir=tmp_path,
    )
    assert out["llm"] is False
    assert out["skipped_etfs"][0]["name"] == "科创人工智能ETF易方达"
    assert out["stocks"][0]["name"] == "南方航空"
    assert (tmp_path / "600029.SH" / "raw_data.json").exists()
