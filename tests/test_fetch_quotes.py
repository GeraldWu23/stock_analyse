"""fetch_quotes.py 的离线解析测试 (不依赖网络)。"""

from __future__ import annotations

import pytest

import fetch_quotes as fq


def _tencent_line(prefix: str, fields: dict[int, str], n: int = 40) -> str:
    arr = ["0"] * n
    for i, v in fields.items():
        arr[i] = v
    return f'v_{prefix}="{"~".join(arr)}";'


def _sina_line(prefix: str, values: list[str]) -> str:
    return f'var hq_str_{prefix}="{",".join(values)}";'


def test_parse_tencent_a_share_volume_in_lots_converted_to_shares():
    line = _tencent_line(
        "sh600029",
        {
            1: "南方航空",
            2: "600029",
            3: "5.18",
            4: "5.10",
            5: "5.14",
            6: "851376",  # 手
            30: "20260730151908",
            31: "0.08",
            33: "5.23",
            34: "5.13",
        },
    )
    q = fq._parse_tencent("sh600029", line)
    assert q is not None
    assert q.name == "南方航空"
    assert q.price == pytest.approx(5.18)
    assert q.prev_close == pytest.approx(5.10)
    assert q.change == pytest.approx(0.08)
    assert q.change_percent == pytest.approx(0.08 / 5.10 * 100)
    assert q.volume == pytest.approx(851376 * 100)  # 手 -> 股
    assert q.time == "2026-07-30 15:19:08"
    assert q.source == "腾讯"


def test_parse_tencent_hk_volume_not_scaled():
    line = _tencent_line(
        "hk01972",
        {
            1: "太古地产",
            2: "01972",
            3: "24.16",
            4: "23.76",
            5: "23.76",
            6: "2006033",
            30: "2026/07/30 15:03:39",
            31: "0.40",
            33: "24.24",
            34: "23.56",
        },
    )
    q = fq._parse_tencent("hk01972", line)
    assert q is not None
    assert q.name == "太古地产"
    assert q.price == pytest.approx(24.16)
    assert q.volume == pytest.approx(2006033)  # 港股不换算
    assert q.source == "腾讯"


def test_parse_sina_a_share():
    values = ["南方航空", "5.140", "5.100", "5.180", "5.230", "5.130",
              "5.180", "5.190", "85137593", "441896497.000"]
    values += ["0"] * 20
    values += ["2026-07-30", "15:19:12"]
    q = fq._parse_sina("sh600029", _sina_line("sh600029", values))
    assert q is not None
    assert q.name == "南方航空"
    assert q.price == pytest.approx(5.180)
    assert q.prev_close == pytest.approx(5.100)
    assert q.volume == pytest.approx(85137593)
    assert q.source == "新浪"


def test_parse_sina_hk():
    values = ["SWIREPROPERTIES", "太古地产", "23.760", "23.760", "24.240",
              "23.560", "24.120", "0.360", "1.515", "24.10000", "24.12000",
              "44520563", "1857633", "0", "0", "0", "0", "2026/07/30", "14:55"]
    q = fq._parse_sina("hk01972", _sina_line("hk01972", values))
    assert q is not None
    assert q.name == "太古地产"
    assert q.price == pytest.approx(24.120)
    assert q.prev_close == pytest.approx(23.760)
    assert q.volume == pytest.approx(44520563)
    assert q.source == "新浪"


def test_default_watchlist_covers_requested_symbols():
    codes = {code for _, code in fq.WATCHLIST}
    assert {"sh600029", "hk01972", "hk03986", "sh561700", "sh561780"} <= codes


def test_render_table_has_headers():
    line = _tencent_line(
        "sh600029",
        {1: "南方航空", 2: "600029", 3: "5.18", 4: "5.10", 5: "5.14",
         6: "1000", 30: "20260730151908", 31: "0.08", 33: "5.2", 34: "5.1"},
    )
    q = fq._parse_tencent("sh600029", line)
    table = fq.render_table([fq._row(q)])
    assert "来源" in table and "涨跌幅" in table and "sh600029" in table
