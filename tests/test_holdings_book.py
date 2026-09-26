from __future__ import annotations

import json
from pathlib import Path

import pytest

from portfolio.collector import SIMULATED_HOLDINGS_JSON, load_holdings
from portfolio.holdings_book import REAL, SIMULATED, Holdings, open_holdings


def test_open_holdings_picks_the_named_book():
    assert open_holdings(None) is REAL
    assert open_holdings("real") is REAL
    assert open_holdings("我的持仓") is REAL
    assert open_holdings("simulated") is SIMULATED
    assert open_holdings("你的持仓") is SIMULATED


def test_unknown_book_is_rejected():
    with pytest.raises(ValueError, match="没有这本账"):
        open_holdings("其他仓")


def test_real_and_simulated_jsonl_keep_their_own_shares():
    real_rows = {row["name"]: row for row in REAL.rows()}
    simulated_rows = {row["name"]: row for row in SIMULATED.rows()}

    assert REAL.book()["account"] == "普通账户"
    assert REAL.cash_cny() == 43452.12
    assert real_rows["南方航空"]["shares"] == 12500
    assert "holdings" not in REAL.book()
    assert SIMULATED.book()["account_owner"] == "assistant"
    assert SIMULATED.cash_cny() == 232117.91
    assert simulated_rows["南方航空"]["shares"] == 3800
    assert "纳斯达克ETF华安" not in simulated_rows
    assert "电力ETF博时" in real_rows
    assert "电力ETF博时" not in simulated_rows
    assert all(row["record"] == "position" for row in REAL.rows())


def test_jsonl_rows_match_the_source_json():
    source = load_holdings()
    simulated = load_holdings(SIMULATED_HOLDINGS_JSON)
    assert [row["name"] for row in REAL.rows()] == [row["name"] for row in source["holdings"]]
    assert [row["shares"] for row in SIMULATED.rows()] == [row["shares"] for row in simulated["holdings"]]
    assert REAL.book()["as_of_date"] == source["as_of_date"]
    assert SIMULATED.book()["ledger_type"] == simulated["ledger_type"]


def test_book_requires_exactly_one_header(tmp_path: Path):
    path = tmp_path / "holdings.jsonl"
    path.write_text(json.dumps({"record": "position", "name": "南方航空"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="应有且只有一行账本头"):
        Holdings(path).book()
