from __future__ import annotations

import json
from pathlib import Path

from portfolio.info_day import REQUIRED, field, load, missing_of, save, write_collected_day

REPO = Path(__file__).resolve().parents[1]


def test_required_lists_stay_split_by_kind():
    assert REQUIRED["stock"] == ("last_price", "prev_close", "financials", "kline")
    assert "iopv" not in REQUIRED["stock"]
    assert REQUIRED["etf"][-1] == "holdings_report_date"


def test_zero_is_present_and_empty_basket_is_missing():
    fields = {
        "last_price": field(1.0, "2026-09-29 16:14:57", "test"),
        "prev_close": field(1.0, "2026-09-29 16:14:57", "test"),
        "iopv": field(1.0, "2026-09-29 16:14:57", "test"),
        "premium_pct": field(0.0, "2026-09-29 16:14:57", "test"),
        "top_holdings": field([], None, "test"),
        "holdings_report_date": field(None, None, "test"),
    }
    assert missing_of("etf", fields) == ["top_holdings", "holdings_report_date"]


def test_save_roundtrip_marks_stock_not_ready_without_financials(tmp_path):
    fields = {
        "last_price": field(4.84, "2026-09-29 16:14:44", "test"),
        "prev_close": field(4.82, "2026-09-29 16:14:44", "test"),
        "financials": field(None, "2026-09-29T08:25:27+00:00", "test", "没有财报"),
        "kline": field({"kline_count": 1}, "2026-09-29", "test"),
    }
    save("2026-09-29", "01972.HK", "太古地产", "stock", fields, tmp_path)
    record = load("2026-09-29", "01972.HK", tmp_path)
    assert record["ready"] is False
    assert record["missing"] == ["financials"]
    assert record["fields"]["last_price"]["value"] == 4.84


def test_virtual_book_day_matches_the_collected_snapshot():
    day = REPO / "data" / "info" / "2026-09-29"
    south = json.loads((day / "600029.SH.json").read_text(encoding="utf-8"))
    swire = json.loads((day / "01972.HK.json").read_text(encoding="utf-8"))
    gold = json.loads((day / "159934.SZ.json").read_text(encoding="utf-8"))
    chip = json.loads((day / "588730.SH.json").read_text(encoding="utf-8"))

    assert south["ready"] is True
    assert south["fields"]["last_price"]["value"] == 4.84
    assert south["fields"]["prev_close"]["value"] == 4.82
    assert south["fields"]["financials"]["value"]["financial_years"][-1] == "2025"
    assert south["fields"]["kline"]["as_of"] == "2026-09-28"

    assert swire["ready"] is False
    assert swire["missing"] == ["financials"]
    assert swire["fields"]["kline"]["as_of"] == "2026-09-29"

    assert gold["ready"] is False
    assert gold["missing"] == ["iopv", "premium_pct", "top_holdings", "holdings_report_date"]
    assert chip["ready"] is False
    assert chip["missing"] == ["iopv", "premium_pct", "holdings_report_date"]
    assert chip["fields"]["top_holdings"]["value"][0]["name"] == "芯原股份"
    assert "shares" not in chip


def test_writer_uses_only_collected_files(tmp_path):
    snapshot = REPO / "portfolio" / "collected" / "latest.json"
    if not snapshot.exists():
        return
    written = write_collected_day(
        REPO / "portfolio" / "collected" / "latest.json",
        REPO / "portfolio" / "simulated" / "holdings.json",
        REPO / "portfolio" / "collected",
        "2026-09-29",
        tmp_path,
    )
    by_name = {record["name"]: record for record in written}
    assert by_name["长鑫科技"]["ready"] is True
    assert by_name["长鑫科技"]["fields"]["last_price"]["value"] == 55.55
    assert by_name["绿色电力ETF富国"]["fields"]["top_holdings"]["value"][0]["weight_pct"] == 10.73
    assert by_name["太古地产"]["fields"]["financials"]["value"] is None
