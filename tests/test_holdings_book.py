from __future__ import annotations

import json
from pathlib import Path

import pytest

from portfolio.holdings_book import MINE, VIRTUAL, Holdings, open_holdings

REPO = Path(__file__).resolve().parents[1]


def test_open_holdings_picks_the_named_book():
    assert open_holdings(None) is MINE
    assert open_holdings("我的持仓") is MINE
    assert open_holdings("虚拟仓") is VIRTUAL
    assert MINE.folder == REPO / "data" / "我的持仓"
    assert VIRTUAL.folder == REPO / "data" / "虚拟仓"


def test_unknown_book_is_rejected():
    with pytest.raises(ValueError, match="没有这本账"):
        open_holdings("其他仓")


def test_two_books_keep_their_own_shares():
    mine_rows = {row["name"]: row for row in MINE.rows()}
    virtual_rows = {row["name"]: row for row in VIRTUAL.rows()}

    assert MINE.book()["account"] == "普通账户"
    assert MINE.cash_cny() == 43452.12
    assert mine_rows["南方航空"]["shares"] == 12500
    assert "holdings" not in MINE.book()
    assert VIRTUAL.book()["account_owner"] == "assistant"
    assert VIRTUAL.cash_cny() == 232117.91
    assert virtual_rows["南方航空"]["shares"] == 3800
    assert "纳斯达克ETF华安" not in virtual_rows
    assert "电力ETF博时" in mine_rows
    assert "电力ETF博时" not in virtual_rows
    assert all(row["record"] == "position" for row in MINE.rows())


def test_jsonl_rows_match_the_ledger_json():
    source = json.loads((REPO / "portfolio" / "holdings.json").read_text(encoding="utf-8"))
    virtual = json.loads((REPO / "portfolio" / "simulated" / "holdings.json").read_text(encoding="utf-8"))
    assert [row["name"] for row in MINE.rows()] == [row["name"] for row in source["holdings"]]
    assert [row["shares"] for row in VIRTUAL.rows()] == [row["shares"] for row in virtual["holdings"]]
    assert MINE.book()["as_of_date"] == source["as_of_date"]
    assert VIRTUAL.book()["ledger_type"] == virtual["ledger_type"]


def test_dump_then_load_roundtrip(tmp_path: Path):
    book = Holdings("临时仓", root=tmp_path)
    records = [
        {"record": "book", "cash": {"account_cash_cny": 1.5}},
        {"record": "position", "name": "南方航空", "shares": 100},
    ]
    book.dump(records)
    assert book.load() == records
    assert (tmp_path / "临时仓" / "holdings.jsonl").is_file()


def test_book_requires_exactly_one_header(tmp_path: Path):
    book = Holdings("坏账", root=tmp_path)
    book.dump([{"record": "position", "name": "南方航空"}])
    with pytest.raises(ValueError, match="应有且只有一行账本头"):
        book.book()
